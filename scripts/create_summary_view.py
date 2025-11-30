#!/usr/bin/env python3
"""
Create a boss-friendly summary view of insights with key metrics.

This script creates two views:
1. Executive Summary CSV: High-level overview with quality scores
2. Quick Review CSV: Just the insight content for quick reading

Usage:
    python scripts/create_summary_view.py output/insights_final.json
"""

import json
import csv
import sys
import argparse
from pathlib import Path
from collections import Counter


def create_executive_summary(json_file: str, output_dir: str = None):
    """
    Create executive summary with aggregated statistics and top insights.

    Args:
        json_file: Path to insights JSON file
        output_dir: Output directory (default: same as input)
    """
    # Read JSON
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    insights = data.get("insights", []) if isinstance(data, dict) else data

    if not insights:
        print("No insights found")
        return

    # Determine output directory
    if output_dir is None:
        output_dir = str(Path(json_file).parent)

    # Calculate statistics
    total_insights = len(insights)
    validated_count = sum(
        1 for i in insights if i.get("validation", {}).get("validated", False)
    )
    validation_rate = (validated_count / total_insights * 100) if total_insights > 0 else 0

    # Evaluation scores
    eval_scores = []
    for insight in insights:
        eval_result = insight.get("evaluation", {}).get("result", {})
        if isinstance(eval_result, dict):
            score = eval_result.get("overall_score", eval_result.get("score"))
            if score is not None and score != "N/A":
                try:
                    eval_scores.append(float(score))
                except (ValueError, TypeError):
                    pass

    avg_eval_score = sum(eval_scores) / len(eval_scores) if eval_scores else 0

    # Template distribution
    templates = [
        i.get("metadata", {}).get("insight_template", {}).get("type", "Unknown")
        for i in insights
    ]
    template_counts = Counter(templates)

    # Cohort distribution
    cohorts = [
        i.get("metadata", {}).get("cohort", {}).get("cohort_id", "Unknown")
        for i in insights
    ]
    cohort_counts = Counter(cohorts)

    # Create executive summary report
    summary_file = Path(output_dir) / "executive_summary.txt"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("DYK INSIGHTS - EXECUTIVE SUMMARY\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"Total Insights Generated: {total_insights}\n")
        f.write(f"Validated Insights: {validated_count} ({validation_rate:.1f}%)\n")
        f.write(f"Average Quality Score: {avg_eval_score:.2f}/10\n\n")

        f.write("-" * 80 + "\n")
        f.write("TOP 5 INSIGHT TEMPLATES\n")
        f.write("-" * 80 + "\n")
        for template, count in template_counts.most_common(5):
            percentage = (count / total_insights * 100)
            f.write(f"  {template:40s} {count:4d} ({percentage:5.1f}%)\n")

        f.write("\n" + "-" * 80 + "\n")
        f.write("TOP 5 COHORTS\n")
        f.write("-" * 80 + "\n")
        for cohort, count in cohort_counts.most_common(5):
            percentage = (count / total_insights * 100)
            # Get cohort description
            cohort_desc = next(
                (
                    i.get("metadata", {}).get("cohort", {}).get("description", cohort)
                    for i in insights
                    if i.get("metadata", {}).get("cohort", {}).get("cohort_id") == cohort
                ),
                cohort,
            )
            f.write(f"  {cohort} - {cohort_desc}\n")
            f.write(f"    Insights: {count} ({percentage:.1f}%)\n\n")

    print(f"✓ Executive summary saved to: {summary_file}")

    # Create top insights CSV
    top_insights_file = Path(output_dir) / "top_insights.csv"

    # Sort insights by evaluation score (if available)
    scored_insights = []
    for insight in insights:
        if not insight.get("validation", {}).get("validated", False):
            continue  # Skip invalid insights

        eval_result = insight.get("evaluation", {}).get("result", {})
        score = 0
        if isinstance(eval_result, dict):
            score = eval_result.get("overall_score", eval_result.get("score", 0))
            try:
                score = float(score)
            except (ValueError, TypeError):
                score = 0

        scored_insights.append((score, insight))

    scored_insights.sort(reverse=True, key=lambda x: x[0])

    # Write top 50 insights
    with open(top_insights_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "Rank",
                "Score",
                "Hook",
                "Explanation",
                "Action",
                "Target Audience",
                "Template Type",
            ]
        )

        for rank, (score, insight) in enumerate(scored_insights[:50], 1):
            cohort_desc = (
                insight.get("metadata", {}).get("cohort", {}).get("description", "")
            )
            template_type = (
                insight.get("metadata", {}).get("insight_template", {}).get("type", "")
            )

            writer.writerow(
                [
                    rank,
                    f"{score:.1f}" if score > 0 else "N/A",
                    insight.get("hook", ""),
                    insight.get("explanation", ""),
                    insight.get("action", ""),
                    cohort_desc,
                    template_type,
                ]
            )

    print(f"✓ Top 50 insights saved to: {top_insights_file}")

    # Create quick review CSV (just for reading insights)
    quick_review_file = Path(output_dir) / "quick_review.csv"
    with open(quick_review_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "ID",
                "Full Insight (Hook + Explanation + Action)",
                "Target Audience",
                "Quality Score",
            ]
        )

        for idx, insight in enumerate(insights[:100], 1):  # First 100 insights
            # Skip unvalidated
            if not insight.get("validation", {}).get("validated", False):
                continue

            hook = insight.get("hook", "")
            explanation = insight.get("explanation", "")
            action = insight.get("action", "")

            full_insight = f"{hook}\n\n{explanation}\n\nAction: {action}"

            cohort_desc = (
                insight.get("metadata", {}).get("cohort", {}).get("description", "")
            )

            eval_result = insight.get("evaluation", {}).get("result", {})
            score = "N/A"
            if isinstance(eval_result, dict):
                score = eval_result.get("overall_score", eval_result.get("score", "N/A"))

            writer.writerow([f"INS_{idx:04d}", full_insight, cohort_desc, score])

    print(f"✓ Quick review (first 100 validated) saved to: {quick_review_file}")

    return {
        "summary": summary_file,
        "top_insights": top_insights_file,
        "quick_review": quick_review_file,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Create boss-friendly summary views of DYK insights",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
This creates three files:
  1. executive_summary.txt - High-level statistics and distributions
  2. top_insights.csv - Top 50 highest-scoring insights
  3. quick_review.csv - First 100 validated insights for quick reading

Examples:
  python scripts/create_summary_view.py output/insights_final.json
  python scripts/create_summary_view.py output/insights_final.json --output-dir reports/
        """,
    )

    parser.add_argument("json_file", help="Path to insights JSON file")
    parser.add_argument(
        "-o", "--output-dir", help="Output directory (default: same as input file)"
    )

    args = parser.parse_args()

    try:
        files = create_executive_summary(args.json_file, args.output_dir)
        print("\n" + "=" * 80)
        print("SUMMARY VIEWS CREATED")
        print("=" * 80)
        print("\nGenerated files:")
        for name, path in files.items():
            print(f"  • {name}: {path}")
        print("\nOpen these files in Excel/Google Sheets for easy review!")

    except FileNotFoundError:
        print(f"Error: File not found: {args.json_file}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
