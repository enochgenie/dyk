"""
Async Evaluator Layer
Ensures insights are factually accurate, safe, faithful to evidence, relevant, actionable, and culturally appropriate.
"""

import asyncio
import json
from typing import Any, Dict, List
from src.prompts.prompt_templates import PromptTemplates
from src.core.insight_generator_async import AsyncOpenRouterClient


class AsyncInsightEvaluator:
    """
    Async evaluator for DYK insights with parallel processing support.

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
        llm: AsyncOpenRouterClient,
        prompt_templates: PromptTemplates,
        max_concurrent: int = 20,
    ):
        """
        Initialize async evaluator.

        Args:
            llm: AsyncOpenRouterClient instance
            prompt_templates: PromptTemplates instance
            max_concurrent: Maximum number of concurrent evaluations (default: 20)
        """
        self.llm = llm
        self.prompts = prompt_templates
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
            prompt = self.prompts.validation_prompt(
                insight, cohort, insight_template, market
            )

            # Call LLM asynchronously
            evaluation_results = await self.llm.generate(
                prompt, model, temperature, max_tokens
            )
            evaluation_results = self._parse_json_response(evaluation_results)

            return evaluation_results

    # async def evaluate_batch(
    #     self,
    #     insights: List[Dict[str, Any]],
    #     cohorts: List[Dict[str, Any]],
    #     insight_templates: List[Dict[str, Any]],
    #     region: str,
    #     model: str = None,
    #     temperature: float = 0.3,
    #     max_tokens: int = 3000,
    # ) -> List[Dict[str, Any]]:
    #     """
    #     Evaluate multiple insights in parallel.

    #     Args:
    #         insights: List of insights to evaluate
    #         cohorts: List of corresponding cohorts
    #         insight_templates: List of corresponding templates
    #         region: Target region
    #         model: Model to use
    #         temperature: Sampling temperature
    #         max_tokens: Maximum tokens

    #     Returns:
    #         List of evaluation results (or exceptions if failed)
    #     """

    #     tasks = [
    #         self.evaluate(
    #             insight, cohort, template, region, model, temperature, max_tokens
    #         )
    #         for insight, cohort, template in zip(insights, cohorts, insight_templates)
    #     ]

    #     # return_exceptions=True means one failure won't stop the others
    #     return await asyncio.gather(*tasks, return_exceptions=True)

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
    import asyncio
    import time
    from pathlib import Path
    from dotenv import load_dotenv
    from src.utils.config_loader import ConfigLoader

    # Load environment variables
    load_dotenv(Path(__file__).parent.parent.parent / ".env")

    async def test_async_evaluator():
        """Test async evaluator with parallel evaluation."""

        # Sample insights to evaluate
        insights = [
            {
                "hook": "Did you know that regular exercise can reduce your risk of depression by up to 30%?",
                "explanation": "Engaging in physical activity releases endorphins and other chemicals that improve mood and reduce stress, which is particularly beneficial for individuals aged 50-59 who are obese.",
                "action": "Aim for at least 150 minutes of moderate exercise each week, such as brisk walking or cycling.",
                "source_name": "Health Promotion Board (HPB)",
                "source_url": "https://www.healthhub.sg",
                "numeric_claim": "reduce your risk of depression by up to 30%",
            },
            {
                "hook": "Did you know getting 7-8 hours of sleep can reduce obesity risk by 20%?",
                "explanation": "Adequate sleep regulates hormones that control appetite and metabolism, helping maintain healthy weight.",
                "action": "Set a consistent bedtime and create a relaxing pre-sleep routine.",
                "source_name": "Ministry of Health Singapore",
                "source_url": "https://www.moh.gov.sg",
                "numeric_claim": "reduce obesity risk by 20%",
            },
            {
                "hook": "Did you know eating 5 servings of fruits and vegetables daily reduces chronic disease risk by 25%?",
                "explanation": "Plant foods provide essential nutrients, fiber, and antioxidants that protect against disease.",
                "action": "Fill half your plate with vegetables and fruits at each meal.",
                "source_name": "Health Promotion Board",
                "source_url": "https://www.hpb.gov.sg",
                "numeric_claim": "reduces chronic disease risk by 25%",
            },
        ]

        # Sample cohort
        market = "singapore"
        model = "google/gemini-2.5-flash"
        loader = ConfigLoader(market=market)
        cohort = loader.priority_cohorts[0]
        insight_template = loader.insight_templates["quantified_action_benefit"]

        print("\n" + "=" * 80)
        print("ASYNC EVALUATOR TEST")
        print("=" * 80)
        print(f"Evaluating {len(insights)} insights in parallel...")
        print(f"Model: {model}")
        print("=" * 80 + "\n")

        # Create async client
        async with AsyncOpenRouterClient(model=model) as client:
            # Create evaluator with concurrency control
            evaluator = AsyncInsightEvaluator(
                llm=client,
                prompt_templates=PromptTemplates(),
                max_concurrent=3,  # Evaluate 3 at a time
            )

            # Test 1: Evaluate single insight
            print("[TEST 1] Single evaluation...")

            start = time.time()
            result = await evaluator.evaluate(
                insight=insights[0],
                cohort=cohort,
                insight_template=insight_template,
                market=market,
                model=model,
            )
            duration = time.time() - start

            print(f"✓ Completed in {duration:.2f}s")
            print(f"Score: {result.get('overall_score', 'N/A')}")
            print(f"Recommendation: {result.get('recommendation', 'N/A')}\n")

            # Test 2: Evaluate batch in parallel
            print(f"[TEST 2] Batch evaluation ({len(insights)} insights)...")

            start = time.time()
            tasks = [
                evaluator.evaluate(insight, cohort, insight_template, market, model)
                for insight in insights
            ]

            # return_exceptions=True means one failure won't stop the others
            results = await asyncio.gather(*tasks, return_exceptions=True)
            duration = time.time() - start

            print(f"✓ Completed {len(results)} evaluations in {duration:.2f}s")
            print(f"Average: {duration / len(results):.2f}s per insight\n")

            # Display results
            print("=" * 80)
            print("EVALUATION RESULTS")
            print("=" * 80)

            for i, (insight, result) in enumerate(zip(insights, results), 1):
                print("Insight:", insight)
                print("Result:", result)

            print("\n" + "=" * 80)
            print(f"✓ Async evaluation test complete!")
            print("=" * 80 + "\n")

    # Run test
    asyncio.run(test_async_evaluator())
