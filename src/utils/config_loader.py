"""Configuration loader for YAML config files."""

import yaml
from pathlib import Path
import random
from typing import Dict, Any, Optional


class ConfigLoader:
    """Load and manage configuration files."""

    def __init__(self, market: str, config_base_path: Optional[Path] = None):
        """
        Initialize the config loader.

        Args:
            market: region-specific configuration
            config_base_path: Base path for config files. Defaults to src/config/
        """
        self.market = market.lower()

        if config_base_path is None:
            # Default to src/config relative to this file
            self.config_base_path = Path(__file__).parent.parent / "config"
        else:
            self.config_base_path = Path(config_base_path)

        self.market_path = self.config_base_path / market

    def load_yaml(self, filepath: Path) -> Dict[str, Any]:
        """Load a single YAML file."""
        with open(filepath, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)

    @property
    def sources(self):
        return self.load_yaml(self.market_path / "sources.yaml")["evidence_sources"]

    @property
    def cohort_definitions(self):
        return self.load_yaml(self.market_path / "cohort_definitions.yaml")[
            "cohort_definitions"
        ]

    @property
    def priority_cohorts(self):
        return self.load_yaml(self.market_path / "priority_cohorts.yaml")[
            "priority_cohorts"
        ]

    @property
    def health_domains(self):
        return self.load_yaml(self.config_base_path / "health_domains.yaml")[
            "health_domains"
        ]

    @property
    def insight_templates(self):
        return self.load_yaml(self.config_base_path / "insight_templates.yaml")[
            "insight_templates"
        ]

    def sample_insight_templates(self, n: int = 1):
        """

        Args:
            n (int): number of templates to sample
        """
        templates = self.insight_templates

        keys = list(templates.keys())
        n = min(n, len(keys))
        weights = [templates[k]["weight"] for k in keys]

        sampled_keys = random.choices(keys, weights=weights, k=n)

        return [templates[key] for key in sampled_keys]

    def sample_health_domains(self, n: int = 1):
        """
        Randomly sample N health domains (uniform probability) with replacement.

        Args:
            n (int): number of health domains to sample
        """
        domains = self.health_domains
        keys = list(domains.keys())
        n = min(n, len(keys))

        sampled_keys = random.sample(keys, n)

        return [domains[key] for key in sampled_keys]


if __name__ == "__main__":
    # test code
    loader = ConfigLoader(market="singapore")

    print("Sources:")
    print(loader.sources)

    print("\nCohort Definitions:")
    print(loader.cohort_definitions)

    print("\nPriority Cohorts:")
    print(loader.priority_cohorts)

    print("\nHealth Domains:")
    print(loader.health_domains)

    print("\nInsight Templates:")
    print(loader.insight_templates)

    print("\nSampled insight templates:")
    print(loader.sample_insight_templates(3))

    print("\nSampled health domains:")
    print(loader.sample_health_domains(3))
