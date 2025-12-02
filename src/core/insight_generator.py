"""
Insight Generator with async/parallel processing support.
"""

import asyncio
import json
from typing import Dict, Any
from src.core.llm_client import OpenRouterClient
from src.prompts.prompt_templates import PromptTemplates


class InsightGenerator:
    """Insight generation orchestrator with async support."""

    def __init__(
        self,
        llm_client: OpenRouterClient,
        prompt_template: PromptTemplates,
        max_concurrent: int = 10,
    ):
        """
        Initialize insight generator.

        Args:
            llm_client: OpenRouterClient instance
            prompt_template: PromptTemplates instance
            max_concurrent: Maximum number of concurrent generation calls (default: 10)
        """
        self.llm = llm_client
        self.prompt_template = prompt_template
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def generate(
        self,
        cohort: dict,
        insight_template: dict,
        health_domains: dict,
        sources: dict,
        market: str = "singapore",
        num_insights: int = 5,
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
    ) -> Dict[str, Any]:
        """
        Generate insights asynchronously.

        Uses semaphore to limit concurrent generations and prevent overwhelming the API.
        """

        async with self.semaphore:
            # Build prompt
            prompt = self.prompt_template.generation_prompt(
                cohort=cohort,
                insight_template=insight_template,
                health_domains=health_domains,
                sources=sources,
                market=market,
                num_insights=num_insights,
            )

            # Call LLM asynchronously
            response = await self.llm.generate(prompt, model, temperature, max_tokens)

            # Parse response
            return self._parse_json_response(response)

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
            print("❌ JSON PARSE ERROR")
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


if __name__ == "__main__":
    from src.utils.config_loader import ConfigLoader
    from dotenv import load_dotenv
    import time
    import datetime
    from pathlib import Path

    # Load environment variables
    load_dotenv(Path(__file__).parent.parent.parent / ".env")

    async def main():
        """Test concurrent generation."""
        market = "singapore"
        loader = ConfigLoader(market=market)
        cohorts = loader.priority_cohorts
        insight_templates = loader.insight_templates
        sources = loader.source_names
        health_domains = loader.health_domains
        model = "arcee-ai/trinity-mini:free"
        prompt_template = PromptTemplates()

        async with OpenRouterClient(model=model) as llm_client:
            generator = InsightGenerator(llm_client, prompt_template, max_concurrent=5)

            start_time = time.time()

            # Create all generation tasks
            gen_tasks = []
            task_metadata = []  # Track which cohort+template each task corresponds to

            # Run all generations concurrently
            for cohort in cohorts:
                for template in insight_templates.values():
                    task = generator.generate(
                        cohort=cohort,
                        insight_template=template,
                        health_domains=health_domains,
                        sources=sources,
                        market=market,
                        num_insights=5,
                        model=model,
                        temperature=0.7,
                        max_tokens=4000,
                    )
                    gen_tasks.append(task)
                    task_metadata.append(
                        {"cohort": cohort, "insight_template": template}
                    )
                    break  # WE ONLY DO 1 TEMPLATE FOR THIS

            print(f"Launching {len(gen_tasks)} generation tasks/calls...")
            results = await asyncio.gather(*gen_tasks, return_exceptions=True)

            duration = time.time() - start_time

            # Print results
            print(f"\nProcessed {len(results)} calls in {duration:.1f}s")
            print("Total requests:", llm_client.total_requests)
            print("Successful requests:", llm_client.successful_requests)
            print("Failed requests:", llm_client.failed_requests)

            generation_successes = 0
            generation_failures = 0

            # Process generation results
            all_insights = []
            for result, metadata in zip(results, task_metadata):
                if isinstance(result, Exception):
                    generation_failures += 1
                    print(f"Generation failed: {str(result)[:100]}")
                elif isinstance(result, dict) and "insights" in result:
                    generation_successes += 1

                    # Attach only varying metadata to each insight
                    for insight in result["insights"]:
                        insight["cohort"] = metadata["cohort"]
                        insight["insight_template"] = metadata["insight_template"]
                        insight["generation_model"] = model
                        all_insights.append(insight)
                elif isinstance(result, list) and len(result) > 0:
                    # Handle case where LLM returns list directly instead of {"insights": [...]}
                    print(f"Got list instead of dict (length: {len(result)})")
                    try:
                        for insight in result:
                            if isinstance(insight, dict):
                                insight["cohort"] = metadata["cohort"]
                                insight["insight_template"] = metadata[
                                    "insight_template"
                                ]
                                insight["generation_model"] = model
                                all_insights.append(insight)
                            else:
                                print(f"Skipping non-dict item: {type(insight)}")
                        generation_successes += 1
                    except Exception as e:
                        generation_failures += 1
                        print(f"Failed to process list result: {str(e)[:100]}")
                else:
                    # Unexpected format
                    generation_failures += 1
                    print(f"Unexpected result format: {type(result)}")

            print(f"\n✓ Generated {len(all_insights)} total insights")
            print(f"✓ Success rate: {generation_successes}/{len(gen_tasks)}")

            # Save to JSON with two-level metadata structure
            output_dir = Path("output")
            output_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = output_dir / f"insights_{market}_{timestamp}.json"

            output_data = {
                "generation_metadata": {
                    "market": market,
                    "generation_model": model,
                    "generation_temperature": 0.7,
                    "max_tokens": 4000,
                    "generated_at": datetime.datetime.now().isoformat(),
                    "num_cohorts": len(cohorts),
                    "num_templates": len(insight_templates),
                    "total_calls": len(gen_tasks),
                    "successful_calls": generation_successes,
                    "failed_calls": generation_failures,
                    "duration_seconds": round(duration, 2),
                },
                "insights": all_insights,
            }

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)

            print(f"\n✓ Saved to: {output_file}")

    asyncio.run(main())
