"""
Async DYK Pipeline Orchestrator
High-performance pipeline using batch generation and async processing.
"""

import os
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import argparse
import sys
from dotenv import load_dotenv

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from core.cohort_generator import CohortGenerator
from core.insight_generator_async import AsyncBatchInsightGenerator, save_insights
from core.validator import InsightValidator, QualityScorer
from utils.config_loader import ConfigLoader

# Load environment variables from .env file in project root
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")


class AsyncDYKPipeline:
    """High-performance async DYK insight generation pipeline."""

    def __init__(
        self,
        openrouter_api_key: Optional[str] = None,
        pubmed_email: Optional[str] = None,
        pubmed_api_key: Optional[str] = None,
        market: str = "singapore",
        requests_per_minute: int = 60,
        max_concurrent: int = 10,
    ):
        """
        Initialize the async pipeline.

        Args:
            openrouter_api_key: OpenRouter API key
            pubmed_email: Email for PubMed API
            pubmed_api_key: Optional PubMed API key
            market: Market identifier
            requests_per_minute: API rate limit
            max_concurrent: Maximum concurrent API calls
        """
        # Load configuration
        loader = ConfigLoader()
        self.config = loader.load_market_config(market)
        self.market = market

        # Initialize components
        self.cohort_generator = CohortGenerator(market=market, config=self.config)
        self.insight_generator = AsyncBatchInsightGenerator(
            api_key=openrouter_api_key,
            pubmed_email=pubmed_email,
            pubmed_api_key=pubmed_api_key,
            requests_per_minute=requests_per_minute,
            max_concurrent=max_concurrent,
        )
        self.validator = InsightValidator(self.config)
        self.quality_scorer = QualityScorer()

        # Pipeline state
        self.cohorts = []
        self.insights = []
        self.validation_results = []

    async def run_full_pipeline(
        self,
        max_cohorts: Optional[int] = None,
        template_types: Optional[List[str]] = None,
        health_domains: Optional[List[str]] = None,
        insights_per_combination: int = 3,
        region: str = "singapore",
        validate: bool = True,
        filter_invalid: bool = True,
        min_quality_score: float = 60.0,
        output_dir: str = "output",
    ) -> Dict[str, Any]:
        """
        Run the complete async pipeline with batch generation.

        Args:
            max_cohorts: Maximum cohorts to process (None = all)
            template_types: Template types to use (None = use config weights)
            health_domains: Health domains to cover (None = use all from config)
            insights_per_combination: Insights per cohort×template×domain
            region: Target region
            validate: Whether to validate insights
            filter_invalid: Remove invalid insights
            min_quality_score: Minimum quality score threshold
            output_dir: Directory for output files

        Returns:
            Pipeline summary statistics
        """
        print("\n" + "=" * 80)
        print("ASYNC DYK INSIGHT GENERATION PIPELINE")
        print("=" * 80)

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Step 1: Generate cohorts
        print("\n[STEP 1] Generating cohorts...")
        self.cohorts = self.cohort_generator.generate_priority_cohorts()

        if max_cohorts:
            self.cohorts = self.cohorts[:max_cohorts]

        print(f"✓ Generated {len(self.cohorts)} cohorts")

        # Save cohorts
        cohorts_path = os.path.join(output_dir, f"cohorts_{timestamp}.json")
        with open(cohorts_path, "w") as f:
            json.dump(self.cohorts, f, indent=2)
        print(f"✓ Saved cohorts to {cohorts_path}")

        # Step 2: Determine template types from config weights
        if template_types is None:
            templates_by_weight = ConfigLoader().get_templates_by_weight(self.config)
            # Use top 5 templates by weight
            template_types = [t["type"] for t in templates_by_weight[:5]]
            print(f"\n[STEP 2] Selected top {len(template_types)} templates by weight:")
            for i, t in enumerate(templates_by_weight[:5], 1):
                print(f"  {i}. {t['type']} (weight: {t['weight']})")
        else:
            print(f"\n[STEP 2] Using specified templates: {template_types}")

        # Step 3: Determine health domains
        if health_domains is None:
            all_domains = self.config.get("health_domains", [])
            # Use top 5 domains
            health_domains = [d["name"] for d in all_domains[:5]]
            print(f"\n[STEP 3] Selected {len(health_domains)} health domains:")
            for domain in health_domains:
                print(f"  - {domain}")
        else:
            print(f"\n[STEP 3] Using specified domains: {health_domains}")

        # Step 4: Generate insights asynchronously
        print(f"\n[STEP 4] Generating insights using async batch method")
        total_combinations = len(self.cohorts) * len(template_types) * len(health_domains)
        total_expected = total_combinations * insights_per_combination
        print(f"Combinations: {len(self.cohorts)} cohorts × {len(template_types)} templates × {len(health_domains)} domains")
        print(f"Expected insights: {total_expected} ({insights_per_combination} per combination)")

        self.insights = await self.insight_generator.generate_batch_for_cohorts(
            cohort_specs=self.cohorts,
            template_types=template_types,
            health_domains=health_domains,
            region=region,
            insights_per_combination=insights_per_combination,
        )

        print(f"✓ Generated {len(self.insights)} insights")

        # Save raw insights
        raw_path = os.path.join(output_dir, f"insights_raw_{timestamp}.json")
        save_insights(self.insights, raw_path)

        # Step 5: Validate insights
        if validate:
            print("\n[STEP 5] Validating insights...")
            validation_summary = self.validator.validate_batch(self.insights)
            self.validation_results = validation_summary["results"]

            print(f"✓ Validated {validation_summary['total_insights']} insights")
            print(f"  - Valid: {validation_summary['valid_insights']}")
            print(f"  - Invalid: {validation_summary['invalid_insights']}")
            print(f"  - Average score: {validation_summary['average_score']:.1f}/100")
            print(f"  - Total issues: {validation_summary['total_issues']}")
            print(f"  - Total warnings: {validation_summary['total_warnings']}")

            # Add validation results to insights
            for insight, validation in zip(self.insights, self.validation_results):
                insight["validation"] = validation

            # Save validation summary
            validation_path = os.path.join(output_dir, f"validation_{timestamp}.json")
            with open(validation_path, "w") as f:
                json.dump(validation_summary, f, indent=2)
            print(f"✓ Saved validation results to {validation_path}")

        # Step 6: Check for duplicates
        print("\n[STEP 6] Checking for duplicates...")
        duplicates = self.validator.check_duplicates(self.insights, threshold=0.85)

        if duplicates:
            print(f"⚠ Found {len(duplicates)} duplicate pairs")
            # Remove duplicates (keep first occurrence)
            indices_to_remove = set(j for i, j, sim in duplicates)
            self.insights = [
                ins
                for idx, ins in enumerate(self.insights)
                if idx not in indices_to_remove
            ]
            print(f"✓ Removed {len(indices_to_remove)} duplicate insights")
        else:
            print("✓ No duplicates found")

        # Step 7: Calculate quality scores
        print("\n[STEP 7] Calculating quality scores...")
        for insight in self.insights:
            insight["quality_score"] = self.quality_scorer.calculate_engagement_score(
                insight
            )

        if self.insights:
            avg_quality = sum(i["quality_score"] for i in self.insights) / len(
                self.insights
            )
            print(f"✓ Average quality score: {avg_quality:.2f}/100")
        else:
            print("⚠ No insights generated - skipping quality scoring")

        # Step 8: Filter insights
        print("\n[STEP 8] Filtering insights...")
        initial_count = len(self.insights)

        if filter_invalid and validate:
            self.insights = [
                ins
                for ins in self.insights
                if ins.get("validation", {}).get("overall_valid", False)
            ]
            removed_invalid = initial_count - len(self.insights)
            print(f"✓ Filtered out {removed_invalid} invalid insights")
            initial_count = len(self.insights)

        # Filter by quality score
        self.insights = [
            ins
            for ins in self.insights
            if ins.get("quality_score", 0) >= min_quality_score
        ]
        removed_low_quality = initial_count - len(self.insights)
        print(f"✓ Filtered out {removed_low_quality} low-quality insights")
        print(f"✓ Final count: {len(self.insights)} insights")

        # Step 9: Save final insights
        print("\n[STEP 9] Saving final outputs...")

        final_path = os.path.join(output_dir, f"insights_final_{timestamp}.json")
        save_insights(self.insights, final_path)

        # Create CSV export
        csv_path = os.path.join(output_dir, f"insights_final_{timestamp}.csv")
        self._export_to_csv(self.insights, csv_path)
        print(f"✓ Saved CSV to {csv_path}")

        # Generate summary report
        summary = self._generate_summary()
        summary_path = os.path.join(output_dir, f"summary_{timestamp}.json")
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"✓ Saved summary to {summary_path}")

        # Step 10: Print API statistics
        print("\n[STEP 10] API Statistics:")
        stats = self.insight_generator.get_stats()
        print(f"  Generation:")
        print(f"    - Total batches: {stats['generation']['total_batches']}")
        print(f"    - Successful insights: {stats['generation']['successful_insights']}")
        print(f"    - Failed insights: {stats['generation']['failed_insights']}")
        print(f"  API:")
        print(f"    - Total requests: {stats['api']['total_requests']}")
        print(f"    - Success rate: {stats['api']['success_rate']:.1f}%")
        print(f"    - Retried requests: {stats['api']['retried_requests']}")
        print(f"    - Total tokens: {stats['api']['total_tokens']:,}")

        print("\n" + "=" * 80)
        print("PIPELINE COMPLETE")
        print("=" * 80)
        print(f"\nGenerated {len(self.insights)} high-quality insights")
        print(f"Coverage: {len(set(i['cohort_id'] for i in self.insights))} cohorts")
        print(f"\nOutputs saved to: {output_dir}/")

        return summary

    def _export_to_csv(self, insights: List[Dict[str, Any]], output_path: str):
        """Export insights to CSV format."""
        import csv

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # Header
            writer.writerow(
                [
                    "cohort_id",
                    "cohort_description",
                    "template_type",
                    "health_domain",
                    "hook",
                    "explanation",
                    "action",
                    "source_name",
                    "source_url",
                    "quality_score",
                    "validation_score",
                    "confidence",
                    "numeric_claim",
                ]
            )

            # Data
            for insight in insights:
                writer.writerow(
                    [
                        insight.get("cohort_id", ""),
                        self._get_cohort_description(insight.get("cohort_params", {})),
                        insight.get("template_type", ""),
                        insight.get("health_domain", ""),
                        insight.get("hook", ""),
                        insight.get("explanation", ""),
                        insight.get("action", ""),
                        insight.get("source_name", ""),
                        insight.get("source_url", ""),
                        insight.get("quality_score", 0),
                        insight.get("validation", {}).get("overall_score", 0),
                        insight.get("confidence", ""),
                        insight.get("numeric_claim", ""),
                    ]
                )

    def _get_cohort_description(self, cohort_params: Dict[str, str]) -> str:
        """Generate human-readable cohort description."""
        parts = []

        if "age_group" in cohort_params:
            parts.append(f"{cohort_params['age_group']} years")
        if "gender" in cohort_params:
            parts.append(cohort_params["gender"])

        for key, value in cohort_params.items():
            if key not in ["age_group", "gender"]:
                parts.append(value.replace("-", " "))

        return ", ".join(parts)

    def _generate_summary(self) -> Dict[str, Any]:
        """Generate pipeline summary statistics."""
        summary = {
            "timestamp": datetime.now().isoformat(),
            "market": self.market,
            "total_cohorts": len(self.cohorts),
            "total_insights": len(self.insights),
            "insights_per_cohort": {},
            "by_health_domain": {},
            "by_template_type": {},
            "quality_stats": {"average": 0, "median": 0, "min": 0, "max": 0},
            "validation_stats": {"average": 0, "valid_count": 0},
            "api_stats": self.insight_generator.get_stats(),
        }

        # Count insights per cohort
        for insight in self.insights:
            cohort_id = insight.get("cohort_id")
            summary["insights_per_cohort"][cohort_id] = (
                summary["insights_per_cohort"].get(cohort_id, 0) + 1
            )

        # Count by health domain
        for insight in self.insights:
            domain = insight.get("health_domain", "unknown")
            summary["by_health_domain"][domain] = (
                summary["by_health_domain"].get(domain, 0) + 1
            )

        # Count by template type
        for insight in self.insights:
            template = insight.get("template_type", "unknown")
            summary["by_template_type"][template] = (
                summary["by_template_type"].get(template, 0) + 1
            )

        # Quality statistics
        quality_scores = [i.get("quality_score", 0) for i in self.insights]
        if quality_scores:
            quality_scores.sort()
            summary["quality_stats"]["average"] = sum(quality_scores) / len(
                quality_scores
            )
            summary["quality_stats"]["median"] = quality_scores[
                len(quality_scores) // 2
            ]
            summary["quality_stats"]["min"] = quality_scores[0]
            summary["quality_stats"]["max"] = quality_scores[-1]

        # Validation statistics
        validation_scores = [
            i.get("validation", {}).get("overall_score", 0) for i in self.insights
        ]
        if validation_scores:
            summary["validation_stats"]["average"] = sum(validation_scores) / len(
                validation_scores
            )
            summary["validation_stats"]["valid_count"] = sum(
                1
                for i in self.insights
                if i.get("validation", {}).get("overall_valid", False)
            )

        return summary


async def async_main(args):
    """Async main entry point."""
    # Initialize pipeline
    pipeline = AsyncDYKPipeline(
        openrouter_api_key=args.openrouter_key or os.getenv("OPENROUTER_API_KEY"),
        pubmed_email=args.pubmed_email or os.getenv("PUBMED_EMAIL"),
        market=args.market,
        requests_per_minute=args.rate_limit,
        max_concurrent=args.max_concurrent,
    )

    # Parse template types and domains
    template_types = args.templates.split(",") if args.templates else None
    health_domains = args.domains.split(",") if args.domains else None

    # Run pipeline
    summary = await pipeline.run_full_pipeline(
        max_cohorts=args.max_cohorts,
        template_types=template_types,
        health_domains=health_domains,
        insights_per_combination=args.insights_per_combo,
        region=args.region,
        validate=not args.no_validate,
        min_quality_score=args.min_quality,
        output_dir=args.output_dir,
    )

    print("\n✓ Pipeline completed successfully!")
    print(f"\nSummary: {json.dumps(summary, indent=2)}")


def main():
    """Main entry point with CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Async DYK Insight Generation Pipeline (High Performance)"
    )

    parser.add_argument(
        "--market", default="singapore", help="Market to generate insights for"
    )
    parser.add_argument("--max-cohorts", type=int, help="Maximum cohorts to process")
    parser.add_argument(
        "--templates",
        help="Comma-separated template types (e.g., 'risk_amplification,protective_factors')",
    )
    parser.add_argument(
        "--domains",
        help="Comma-separated health domains (e.g., 'cardiovascular,metabolic')",
    )
    parser.add_argument(
        "--insights-per-combo",
        type=int,
        default=3,
        help="Insights per cohort×template×domain combination",
    )
    parser.add_argument("--region", default="singapore", help="Target region")
    parser.add_argument(
        "--no-validate", action="store_true", help="Skip validation step"
    )
    parser.add_argument(
        "--min-quality",
        type=float,
        default=60.0,
        help="Minimum quality score threshold",
    )
    parser.add_argument("--output-dir", default="output", help="Output directory")
    parser.add_argument("--openrouter-key", help="OpenRouter API key")
    parser.add_argument("--pubmed-email", help="Email for PubMed API")
    parser.add_argument(
        "--rate-limit",
        type=int,
        default=60,
        help="API requests per minute (default: 60)",
    )
    parser.add_argument(
        "--max-concurrent",
        type=int,
        default=10,
        help="Maximum concurrent API calls (default: 10)",
    )

    args = parser.parse_args()

    # Run async pipeline
    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()
