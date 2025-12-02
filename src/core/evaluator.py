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
        """Parse JSON from LLM response."""
        response = response.strip()

        # Remove markdown code blocks (common LLM behavior)
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]

        response = response.strip()

        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
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
        with open("output/test_creative.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        insights = data["insights"][:3]  # take first 3 insights

        # Sample cohort
        market = "singapore"
        model = "arcee-ai/trinity-mini:free"
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
            tasks = []

            for insight in insights:
                for variation in insight["variations"]:
                    task = evaluator.evaluate(
                        variation,
                        insight["cohort"],
                        insight["insight_template"],
                        market,
                        model,
                    )

                    tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)
            duration = time.time() - start

            print(results)

            successes = 0
            failures = 0

            # Process generation results
            evaluated_insights = []

            for insight in insights:
                new_insight = insight.copy()
                evaluated_variations = []

            #     for idx, variation in enumerate(insight["variations"]):
            #         result = results.pop(0)

            #         new_variation = variation.copy()
            #         if isinstance(result, Exception):
            #             failures += 1
            #             new_variation["evaluation"] = {
            #                 "error": True,
            #                 "message": str(result),
            #             }
            #         elif isinstance(result, dict) and "criteria" in result:
            #             successes += 1
            #             new_variation["evaluation"] = result
            #         else:
            #             failures += 1
            #             new_variation["evaluation"] = {
            #                 "error": True,
            #                 "message": f"Unknown object: {type(result)}",
            #             }

            #         evaluated_variations.append(new_variation)

            #     new_insight["variations"] = evaluated_variations
            #     evaluated_insights.append(new_insight)

            # print(f"✓ Completed {len(results)} evaluations in {duration:.2f}s")
            # print(f"✓ Success rate: {successes}/{len(tasks)}")
            # print(f"Average: {duration / len(results):.2f}s per insight\n")

            # print(evaluated_insights)

            # output_data = {
            #     "creative_metadata": data["creative_metadata"],
            #     "generation_metadata": data["generation_metadata"],
            #     "evaluation_metadata": {
            #         "market": market,
            #         "model": model,
            #         "temperature": 0.3,
            #         "max_tokens": 4000,
            #         "generated_at": datetime.datetime.now().isoformat(),
            #         "total_calls": len(tasks),
            #         "successful_calls": successes,
            #         "failed_calls": failures,
            #         "duration_seconds": round(duration, 2),
            #     },
            #     "insights": evaluated_insights,
            # }

            # # Save to JSON with two-level metadata structure
            # output_dir = Path("output")
            # output_dir.mkdir(parents=True, exist_ok=True)

            # timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            # output_file = output_dir / f"evaluated_{timestamp}.json"

            # with open(output_file, "w", encoding="utf-8") as f:
            #     json.dump(output_data, f, indent=2, ensure_ascii=False)

            # print(f"\n✓ Saved to: {output_file}")

    # Run test
    asyncio.run(main())
