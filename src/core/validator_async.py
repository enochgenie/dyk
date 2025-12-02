"""
Async Validation Layer with parallel processing.
Ensures insights conform to schema, have valid sources, and meet quality standards.
"""

import asyncio
import aiohttp
import json
from typing import Dict, Any, List
from urllib.parse import urlparse


class AsyncInsightValidator:
    """
    Async validator for DYK insights with parallel processing support.

    Validation includes:
    1. JSON validity
    2. Schema conformity (required fields, types, lengths)
    3. Source verification (valid and accessible URLs)
    """

    def __init__(self, max_concurrent: int = 50):
        """
        Initialize async validator.

        Args:
            max_concurrent: Maximum number of concurrent validations (default: 50)
        """
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)

    def _validate_json(self, insight: Dict[str, Any]) -> Dict[str, Any]:
        """Validate JSON serializability (synchronous)."""
        try:
            json.dumps(insight)
            return {"passed": True, "issues": []}
        except (TypeError, ValueError) as e:
            return {
                "passed": False,
                "issues": [f"Insight is NOT valid JSON: {str(e)}"],
            }

    def _validate_schema(self, insight: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate schema conformity (synchronous).

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

    async def _validate_source(self, insight: Dict[str, Any]) -> Dict[str, Any]:
        """Validate source URL accessibility (async)."""
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
                    # Check URL accessibility (async) with semaphore
                    async with self.semaphore:
                        try:
                            async with aiohttp.ClientSession() as session:
                                async with session.head(
                                    source_url,
                                    timeout=aiohttp.ClientTimeout(total=5),
                                    allow_redirects=True,
                                ) as response:
                                    if response.status >= 400:
                                        issues.append(
                                            f"Source URL not accessible, status code: {response.status}"
                                        )
                        except asyncio.TimeoutError:
                            issues.append(f"Timeout accessing source URL: {source_url}")
                        except Exception as e:
                            issues.append(f"Error accessing source URL: {str(e)}")

            except Exception as e:
                issues.append(f"Error parsing URL: {str(e)}")

        return {"passed": len(issues) == 0, "issues": issues, "warnings": warnings}

    async def validate(self, insight: Dict[str, Any]) -> Dict[str, Any]:
        """
        Comprehensive validation of a single insight (async).

        Args:
            insight: Insight dictionary to validate

        Returns:
            Validation result with scores and issues
        """
        # Run synchronous checks immediately
        json_check = self._validate_json(insight)
        schema_check = self._validate_schema(insight)

        # Run async source check
        source_check = await self._validate_source(insight)

        checks = {
            "json_validity": json_check,
            "schema_conformity": schema_check,
            "source_verification": source_check,
        }

        number_failed = sum(1 for check in checks.values() if not check["passed"])

        return {
            "validated": number_failed == 0,
            "number_failed": number_failed,
            "checks": checks,
        }

    async def validate_batch(
        self, insights: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Validate multiple insights in parallel.

        Args:
            insights: List of insights to validate

        Returns:
            List of validation results (or exceptions if failed)
        """
        tasks = [self.validate(insight) for insight in insights]

        # return_exceptions=True means one failure won't stop the others
        return await asyncio.gather(*tasks, return_exceptions=True)


# Example usage
if __name__ == "__main__":
    import asyncio
    import time

    async def test_async_validator():
        """Test async validator with parallel validation."""

        # Sample insights to validate
        insights = [
            {
                "hook": "Did you know regular exercise can reduce depression by 30%?",
                "explanation": "Regular physical activity releases endorphins and other mood-boosting chemicals, which can help reduce symptoms of depression and improve overall mental wellbeing for adults in Singapore.",
                "action": "Aim for at least 150 minutes of moderate exercise each week, such as brisk walking or cycling.",
                "source_name": "Health Promotion Board (HPB)",
                "source_url": "https://www.hpb.gov.sg",
                "numeric_claim": "reduce depression by 30%",
            },
            {
                "hook": "Did you know sleeping 7-8 hours lowers obesity risk by 20%?",
                "explanation": "Adequate sleep regulates hormones that control appetite and metabolism, helping maintain a healthy weight and reducing the risk of obesity among young adults.",
                "action": "Set a consistent bedtime and create a relaxing pre-sleep routine to ensure 7-8 hours of quality sleep.",
                "source_name": "Ministry of Health Singapore",
                "source_url": "https://www.moh.gov.sg",
                "numeric_claim": "lowers obesity risk by 20%",
            },
            {
                # Missing required field (source_url)
                "hook": "Did you know eating vegetables reduces disease risk?",
                "explanation": "Vegetables provide essential nutrients and fiber that support overall health and reduce chronic disease risk.",
                "action": "Eat at least 5 servings of vegetables daily.",
                "source_name": "HPB",
                "numeric_claim": "N/A",
            },
            {
                # Invalid URL
                "hook": "Did you know hydration improves focus?",
                "explanation": "Staying properly hydrated helps maintain cognitive function, concentration, and mental clarity throughout the day for working adults.",
                "action": "Drink 8 glasses of water daily, especially before and after exercise.",
                "source_name": "Health Authority",
                "source_url": "not-a-valid-url",
                "numeric_claim": "N/A",
            },
        ]

        print("\n" + "=" * 80)
        print("ASYNC VALIDATOR TEST")
        print("=" * 80)
        print(f"Validating {len(insights)} insights...")
        print("=" * 80 + "\n")

        validator = AsyncInsightValidator(max_concurrent=10)

        # Test 1: Validate single insight
        print("[TEST 1] Single validation...")
        start = time.time()
        result = await validator.validate(insights[0])
        duration = time.time() - start

        print(f"✓ Completed in {duration:.2f}s")
        print(f"Validated: {result['validated']}")
        print(f"Failed checks: {result['number_failed']}\n")

        # Test 2: Validate batch in parallel
        print(f"[TEST 2] Batch validation ({len(insights)} insights)...")

        start = time.time()
        results = await validator.validate_batch(insights)
        duration = time.time() - start

        print(f"✓ Completed {len(results)} validations in {duration:.2f}s")
        print(f"Average: {duration/len(results):.2f}s per insight\n")

        # Display results
        print("=" * 80)
        print("VALIDATION RESULTS")
        print("=" * 80)

        for i, (insight, result) in enumerate(zip(insights, results), 1):
            print(f"\n[{i}] {insight['hook'][:60]}...")

            if isinstance(result, Exception):
                print(f"    ✗ ERROR: {result}")
            else:
                if result["validated"]:
                    print(f"    ✓ PASSED")
                else:
                    print(f"    ✗ FAILED ({result['number_failed']} checks failed)")

                    # Show which checks failed
                    for check_name, check_result in result["checks"].items():
                        if not check_result["passed"]:
                            print(f"      - {check_name}:")
                            for issue in check_result["issues"]:
                                print(f"          • {issue}")

        print("\n" + "=" * 80)
        print(f"✓ Async validation test complete!")
        print("=" * 80 + "\n")

    # Run test
    asyncio.run(test_async_validator())
