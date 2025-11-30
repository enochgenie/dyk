#!/usr/bin/env python3
"""
Quick script to show validation failures from insights_with_validation.json

Usage:
    python scripts/show_validation_failures.py
    python scripts/show_validation_failures.py --output-dir custom_output
    python scripts/show_validation_failures.py --verbose
"""

import json
import argparse
from pathlib import Path
from collections import Counter


def show_failures(output_dir="output", verbose=False):
    """Show validation failures in a clean format."""

    file_path = Path(output_dir) / "insights_with_validation.json"

    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        print("\nMake sure you've run the pipeline with validation enabled:")
        print("  python src/generate_insights.py --max-cohorts 3")
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    total = data.get("total_insights", 0)
    passed = data.get("passed", 0)
    failed = data.get("failed", 0)

    print("="*80)
    print("VALIDATION RESULTS")
    print("="*80)
    print(f"\n✅ Passed: {passed}/{total} ({passed/total*100:.1f}%)")
    print(f"❌ Failed: {failed}/{total} ({failed/total*100:.1f}%)")

    if failed == 0:
        print("\n🎉 All insights passed validation!")
        return

    # Find failed insights
    failed_insights = [
        insight for insight in data.get("insights", [])
        if not insight.get("validation", {}).get("validated", False)
    ]

    # Count failure reasons
    failure_reasons = Counter()
    for insight in failed_insights:
        checks = insight.get("validation", {}).get("checks", {})
        for check_name, check_result in checks.items():
            if not check_result.get("passed", False):
                for issue in check_result.get("issues", []):
                    failure_reasons[f"{check_name}: {issue}"] += 1

    print("\n" + "="*80)
    print("TOP FAILURE REASONS")
    print("="*80)
    for reason, count in failure_reasons.most_common(10):
        print(f"  [{count:2d}x] {reason}")

    if verbose:
        print("\n" + "="*80)
        print(f"FAILED INSIGHTS DETAILS ({len(failed_insights)} total)")
        print("="*80)

        for idx, insight in enumerate(failed_insights, 1):
            print(f"\n--- Failed Insight #{idx} ---")

            metadata = insight.get("metadata", {})
            print(f"Cohort: {metadata.get('cohort_id')} - {metadata.get('cohort_description')}")
            print(f"Template: {metadata.get('template_type')}")
            print(f"Domain: {metadata.get('health_domain')}")

            hook = insight.get("hook", "N/A")
            print(f"Hook: {hook[:100]}{'...' if len(hook) > 100 else ''}")

            validation = insight.get("validation", {})
            checks = validation.get("checks", {})

            for check_name, check_result in checks.items():
                if not check_result.get("passed", False):
                    print(f"\n  ❌ {check_name}:")
                    for issue in check_result.get("issues", []):
                        print(f"     • {issue}")
                    for warning in check_result.get("warnings", []):
                        print(f"     ⚠️  {warning}")
    else:
        print(f"\n💡 Run with --verbose to see details of all {len(failed_insights)} failed insights")

    print("\n" + "="*80)
    print(f"📄 Full data: {file_path}")
    print("="*80)


def main():
    parser = argparse.ArgumentParser(
        description="Show validation failures from pipeline output"
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Output directory (default: output)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed information for each failed insight"
    )

    args = parser.parse_args()
    show_failures(args.output_dir, args.verbose)


if __name__ == "__main__":
    main()
