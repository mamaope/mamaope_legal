"""
Response Processor Module for mamaope_legal AI CDSS.

This module handles processing and formatting AI responses.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ProcessedResponse:
    """Processed AI response."""
    content: str
    format_type: str
    metadata: Dict[str, Any]
    is_valid: bool
    error_message: Optional[str] = None


class ResponseProcessor:
    """Processes and formats AI responses."""
    
    def __init__(self):
        """Initialize the response processor."""
        self.logger = logging.getLogger(__name__)
    
    def process_response(self, raw_response: str, query_type: str) -> ProcessedResponse:
        """Process a raw AI response."""
        try:
            # Try to parse as JSON first
            if self._is_json_response(raw_response):
                return self._process_json_response(raw_response)
            else:
                return self._process_text_response(raw_response, query_type)
        
        except Exception as e:
            logger.error(f"Error processing response: {e}")
            return ProcessedResponse(
                content=raw_response,
                format_type="text",
                metadata={"error": str(e)},
                is_valid=False,
                error_message=str(e)
            )
    
    def _is_json_response(self, response: str) -> bool:
        """Check if response is valid JSON or contains JSON in markdown code blocks."""
        try:
            # First try direct JSON parsing
            json.loads(response.strip())
            return True
        except (json.JSONDecodeError, ValueError):
            # Check if it's JSON wrapped in markdown code blocks
            if self._extract_json_from_markdown(response):
                return True
            return False
    
    def _extract_json_from_markdown(self, response: str) -> Optional[str]:
        """Extract JSON from markdown code blocks."""
        import re
        
        # Look for JSON in markdown code blocks
        json_pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
        matches = re.findall(json_pattern, response, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            try:
                # Try to parse the extracted content as JSON
                json.loads(match.strip())
                return match.strip()
            except (json.JSONDecodeError, ValueError):
                continue
        
        return None
    
    def _process_json_response(self, response: str) -> ProcessedResponse:
        """Process a JSON response."""
        try:
            # First try direct JSON parsing
            try:
                parsed_json = json.loads(response.strip())
            except (json.JSONDecodeError, ValueError):
                # Try extracting JSON from markdown code blocks
                json_content = self._extract_json_from_markdown(response)
                if json_content:
                    parsed_json = json.loads(json_content)
                else:
                    raise ValueError("No valid JSON found in response")
            
            # Validate and clean JSON structure for differential diagnosis
            if self._is_differential_diagnosis_json(parsed_json):
                # Ensure proper JSON structure
                cleaned_json = self._clean_differential_diagnosis_json(parsed_json)
                
                return ProcessedResponse(
                    content=json.dumps(cleaned_json, indent=2),
                    format_type="json",
                    metadata={
                        "parsed_json": cleaned_json,
                        "has_clinical_overview": "clinical_overview" in cleaned_json,
                        "has_differential_diagnoses": "differential_diagnoses" in cleaned_json,
                        "has_critical_alert": "critical_alert" in cleaned_json,
                        "diagnosis_count": len(cleaned_json.get("differential_diagnoses", [])),
                        "is_structured": True
                    },
                    is_valid=True
                )
            else:
                # For other JSON responses, return as-is
                return ProcessedResponse(
                    content=json.dumps(parsed_json, indent=2),
                    format_type="json",
                    metadata={"parsed_json": parsed_json},
                    is_valid=True
                )
        
        except Exception as e:
            logger.error(f"Error processing JSON response: {e}")
            return ProcessedResponse(
                content=response,
                format_type="json",
                metadata={"error": str(e)},
                is_valid=False,
                error_message=str(e)
            )
    
    def _process_text_response(self, response: str, query_type: str) -> ProcessedResponse:
        """Process a text response."""
        # For text responses, we'll format them appropriately
        formatted_response = self._format_text_response(response, query_type)
        
        return ProcessedResponse(
            content=formatted_response,
            format_type="text",
            metadata={
                "original_length": len(response),
                "formatted_length": len(formatted_response),
                "query_type": query_type
            },
            is_valid=True
        )
    
    def _is_differential_diagnosis_json(self, parsed_json: Dict[str, Any]) -> bool:
        """Check if JSON follows differential diagnosis schema."""
        required_fields = ["clinical_overview", "differential_diagnoses"]
        return all(field in parsed_json for field in required_fields)
    
    def _clean_differential_diagnosis_json(self, json_data: Dict[str, Any]) -> Dict[str, Any]:
        """Clean and validate differential diagnosis JSON structure."""
        cleaned = {}
        
        # Clinical Overview
        if "clinical_overview" in json_data:
            cleaned["clinical_overview"] = str(json_data["clinical_overview"]).strip()
        
        # Critical Alert
        if "critical_alert" in json_data:
            cleaned["critical_alert"] = bool(json_data["critical_alert"])
        
        # Differential Diagnoses
        if "differential_diagnoses" in json_data and isinstance(json_data["differential_diagnoses"], list):
            cleaned["differential_diagnoses"] = []
            for diagnosis in json_data["differential_diagnoses"]:
                if isinstance(diagnosis, dict):
                    cleaned_diagnosis = {
                        "diagnosis": str(diagnosis.get("diagnosis", "")).strip(),
                        "probability_percent": self._validate_probability(diagnosis.get("probability_percent", 0)),
                        "evidence": str(diagnosis.get("evidence", "")).strip(),
                        "citations": self._clean_citations(diagnosis.get("citations", []))
                    }
                    cleaned["differential_diagnoses"].append(cleaned_diagnosis)
        
        # Immediate Workup
        if "immediate_workup" in json_data and isinstance(json_data["immediate_workup"], list):
            cleaned["immediate_workup"] = [str(item).strip() for item in json_data["immediate_workup"] if str(item).strip()]
        
        # Management
        if "management" in json_data and isinstance(json_data["management"], list):
            cleaned["management"] = [str(item).strip() for item in json_data["management"] if str(item).strip()]
        
        # Red Flags
        if "red_flags" in json_data and isinstance(json_data["red_flags"], list):
            cleaned["red_flags"] = [str(item).strip() for item in json_data["red_flags"] if str(item).strip()]
        
        # Additional Information Needed
        if "additional_information_needed" in json_data:
            additional_info = json_data["additional_information_needed"]
            if additional_info and str(additional_info).strip():
                cleaned["additional_information_needed"] = str(additional_info).strip()
            else:
                cleaned["additional_information_needed"] = None
        
        # Sources Used
        if "sources_used" in json_data and isinstance(json_data["sources_used"], list):
            cleaned["sources_used"] = [str(item).strip() for item in json_data["sources_used"] if str(item).strip()]
        
        return cleaned
    
    def _validate_probability(self, probability: Any) -> int:
        """Validate and clean probability percentage."""
        try:
            prob = int(float(probability))
            return max(0, min(100, prob))  # Clamp between 0 and 100
        except (ValueError, TypeError):
            return 0
    
    def _clean_citations(self, citations: Any) -> List[str]:
        """Clean and validate citations list."""
        if not isinstance(citations, list):
            return []
        
        cleaned_citations = []
        for citation in citations:
            if citation and str(citation).strip():
                cleaned_citations.append(str(citation).strip())
        
        return cleaned_citations
    
    def _format_text_response(self, response: str, query_type: str) -> str:
        """Format text response based on query type."""
        if query_type == "differential_diagnosis":
            return self._format_differential_diagnosis_text(response)
        elif query_type == "drug_information":
            return self._format_drug_information_text(response)
        elif query_type == "clinical_guidance":
            return self._format_clinical_guidance_text(response)
        else:
            return response
    
    def _format_differential_diagnosis_text(self, response: str) -> str:
        """Format differential diagnosis text response."""
        # Add basic formatting for differential diagnosis
        formatted = response.replace("**", "**")
        return formatted
    
    def _format_drug_information_text(self, response: str) -> str:
        """Format drug information text response."""
        return response
    
    def _format_clinical_guidance_text(self, response: str) -> str:
        """Format clinical guidance text response."""
        return response
    
    def extract_sources(self, response: str) -> List[str]:
        """Extract sources from response."""
        sources = []
        
        # Look for source patterns
        import re
        source_patterns = [
            r"\[Source: ([^\]]+)\]",
            r"Source: ([^\n]+)",
            r"Reference: ([^\n]+)"
        ]
        
        for pattern in source_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            sources.extend(matches)
        
        return list(set(sources))  # Remove duplicates
    
    def validate_response(self, response: str, query_type: str) -> Dict[str, Any]:
        """Validate response quality."""
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "metrics": {}
        }
        
        # Basic validation
        if not response or len(response.strip()) < 10:
            validation_result["is_valid"] = False
            validation_result["errors"].append("Response too short")
        
        # Length validation
        if len(response) > 50000:
            validation_result["warnings"].append("Response very long")
        
        # Content validation based on query type
        if query_type == "differential_diagnosis":
            if "differential" not in response.lower():
                validation_result["warnings"].append("Missing differential diagnosis content")
        
        validation_result["metrics"] = {
            "length": len(response),
            "word_count": len(response.split()),
            "has_sources": len(self.extract_sources(response)) > 0
        }
        
        return validation_result


# Global response processor instance
_response_processor: Optional[ResponseProcessor] = None


def get_response_processor() -> ResponseProcessor:
    """Get the global response processor instance."""
    global _response_processor
    if _response_processor is None:
        _response_processor = ResponseProcessor()
    return _response_processor
