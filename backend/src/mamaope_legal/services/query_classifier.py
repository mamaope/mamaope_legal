"""
Query Classifier Module for mamaope_legal AI CDSS.

This module handles query classification and routing.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .prompt_manager import QueryType

logger = logging.getLogger(__name__)


@dataclass
class ClassificationRule:
    """Rule for classifying queries."""
    pattern: str
    query_type: QueryType
    confidence: float
    description: str


class QueryClassifier:
    """Classifies queries into different types."""
    
    def __init__(self):
        """Initialize the query classifier."""
        self.rules: List[ClassificationRule] = []
        self._load_classification_rules()
    
    def _load_classification_rules(self) -> None:
        """Load classification rules."""
        logger.info("Loading query classification rules...")
        
        # Default classification rules
        self.rules = [
            # Differential diagnosis patterns
            ClassificationRule(
                pattern=r"(differential diagnosis|what could this be|possible causes|diagnosis|symptoms suggest)",
                query_type=QueryType.DIFFERENTIAL_DIAGNOSIS,
                confidence=0.9,
                description="Differential diagnosis query"
            ),
            ClassificationRule(
                pattern=r"(patient presents with|history of|complaining of|chief complaint)",
                query_type=QueryType.DIFFERENTIAL_DIAGNOSIS,
                confidence=0.8,
                description="Clinical presentation query"
            ),
            ClassificationRule(
                pattern=r"(workup|investigation|tests needed|what to order)",
                query_type=QueryType.DIFFERENTIAL_DIAGNOSIS,
                confidence=0.7,
                description="Clinical workup query"
            ),
            
            # Drug information patterns
            ClassificationRule(
                pattern=r"(drug|medication|medicine|pharmaceutical|dosage|side effects|interactions)",
                query_type=QueryType.DRUG_INFORMATION,
                confidence=0.9,
                description="Drug information query"
            ),
            ClassificationRule(
                pattern=r"(contraindications|adverse effects|pharmacology|mechanism of action)",
                query_type=QueryType.DRUG_INFORMATION,
                confidence=0.8,
                description="Drug safety query"
            ),
            
            # Clinical guidance patterns
            ClassificationRule(
                pattern=r"(treatment|management|therapy|protocol|guideline|recommendation)",
                query_type=QueryType.CLINICAL_GUIDANCE,
                confidence=0.8,
                description="Clinical guidance query"
            ),
            ClassificationRule(
                pattern=r"(follow-up|monitoring|prognosis|outcome|next steps)",
                query_type=QueryType.CLINICAL_GUIDANCE,
                confidence=0.7,
                description="Clinical management query"
            ),
            
            # General query fallback
            ClassificationRule(
                pattern=r".*",
                query_type=QueryType.GENERAL_QUERY,
                confidence=0.1,
                description="General query fallback"
            )
        ]
        
        logger.info(f"Loaded {len(self.rules)} classification rules")
    
    def classify_query(self, query: str, patient_data: str = "") -> Tuple[QueryType, float]:
        """Classify a query into a specific type."""
        if not query:
            return QueryType.GENERAL_QUERY, 0.0
        
        # Combine query and patient data for better classification
        combined_text = f"{query} {patient_data}".lower()
        
        best_match = None
        best_confidence = 0.0
        
        for rule in self.rules:
            if re.search(rule.pattern, combined_text, re.IGNORECASE):
                if rule.confidence > best_confidence:
                    best_match = rule.query_type
                    best_confidence = rule.confidence
        
        # If no specific match found, use general query
        if best_match is None:
            best_match = QueryType.GENERAL_QUERY
            best_confidence = 0.1
        
        logger.info(f"Classified query as {best_match} with confidence {best_confidence}")
        return best_match, best_confidence
    
    def get_classification_rules(self) -> List[ClassificationRule]:
        """Get all classification rules."""
        return self.rules.copy()
    
    def add_classification_rule(self, rule: ClassificationRule) -> None:
        """Add a new classification rule."""
        self.rules.append(rule)
        logger.info(f"Added classification rule: {rule.description}")


# Global query classifier instance
_query_classifier: Optional[QueryClassifier] = None


def get_query_classifier() -> QueryClassifier:
    """Get the global query classifier instance."""
    global _query_classifier
    if _query_classifier is None:
        _query_classifier = QueryClassifier()
    return _query_classifier


















