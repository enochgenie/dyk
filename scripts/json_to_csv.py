#!/usr/bin/env python3
"""
Convert DYK insights from JSON to CSV format for easy viewing in Excel/Google Sheets.

Usage:
    python scripts/json_to_csv.py output/insights_final.json
    python scripts/json_to_csv.py output/insights_final.json --output my_insights.csv
"""

import json
import csv
import sys
import argparse
from pathlib import Path
from typing import Dict, Any, List


def convert_insights_to_csv(
    json_file: str, csv_file: str = None, include_all_fields: bool = False
) -> str:
    """
    Convert insights JSON to CSV format.

    Args:
        json_file: Path to JSON file
        csv_file: Path to output CSV (optional)
        include_all_fields: Include all metadata fields (creates wider CSV)

    Returns:
        Path to created CSV file
    """
    # Read JSON
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Extract insights list
    if isinstance(data, dict):
        insights = data.get("insights", [])
    elif isinstance(data, list):
        insights = data
    else:
        raise ValueError("JSON must be a dict with 'insights' key or a list")

    if not insights:
        print("No insights found in JSON file")
        return None

    # Determine output file
    if csv_file is None:
        csv_file = str(Path(json_file).with_suffix(".csv"))

    # Write CSV
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Define headers based on mode
        if include_all_fields:
            headers = [
                "Insight ID",
                "Hook",
                "Explanation",
                "Action",
                "Numeric Claim",
                "Source Name",
                "Source URL",
                "Cohort ID",
                "Cohort Description",
                "Age Group",
                "Gender",
                "Race",
                "BMI",
                "Health Conditions",
                "Template Type",
                "Template Weight",
                "Health Domains",
                "Priority Level",
                "Validated",
                "Validation Issues",
                "Evaluation Score",
                "Evaluation Feedback",
                "Generation Model",
                "Generation Temperature",
                "Generated At",
            ]
        else:
            headers = [
                "Insight ID",
                "Hook",
                "Explanation",
                "Action",
                "Numeric Claim",
                "Source Name",
                "Source URL",
                "Cohort ID",
                "Cohort Description",
                "Age Group",
                "Template Type",
                "Validated",
                "Validation Issues",
                "Evaluation Score",
                "Generated At",
            ]

        writer.writerow(headers)

        # Write data rows
        for idx, insight in enumerate(insights, 1):
            # Extract metadata
            metadata = insight.get("metadata", {})
            cohort = metadata.get("cohort", {})
            template = metadata.get("insight_template", {})
            cohort_params = cohort.get("cohort_params", {})

            # Extract validation info
            validation = insight.get("validation", {})
            validated = validation.get("validated", False)
            validation_issues = ""
            if not validated and "checks" in validation:
                issues = []
                for check_result in validation["checks"].values():
                    if not check_result.get("passed", True):
                        issues.extend(check_result.get("issues", []))
                validation_issues = "; ".join(issues)

            # Extract evaluation info
            evaluation = insight.get("evaluation", {})
            eval_result = evaluation.get("result", {})
            if isinstance(eval_result, dict):
                eval_score = eval_result.get(
                    "overall_score", eval_result.get("score", "N/A")
                )
                eval_feedback = eval_result.get("feedback", "")
            elif isinstance(eval_result, str):
                eval_score = "N/A"
                eval_feedback = eval_result[:100] + "..." if len(eval_result) > 100 else eval_result
            else:
                eval_score = "N/A"
                eval_feedback = ""

            # Extract health domains (if list)
            health_domains = metadata.get("health_domains", "")
            if isinstance(health_domains, list):
                health_domains = ", ".join([d.get("name", str(d)) for d in health_domains])
            elif isinstance(health_domains, dict):
                health_domains = health_domains.get("name", "")

            if include_all_fields:
                row = [
                    f"INS_{idx:04d}",
                    insight.get("hook", ""),
                    insight.get("explanation", ""),
                    insight.get("action", ""),
                    insight.get("numeric_claim", ""),
                    insight.get("source_name", ""),
                    insight.get("source_url", ""),
                    cohort.get("cohort_id", ""),
                    cohort.get("description", ""),
                    cohort_params.get("age_group", ""),
                    cohort_params.get("gender", ""),
                    cohort_params.get("race", ""),
                    cohort_params.get("bmi", ""),
                    cohort_params.get("health_conditions", ""),
                    template.get("type", ""),
                    template.get("weight", ""),
                    health_domains,
                    cohort.get("priority_level", ""),
                    "Yes" if validated else "No",
                    validation_issues,
                    eval_score,
                    eval_feedback,
                    metadata.get("generation_model", ""),
                    metadata.get("generation_temperature", ""),
                    metadata.get("generation_timestamp", ""),
                ]
            else:
                row = [
                    f"INS_{idx:04d}",
                    insight.get("hook", ""),
                    insight.get("explanation", ""),
                    insight.get("action", ""),
                    insight.get("numeric_claim", ""),
                    insight.get("source_name", ""),
                    insight.get("source_url", ""),
                    cohort.get("cohort_id", ""),
                    cohort.get("description", ""),
                    cohort_params.get("age_group", ""),
                    template.get("type", ""),
                    "Yes" if validated else "No",
                    validation_issues,
                    eval_score,
                    metadata.get("generation_timestamp", ""),
                ]

            writer.writerow(row)

    print(f"✓ Converted {len(insights)} insights to CSV")
    print(f"✓ Saved to: {csv_file}")
    return csv_file


def main():
    parser = argparse.ArgumentParser(
        description="Convert DYK insights JSON to CSV format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert with default output name
  python scripts/json_to_csv.py output/insights_final.json

  # Specify output file
  python scripts/json_to_csv.py output/insights_final.json --output my_insights.csv

  # Include all metadata fields
  python scripts/json_to_csv.py output/insights_final.json --all-fields
        """,
    )

    parser.add_argument("json_file", help="Path to JSON file containing insights")
    parser.add_argument(
        "-o", "--output", help="Output CSV file path (default: same as JSON with .csv extension)"
    )
    parser.add_argument(
        "-a",
        "--all-fields",
        action="store_true",
        help="Include all metadata fields (creates wider CSV)",
    )

    args = parser.parse_args()

    try:
        csv_file = convert_insights_to_csv(
            args.json_file, args.output, args.all_fields
        )

        if csv_file:
            print("\nYou can now open this file in Excel, Google Sheets, or any spreadsheet software!")

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
