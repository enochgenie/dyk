"""
Insight Generator with async processing support.
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
                    f"⚠️  Auto-repaired JSON (Insight Generator): {e.msg} at position {e.pos}"
                )
                try:
                    return json.loads(repaired)
                except json.JSONDecodeError:
                    pass  # Repair failed, fall through to error logging

            # Repair failed or not attempted - log detailed error
            print("\n" + "=" * 80)
            print("❌ JSON PARSE ERROR (Insight Generator)")
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


if __name__ == "__main__":
    from src.utils.config_loader import ConfigLoader
    from dotenv import load_dotenv
    import time
    import datetime
    from pathlib import Path
    import uuid

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
            for cohort in cohorts[:2]:  # ONLY DO 2 COHORTS
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
                        insight["insight_id"] = str(uuid.uuid4())
                        insight["cohort"] = metadata["cohort"]
                        insight["cohort_name"] = metadata["cohort"]["name"]
                        insight["insight_template"] = metadata["insight_template"]
                        insight["insight_template_type"] = metadata["insight_template"][
                            "type"
                        ]
                        insight["generation_model"] = model
                        insight["generated_at"] = datetime.datetime.now().isoformat()
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
