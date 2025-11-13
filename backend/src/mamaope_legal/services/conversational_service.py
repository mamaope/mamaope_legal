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
from datetime import datetime, timedelta

from mamaope_legal.core.constants import (
    MODEL_NAME, PROMPT_TOKEN_LIMIT, CACHE_TTL_MINUTES, MAX_CACHE_SIZE,
    DEFAULT_CONTEXT_MAX_CHARS, BALANCED_CONTEXT_MAX_CHARS,
    MAX_RETRY_ATTEMPTS, RETRY_MULTIPLIER, RETRY_MIN_WAIT, RETRY_MAX_WAIT,
    OPTIMIZED_PROMPT, PROMPT
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)
load_dotenv()

# Simple in-memory cache for responses
RESPONSE_CACHE: Dict[str, Tuple[str, datetime]] = {}

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
    full_response_text = ""  
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
        
        context, actual_sources = search_all_collections(query, case_data, k=3)
        optimized_context = optimize_context_for_llm(context, max_chunks=3)
        logger.info(f"Context optimized: {len(context)} -> {len(optimized_context)} chars")

        sources_text = ", ".join(actual_sources) if actual_sources else "No sources available"
        
        full_prompt = OPTIMIZED_PROMPT.format(sources=sources_text, context=optimized_context)
        user_context_block = f"""
            ### USER QUESTION:
            {query}

            ### CONTEXT (if provided):
            {case_data or 'No additional context provided.'}

            ### PREVIOUS CONVERSATION SUMMARY:
            {chat_history or 'No previous conversation.'}
            """
        full_prompt += f"\n\n{user_context_block.strip()}"

        logger.info(f"--- PROMPT SENT TO API (first 500 chars) ---\n{full_prompt[:500]}\n...")

        # Get the GenAI client
        client = get_genai_client()

        # Generate the response
        llm_start = time.time()
        logger.info("Generating response from model...")

        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=[{"role": "user", "parts": [{"text": full_prompt}]}],
                config={
                    "temperature": 0.2,
                    "max_output_tokens": 2000,
                    "top_p": 0.95,
                    "top_k": 20,
                    "candidate_count": 1
                }
            )
        except Exception as e:
            logger.error(f"Failed to generate content: {e}", exc_info=True)
            return f"⚠️ Failed to generate content: {str(e)}", actual_sources, "error"

        # Process model output
        try:
            if response and hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]

                if not (hasattr(candidate, 'content') and hasattr(candidate.content, 'parts') and candidate.content.parts):
                    logger.error("Empty or blocked response (no content parts).")
                    return "⚠️ The content was blocked. Please rephrase your question.", actual_sources, "error"

                full_response_text = candidate.content.parts[0].text.strip()
                finish_reason = getattr(candidate, 'finish_reason', 'UNKNOWN')
                logger.info(f"Response finish reason: {finish_reason}")

                if finish_reason == 'MAX_TOKENS':
                    full_response_text += "\n\n**[Note: The response was truncated due to token limits. Try asking a more specific question.]**"
                elif finish_reason in ['SAFETY', 'RECITATION']:
                    full_response_text += "\n\n**[Note: Some content was filtered for safety or duplication.]**"

            else:
                logger.error("Model returned no candidates or empty response.")
                return "⚠️ No valid response was generated. Please try again.", actual_sources, "error"

        except Exception as e:
            logger.error(f"Error processing model output: {e}", exc_info=True)
            return f"An error occurred while processing the response: {str(e)}", actual_sources, "error"

        # Cache the response for future use
        if cache_key and full_response_text:
            _cache_response(cache_key, full_response_text)

        logger.info(f"✅ Response generated successfully in {time.time() - llm_start:.3f}s")
        logger.info(f"Full pipeline completed in {time.time() - total_start_time:.3f}s")

        return full_response_text, actual_sources, "success"

    except Exception as e:
        logger.error(f"FATAL error in generate_response: {e}", exc_info=True)
        return f"🚨 Unexpected error: {str(e)}", actual_sources, "error"
