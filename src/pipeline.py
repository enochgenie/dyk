"""
Async DYK Pipeline - Parallel Insight Generation and Evaluation

This pipeline:
1. Generates cohorts (sync)
2. Generates insights in parallel (async)
3. Evaluates insights in parallel (async) - SKIPS VALIDATION
4. Saves results to JSON and CSV
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import argparse

from src.core.llm_client import OpenRouterClient, RateLimiter
from src.core.insight_generator import InsightGenerator
from src.core.evaluator import InsightEvaluator
from src.core.creative_rewriter import CreativeRewriter
from src.core.cohort_generator import CohortGenerator
from src.prompts.prompt_templates import PromptTemplates
from src.utils.config_loader import ConfigLoader


class DYKPipeline:
    """Pipeline for generating and evaluating DYK insights."""

    def __init__(
        self,
        market: str = "singapore",
        generation_model: str = "google/gemini-2.5-flash",
        evaluation_model: str = "google/gemini-2.5-flash",
        max_concurrent_generations: int = 10,
        max_concurrent_evaluations: int = 20,
        generation_temperature: float = 0.7,
        evaluation_temperature: float = 0.3,
        requests_per_minute: int = 60,
        requests_per_second: int = 10,
    ):
        """
        Initialize async pipeline.

        Args:
            market: Target market (e.g., 'singapore')
            generation_model: Model for insight generation
            evaluation_model: Model for insight evaluation
            max_concurrent_generations: Max parallel generations
            max_concurrent_evaluations: Max parallel evaluations
            generation_temperature: Temperature for generation (default: 0.7)
            evaluation_temperature: Temperature for evaluation (default: 0.3)
            requests_per_minute: API rate limit per minute
            requests_per_second: API rate limit per second
        """
        self.market = market
        self.generation_model = generation_model
        self.evaluation_model = evaluation_model
        self.max_concurrent_generations = max_concurrent_generations
        self.max_concurrent_evaluations = max_concurrent_evaluations
        self.generation_temperature = generation_temperature
        self.evaluation_temperature = evaluation_temperature

        # Load config
        self.loader = ConfigLoader(market=market)
        self.prompt_templates = PromptTemplates()

        # Shared rate limiter for both generation and evaluation
        self.rate_limiter = RateLimiter(
            requests_per_minute=requests_per_minute,
            requests_per_second=requests_per_second,
        )

        # Statistics
        self.stats = {
            "cohorts_generated": 0,
            "generation_attempts": 0,
            "generation_successes": 0,
            "generation_failures": 0,
            "total_insights_generated": 0,
            "evaluation_attempts": 0,
            "evaluation_successes": 0,
            "evaluation_failures": 0,
            "final_insights": 0,
            "average_score": 0.0,
            "generation_time": 0.0,
            "evaluation_time": 0.0,
            "total_time": 0.0,
        }

    async def run_async(
        self,
        max_cohorts: int = None,
        insights_per_call: int = 3,
        output_dir: str = "output",
        min_score: float = 7.0,
    ) -> List[Dict[str, Any]]:
        """
        Run the async pipeline.

        Args:
            max_cohorts: Maximum number of cohorts to process (None = all)
            insights_per_call: Number of insights to generate per API call
            output_dir: Directory to save results
            min_score: Minimum evaluation score to keep insights (default: 7.0)

        Returns:
            List of evaluated insights
        """
        pipeline_start = time.time()

        print("\n" + "=" * 80)
        print("ASYNC DYK PIPELINE")
        print("=" * 80)
        print(f"Market: {self.market}")
        print(f"Generation Model: {self.generation_model}")
        print(f"Evaluation Model: {self.evaluation_model}")
        print(f"Max Concurrent Generations: {self.max_concurrent_generations}")
        print(f"Max Concurrent Evaluations: {self.max_concurrent_evaluations}")
        print(f"Minimum Score: {min_score}")
        print("=" * 80 + "\n")

        # ========================================
        # STEP 1: Read configuration files
        # ========================================
        print("[STEP 1] Reading configuration files...")
        cohorts = self.loader.priority_cohorts

        if max_cohorts:
            cohorts = cohorts[:max_cohorts]

        # Get insight templates
        insight_templates = self.loader.insight_templates
        total_combinations = len(cohorts) * len(insight_templates)

        print(
            f"Total combinations: {len(cohorts)} cohorts x {len(insight_templates)} templates = {total_combinations}\n"
        )

        # sources
        sources = self.loader.source_names
        health_domains = self.loader.health_domains

        # ========================================
        # STEP 2: Generate Insights
        # ========================================
        print("[STEP 2] Generating insights...")
        print(f"Max concurrent: {self.max_concurrent_generations}")
        print(f"Insights per call: {insights_per_call}\n")

        gen_start = time.time()

        async with OpenRouterClient(
            model=self.generation_model, rate_limiter=self.rate_limiter
        ) as gen_client:
            generator = InsightGenerator(
                llm_client=gen_client,
                prompt_template=self.prompt_templates,
                max_concurrent=self.max_concurrent_generations,
            )

            # Create all generation tasks
            generation_tasks = []
            task_metadata = []  # Track which cohort+template each task corresponds to

            for cohort in cohorts:
                for template in insight_templates.values():
                    task = generator.generate(
                        cohort=cohort,
                        insight_template=template,
                        health_domains=health_domains,
                        sources=sources,
                        market=self.market,
                        num_insights=insights_per_call,
                        model=self.generation_model,
                        temperature=self.generation_temperature,
                        max_tokens=4000,
                    )
                    generation_tasks.append(task)
                    task_metadata.append(
                        {
                            "cohort": cohort,
                            "insight_template": template,
                        }
                    )

            self.stats["generation_attempts"] = len(generation_tasks)
            print(f"  Launching {len(generation_tasks)} generation tasks...")

            # Execute all tasks in parallel
            results = await asyncio.gather(*generation_tasks, return_exceptions=True)

        gen_duration = time.time() - gen_start
        self.stats["generation_time"] = gen_duration

        # Process generation results
        all_insights = []
        for result, metadata in zip(results, task_metadata):
            if isinstance(result, Exception):
                self.stats["generation_failures"] += 1
                print(f"Generation failed: {str(result)[:100]}")
            elif isinstance(result, dict) and "insights" in result:
                self.stats["generation_successes"] += 1

                # Attach metadata to each insight
                for insight in result["insights"]:
                    insight["cohort"] = metadata["cohort"]["name"]
                    insight["insight_template"] = metadata["insight_template"]["type"]
                    insight["generated_at"] = datetime.now().isoformat()
                    all_insights.append(insight)

        self.stats["total_insights_generated"] = len(all_insights)

        print("Generation complete!")
        print(f"Time: {gen_duration:.1f}s")
        print(
            f"Success rate: {self.stats['generation_successes']}/{self.stats['generation_attempts']} ({self.stats['generation_successes'] / self.stats['generation_attempts'] * 100:.1f}%)"
        )
        print(f"Total insights generated: {len(all_insights)}\n")

        if len(all_insights) == 0:
            print("No insights generated. Exiting.\n")
            return []

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save to JSON
        json_file = output_path / f"insights_{self.market}_{timestamp}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "generation_metadata": {
                        "market": self.market,
                        "generation_model": self.generation_model,
                        "evaluation_model": self.evaluation_model,
                        "generated_at": datetime.now().isoformat(),
                        "pipeline_stats": self.stats,
                    },
                    "insights": all_insights,
                },
                f,
                indent=2,
                ensure_ascii=False,
            )

        print(f"Saved JSON: {json_file}")

        # # Save to CSV
        # csv_file = output_path / f"insights_{self.market}_{timestamp}.csv"
        # self._save_to_csv(all_insights, csv_file)
        # print(f"   Saved CSV: {csv_file}\n")

        # ========================================
        # STEP 3: Deduplication step (SKIP)
        # SKIPPING VALIDATION
        # ========================================


#         # ========================================
#         # STEP 3: Evaluate Insights (PARALLEL)
#         # SKIPPING VALIDATION
#         # ========================================
#         print(f"[STEP 3] Evaluating {len(all_insights)} insights in parallel...")
#         print(f"  Max concurrent: {self.max_concurrent_evaluations}")
#         print("  (Skipping validation - sources from pretrained data)\n")

#         eval_start = time.time()

#         async with OpenRouterClient(
#             model=self.evaluation_model, rate_limiter=self.rate_limiter
#         ) as eval_client:
#             evaluator = InsightEvaluator(
#                 llm=eval_client,
#                 prompt_templates=self.prompt_templates,
#                 max_concurrent=self.max_concurrent_evaluations,
#             )

#             # Create all evaluation tasks
#             eval_tasks = []
#             for insight in all_insights:
#                 task = evaluator.evaluate(
#                     insight=insight,
#                     cohort=insight["metadata"]["cohort"],
#                     insight_template=insight["metadata"]["template"],
#                     market=self.market,
#                     model=self.evaluation_model,
#                     temperature=self.evaluation_temperature,
#                     max_tokens=4000,
#                 )
#                 eval_tasks.append(task)

#             self.stats["evaluation_attempts"] = len(eval_tasks)
#             print(f"  Launching {len(eval_tasks)} evaluation tasks...")

#             # Execute all tasks in parallel
#             eval_results = await asyncio.gather(*eval_tasks, return_exceptions=True)

#         eval_duration = time.time() - eval_start
#         self.stats["evaluation_time"] = eval_duration

#         # Process evaluation results
#         evaluated_insights = []
#         scores = []

#         for insight, eval_result in zip(all_insights, eval_results):
#             if isinstance(eval_result, Exception):
#                 self.stats["evaluation_failures"] += 1
#                 print(f"   Evaluation failed: {str(eval_result)[:100]}")
#             elif isinstance(eval_result, dict):
#                 self.stats["evaluation_successes"] += 1
#                 insight["evaluation"] = eval_result

#                 # Track scores
#                 if "overall_score" in eval_result:
#                     score = eval_result["overall_score"]
#                     scores.append(score)

#                     # Only keep insights above minimum score
#                     if score >= min_score:
#                         evaluated_insights.append(insight)

#         self.stats["final_insights"] = len(evaluated_insights)
#         self.stats["average_score"] = sum(scores) / len(scores) if scores else 0.0

#         print(f"\n   Evaluation complete!")
#         print(f"  Time: {eval_duration:.1f}s")
#         print(
#             f"  Success rate: {self.stats['evaluation_successes']}/{self.stats['evaluation_attempts']} ({self.stats['evaluation_successes'] / self.stats['evaluation_attempts'] * 100:.1f}%)"
#         )
#         print(f"  Average score: {self.stats['average_score']:.2f}/10")
#         print(
#             f"  Insights above {min_score}: {len(evaluated_insights)}/{len(all_insights)} ({len(evaluated_insights) / len(all_insights) * 100:.1f}%)\n"
#         )

#         # ========================================
#         # STEP 4: Save Results
#         # ========================================
#         print(f"[STEP 4] Saving results...")

#         output_path = Path(output_dir)
#         output_path.mkdir(parents=True, exist_ok=True)

#         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

#         # Save to JSON
#         json_file = output_path / f"insights_{self.market}_{timestamp}.json"
#         with open(json_file, "w", encoding="utf-8") as f:
#             json.dump(
#                 {
#                     "metadata": {
#                         "market": self.market,
#                         "generation_model": self.generation_model,
#                         "evaluation_model": self.evaluation_model,
#                         "generated_at": datetime.now().isoformat(),
#                         "pipeline_stats": self.stats,
#                     },
#                     "insights": evaluated_insights,
#                 },
#                 f,
#                 indent=2,
#                 ensure_ascii=False,
#             )

#         print(f"   Saved JSON: {json_file}")

#         # Save to CSV
#         csv_file = output_path / f"insights_{self.market}_{timestamp}.csv"
#         self._save_to_csv(evaluated_insights, csv_file)
#         print(f"   Saved CSV: {csv_file}\n")

#         # ========================================
#         # STEP 5: Summary
#         # ========================================
#         pipeline_duration = time.time() - pipeline_start
#         self.stats["total_time"] = pipeline_duration

#         print("=" * 80)
#         print("PIPELINE COMPLETE")
#         print("=" * 80)
#         print(f"Total time: {pipeline_duration:.1f}s")
#         print(
#             f"  - Generation: {gen_duration:.1f}s ({gen_duration / pipeline_duration * 100:.1f}%)"
#         )
#         print(
#             f"  - Evaluation: {eval_duration:.1f}s ({eval_duration / pipeline_duration * 100:.1f}%)"
#         )
#         print(f"\nFinal insights: {len(evaluated_insights)}")
#         print(f"Average score: {self.stats['average_score']:.2f}/10")
#         print(f"\nThroughput:")
#         print(f"  - Generation: {len(all_insights) / gen_duration:.1f} insights/sec")
#         print(
#             f"  - Evaluation: {len(evaluated_insights) / eval_duration:.1f} insights/sec"
#         )
#         print(
#             f"  - Overall: {len(evaluated_insights) / pipeline_duration:.1f} insights/sec"
#         )
#         print("=" * 80 + "\n")

#         return evaluated_insights

#     def _save_to_csv(self, insights: List[Dict[str, Any]], filepath: Path):
#         """Save insights to CSV file."""
#         import csv

#         with open(filepath, "w", encoding="utf-8", newline="") as f:
#             fieldnames = [
#                 "hook",
#                 "explanation",
#                 "action",
#                 "source_name",
#                 "source_url",
#                 "numeric_claim",
#                 "cohort_name",
#                 "template_key",
#                 "overall_score",
#                 "recommendation",
#                 "generation_model",
#                 "generated_at",
#             ]

#             writer = csv.DictWriter(f, fieldnames=fieldnames)
#             writer.writeheader()

#             for insight in insights:
#                 row = {
#                     "hook": insight.get("hook", ""),
#                     "explanation": insight.get("explanation", ""),
#                     "action": insight.get("action", ""),
#                     "source_name": insight.get("source_name", ""),
#                     "source_url": insight.get("source_url", ""),
#                     "numeric_claim": insight.get("numeric_claim", ""),
#                     "cohort_name": insight.get("metadata", {})
#                     .get("cohort", {})
#                     .get("name", ""),
#                     "template_key": insight.get("metadata", {}).get("template_key", ""),
#                     "overall_score": insight.get("evaluation", {}).get(
#                         "overall_score", ""
#                     ),
#                     "recommendation": insight.get("evaluation", {}).get(
#                         "recommendation", ""
#                     ),
#                     "generation_model": insight.get("metadata", {}).get(
#                         "generation_model", ""
#                     ),
#                     "generated_at": insight.get("metadata", {}).get("generated_at", ""),
#                 }
#                 writer.writerow(row)


async def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run async DYK insight generation and evaluation pipeline"
    )

    parser.add_argument(
        "--market",
        type=str,
        default="singapore",
        help="Target market (default: singapore)",
    )

    parser.add_argument(
        "--generation-model",
        type=str,
        default="google/gemini-2.5-flash",
        help="Model for insight generation (default: google/gemini-2.5-flash)",
    )

    parser.add_argument(
        "--evaluation-model",
        type=str,
        default="google/gemini-2.5-flash",
        help="Model for insight evaluation (default: google/gemini-2.5-flash)",
    )

    parser.add_argument(
        "--max-cohorts",
        type=int,
        default=None,
        help="Maximum number of cohorts to process (default: all)",
    )

    parser.add_argument(
        "--insights-per-call",
        type=int,
        default=3,
        help="Number of insights to generate per API call (default: 3)",
    )

    parser.add_argument(
        "--max-concurrent-generations",
        type=int,
        default=10,
        help="Max concurrent generation tasks (default: 10)",
    )

    parser.add_argument(
        "--max-concurrent-evaluations",
        type=int,
        default=20,
        help="Max concurrent evaluation tasks (default: 20)",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="Output directory for results (default: output)",
    )

    parser.add_argument(
        "--min-score",
        type=float,
        default=7.0,
        help="Minimum evaluation score to keep insights (default: 7.0)",
    )

    parser.add_argument(
        "--requests-per-minute",
        type=int,
        default=60,
        help="API rate limit per minute (default: 60)",
    )

    parser.add_argument(
        "--requests-per-second",
        type=int,
        default=10,
        help="API rate limit per second (default: 10)",
    )

    args = parser.parse_args()

    # Create pipeline
    pipeline = DYKPipeline(
        market=args.market,
        generation_model=args.generation_model,
        evaluation_model=args.evaluation_model,
        max_concurrent_generations=args.max_concurrent_generations,
        max_concurrent_evaluations=args.max_concurrent_evaluations,
        requests_per_minute=args.requests_per_minute,
        requests_per_second=args.requests_per_second,
    )

    # Run pipeline
    insights = await pipeline.run_async(
        max_cohorts=args.max_cohorts,
        insights_per_call=args.insights_per_call,
        output_dir=args.output_dir,
        min_score=args.min_score,
    )

    print(f" Pipeline complete! Generated {len(insights)} high-quality insights.\n")


if __name__ == "__main__":
    asyncio.run(main())
