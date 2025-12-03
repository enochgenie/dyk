"""
Creative Rewriting Layer
Generates diverse linguistic variations of insights while preserving factual accuracy.
Adds variety to the insight pool for better user engagement and A/B testing.
"""

import asyncio
import json
from typing import Any, Dict
from src.prompts.prompt_templates import PromptTemplates
from src.core.llm_client import OpenRouterClient


class CreativeRewriter:
    """
    Async creative rewriter for DYK insights.

    This layer:
    1. Takes generated insights
    2. Creates multiple creative variations of each
    3. Preserves all factual content and sources
    4. Adds linguistic diversity for better engagement
    """

    def __init__(
        self,
        llm_client: OpenRouterClient,
        prompt_template: PromptTemplates,
        max_concurrent: int = 15,
    ):
        """
        Initialize creative rewriter.

        Args:
            llm_client: OpenRouterClient instance
            prompt_templates: PromptTemplates instance
            max_concurrent: Maximum number of concurrent rewrites (default: 15)
        """
        self.llm = llm_client
        self.prompt_template = prompt_template
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def rewrite(
        self,
        insight: Dict[str, Any],
        cohort: Dict[str, Any],
        market: str,
        num_variations: int = 3,
        model: str = None,
        temperature: float = 0.8,  # Higher temp for creative diversity
        max_tokens: int = 4000,
    ) -> Dict[str, Any]:
        """
        Generate creative variations of a single insight (async).

        Args:
            insight: The insight to rewrite
            cohort: Target cohort
            market: Target region
            num_variations: Number of variations to generate (default: 3)
            model: Model to use (optional, uses client default)
            temperature: Sampling temperature (default: 0.8 for creativity)
            max_tokens: Maximum tokens (default: 4000)

        Returns:
            A dictionary with:
            - "original": the original insight (for reference/tracking)
            - "variations": list of rewritten variations
        """

        async with self.semaphore:
            # Generate prompt
            prompt = self.prompt_template.creative_rewriting_prompt(
                insight=insight,
                cohort=cohort,
                market=market,
                num_variations=num_variations,
            )

            # Call LLM asynchronously
            results = await self.llm.generate(prompt, model, temperature, max_tokens)
            results = self._parse_json_response(results)

            insight_copy = insight.copy()
            insight_copy["variations"] = results["variations"]
            return insight_copy

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response with automatic repair for common issues."""
        response = response.strip()

        # Remove markdown code blocks (common LLM behavior)
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]

        response = response.strip()

        # Try parsing original response
        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            # Attempt automatic repairs for common LLM JSON errors
            repaired = self._attempt_json_repair(response, e)

            if repaired:
                print(
                    f"⚠️  Auto-repaired JSON (Creative Rewriter): {e.msg} at position {e.pos}"
                )
                try:
                    return json.loads(repaired)
                except json.JSONDecodeError:
                    pass  # Repair failed, fall through to error logging

            # Repair failed or not attempted - log detailed error
            print("\n" + "=" * 80)
            print("❌ JSON PARSE ERROR (Creative Rewriter)")
            print("=" * 80)
            print(f"Error: {e}")
            print(f"Position: Line {e.lineno}, Column {e.colno}")

            print("\n--- CONTEXT AROUND ERROR ---")
            start = max(0, e.pos - 150)
            end = min(len(response), e.pos + 150)
            snippet = response[start:end]
            pointer_pos = e.pos - start
            print(snippet)
            print(" " * pointer_pos + "^" * 10 + " ERROR HERE")

            print("\n--- FULL RESPONSE ---")
            print(response)
            print("=" * 80 + "\n")

            raise

    def _attempt_json_repair(self, response: str, error: json.JSONDecodeError) -> str:
        """
        Attempt to repair common JSON formatting issues from LLM responses.

        Common issues fixed:
        1. Missing commas between object properties
        2. Trailing commas before closing braces/brackets
        3. Missing closing brackets/braces

        Args:
            response: The malformed JSON string
            error: The JSONDecodeError with position information

        Returns:
            Repaired JSON string if repair was attempted, None otherwise
        """

        # Only attempt repair for specific, fixable errors
        error_msg = error.msg.lower()

        # Fix 1: Missing comma between properties
        # Error: "Expecting ',' delimiter" or "Expecting property name"
        if (
            "expecting ',' delimiter" in error_msg
            or "expecting property name" in error_msg
        ):
            # Check if there's a missing comma before a quote
            pos = error.pos
            if pos < len(response) and response[pos] == '"':
                # Look backward to find the end of previous value
                # Common pattern: }"key" should be },"key"
                if pos > 0 and response[pos - 1] == "}":
                    return response[:pos] + "," + response[pos:]
                # Pattern: ]"key" should be ],"key"
                if pos > 0 and response[pos - 1] == "]":
                    return response[:pos] + "," + response[pos:]

        # Fix 2: Trailing comma before closing brace/bracket
        # Error: "Expecting property name" right after comma
        if "expecting property name" in error_msg:
            pos = error.pos
            # Look backward for comma followed by whitespace and closing brace
            check_start = max(0, pos - 10)
            snippet = response[check_start : pos + 5]
            if "," in snippet and ("}" in snippet or "]" in snippet):
                # Find the trailing comma
                for i in range(pos - 1, max(0, pos - 20), -1):
                    if response[i] == ",":
                        # Check if only whitespace between comma and closing brace
                        after_comma = response[i + 1 : pos + 5].strip()
                        if after_comma and after_comma[0] in ["}", "]"]:
                            return response[:i] + response[i + 1 :]

        # Fix 3: Missing closing braces/brackets (simple heuristic)
        if "expecting" in error_msg and error.pos >= len(response) - 5:
            # Count opening and closing braces
            open_braces = response.count("{")
            close_braces = response.count("}")
            open_brackets = response.count("[")
            close_brackets = response.count("]")

            # Add missing closing characters
            missing = ""
            if close_brackets < open_brackets:
                missing += "]" * (open_brackets - close_brackets)
            if close_braces < open_braces:
                missing += "}" * (open_braces - close_braces)

            if missing:
                return response + missing

        # No repair attempted
        return None


# Example usage
if __name__ == "__main__":
    from dotenv import load_dotenv
    import time
    from pathlib import Path
    import datetime

    # Load environment variables
    load_dotenv(Path(__file__).parent.parent.parent / ".env")

    async def main():
        """Test async creative rewriter"""

        # Sample cohort
        market = "singapore"
        # model = "deepseek/deepseek-v3.2"
        model = "arcee-ai/trinity-mini:free"
        prompt_template = PromptTemplates()
        num_variations = 2

        with open("output/test_insights.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        insights = data["insights"]

        print("\n" + "=" * 80)
        print("ASYNC CREATIVE REWRITER TEST")
        print("=" * 80)
        print(f"Rewriting {len(insights)} insights...")
        print(f"Model: {model}")
        print(f"Variations per insight: {num_variations}")
        print("=" * 80 + "\n")

        # Create async client
        async with OpenRouterClient(model=model) as client:
            # Create rewriter with concurrency control
            rewriter = CreativeRewriter(client, prompt_template, 5)

            # Rewrite batch in parallel
            print(f"Batch rewrite ({len(insights)} insights)...")

            start = time.time()
            # Manual loop pattern - consistent with pipeline architecture
            tasks = [
                rewriter.rewrite(
                    insight,
                    insight["cohort"],
                    market,
                    num_variations=num_variations,
                    model=model,
                )
                for insight in insights
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            duration = time.time() - start

            successes = 0
            failures = 0

            rewritten_results = []
            # Process generation results
            for insight, result in zip(insights, results):
                if isinstance(result, Exception):
                    failures += 1
                    print(f"Creation failed: {str(result)}")
                    continue  # Skip failed insights

                elif isinstance(result, dict) and "variations" in result:
                    successes += 1

                    for idx, variation in enumerate(result["variations"]):
                        rewritten_results.append(
                            {
                                "variation_id": f"{insight['insight_id']}_v{idx + 1}",
                                "hook": variation.get("hook", ""),
                                "explanation": variation.get("explanation", ""),
                                "action": variation.get("action", ""),
                                "narrative_angle": variation.get("narrative_angle", ""),
                                "insight_id": insight["insight_id"],
                                "original_hook": insight["hook"],
                                "original_explanation": insight["explanation"],
                                "original_action": insight["action"],
                                "source_name": insight.get("source_name", ""),
                                "source_url": insight.get("source_url", ""),
                                "numeric_claim": insight.get("numeric_claim", ""),
                                "cohort": insight["cohort"],
                                "insight_template": insight["insight_template"],
                                "generation_model": insight["generation_model"],
                                "generated_at": insight["generated_at"],
                                "creative_model": model,
                                "created_at": datetime.datetime.now().isoformat(),
                            }
                        )

            print(f"✓ Completed {len(results)} rewrites in {duration:.2f}s")
            print(f"✓ Success rate: {successes}/{len(tasks)}")
            print(f"Average: {duration / len(results):.2f}s per insight\n")

            output_data = {
                "creative_metadata": {
                    "market": market,
                    "model": model,
                    "temperature": 0.8,
                    "max_tokens": 4000,
                    "generated_at": datetime.datetime.now().isoformat(),
                    "total_calls": len(tasks),
                    "successful_calls": successes,
                    "failed_calls": failures,
                    "duration_seconds": round(duration, 2),
                },
                "generation_metadata": data["generation_metadata"],
                "insights": rewritten_results,
                "duplication_results": data["duplication_results"],
            }

            # Save to JSON with two-level metadata structure
            output_dir = Path("output")
            output_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = output_dir / f"creative_{timestamp}.json"

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)

            print(f"\n✓ Saved to: {output_file}")

    # Run test
    asyncio.run(main())
