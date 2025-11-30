#!/usr/bin/env python3
"""
CLI script to generate health insights.

Usage:
    python scripts/generate_insights.py --market singapore --cohort "male,40-49,chinese"
    python scripts/generate_insights.py --market singapore --all-priority-cohorts
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.config_loader import ConfigLoader
from utils.file_utils import save_json, get_timestamped_filename, ensure_directory


def main():
    parser = argparse.ArgumentParser(description="Generate DYK health insights")
    parser.add_argument("--market", default="singapore", help="Market to generate for (default: singapore)")
    parser.add_argument("--cohort", help="Specific cohort (comma-separated dimensions)")
    parser.add_argument("--all-priority-cohorts", action="store_true", help="Generate for all priority cohorts")
    parser.add_argument("--output-dir", default="output", help="Output directory")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be generated without making API calls")

    args = parser.parse_args()

    # Load configuration
    print(f"Loading configuration for market: {args.market}")
    loader = ConfigLoader()
    config = loader.load_market_config(args.market)

    print(f"Loaded {len(config.get('insight_templates', []))} insight templates")
    print(f"Templates by weight:")
    for template in loader.get_templates_by_weight(config)[:5]:
        print(f"  - {template['type']} (weight: {template['weight']})")

    if args.dry_run:
        print("\n[DRY RUN] Would generate insights but not making API calls")
        return

    # TODO: Implement actual insight generation
    print("\nInsight generation not yet implemented. This is a placeholder.")
    print("Next steps:")
    print("1. Import pipeline.py or insight_generator.py")
    print("2. Generate insights based on selected cohorts")
    print("3. Save to output directory")

    output_dir = ensure_directory(Path(args.output_dir))
    print(f"\nOutput will be saved to: {output_dir}")


if __name__ == "__main__":
    main()
