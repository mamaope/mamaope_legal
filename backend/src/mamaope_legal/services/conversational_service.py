"""
Enhanced conversational service for mamaope_legal AI.

This module provides secure AI conversation handling with proper validation,
audit logging, and data protection following legal consultation standards.
"""

import os
import time
import logging
import asyncio
import hashlib
from fastapi import HTTPException
from mamaope_legal.services.genai_client import get_genai_client
from mamaope_legal.services.vectorstore_manager import search_all_collections, enrich_retrieval_results, build_context
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_not_exception_type
from dotenv import load_dotenv
from typing import Dict, Tuple, List
from google.api_core import exceptions
from enum import Enum
# import concurrent.futures  # Not used in this implementation
from datetime import datetime, timedelta

from mamaope_legal.core.constants import (
    MODEL_NAME, PROMPT_TOKEN_LIMIT, CACHE_TTL_MINUTES, MAX_CACHE_SIZE,
    DEFAULT_CONTEXT_MAX_CHARS, BALANCED_CONTEXT_MAX_CHARS,
    MAX_RETRY_ATTEMPTS, RETRY_MULTIPLIER, RETRY_MIN_WAIT, RETRY_MAX_WAIT
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)
load_dotenv()

# GenAI client will be initialized at startup

# Simple in-memory cache for responses
RESPONSE_CACHE: Dict[str, Tuple[str, datetime]] = {}
    
PROMPT = """
YOU ARE **Mamaope Legal**, a professional AI legal assistant specializing in Ugandan and East African law.

---

### OBJECTIVE
Provide clear, factual, and contextually rich legal information grounded **only** in the EVIDENCE BASE below.

Your responses should sound like a well-trained legal analyst explaining a law to either a lawyer or an informed citizen — accurate, explanatory, but never opinionated.

---

### CORE DIRECTIVES

1.  **ABSOLUTE GROUNDING (CRITICAL):**
    - You **MUST** base your entire response *only* on the information inside the "EVIDENCE BASE" (the {context} provided below).
    - **DO NOT** use any outside knowledge, and **DO NOT** invent information.
    - If the answer is not in the EVIDENCE BASE, you **MUST** state: "I could not find specific information about the topic."

2.  **LEGAL CITATION FORMAT (CRITICAL):**
    - Always include citations exactly as they appear in the evidence, e.g.:  
       “According to **Article 80(1)** of the Constitution of Uganda.”
    - You may refer to articles, sections, or chapters naturally.
    - List references at the end of your response under a heading **References:**
    - **DO NOT** use phrases like "According to the context..." or "The provided text...".
    - **Correct Example:** "The right to a fair hearing is guaranteed [Source: Constitution of the Republic of Uganda, Article 9, Section 2]."
    - **Incorrect Example:** "The context states that the right to a fair hearing is guaranteed."

3.  **PERSONA & TONE:**
    - You are a professional, objective, and neutral legal information provider.
    - Your tone must be formal and direct.
    - **ONLY** provide legal *information* (e.g., "Article X states that...").

4.  **FORMATTING:**
    - Use headings, bold text, and bullet points for clarity.
    - Place a blank line before and after all headings.

---

### CRITICAL PROHIBITIONS
-   **NEVER** provide an opinion.
-   **NEVER** invent an article or section number.

---

**AVAILABLE SOURCES:** {sources}
**EVIDENCE BASE:**
{context}
"""

# ### RESPONSE STYLE & LEGAL CITATION RULES

# 1. **FORMATTING & CONCISENESS RULES
#    - **BE CONCISE:** Extract the most critical points from the EVIDENCE BASE and focus on delivering a direct answer to the user's query. **Do not elaborate or summarize** beyond what is necessary to answer the question clearly.
#    - **USE HEADINGS:** Structure the answer using clear, bolded headings (e.g., **1. Separation of Powers**) for readability.
#    - **USE LISTS:** Use bullet points or numbered lists (with emojis if appropriate) to present information concisely.

# 2. **GROUNDING (MANDATORY)**
#    - You must base every statement strictly on the information within the EVIDENCE BASE below.
#    - If the evidence does not cover the question, say:  
#      “I could not find specific information about the topic.”

# 3. **CITATION FORMAT**
#    - Always include citations exactly as they appear in the evidence, e.g.:  
#      “According to **Article 80(1)** of the Constitution of Uganda.”
#    - You may refer to articles, sections, or chapters naturally, not mechanically.
#    - List references at the end of your response under a heading **References:**

# 4. **WRITING STYLE**
#    - Use formal yet readable English.
#    - Provide short contextual explanations (e.g., “Under Chapter Six on the Legislature...”).
#    - Avoid bullet lists unless summarizing several requirements.
#    - Begin with a concise overview sentence, then elaborate with article references.

# ---

# **AVAILABLE SOURCES:** {sources}

# **EVIDENCE BASE:**
# {context}
# """

def optimize_context_for_llm(chunks: list[dict], max_chunks: int = 3) -> str:
    """
    Take only the top most relevant chunks to include in the LLM prompt.
    """
    top_chunks = chunks[:max_chunks] 
    context_parts = []
    for chunk in top_chunks:
        file_name = os.path.basename(chunk['file_path'])
        pdf_page = chunk.get("display_page_number", "?")
        context_parts.append(f"[SOURCE: {file_name} (Page: {pdf_page})]\n{chunk['content'].strip()}")
    return "\n\n".join(context_parts)

def _generate_cache_key(query: str, case_data: str) -> str:
    """Generate a cache key from query and case data."""
    combined = f"{query}|{case_data}".lower().strip()
    return hashlib.md5(combined.encode()).hexdigest()

def _get_cached_response(cache_key: str) -> str:
    """Get cached response if available and not expired."""
    if cache_key in RESPONSE_CACHE:
        response, timestamp = RESPONSE_CACHE[cache_key]
        if datetime.now() - timestamp < timedelta(minutes=CACHE_TTL_MINUTES):
            logger.info(f"Cache HIT - Returning cached response (age: {(datetime.now() - timestamp).seconds}s)")
            return response
        else:
            # Expired, remove from cache
            del RESPONSE_CACHE[cache_key]
            logger.info("Cache EXPIRED - Will generate new response")
    return None

def _cache_response(cache_key: str, response: str):
    """Cache a response with timestamp."""
    RESPONSE_CACHE[cache_key] = (response, datetime.now())
    logger.info(f"Response cached (cache size: {len(RESPONSE_CACHE)} entries)")
    
    # Cleanup old entries if cache gets too large
    if len(RESPONSE_CACHE) > MAX_CACHE_SIZE:
        # Remove oldest entries
        sorted_keys = sorted(RESPONSE_CACHE.keys(), key=lambda k: RESPONSE_CACHE[k][1])
        for key in sorted_keys[:20]:  # Remove 20 oldest
            del RESPONSE_CACHE[key]
        logger.info(f"🧹 Cache cleanup - Removed 20 oldest entries")

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    reraise=True,
    retry=retry_if_not_exception_type(HTTPException)
)
async def generate_response(query: str, chat_history: str, case_data: str) -> Tuple[str, List[str], str]:
    
    total_start_time = time.time()
    full_response_text = ""  # Initialize at outer scope
    actual_sources = []
    
    try:
        # Check cache first (skip for queries with chat history)
        cache_key = None
        if not chat_history or chat_history == "No previous conversation":
            cache_key = _generate_cache_key(query, case_data)
            cached_response = _get_cached_response(cache_key)
            if cached_response:
                logger.info(f"⚡ Cached response returned in {time.time() - total_start_time:.3f}s")
                return cached_response, [], "success"
        
        # Retrieve and Optimize Context
        context, actual_sources = search_all_collections(query, case_data, k=6)
        optimized_context = optimize_context_for_llm(context, max_chunks=3)
        logger.info(f"Context optimized: {len(context)} -> {len(optimized_context)} chars")

        sources_text = ", ".join(actual_sources) if actual_sources else "No sources available"
        
        prompt_template = PROMPT

        full_prompt = prompt_template.format(sources=sources_text, context=optimized_context)
        full_prompt += f"\n\nQUERY: {query}\n\nCLIENT INFO: {case_data}\n\nPREVIOUS CONVERSATION: {chat_history or 'No previous conversation'}"
        
        logger.info(f"--- PROMPT SENT TO API (first 500 chars) ---\n{full_prompt[:500]}\n...")

        # Step 4: Generate Content 
        llm_start = time.time()
        logger.info(f"Generating response...")

        # Get the GenAI client
        client = get_genai_client()

        try:
            # Count tokens using the new API
            token_count_response = client.models.count_tokens(
                model=MODEL_NAME,
                contents=[{"role": "user", "parts": [{"text": full_prompt}]}]
            )
            prompt_token_count = token_count_response.total_tokens
            logger.info(f"Calculated input prompt token count: {prompt_token_count}")
            if prompt_token_count > PROMPT_TOKEN_LIMIT:
                error_msg = f"Error: Input prompt exceeds token limit ({prompt_token_count}/{PROMPT_TOKEN_LIMIT})."
                logger.error(error_msg)
                return error_msg, actual_sources, "error"
        except Exception as e:
            # Do not fail hard if token counting endpoint is unavailable; proceed to generation
            logger.warning(f"Token count unavailable, proceeding without validation: {e}")

        logger.info("Generating response...")
        
        try:
            # Generate content using the new API
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=[{"role": "user", "parts": [{"text": full_prompt}]}],
                config={
                    "temperature": 0.2,
                    "max_output_tokens": 4000,
                    "top_p": 0.9,
                    "top_k": 40,
                    "candidate_count": 1
                }
            )
        except Exception as e:
            logger.error(f"Failed to generate content: {e}", exc_info=True)
            return f"Failed to start content generation: {str(e)}", actual_sources, "error"
        
        try:
            if response and hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                
                # check if content exists AT ALL. 
                if not (hasattr(candidate, 'content') and hasattr(candidate.content, 'parts') and candidate.content.parts):
                    logger.error("Response was empty or blocked. Candidate exists but has no content parts.")
                    return "Content was blocked. Please rephrase your legal query with more appropriate terminology.", actual_sources, "error"

                # Get the text part
                full_response_text = candidate.content.parts[0].text.strip()
                
                # Get the finish reason
                finish_reason = getattr(candidate, 'finish_reason', 'UNKNOWN')
                logger.info(f"Response finish reason: {finish_reason}")
                
                if finish_reason == 'MAX_TOKENS':
                    logger.warning(f"Response generation hit MAX_TOKENS limit. Response is TRUNCATED.")
                    # Append a clear warning to the user
                    full_response_text += "\n\n**[WARNING: The response was truncated because it exceeded the maximum output length. Please ask a more specific follow-up question if needed.]**"
                elif finish_reason == 'SAFETY':
                    logger.warning("Response generation was cut short due to SAFETY filters.")
                    full_response_text += "\n\n**[WARNING: The response was partially blocked by safety filters.]**"
                elif finish_reason == 'RECITATION':
                    logger.warning("Response generation was cut short due to RECITATION filters.")
                elif finish_reason == 'STOP':
                    logger.info(f"⚡ Response generated successfully in {time.time() - llm_start:.3f}s (Finish: STOP)")
                else:
                    logger.warning(f"Response finished with unhandled reason: {finish_reason}")

            else:
                logger.error("Response was empty or blocked by safety filters (no candidates returned)")
                return "Content was blocked. Please rephrase your legal query with more appropriate terminology.", actual_sources, "error"

        except Exception as e:
            logger.error(f"Error processing response: {e}", exc_info=True)
            return f"An error occurred: {str(e)}", actual_sources, "error"

        # Cache the complete response if applicable
        if cache_key and full_response_text:
            _cache_response(cache_key, full_response_text)
            
        logger.info(f"Total generation completed in {time.time() - llm_start:.3f}s")
        logger.info(f"Full pipeline completed in {time.time() - total_start_time:.3f}s")
        
        # Return the response with status
        return full_response_text, actual_sources,"success"

    except Exception as e:
        # Catch any other unexpected errors at the top level
        logger.error(f"FATAL error in generate_response: {e}", exc_info=True)
        error_message = f"An unexpected error occurred: {str(e)}"
        return error_message, actual_sources, "error"
