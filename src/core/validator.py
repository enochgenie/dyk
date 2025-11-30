"""
Validation Layer
Ensures insights conform to schema, have valid sources, and meet quality standards.
"""

import re
import json
from typing import Dict, Any, List, Tuple, Optional
from urllib.parse import urlparse
import requests
from difflib import SequenceMatcher


class InsightValidator:
    """
    Validator for DYK insights.

    Validation includes:
    1. JSON validity
    2. Schema conformity (required fields, types, lengths)
    3. Source verification (valid and accessible URLs)
    4. Domain credibility (whitelisted domains)
    """

    def __init__(self):
        pass

    def _validate_json(self, insight: Dict[str, Any]) -> Dict[str, Any]:
        """Validate JSON serializability."""
        try:
            json.dumps(insight)
            return {"passed": True, "issues": []}
        except (TypeError, ValueError) as e:
            return {"passed": False, "issues": [f"Insight is NOT valid JSON: {str(e)}"]}

    def _validate_schema(self, insight: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate schema conformity.

        Three criteria:
        1. Required fields present
        2. Field types correct
        3. Field lengths within acceptable ranges
        """
        issues = []

        required_fields = {
            "hook": str,
            "explanation": str,
            "action": str,
            "source_name": str,
            "source_url": str,
            "numeric_claim": str,
        }

        # --- 1. Required fields ---
        missing = [f for f in required_fields if f not in insight]
        if missing:
            issues.append(f"Missing required fields: {missing}")

        # --- 2. Field type checks ---
        for field, expected_type in required_fields.items():
            if field in insight:
                if not isinstance(insight[field], expected_type):
                    issues.append(
                        f"Field '{field}' must be {expected_type.__name__}, "
                        f"got {type(insight[field]).__name__}."
                    )

        # Check field lengths
        if "hook" in insight:
            hook_words = len(insight["hook"].split())
            if hook_words > 20:
                issues.append(f"Hook too long: {hook_words} words (max 20)")

        if "explanation" in insight:
            exp_words = len(insight["explanation"].split())
            if exp_words < 30 or exp_words > 60:
                issues.append(
                    f"Explanation length suboptimal: {exp_words} words (target 40-60)"
                )

        if "action" in insight:
            action_words = len(insight["action"].split())
            if action_words > 30:
                issues.append(f"Action too long: {action_words} words (max 30)")

        return {"passed": len(issues) == 0, "issues": issues}

    def _validate_source(self, insight: Dict[str, Any]) -> Dict[str, Any]:
        """Validate source URL accessibility"""
        issues = []
        warnings = []

        source_url = insight.get("source_url", "")
        source_name = insight.get("source_name", "")

        if not source_name:
            issues.append("Missing source name")

        if not source_url:
            issues.append("Missing source URL")
        elif source_url == "general medical knowledge":
            warnings.append("No specific source URL provided")
        else:
            # Validate URL format
            try:
                parsed = urlparse(source_url)
                if not parsed.scheme or not parsed.netloc:
                    issues.append(f"Invalid URL format: {source_url}")
                else:
                    # Check URL accessibility
                    try:
                        response = requests.head(source_url, timeout=5)
                        if response.status_code >= 400:
                            issues.append(
                                f"Source URL not accessible, status code: {response.status_code}"
                            )
                    except requests.RequestException as e:
                        issues.append(f"Error accessing source URL: {str(e)}")

            except Exception as e:
                issues.append(f"Error parsing URL: {str(e)}")

        return {"passed": len(issues) == 0, "issues": issues, "warnings": warnings}

    # TODO: implement validation method for domain
    def _validate_domain(self, insight: Dict[str, Any]) -> Dict[str, Any]:
        pass

    def validate(self, insight: Dict[str, Any]) -> Dict[str, Any]:
        """
        Comprehensive validation of a single insight.

        Args:
            insight: Insight dictionary to validate

        Returns:
            Validation result with scores and issues
        """
        checks = {
            "json_validity": self._validate_json(insight),
            "schema_conformity": self._validate_schema(insight),
            "source_verification": self._validate_source(insight),
            # "domain_credibility": self._validate_domain(insight)
        }

        number_failed = sum(1 for check in checks.values() if not check["passed"])

        return {
            "validated": number_failed == 0,
            "number_failed": number_failed,
            "checks": checks,
        }


# Example usage
if __name__ == "__main__":
    validator = InsightValidator()

    # Example insight
    insight = {
        "hook": "Did you know regular exercise + balanced diet doubles protection against depression compared to either alone?",
        "explanation": "For obese Singaporeans aged 50-59 at higher depression risk from inflammation and low mood, this synergy boosts brain chemicals like serotonin more effectively, enhancing emotional wellbeing as promoted by HPB guidelines (40 words)",
        "action": "Aim for 150min weekly brisk walking and follow HPB My Healthy Plate: fill half your plate with fruits/veggies, quarter wholegrains, quarter lean protein.",
        "source_name": "Health Promotion Board (HPB)",
        "source_url": "https://www.hpb.gov.sg/healthy-living/mental-wellbeing",
        "numeric_claim": "doubles protection",
    }

    result = validator._validate_json(insight)
    print("JSON Validation Result:", result)

    result = validator._validate_schema(insight)
    print("Schema Validation Result:", result)

    result = validator._validate_source(insight)
    print("Source Validation Result:", result)

    result = validator.validate(insight)
    print("Comprehensive Validation Result:", result)
