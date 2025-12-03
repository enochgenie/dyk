"""
Async DYK Pipeline - Complete Insight Generation Flow

Pipeline Flow:
1. Generate insights (async parallel)
2. Deduplicate insights (sync)
3. Creative rewriting (async parallel)
4. Evaluate rewritten insights (async parallel)
5. Save results to JSON and CSV
"""

import asyncio
import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import argparse
from dotenv import load_dotenv
import networkx as nx

from src.core.llm_client import OpenRouterClient, RateLimiter
from src.core.insight_generator import InsightGenerator
from src.core.deduplicator import InsightDeduplicator
from src.core.creative_rewriter import CreativeRewriter
from src.core.evaluator import InsightEvaluator
from src.prompts.prompt_templates import PromptTemplates
from src.utils.config_loader import ConfigLoader

load_dotenv(Path(__file__).parent.parent / ".env")


class DYKPipeline:
    """Complete pipeline for generating, rewriting, and evaluating DYK insights."""

    def __init__(
        self,
        market: str = "singapore",
        generation_model: str = "google/gemini-2.5-flash",
        creative_model: str = "google/gemini-2.5-flash",
        evaluation_model: str = "google/gemini-2.5-flash",
        max_concurrent_generations: int = 10,
        max_concurrent_creative: int = 15,
        max_concurrent_evaluations: int = 20,
        generation_temperature: float = 0.7,
        creative_temperature: float = 0.8,
        evaluation_temperature: float = 0.3,
        requests_per_minute: int = 60,
        requests_per_second: int = 10,
    ):
        """
        Initialize async pipeline.

        Args:
            market: Target market (e.g., 'singapore')
            generation_model: Model for insight generation
            creative_model: Model for creative rewriting
            evaluation_model: Model for insight evaluation
            max_concurrent_generations: Max parallel generations
            max_concurrent_creative: Max parallel creative rewrites
            max_concurrent_evaluations: Max parallel evaluations
            generation_temperature: Temperature for generation (default: 0.7)
            creative_temperature: Temperature for creative rewriting (default: 0.8)
            evaluation_temperature: Temperature for evaluation (default: 0.3)
            requests_per_minute: API rate limit per minute
            requests_per_second: API rate limit per second
        """
        self.market = market
        self.generation_model = generation_model
        self.creative_model = creative_model
        self.evaluation_model = evaluation_model
        self.max_concurrent_generations = max_concurrent_generations
        self.max_concurrent_creative = max_concurrent_creative
        self.max_concurrent_evaluations = max_concurrent_evaluations
        self.generation_temperature = generation_temperature
        self.creative_temperature = creative_temperature
        self.evaluation_temperature = evaluation_temperature

        # Load config
        self.loader = ConfigLoader(market=market)
        self.prompt_templates = PromptTemplates()

        # Shared rate limiter for all LLM calls
        self.rate_limiter = RateLimiter(
            requests_per_minute=requests_per_minute,
            requests_per_second=requests_per_second,
        )

        # Statistics
        self.stats = {
            "generation_attempts": 0,
            "generation_successes": 0,
            "generation_failures": 0,
            "total_insights_generated": 0,
            "deduplication_threshold": 0.0,
            "unique_insights_after_dedup": 0,
            "creative_attempts": 0,
            "creative_successes": 0,
            "creative_failures": 0,
            "total_variations_created": 0,
            "evaluation_attempts": 0,
            "evaluation_successes": 0,
            "evaluation_failures": 0,
            "final_insights": 0,
            "generation_time": 0.0,
            "deduplication_time": 0.0,
            "creative_time": 0.0,
            "evaluation_time": 0.0,
            "total_time": 0.0,
        }

    async def run_async(
        self,
        max_cohorts: int = None,
        insights_per_call: int = 5,
        dedup_threshold: float = 0.85,
        num_variations: int = 3,
        output_dir: str = "output",
    ) -> List[Dict[str, Any]]:
        """
        Run the complete async pipeline.

        Args:
            max_cohorts: Maximum number of cohorts to process (None = all)
            insights_per_call: Number of insights to generate per API call
            dedup_threshold: Similarity threshold for deduplication (0.0-1.0)
            num_variations: Number of creative variations per insight
            output_dir: Directory to save results

        Returns:
            List of evaluated insights with creative variations
        """
        pipeline_start = time.time()

        print("\n" + "=" * 80)
        print("DYK COMPLETE PIPELINE")
        print("=" * 80)
        print(f"Market: {self.market}")
        print(f"Generation Model: {self.generation_model}")
        print(f"Creative Model: {self.creative_model}")
        print(f"Evaluation Model: {self.evaluation_model}")
        print(f"Deduplication Threshold: {dedup_threshold}")
        print(f"Variations per Insight: {num_variations}")
        print("=" * 80 + "\n")

        # ========================================
        # STEP 1: Load Configuration
        # ========================================
        print("[STEP 1] Loading configuration...")
        cohorts = self.loader.priority_cohorts
        if max_cohorts:
            cohorts = cohorts[:max_cohorts]

        insight_templates = self.loader.insight_templates
        sources = self.loader.source_names
        health_domains = self.loader.health_domains

        print(f"Cohorts: {len(cohorts)}")
        print(f"Templates: {len(insight_templates)}")
        print(f"Total combinations: {len(cohorts) * len(insight_templates)}\n")

        # ========================================
        # STEP 2: Generate Insights
        # ========================================
        print("[STEP 2] Generating insights...")
        gen_start = time.time()

        async with OpenRouterClient(
            model=self.generation_model, rate_limiter=self.rate_limiter
        ) as gen_client:
            generator = InsightGenerator(
                llm_client=gen_client,
                prompt_template=self.prompt_templates,
                max_concurrent=self.max_concurrent_generations,
            )

            # Create generation tasks
            generation_tasks = []
            task_metadata = []

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
                        {"cohort": cohort, "insight_template": template}
                    )

            self.stats["generation_attempts"] = len(generation_tasks)
            print(f"Launching {len(generation_tasks)} generation tasks...")

            results = await asyncio.gather(*generation_tasks, return_exceptions=True)

        gen_duration = time.time() - gen_start
        self.stats["generation_time"] = gen_duration
        generation_timestamp = datetime.now().isoformat()

        # Process generation results
        all_insights = []
        for result, metadata in zip(results, task_metadata):
            if isinstance(result, Exception):
                self.stats["generation_failures"] += 1
                print(f"Generation failed: {str(result)[:100]}")
            elif isinstance(result, dict) and "insights" in result:
                self.stats["generation_successes"] += 1

                for insight in result["insights"]:
                    insight["insight_id"] = str(uuid.uuid4())
                    insight["cohort"] = metadata["cohort"]
                    insight["insight_template"] = metadata["insight_template"]
                    insight["generation_model"] = self.generation_model
                    insight["generated_at"] = generation_timestamp
                    all_insights.append(insight)

        self.stats["total_insights_generated"] = len(all_insights)

        print(f"✓ Generation complete in {gen_duration:.1f}s")
        print(f"✓ Generated {len(all_insights)} insights")
        print(
            f"✓ Success rate: {self.stats['generation_successes']}/{self.stats['generation_attempts']}\n"
        )

        if len(all_insights) == 0:
            print("No insights generated. Exiting.\n")
            return []

        # ========================================
        # STEP 3: Deduplicate Insights
        # ========================================
        print(f"[STEP 3] Deduplicating insights (threshold={dedup_threshold})...")
        dedup_start = time.time()

        deduplicator = InsightDeduplicator(
            insights=all_insights,
            threshold=dedup_threshold,
            model_name="all-MiniLM-L6-v2",
        )

        deduplicator.compute_embeddings(show_progress=False)
        dedup_analysis = deduplicator.analyze()

        # Get unique insights (filter out duplicates)
        # Use connected components approach - keep one from each cluster
        similarity_matrix = deduplicator.get_similarity_matrix()

        n = len(all_insights)
        G = nx.Graph()
        G.add_nodes_from(range(n))

        for i in range(n):
            for j in range(i + 1, n):
                if similarity_matrix[i, j] >= dedup_threshold:
                    G.add_edge(i, j)

        clusters = list(nx.connected_components(G))
        unique_indices = [
            min(cluster) for cluster in clusters
        ]  # Keep first from each cluster
        unique_insights = [all_insights[i] for i in sorted(unique_indices)]

        dedup_duration = time.time() - dedup_start
        self.stats["deduplication_time"] = dedup_duration
        self.stats["deduplication_threshold"] = dedup_threshold
        self.stats["unique_insights_after_dedup"] = len(unique_insights)

        print(f"✓ Deduplication complete in {dedup_duration:.1f}s")
        print(f"✓ Unique insights: {len(unique_insights)} (from {len(all_insights)})")
        print(
            f"✓ Reduction: {(1 - len(unique_insights) / len(all_insights)) * 100:.1f}%"
        )

        # Print analytics summary
        overall = dedup_analysis["overall"]
        print(f"✓ Cluster count: {overall.iloc[0]['cluster_count']}")
        print(
            f"✓ Mean duplicates per insight: {overall.iloc[0]['mean_duplicates_per_insight']:.2f}\n"
        )

        # ========================================
        # STEP 4: Creative Rewriting
        # ========================================
        print(f"[STEP 4] Creating {num_variations} creative variations per insight...")
        creative_start = time.time()

        async with OpenRouterClient(
            model=self.creative_model, rate_limiter=self.rate_limiter
        ) as creative_client:
            rewriter = CreativeRewriter(
                llm_client=creative_client,
                prompt_template=self.prompt_templates,
                max_concurrent=self.max_concurrent_creative,
            )

            creative_tasks = [
                rewriter.rewrite(
                    insight=insight,
                    cohort=insight["cohort"],
                    market=self.market,
                    num_variations=num_variations,
                    model=self.creative_model,
                    temperature=self.creative_temperature,
                    max_tokens=4000,
                )
                for insight in unique_insights
            ]

            self.stats["creative_attempts"] = len(creative_tasks)
            print(f"Launching {len(creative_tasks)} creative rewriting tasks...")

            creative_results = await asyncio.gather(
                *creative_tasks, return_exceptions=True
            )

        creative_duration = time.time() - creative_start
        self.stats["creative_time"] = creative_duration
        creative_timestamp = datetime.now().isoformat()

        # Process creative results - flatten variations
        all_variations = []
        for insight, result in zip(unique_insights, creative_results):
            if isinstance(result, Exception):
                self.stats["creative_failures"] += 1
                print(f"Creative rewriting failed: {str(result)[:100]}")
            elif isinstance(result, dict) and "variations" in result:
                self.stats["creative_successes"] += 1

                for idx, variation in enumerate(result["variations"]):
                    all_variations.append(
                        {
                            "variation_id": f"{insight['insight_id']}_v{idx + 1}",
                            "hook": variation.get("hook", ""),
                            "explanation": variation.get("explanation", ""),
                            "action": variation.get("action", ""),
                            "narrative_angle": variation.get("narrative_angle", ""),
                            "insight_id": insight["insight_id"],
                            "original_hook": insight.get("hook", ""),
                            "original_explanation": insight.get("explanation", ""),
                            "original_action": insight.get("action", ""),
                            "source_name": insight.get("source_name", ""),
                            "source_url": insight.get("source_url", ""),
                            "numeric_claim": insight.get("numeric_claim", ""),
                            "cohort": insight["cohort"],
                            "insight_template": insight["insight_template"],
                            "generation_model": insight["generation_model"],
                            "generated_at": insight["generated_at"],
                            "creative_model": self.creative_model,
                            "created_at": creative_timestamp,
                        }
                    )

        self.stats["total_variations_created"] = len(all_variations)

        print(f"✓ Creative rewriting complete in {creative_duration:.1f}s")
        print(f"✓ Created {len(all_variations)} variations")
        print(
            f"✓ Success rate: {self.stats['creative_successes']}/{self.stats['creative_attempts']}\n"
        )

        if len(all_variations) == 0:
            print("No variations created. Exiting.\n")
            return []

        # ========================================
        # STEP 5: Evaluate Variations
        # ========================================
        print(f"[STEP 5] Evaluating {len(all_variations)} variations...")
        eval_start = time.time()

        async with OpenRouterClient(
            model=self.evaluation_model, rate_limiter=self.rate_limiter
        ) as eval_client:
            evaluator = InsightEvaluator(
                llm_client=eval_client,
                prompt_template=self.prompt_templates,
                max_concurrent=self.max_concurrent_evaluations,
            )

            eval_tasks = [
                evaluator.evaluate(
                    insight=variation,
                    cohort=variation["cohort"],
                    insight_template=variation["insight_template"],
                    market=self.market,
                    model=self.evaluation_model,
                    temperature=self.evaluation_temperature,
                    max_tokens=4000,
                )
                for variation in all_variations
            ]

            self.stats["evaluation_attempts"] = len(eval_tasks)
            print(f"Launching {len(eval_tasks)} evaluation tasks...")

            eval_results = await asyncio.gather(*eval_tasks, return_exceptions=True)

        eval_duration = time.time() - eval_start
        self.stats["evaluation_time"] = eval_duration
        evaluation_timestamp = datetime.now().isoformat()

        # Process evaluation results
        evaluated_insights = []
        for variation, result in zip(all_variations, eval_results):
            if isinstance(result, Exception):
                self.stats["evaluation_failures"] += 1
                print(f"Evaluation failed: {str(result)[:100]}")
                variation["evaluation"] = {"status": "failed", "error": str(result)}
            elif isinstance(result, dict) and "criteria" in result:
                self.stats["evaluation_successes"] += 1
                variation["evaluation"] = result
            else:
                self.stats["evaluation_failures"] += 1
                variation["evaluation"] = {
                    "status": "failed",
                    "error": f"Unknown object: {type(result)}",
                }

            variation["evaluation_model"] = self.evaluation_model
            variation["evaluated_at"] = evaluation_timestamp
            evaluated_insights.append(variation)

        self.stats["final_insights"] = len(evaluated_insights)

        print(f"✓ Evaluation complete in {eval_duration:.1f}s")
        print(
            f"✓ Success rate: {self.stats['evaluation_successes']}/{self.stats['evaluation_attempts']}\n"
        )

        # ========================================
        # STEP 6: Save Results
        # ========================================
        print("[STEP 6] Saving results...")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Prepare output data
        output_data = {
            "generation_metadata": {
                "market": self.market,
                "model": self.generation_model,
                "temperature": self.generation_temperature,
                "max_tokens": 4000,
                "generated_at": generation_timestamp,
                "total_calls": self.stats["generation_attempts"],
                "successful_calls": self.stats["generation_successes"],
                "failed_calls": self.stats["generation_failures"],
                "duration_seconds": round(self.stats["generation_time"], 2),
            },
            "deduplication_metadata": {
                "threshold": dedup_threshold,
                "total_insights": self.stats["total_insights_generated"],
                "unique_insights": self.stats["unique_insights_after_dedup"],
                "reduction_pct": round(
                    (
                        1
                        - self.stats["unique_insights_after_dedup"]
                        / self.stats["total_insights_generated"]
                    )
                    * 100,
                    2,
                )
                if self.stats["total_insights_generated"] > 0
                else 0,
                "duration_seconds": round(self.stats["deduplication_time"], 2),
            },
            "deduplication_analytics": {
                "overall": dedup_analysis["overall"].to_dict(orient="records")[0],
                "by_cohort": dedup_analysis["by_cohort"].to_dict(orient="records"),
                "by_template": dedup_analysis["by_template"].to_dict(orient="records"),
                "worst_insights": dedup_analysis["worst_insights"].to_dict(
                    orient="records"
                ),
            },
            "creative_metadata": {
                "market": self.market,
                "model": self.creative_model,
                "temperature": self.creative_temperature,
                "max_tokens": 4000,
                "generated_at": creative_timestamp,
                "total_calls": self.stats["creative_attempts"],
                "successful_calls": self.stats["creative_successes"],
                "failed_calls": self.stats["creative_failures"],
                "duration_seconds": round(self.stats["creative_time"], 2),
            },
            "evaluation_metadata": {
                "market": self.market,
                "model": self.evaluation_model,
                "temperature": self.evaluation_temperature,
                "max_tokens": 4000,
                "generated_at": evaluation_timestamp,
                "total_calls": self.stats["evaluation_attempts"],
                "successful_calls": self.stats["evaluation_successes"],
                "failed_calls": self.stats["evaluation_failures"],
                "duration_seconds": round(self.stats["evaluation_time"], 2),
            },
            "insights": evaluated_insights,
        }

        # Save JSON
        json_file = output_path / f"pipeline_{self.market}_{timestamp}.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"✓ Saved JSON: {json_file}")

        # Save CSV
        import csv

        csv_file = output_path / f"pipeline_{self.market}_{timestamp}.csv"

        with open(csv_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)

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

        print(f"✓ Saved CSV: {csv_file}\n")

        # ========================================
        # STEP 7: Summary
        # ========================================
        pipeline_duration = time.time() - pipeline_start
        self.stats["total_time"] = pipeline_duration

        print("=" * 80)
        print("PIPELINE COMPLETE")
        print("=" * 80)
        print(f"Total time: {pipeline_duration:.1f}s")
        print(f"  - Generation: {self.stats['generation_time']:.1f}s")
        print(f"  - Deduplication: {self.stats['deduplication_time']:.1f}s")
        print(f"  - Creative: {self.stats['creative_time']:.1f}s")
        print(f"  - Evaluation: {self.stats['evaluation_time']:.1f}s")
        print("\nFlow:")
        print(f"  - Generated: {self.stats['total_insights_generated']} insights")
        print(
            f"  - After dedup: {self.stats['unique_insights_after_dedup']} unique insights"
        )
        print(f"  - Created: {self.stats['total_variations_created']} variations")
        print(f"  - Evaluated: {self.stats['final_insights']} final insights")
        print("=" * 80 + "\n")

        return evaluated_insights


async def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Run complete DYK pipeline")

    parser.add_argument("--market", type=str, default="singapore", help="Target market")
    parser.add_argument(
        "--generation-model", type=str, default="google/gemini-2.5-flash"
    )
    parser.add_argument("--creative-model", type=str, default="google/gemini-2.5-flash")
    parser.add_argument(
        "--evaluation-model", type=str, default="google/gemini-2.5-flash"
    )
    parser.add_argument(
        "--max-cohorts", type=int, default=None, help="Max cohorts to process"
    )
    parser.add_argument("--insights-per-call", type=int, default=5)
    parser.add_argument("--dedup-threshold", type=float, default=0.85)
    parser.add_argument("--num-variations", type=int, default=3)
    parser.add_argument("--max-concurrent-generations", type=int, default=10)
    parser.add_argument("--max-concurrent-creative", type=int, default=15)
    parser.add_argument("--max-concurrent-evaluations", type=int, default=20)
    parser.add_argument("--output-dir", type=str, default="output")
    parser.add_argument("--requests-per-minute", type=int, default=60)
    parser.add_argument("--requests-per-second", type=int, default=10)

    args = parser.parse_args()

    pipeline = DYKPipeline(
        market=args.market,
        generation_model=args.generation_model,
        creative_model=args.creative_model,
        evaluation_model=args.evaluation_model,
        max_concurrent_generations=args.max_concurrent_generations,
        max_concurrent_creative=args.max_concurrent_creative,
        max_concurrent_evaluations=args.max_concurrent_evaluations,
        requests_per_minute=args.requests_per_minute,
        requests_per_second=args.requests_per_second,
    )

    insights = await pipeline.run_async(
        max_cohorts=args.max_cohorts,
        insights_per_call=args.insights_per_call,
        dedup_threshold=args.dedup_threshold,
        num_variations=args.num_variations,
        output_dir=args.output_dir,
    )

    print(f"✓ Pipeline complete! Generated {len(insights)} evaluated insights.\n")


if __name__ == "__main__":
    asyncio.run(main())
