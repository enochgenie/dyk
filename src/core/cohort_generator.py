"""
Cohort Generator Module
Generates all cohort combinations based on priority rules to avoid combinatorial explosion.
"""

import json
from itertools import product
from typing import List, Dict, Any
from collections import defaultdict
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.config_loader import ConfigLoader


class CohortGenerator:
    """Generate priority-based cohort combinations."""

    def __init__(self, market: str = "singapore"):
        """
        Initialize cohort generator.

        Args:
            market: Market identifier (e.g., 'singapore', 'australia')
        """
        loader = ConfigLoader(market=market)
        self.priority_cohorts = loader.priority_cohorts

    def generate_priority_cohorts(self) -> List[Dict[str, Any]]:
        """
        Generate cohort combinations based on priority rules.
        Returns a list of cohort specifications with metadata.
        """
        cohorts = []
        cohort_id = 1

        for priority_group in self.priority_cohorts:
            cohort = {
                "cohort_id": f"cohort_{cohort_id:04d}",
                "cohort_params": priority_group["dimensions"],
                "priority_level": priority_group["priority"],
                "description": priority_group.get("description", ""),
                "rationale": priority_group.get("rationale", ""),
                "insight_angles": priority_group.get("insight_angles", []),
            }
            cohorts.append(cohort)
            cohort_id += 1

        # Sort by priority (lower number = higher priority)
        cohorts.sort(key=lambda x: x["priority_level"])

        return cohorts

    # def generate_priority_cohorts(self) -> List[Dict[str, Any]]:
    #     """
    #     Generate cohort combinations based on priority rules.
    #     Returns a list of cohort specifications with metadata.
    #     """
    #     cohorts = []
    #     cohort_id = 1

    #     for priority_group in self.priority_cohorts:
    #         dimensions = priority_group["dimensions"]

    #         # Generate all combinations for this priority group
    #         dimension_names = list(dimensions.keys())
    #         dimension_values = [dimensions[dim] for dim in dimension_names]

    #         for combination in product(*dimension_values):
    #             cohort_spec = {
    #                 "cohort_id": f"cohort_{cohort_id:04d}",
    #                 "cohort_params": {},
    #                 "priority_level": self._calculate_priority(
    #                     dict(zip(dimension_names, combination))
    #                 ),
    #             }

    #             # Build cohort parameters
    #             for dim_name, value in zip(dimension_names, combination):
    #                 cohort_spec["cohort_params"][dim_name] = value

    #             # Add human-readable description
    #             cohort_spec["description"] = self._generate_description(
    #                 cohort_spec["cohort_params"]
    #             )

    #             cohorts.append(cohort_spec)
    #             cohort_id += 1

    #     # Sort by priority (lower number = higher priority)
    #     cohorts.sort(key=lambda x: x["priority_level"])

    #     return cohorts

    def _calculate_priority(self, params: Dict[str, str]) -> int:
        """
        Calculate aggregate priority score for a cohort.
        Lower score = higher priority.

        params have the following structure:
        {'age_group': '50-59', 'gender': 'female', 'chronic_conditions': 'prediabetes'}
        """
        priority_score = 0

        for dimension, value in params.items():
            # Find priority for this specific value
            dimension_config = self.cohort_definitions.get(dimension, [])

            for item in dimension_config:
                if item["name"] == value:
                    priority_score += item.get("priority", 5)
                    break

        return priority_score

    def _generate_description(self, params: Dict[str, str]) -> str:
        """Generate human-readable cohort description."""
        parts = []

        # Order: age, race, gender, then other characteristics
        if "age_group" in params:
            parts.append(f"{params['age_group']} years old")

        if "race" in params:
            parts.append(params["race"])

        if "gender" in params:
            parts.append(params["gender"])

        # Add other characteristics
        for key, value in params.items():
            if key not in ["age_group", "gender", "race"]:
                parts.append(value.replace("-", " "))

        return ", ".join(parts)

    def generate_single_dimension_cohorts(self) -> List[Dict[str, Any]]:
        """
        Generate cohorts for each single dimension (fallback strategy).
        Useful for ensuring basic coverage.
        """
        cohorts = []
        cohort_id = 10000  # Start from higher ID to distinguish

        for dimension_name, values in self.cohort_definitions.items():
            for value_spec in values:
                value = value_spec["name"]
                cohort_spec = {
                    "cohort_id": f"cohort_{cohort_id:04d}",
                    "cohort_params": {dimension_name: value},
                    "priority_level": value_spec.get("priority", 5),
                    "description": value
                    if dimension_name == "age_group"
                    else f"{value.replace('-', ' ')}",
                }
                cohorts.append(cohort_spec)
                cohort_id += 1

        return cohorts

    def export_cohorts(self, output_path: str = "cohorts.json"):
        """Export generated cohorts to JSON file."""
        priority_cohorts = self.generate_priority_cohorts()
        single_cohorts = self.generate_single_dimension_cohorts()

        all_cohorts = {
            "cohorts": priority_cohorts + single_cohorts,
            "total_priority": len(priority_cohorts),
            "total_single": len(single_cohorts),
            "generation_strategy": "priority_based",
        }

        with open(output_path, "w") as f:
            json.dump(all_cohorts, f, indent=2)

        print(f"Generated {len(priority_cohorts)} priority cohorts")
        print(f"Generated {len(single_cohorts)} single-dimension cohorts")
        print(f"Total: {len(priority_cohorts) + len(single_cohorts)} cohorts")
        print(f"Exported to {output_path}")

        return all_cohorts

    def get_cohort_statistics(self) -> Dict[str, Any]:
        """Get statistics about generated cohorts."""
        priority_cohorts = self.generate_priority_cohorts()
        single_cohorts = self.generate_single_dimension_cohorts()

        stats = {
            "total_cohorts": len(priority_cohorts) + len(single_cohorts),
            "by_priority": defaultdict(int),
            "dimensions_used": defaultdict(int),
        }

        for cohort in priority_cohorts:
            stats["by_priority"][cohort["priority_level"]] += 1
            for dimension in cohort["cohort_params"].keys():
                stats["dimensions_used"][dimension] += 1

        for cohort in single_cohorts:
            stats["by_priority"][cohort["priority_level"]] += 1
            for dimension in cohort["cohort_params"].keys():
                stats["dimensions_used"][dimension] += 1

        return dict(stats)


if __name__ == "__main__":
    generator = CohortGenerator(market="singapore")
    root_path = Path(__file__).parent.parent.parent
    output_path = root_path / "output" / "test_cohort.json"
    cohorts = generator.export_cohorts(output_path)

    # Print statistics
    stats = generator.get_cohort_statistics()
    print("\nCohort Statistics:")
    print(json.dumps(stats, indent=2))
