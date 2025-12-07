"""
Evaluator Layer
Ensures insights are factually accurate, safe, faithful to evidence, relevant, actionable, and culturally appropriate.
"""

import asyncio
import json
from typing import Any, Dict
from src.prompts.prompt_templates import PromptTemplates
from src.core.llm_client import OpenRouterClient


class InsightEvaluator:
    """
    Evaluator for DYK insights with parallel processing support.

    Evaluation includes:
    1. Factual accuracy
    2. Safety
    3. Faithfulness to evidence
    4. Cohort Relevance
    5. Actionability
    6. Localization
    """

    def __init__(
        self,
        llm_client: OpenRouterClient,
        prompt_template: PromptTemplates,
        max_concurrent: int = 20,
    ):
        """
        Initialize evaluator.

        Args:
            llm_client: OpenRouterClient instance
            prompt_templates: PromptTemplates instance
            max_concurrent: Maximum number of concurrent evaluations (default: 20)
        """
        self.llm = llm_client
        self.prompt_template = prompt_template
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def evaluate(
        self,
        insight: Dict[str, Any],
        cohort: Dict[str, Any],
        insight_template: Dict[str, Any],
        market: str,
        model: str = None,
        temperature: float = 0.3,  # Lower temp for evaluation (more deterministic)
        max_tokens: int = 4000,
    ) -> dict:
        """
        Evaluate a given insight using LLM (async).

        Args:
            insight: The insight to evaluate
            cohort: The cohort parameters
            insight_template: The template used to generate the insight
            market: The target region for cultural appropriateness
            model: Model to use (optional, uses client default)
            temperature: Sampling temperature (default: 0.3 for consistency)
            max_tokens: Maximum tokens (default: 4000)

        Returns:
            A dictionary with evaluation results
        """

        async with self.semaphore:
            # Generate prompt
            prompt = self.prompt_template.validation_prompt(
                insight, cohort, insight_template, market
            )

            # Call LLM asynchronously
            evaluation_results = await self.llm.generate(
                prompt, model, temperature, max_tokens
            )
            evaluation_results = self._parse_json_response(evaluation_results)

            return evaluation_results

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
                print(f"⚠️  Auto-repaired JSON (Evaluator): {e.msg} at position {e.pos}")
                try:
                    return json.loads(repaired)
                except json.JSONDecodeError:
                    pass  # Repair failed, fall through to error logging

            # Repair failed or not attempted - log detailed error
            print("\n" + "=" * 80)
            print("❌ JSON PARSE ERROR (Evaluator)")
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
    import datetime
    import time
    from pathlib import Path
    from dotenv import load_dotenv

    # Load environment variables
    load_dotenv(Path(__file__).parent.parent.parent / ".env")

    async def main():
        """Test evaluator."""

        # Sample insights to evaluate
        with open("output/creative_insights.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        insights = data["insights"]  # take first 3 insights

        # Sample cohort
        market = "singapore"
        model = "amazon/nova-2-lite-v1:free"
        prompt_template = PromptTemplates()

        print("\n" + "=" * 80)
        print("EVALUATOR TEST")
        print("=" * 80)
        print(f"Evaluating {len(insights)} insights...")
        print(f"Model: {model}")
        print("=" * 80 + "\n")

        # Create async client
        async with OpenRouterClient(model=model) as client:
            # Create evaluator with concurrency control
            evaluator = InsightEvaluator(client, prompt_template, max_concurrent=3)

            # Evaluate batch in parallel
            print(f"Batch evaluation ({len(insights)} insights)...")
            start = time.time()
            tasks = [
                evaluator.evaluate(
                    insight,
                    insight["cohort"],
                    insight["insight_template"],
                    market,
                    model,
                    temperature=0.3,
                    max_tokens=4000,
                )
                for insight in insights
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)
            duration = time.time() - start

            successes = 0
            failures = 0

            # Process generation results
            evaluated_insights = []

            for insight, result in zip(insights, results):
                if isinstance(result, Exception):
                    failures += 1
                    print(f"Evaluation failed: {str(result)}")
                    insight["evaluation"] = {"status": "failed", "error": str(result)}
                elif isinstance(result, dict) and "criteria" in result:
                    successes += 1
                    insight["evaluation"] = result
                else:
                    failures += 1
                    insight["evaluation"] = {
                        "status": "failed",
                        "error": f"Unknown object: {type(result)}",
                    }

                insight["evaluation_model"] = model
                insight["evaluated_at"] = datetime.datetime.now().isoformat()

                evaluated_insights.append(insight)

            print(f"✓ Completed {len(results)} evaluations in {duration:.2f}s")
            print(f"✓ Success rate: {successes}/{len(tasks)}")
            print(f"Average: {duration / len(results):.2f}s per insight\n")

            output_data = {
                "creative_metadata": data.get("creative_metadata", {}),
                "generation_metadata": data.get("generation_metadata", {}),
                "evaluation_metadata": {
                    "market": market,
                    "model": model,
                    "temperature": 0.3,
                    "max_tokens": 4000,
                    "generated_at": datetime.datetime.now().isoformat(),
                    "total_calls": len(tasks),
                    "successful_calls": successes,
                    "failed_calls": failures,
                    "duration_seconds": round(duration, 2),
                },
                "insights": evaluated_insights,
            }

            # Save to JSON
            output_dir = Path("output")
            output_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            json_file = output_dir / f"evaluated_{timestamp}.json"

            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)

            print(f"\n✓ Saved JSON to: {json_file}")

            # Save to CSV
            import csv

            csv_file = output_dir / f"evaluated_{timestamp}.csv"

            with open(csv_file, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)

                # Write header - management-focused format
                header = [
                    "variation_id",
                    "hook",
                    "explanation",
                    "action",
                    "insight_id",
                    "original_hook",
                    "original_explanation",
                    "original_action",
                    "source_name",
                    "source_url",
                    "numeric_claim",
                    "cohort_name",
                    "insight_template_type",
                    "generation_model",
                    "generated_at",
                    "creative_model",
                    "created_at",
                    "evaluation_model",
                    "evaluated_at",
                    "factual_accuracy_score",
                    "safety_score",
                    "faithfulness_score",
                    "cohort_relevance_score",
                    "actionability_score",
                    "localization_score",
                    "overall_score",
                    "pass",
                    "strengths",
                    "critical_issues",
                    "recommendations",
                ]
                writer.writerow(header)

                # Write data rows
                for insight in evaluated_insights:
                    evaluation = insight.get("evaluation", {})
                    criteria = evaluation.get("criteria", {})

                    row = [
                        insight.get("variation_id", ""),
                        insight.get("hook", ""),
                        insight.get("explanation", ""),
                        insight.get("action", ""),
                        insight.get("insight_id", ""),
                        insight.get("original_hook", ""),
                        insight.get("original_explanation", ""),
                        insight.get("original_action", ""),
                        insight.get("source_name", ""),
                        insight.get("source_url", ""),
                        insight.get("numeric_claim", ""),
                        insight.get("cohort", {}).get("name", ""),
                        insight.get("insight_template", {}).get("type", ""),
                        insight.get("generation_model", ""),
                        insight.get("generated_at", ""),
                        insight.get("creative_model", ""),
                        insight.get("created_at", ""),
                        insight.get("evaluation_model", ""),
                        insight.get("evaluated_at", ""),
                        criteria.get("factual_accuracy", {}).get("score", ""),
                        criteria.get("safety", {}).get("score", ""),
                        criteria.get("faithfulness", {}).get("score", ""),
                        criteria.get("cohort_relevance", {}).get("score", ""),
                        criteria.get("actionability", {}).get("score", ""),
                        criteria.get("localization", {}).get("score", ""),
                        evaluation.get("overall_score", ""),
                        evaluation.get("pass", ""),
                        evaluation.get("strengths", ""),
                        evaluation.get("critical_issues", ""),
                        evaluation.get("recommendations", ""),
                    ]
                    writer.writerow(row)

            print(f"✓ Saved CSV to: {csv_file}")

    # Run test
    asyncio.run(main())
