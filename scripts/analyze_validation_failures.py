#!/usr/bin/env python3
"""
Analyze validation failures from pipeline output.

This script compares insights_raw.json with insights_validated.json to identify
which insights failed validation and why.

Usage:
    python scripts/analyze_validation_failures.py
    python scripts/analyze_validation_failures.py --output-dir custom_output
"""

import os
import sys
import json
import argparse
from pathlib import Path
from collections import Counter

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def load_json_file(filepath):
    """Load JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found: {filepath}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {filepath}: {e}")
        return None


def analyze_failures(output_dir="output"):
    """Analyze validation failures."""
    print("="*80)
    print("VALIDATION FAILURE ANALYSIS")
    print("="*80)

    raw_file = os.path.join(output_dir, "insights_raw.json")
    validated_file = os.path.join(output_dir, "insights_validated.json")

    # Load files
    print(f"\nLoading files from: {output_dir}/")
    raw_data = load_json_file(raw_file)
    validated_data = load_json_file(validated_file)

    if not raw_data:
        print(f"Error: Could not load {raw_file}")
        print("Make sure you've run the pipeline first!")
        return

    if not validated_data:
        print(f"Warning: {validated_file} not found")
        print("This means validation step was skipped or no insights passed validation")
        validated_data = {"insights": []}

    raw_insights = raw_data.get("insights", [])
    validated_insights = validated_data.get("insights", [])

    print(f"\n📊 Summary:")
    print(f"  Total insights generated: {len(raw_insights)}")
    print(f"  Insights that passed validation: {len(validated_insights)}")
    print(f"  Insights that failed validation: {len(raw_insights) - len(validated_insights)}")

    if len(raw_insights) == len(validated_insights):
        print("\n✅ All insights passed validation! No failures to analyze.")
        return

    # Find failed insights (those in raw but not in validated)
    validated_ids = set()
    for insight in validated_insights:
        # Create unique ID from metadata
        metadata = insight.get("metadata", {})
        unique_id = (
            metadata.get("cohort_id", ""),
            metadata.get("template_type", ""),
            metadata.get("health_domain", ""),
            insight.get("hook", "")[:50]  # First 50 chars of hook
        )
        validated_ids.add(unique_id)

    failed_insights = []
    for insight in raw_insights:
        metadata = insight.get("metadata", {})
        unique_id = (
            metadata.get("cohort_id", ""),
            metadata.get("template_type", ""),
            metadata.get("health_domain", ""),
            insight.get("hook", "")[:50]
        )

        if unique_id not in validated_ids:
            validation = insight.get("validation", {})
            if not validation.get("validated", False):
                failed_insights.append(insight)

    print(f"\n❌ Failed insights: {len(failed_insights)}")

    if not failed_insights:
        print("\nNote: All insights have validation data - check the raw file for details")
        return

    # Analyze failure reasons
    print("\n" + "="*80)
    print("FAILURE ANALYSIS")
    print("="*80)

    # Count failure types
    failure_types = Counter()
    all_issues = []

    for insight in failed_insights:
        validation = insight.get("validation", {})
        checks = validation.get("checks", {})

        for check_name, check_result in checks.items():
            if not check_result.get("passed", False):
                failure_types[check_name] += 1
                issues = check_result.get("issues", [])
                all_issues.extend([(check_name, issue) for issue in issues])

    print(f"\n📋 Failure Types:")
    for failure_type, count in failure_types.most_common():
        print(f"  {failure_type}: {count} insights")

    print(f"\n📝 Common Issues:")
    issue_counter = Counter([issue for _, issue in all_issues])
    for issue, count in issue_counter.most_common(10):
        print(f"  [{count}x] {issue}")

    # Show detailed examples
    print("\n" + "="*80)
    print("DETAILED EXAMPLES (First 5 Failed Insights)")
    print("="*80)

    for idx, insight in enumerate(failed_insights[:5], 1):
        print(f"\n--- Failed Insight #{idx} ---")

        metadata = insight.get("metadata", {})
        print(f"Cohort: {metadata.get('cohort_id', 'N/A')} - {metadata.get('cohort_description', 'N/A')}")
        print(f"Template: {metadata.get('template_type', 'N/A')}")
        print(f"Domain: {metadata.get('health_domain', 'N/A')}")
        print(f"Hook: {insight.get('hook', 'N/A')[:80]}...")

        validation = insight.get("validation", {})
        print(f"\nValidation Status: {'PASS' if validation.get('validated', False) else 'FAIL'}")
        print(f"Failed Checks: {validation.get('number_failed', 0)}")

        checks = validation.get("checks", {})
        for check_name, check_result in checks.items():
            if not check_result.get("passed", False):
                print(f"\n  ❌ {check_name}:")
                for issue in check_result.get("issues", []):
                    print(f"     - {issue}")
                for warning in check_result.get("warnings", []):
                    print(f"     ⚠️  {warning}")

    if len(failed_insights) > 5:
        print(f"\n... and {len(failed_insights) - 5} more failed insights")

    # Save detailed report
    report_file = os.path.join(output_dir, "validation_failures_report.json")
    report = {
        "summary": {
            "total_insights": len(raw_insights),
            "passed": len(validated_insights),
            "failed": len(failed_insights),
            "pass_rate": len(validated_insights) / len(raw_insights) * 100 if raw_insights else 0
        },
        "failure_types": dict(failure_types),
        "common_issues": [
            {"issue": issue, "count": count}
            for issue, count in issue_counter.most_common()
        ],
        "failed_insights": failed_insights
    }

    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)

    print("\n" + "="*80)
    print(f"📄 Detailed report saved to: {report_file}")
    print("="*80)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze validation failures from pipeline output"
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Output directory containing pipeline results (default: output)"
    )

    args = parser.parse_args()
    analyze_failures(args.output_dir)


if __name__ == "__main__":
    main()
