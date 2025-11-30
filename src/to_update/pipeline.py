"""
DYK Pipeline Orchestrator
Main script to run the complete insight generation pipeline.
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import argparse
import sys
from dotenv import load_dotenv

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from core.cohort_generator import CohortGenerator
from core.insight_generator import InsightGenerator, save_insights
from core.validator import InsightValidator, QualityScorer
from utils.config_loader import ConfigLoader

# Load environment variables from .env file in project root
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")


class DYKPipeline:
    """Complete DYK insight generation pipeline."""

    def __init__(
        self,
        openrouter_api_key: Optional[str] = None,
        pubmed_email: Optional[str] = None,
        pubmed_api_key: Optional[str] = None,
        market: str = "singapore",
    ):
        """
        Initialize the pipeline.

        Args:
            openrouter_api_key: OpenRouter API key
            pubmed_email: Email for PubMed API
            pubmed_api_key: Optional PubMed API key
            market: Market identifier (e.g., 'singapore', 'usa')
        """
        # Load configuration using new config loader
        loader = ConfigLoader()
        self.config = loader.load_market_config(market)
        self.market = market

        # Initialize components
        self.cohort_generator = CohortGenerator(market=market, config=self.config)
        self.insight_generator = InsightGenerator(
            api_key=openrouter_api_key,
            pubmed_email=pubmed_email,
            pubmed_api_key=pubmed_api_key,
        )
        self.validator = InsightValidator(self.config)
        self.quality_scorer = QualityScorer()

        # Pipeline state
        self.cohorts = []
        self.insights = []
        self.validation_results = []

    def run_full_pipeline(
        self,
        method: str = "pure_llm",
        max_cohorts: Optional[int] = None,
        insights_per_cohort: int = 3,
        region: str = "singapore",
        validate: bool = True,
        filter_invalid: bool = True,
        min_quality_score: float = 60.0,
        output_dir: str = "output",
    ) -> Dict[str, Any]:
        """
        Run the complete pipeline from cohort generation to validated insights.

        Args:
            method: "pure_llm" or "evidence_based"
            max_cohorts: Maximum number of cohorts to process (None = all)
            insights_per_cohort: Number of insights per cohort
            region: Target region
            validate: Whether to validate insights
            filter_invalid: Remove invalid insights from output
            min_quality_score: Minimum quality score to keep insight
            output_dir: Directory for output files

        Returns:
            Pipeline summary statistics
        """
        print("\n" + "=" * 80)
        print("DYK INSIGHT GENERATION PIPELINE")
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

        # Step 2: Generate insights
        print(f"\n[STEP 2] Generating insights using method: {method}")
        print(
            f"Target: {len(self.cohorts)} cohorts × {insights_per_cohort} insights = {len(self.cohorts) * insights_per_cohort} total"
        )

        template_types = [
            "risk_amplification",
            "protective_factors",
            "behavior_change",
            "early_detection",
            "comparative",
        ]

        self.insights = self.insight_generator.batch_generate(
            cohort_specs=self.cohorts,
            method=method,
            insights_per_cohort=insights_per_cohort,
            template_types=template_types,
            region=region,
            validate=False,  # We'll validate separately
            rate_limit_delay=1.0,
        )

        print(f"✓ Generated {len(self.insights)} insights")

        # Save raw insights
        raw_path = os.path.join(output_dir, f"insights_raw_{timestamp}.json")
        save_insights(self.insights, raw_path)

        # Step 3: Validate insights
        if validate:
            print("\n[STEP 3] Validating insights...")
            validation_summary = self.validator.validate_batch(self.insights)
            self.validation_results = validation_summary["results"]

            print(f"✓ Validated {validation_summary['total_insights']} insights")
            print(f"  - Valid: {validation_summary['valid_insights']}")
            print(f"  - Invalid: {validation_summary['invalid_insights']}")
            print(f"  - Average score: {validation_summary['average_score']}/100")
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

        # Step 4: Check for duplicates
        print("\n[STEP 4] Checking for duplicates...")
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

        # Step 5: Calculate quality scores
        print("\n[STEP 5] Calculating quality scores...")
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

        # Step 6: Filter insights
        print("\n[STEP 6] Filtering insights...")
        initial_count = len(self.insights)

        if filter_invalid and validate:
            self.insights = [
                ins
                for ins in self.insights
                if ins.get("validation", {}).get("overall_valid", False)
            ]
            print(
                f"✓ Filtered out {initial_count - len(self.insights)} invalid insights"
            )

        # Filter by quality score
        self.insights = [
            ins
            for ins in self.insights
            if ins.get("quality_score", 0) >= min_quality_score
        ]
        print(
            f"✓ Filtered out {initial_count - len(self.insights)} low-quality insights"
        )
        print(f"✓ Final count: {len(self.insights)} insights")

        # Step 7: Save final insights
        print("\n[STEP 7] Saving final outputs...")

        final_path = os.path.join(output_dir, f"insights_final_{timestamp}.json")
        save_insights(self.insights, final_path)

        # Create CSV export for easy viewing
        csv_path = os.path.join(output_dir, f"insights_final_{timestamp}.csv")
        self._export_to_csv(self.insights, csv_path)
        print(f"✓ Saved CSV to {csv_path}")

        # Generate summary report
        summary = self._generate_summary()
        summary_path = os.path.join(output_dir, f"summary_{timestamp}.json")
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"✓ Saved summary to {summary_path}")

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
                    "hook",
                    "explanation",
                    "action",
                    "source_name",
                    "source_url",
                    "health_domain",
                    "quality_score",
                    "validation_score",
                    "generation_method",
                ]
            )

            # Data
            for insight in insights:
                writer.writerow(
                    [
                        insight.get("cohort_id", ""),
                        self._get_cohort_description(insight.get("cohort_params", {})),
                        insight.get("hook", ""),
                        insight.get("explanation", ""),
                        insight.get("action", ""),
                        insight.get("source_name", ""),
                        insight.get("source_url", ""),
                        insight.get("health_domain", ""),
                        insight.get("quality_score", 0),
                        insight.get("validation", {}).get("overall_score", 0),
                        insight.get("generation_method", ""),
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
            "total_cohorts": len(self.cohorts),
            "total_insights": len(self.insights),
            "insights_per_cohort": {},
            "by_health_domain": {},
            "by_template_type": {},
            "quality_stats": {"average": 0, "median": 0, "min": 0, "max": 0},
            "validation_stats": {"average": 0, "valid_count": 0},
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


def main():
    """Main entry point with CLI arguments."""
    parser = argparse.ArgumentParser(description="DYK Insight Generation Pipeline")

    parser.add_argument(
        "--method",
        choices=["pure_llm", "evidence_based"],
        default="pure_llm",
        help="Generation method",
    )
    parser.add_argument("--max-cohorts", type=int, help="Maximum cohorts to process")
    parser.add_argument(
        "--insights-per-cohort",
        type=int,
        default=3,
        help="Insights to generate per cohort",
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

    args = parser.parse_args()

    # Initialize pipeline
    pipeline = DYKPipeline(
        openrouter_api_key=args.openrouter_key or os.getenv("OPENROUTER_API_KEY"),
        pubmed_email=args.pubmed_email or os.getenv("PUBMED_EMAIL"),
    )

    # Run pipeline
    summary = pipeline.run_full_pipeline(
        method=args.method,
        max_cohorts=args.max_cohorts,
        insights_per_cohort=args.insights_per_cohort,
        region=args.region,
        validate=not args.no_validate,
        min_quality_score=args.min_quality,
        output_dir=args.output_dir,
    )

    print("\n✓ Pipeline completed successfully!")
    print(f"Summary: {json.dumps(summary, indent=2)}")


if __name__ == "__main__":
    main()
