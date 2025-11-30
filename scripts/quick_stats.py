#!/usr/bin/env python3
"""
Quick statistics viewer for DYK insights.

Displays key metrics in the terminal without needing to open files.

Usage:
    python scripts/quick_stats.py output/insights_final.json
"""

import json
import sys
import argparse
from pathlib import Path
from collections import Counter


def display_quick_stats(json_file: str):
    """Display quick statistics about insights."""
    # Read JSON
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    insights = data.get("insights", []) if isinstance(data, dict) else data

    if not insights:
        print("No insights found in file")
        return

    # Basic counts
    total = len(insights)
    validated = sum(1 for i in insights if i.get("validation", {}).get("validated", False))
    failed = total - validated

    # Evaluation scores
    scores = []
    for insight in insights:
        eval_result = insight.get("evaluation", {}).get("result", {})
        if isinstance(eval_result, dict):
            score = eval_result.get("overall_score", eval_result.get("score"))
            if score is not None and score != "N/A":
                try:
                    scores.append(float(score))
                except (ValueError, TypeError):
                    pass

    avg_score = sum(scores) / len(scores) if scores else 0
    high_quality = sum(1 for s in scores if s >= 8.0)

    # Template distribution
    templates = Counter(
        i.get("metadata", {}).get("insight_template", {}).get("type", "Unknown")
        for i in insights
    )

    # Cohort distribution
    cohorts = Counter(
        i.get("metadata", {}).get("cohort", {}).get("description", "Unknown")
        for i in insights
    )

    # Print statistics
    print("\n" + "=" * 80)
    print(f"DYK INSIGHTS - QUICK STATS")
    print("=" * 80)
    print(f"\nFile: {json_file}")
    print(f"\n{'OVERVIEW':-^80}")
    print(f"  Total Insights:        {total:5d}")
    print(f"  ✓ Validated:           {validated:5d} ({validated/total*100:5.1f}%)")
    print(f"  ✗ Failed Validation:   {failed:5d} ({failed/total*100:5.1f}%)")

    if scores:
        print(f"\n{'QUALITY SCORES':-^80}")
        print(f"  Average Score:         {avg_score:5.2f}/10")
        print(f"  High Quality (≥8.0):   {high_quality:5d} ({high_quality/len(scores)*100:5.1f}%)")
        print(f"  Scored Insights:       {len(scores):5d}")

    print(f"\n{'TOP 5 TEMPLATES':-^80}")
    for i, (template, count) in enumerate(templates.most_common(5), 1):
        pct = count / total * 100
        bar = "█" * int(pct / 2)
        print(f"  {i}. {template:30s} {count:4d} ({pct:5.1f}%) {bar}")

    print(f"\n{'TOP 5 COHORTS':-^80}")
    for i, (cohort, count) in enumerate(cohorts.most_common(5), 1):
        pct = count / total * 100
        bar = "█" * int(pct / 2)
        cohort_short = cohort[:50] + "..." if len(cohort) > 50 else cohort
        print(f"  {i}. {cohort_short:50s}")
        print(f"     {count:4d} insights ({pct:5.1f}%) {bar}")

    # Validation failure analysis
    failure_reasons = Counter()
    for insight in insights:
        if not insight.get("validation", {}).get("validated", False):
            checks = insight.get("validation", {}).get("checks", {})
            for check_name, check_result in checks.items():
                if not check_result.get("passed", True):
                    failure_reasons[check_name] += 1

    if failure_reasons:
        print(f"\n{'VALIDATION FAILURES':-^80}")
        for reason, count in failure_reasons.most_common():
            print(f"  • {reason:30s} {count:4d} failures")

    print("\n" + "=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Display quick statistics for DYK insights",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("json_file", help="Path to insights JSON file")

    args = parser.parse_args()

    try:
        display_quick_stats(args.json_file)
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
