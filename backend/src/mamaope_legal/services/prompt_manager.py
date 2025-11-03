"""
Prompt Manager Module for mamaope_legal AI CDSS.

This module handles loading and managing prompt templates from JSON files.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Types of queries that can be processed."""
    DIFFERENTIAL_DIAGNOSIS = "differential_diagnosis"
    DRUG_INFORMATION = "drug_information"
    CLINICAL_GUIDANCE = "clinical_guidance"
    GENERAL_QUERY = "general_query"


@dataclass
class PromptConfig:
    """Configuration for a prompt template."""
    template: str
    variables: List[str]
    validation_rules: Dict[str, any]
    max_length: int
    description: str
    version: str


class PromptManager:
    """Manages prompt templates and their configurations."""
    
    def __init__(self, config_dir: Optional[Path] = None):
        """Initialize the prompt manager."""
        self.config_dir = self._find_config_directory(config_dir)
        self.prompts: Dict[QueryType, PromptConfig] = {}
        self._load_prompts()
    
    def _find_config_directory(self, config_dir: Optional[Path]) -> Path:
        """Find the configuration directory."""
        if config_dir:
            return config_dir
        
        # Try multiple possible paths
        possible_paths = [
            Path("/app/config"),  # Docker container path
            Path(__file__).parent.parent.parent.parent / "config",  # Relative from this file
            Path("backend/config"),  # Relative from project root
            Path("./config"),  # Current directory
        ]
        
        for path in possible_paths:
            logger.info(f"Checking config path: {path}")
            if path.exists() and (path / "prompts").exists():
                logger.info(f"Found config directory at: {path}")
                return path
        
        logger.warning("Could not find config directory, using fallback")
        return Path("/app/config")  # Fallback
    
    def _load_prompts(self) -> None:
        """Load all prompt templates from JSON files."""
        prompts_dir = self.config_dir / "prompts"
        
        logger.info(f"Loading prompts from: {prompts_dir}")
        
        if not prompts_dir.exists():
            logger.warning(f"Prompts directory not found: {prompts_dir}")
            self._load_default_prompts()
            return
        
        # Load each prompt file
        prompt_files = {
            "differential_diagnosis.json": QueryType.DIFFERENTIAL_DIAGNOSIS,
            "drug_information.json": QueryType.DRUG_INFORMATION,
            "clinical_guidance.json": QueryType.CLINICAL_GUIDANCE
        }
        
        for filename, query_type in prompt_files.items():
            file_path = prompts_dir / filename
            
            logger.info(f"Loading prompt file: {file_path}")
            
            if not file_path.exists():
                logger.warning(f"Prompt file not found: {file_path}")
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                prompt_config = PromptConfig(
                    template=data.get("template", ""),
                    variables=data.get("variables", []),
                    validation_rules=data.get("validation_rules", {}),
                    max_length=data.get("max_length", 8000),
                    description=data.get("description", ""),
                    version=data.get("version", "1.0.0")
                )
                
                self.prompts[query_type] = prompt_config
                logger.info(f"✅ Loaded prompt [{query_type.value}] v{prompt_config.version}: {len(prompt_config.template)} chars")
                
            except Exception as e:
                logger.error(f"Failed to load prompt {filename}: {e}")
        
        # Add default prompts for missing types
        self._add_default_prompts()
        
        logger.info(f"Total prompts loaded: {len(self.prompts)}")
    
    def _add_default_prompts(self) -> None:
        """Add default prompts for missing query types."""
        if QueryType.GENERAL_QUERY not in self.prompts:
            self.prompts[QueryType.GENERAL_QUERY] = PromptConfig(
                template="You are a helpful medical AI assistant. Please provide accurate and helpful information based on the user's query.",
                variables=["query"],
                validation_rules={},
                max_length=2000,
                description="Default general query prompt",
                version="1.0.0"
            )
    
    def _load_default_prompts(self) -> None:
        """Load default unified prompt when JSON files are not available."""
        logger.info("Loading unified GENERAL_PROMPT for all query types")

        # Unified prompt for all query types
        unified_prompt = """
YOU ARE **HealthNavy**, A CLINICAL DECISION SUPPORT SYSTEM (CDSS) BUILT USING RETRIEVAL-AUGMENTED GENERATION (RAG) TECHNOLOGY. YOU POSSESS ACCESS TO A CURATED KNOWLEDGE BASE CONSISTING OF CLINICAL TEXTS, GUIDELINES, RESEARCH ARTICLES, AND DRUG MANUALS STORED IN A VECTOR DATABASE. YOUR PRIMARY FUNCTION IS TO PROVIDE ACCURATE, EVIDENCE-BASED MEDICAL ANSWERS DRAWN FROM RETRIEVED CONTEXT. WHEN INFORMATION IS MISSING OR INCOMPLETE, YOU MUST FALL BACK TO YOUR INTERNAL GENERAL MEDICAL KNOWLEDGE AND PROVIDE VALID REFERENCES.

---

### OBJECTIVE

TO DELIVER AUTHORITATIVE, EVIDENCE-BASED, AND PROFESSIONALLY FORMATTED CLINICAL RESPONSES COVERING:
- DIFFERENTIAL DIAGNOSES
- DRUG INTERACTIONS AND CONTRAINDICATIONS
- GENERAL MEDICAL AND PATHOPHYSIOLOGICAL QUERIES
- DIAGNOSTIC ALGORITHMS AND MANAGEMENT PLANS
- MULTIPLE-CHOICE CLINICAL QUESTIONS (MCQs) WITH EXPLANATIONS

---

### EXECUTION RULES

1. **PRIMARY KNOWLEDGE SOURCE**
   - ALWAYS PRIORITIZE INFORMATION RETRIEVED FROM `{context}` (REFERENCE TEXTS).
   - WHEN REFERENCE TEXT DOES NOT ADDRESS THE QUESTION SUFFICIENTLY, FALL BACK TO MODEL KNOWLEDGE AND GIVE REFERENCES`.

2. **CITATIONS**
   - Cite as `[Source: document_name or filename.pdf]`.

3. **AGE-SPECIFIC CONTEXT**
   - IF PATIENT AGE < 18 → use pediatric references first.
   - IF PATIENT AGE ≥ 18 → use adult guidelines and avoid pediatric sources.

4. **MCQ / OBJECTIVE QUESTION HANDLING**
   - IF THE QUERY CONTAINS MULTIPLE CHOICE OPTIONS (A, B, C, D, etc.):
     - SELECT THE CORRECT ANSWER BASED ON EVIDENCE AND CONTEXT.
     - EXPLAIN WHY IT IS CORRECT USING CLINICAL REASONING.
     - BRIEFLY EXPLAIN WHY OTHER OPTIONS ARE INCORRECT.

   **REQUIRED FORMAT:**
Correct Answer: (X) [Option text]
Explanation: [Reasoning with citations]
Why other options are wrong:

(Y) [Brief reason]

(Z) [Brief reason]

5. **CLINICAL / OPEN QUESTIONS HANDLING**
- PROVIDE A STRUCTURED RESPONSE USING THE FOLLOWING FORMAT:

## 🏥 Summary

[Concise context or definition with citation]

## 🔍 Differential Diagnosis (if applicable)

[Condition 1] — [Rationale + citation]

[Condition 2] — [Rationale + citation]

## 🔬 Investigations / Workup

[Test 1] — [Purpose + citation]

[Test 2] — [Purpose + citation]

## 💊 Management

[First-line approach + citation]

[Alternative options + citation]

## 📚 References

[List all sources used]

6. **FALLBACK BEHAVIOR**
- IF RETRIEVED KNOWLEDGE BASE `{context}` IS EMPTY OR IRRELEVANT:
  - USE INTERNAL MODEL KNOWLEDGE (e.g., Gemini).
  - ALWAYS INCLUDE RELEVANT REFERENCES (e.g., UpToDate, PubMed, or standard clinical guidelines).

7. **STYLE AND LENGTH**
- BE PROFESSIONAL, OBJECTIVE, AND CONCISE (<500 WORDS).
- USE BULLET POINTS, HEADINGS, AND BOLD TEXT FOR CLARITY.

8. **CRITICAL FORMATTING RULES - MUST FOLLOW:**
- ALWAYS put a BLANK LINE (press ENTER twice) after each **HEADING**
- ALWAYS put a BLANK LINE before starting a new **HEADING**
- Each list item (1. 2. 3. or -) must be on its OWN separate line
- NEVER write content on the same line as the heading
- Pattern: **HEADING**[ENTER][ENTER]Content starts here[ENTER][ENTER]**NEXT HEADING**


### CHAIN OF THOUGHTS (MANDATORY INTERNAL REASONING)

FOLLOW THIS STEPWISE APPROACH INTERNALLY BEFORE PRODUCING ANY OUTPUT:

<chain_of_thoughs_rules>
1. **UNDERSTAND:** IDENTIFY THE CORE QUESTION OR TASK (clinical reasoning, MCQ, diagnosis, etc.).
2. **BASICS:** RECALL FUNDAMENTAL MEDICAL PRINCIPLES RELATED TO THE QUERY.
3. **BREAK DOWN:** DECOMPOSE INTO RELEVANT SUBCOMPONENTS (e.g., differential diagnosis, investigations, treatment).
4. **ANALYZE:** CROSS-REFERENCE RETRIEVED CONTEXT FROM `{context}` WITH KNOWN MEDICAL FACTS.
5. **BUILD:** SYNTHESIZE FINDINGS INTO A STRUCTURED, LOGICAL ANSWER.
6. **EDGE CASES:** CONSIDER EXCEPTIONS, AGE VARIATIONS, OR CONTRAINDICATIONS.
7. **FINAL ANSWER:** PRESENT THE INFORMATION PROFESSIONALLY WITH SOURCES AND CLEAR FORMATTING.
</chain_of_thoughs_rules>


### WHAT NOT TO DO

- NEVER PROVIDE UNSUPPORTED OR UNCITED MEDICAL CLAIMS.
- NEVER INVENT REFERENCES OR SOURCES.
- NEVER GUESS — IF DATA IS INSUFFICIENT, FALL BACK TO MODEL KNOWLEDGE.
- NEVER MIX PEDIATRIC AND ADULT GUIDELINES INAPPROPRIATELY.
- NEVER GIVE AMBIGUOUS OR UNSTRUCTURED OUTPUTS.
- NEVER OMIT "REFERENCES" SECTION FROM THE RESPONSE.

**AVAILABLE SOURCES:** {sources}
**REFERENCE TEXT (RAG CONTEXT):** {context}
"""

        self.prompts = {
            QueryType.DIFFERENTIAL_DIAGNOSIS: PromptConfig(
                template=unified_prompt,
                variables=["patient_data", "chat_history", "context", "sources"],
                validation_rules={
                    "max_patient_data_length": 10000,
                    "max_chat_history_length": 50000,
                    "require_critical_assessment": True,
                    "require_structured_response": True,
                    "output_format": "structured_markdown"
                },
                max_length=12000,
                description="Unified HealthNavy prompt for all clinical queries",
                version="1.0.0"
            ),
            QueryType.DRUG_INFORMATION: PromptConfig(
                template=unified_prompt,
                variables=["patient_data", "context", "sources", "chat_history"],
                validation_rules={
                    "max_patient_data_length": 10000,
                    "max_chat_history_length": 50000,
                    "require_drug_specific_info": True,
                    "output_format": "structured_markdown"
                },
                max_length=10000,
                description="Unified HealthNavy prompt for drug information queries",
                version="1.0.0"
            ),
            QueryType.CLINICAL_GUIDANCE: PromptConfig(
                template=unified_prompt,
                variables=["patient_data", "context", "sources", "chat_history"],
                validation_rules={
                    "max_patient_data_length": 10000,
                    "max_chat_history_length": 50000,
                    "require_evidence_based_guidance": True,
                    "output_format": "structured_markdown"
                },
                max_length=10000,
                description="Unified HealthNavy prompt for clinical guidance queries",
                version="1.0.0"
            ),
            QueryType.GENERAL_QUERY: PromptConfig(
                template=unified_prompt,
                variables=["query", "context", "sources"],
                validation_rules={
                    "max_query_length": 2000,
                    "require_references": True,
                    "output_format": "structured_markdown"
                },
                max_length=8000,
                description="Unified HealthNavy prompt for general medical queries",
                version="1.0.0"
            )
        }
    
    def get_prompt(self, query_type: QueryType) -> Optional[PromptConfig]:
        """Get a prompt configuration for a specific query type."""
        return self.prompts.get(query_type)
    
    def get_all_prompts(self) -> Dict[QueryType, PromptConfig]:
        """Get all loaded prompt configurations."""
        return self.prompts.copy()
    
    def reload_prompts(self) -> None:
        """Reload all prompts from JSON files."""
        logger.info("Reloading prompts...")
        self.prompts.clear()
        self._load_prompts()
    
    def get_prompt_template(self, query_type: QueryType) -> str:
        """Get the template string for a specific query type."""
        prompt_config = self.get_prompt(query_type)
        return prompt_config.template if prompt_config else ""
    
    def get_prompt_variables(self, query_type: QueryType) -> List[str]:
        """Get the variables for a specific query type."""
        prompt_config = self.get_prompt(query_type)
        return prompt_config.variables if prompt_config else []


# Global prompt manager instance
_prompt_manager: Optional[PromptManager] = None


def get_prompt_manager() -> PromptManager:
    """Get the global prompt manager instance."""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager


def reload_prompts() -> None:
    """Reload all prompts."""
    get_prompt_manager().reload_prompts()









