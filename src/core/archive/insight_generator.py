"""
Main Insight Generator
Supports both pure LLM and evidence-based generation via OpenRouter API.
"""

import os
import json
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
import sys
import requests

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# from dyk.src.prompts.prompt_templates_old import PromptTemplates, RegionSpecificPrompts
from src.prompts.prompt_templates import PromptTemplates
from src.utils.config_loader import ConfigLoader
from services.pubmed_service import EvidenceRetriever, PubMedAPI


class OpenRouterClient:
    """Client for OpenRouter API."""

    def __init__(self, model="x-ai/grok-4.1-fast", api_key: Optional[str] = None):
        """
        Initialize OpenRouter client.

        Args:
            model: Model to use
            api_key: OpenRouter API key (or set OPENROUTER_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenRouter API key required. Set OPENROUTER_API_KEY environment variable."
            )

        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.default_model = model

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """
        Generate completion via OpenRouter.

        Args:
            prompt: Input prompt
            model: Model to use (default: x-ai/grok-4.1-fast)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text response
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://dyk-health-insights.com",  # Optional but recommended
        }

        data = {
            "model": model or self.default_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            response = requests.post(
                self.base_url, headers=headers, json=data, timeout=60
            )
            response.raise_for_status()

            result = response.json()
            return result["choices"][0]["message"]["content"]

        except requests.exceptions.RequestException as e:
            print(f"OpenRouter API error: {e}")
            if hasattr(e, "response") and e.response is not None:
                print(f"Response: {e.response.text}")
            raise


class InsightGenerator:
    """Main insight generation orchestrator."""

    def __init__(
        self,
        llm_client: OpenRouterClient,
        evidence_retriever: EvidenceRetriever,
        prompt_template: PromptTemplates,
    ):
        """
        Initialize insight generator.

        Args:
            llm_client: OpenRouterClient instance
            evidence_retriever: EvidenceRetriever instance
            prompt_template: PromptTemplates instance
        """
        self.llm = llm_client
        self.evidence_retriever = evidence_retriever
        self.prompt_template = prompt_template

    def generate(
        self,
        cohort: dict,
        insight_template: dict,
        health_domains: dict,
        sources: dict,
        region: str = "singapore",
        num_insights: int = 3,
        model: str = "x-ai/grok-4.1-fast",
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ):
        prompt = self.prompt_template.pure_llm_generation(
            cohort=cohort,
            insight_template=insight_template,
            health_domains=health_domains,
            sources=sources,
            region=region,
            num_insights=num_insights,
        )

        # call llm
        response = self.llm.generate(
            prompt, model=model, temperature=temperature, max_tokens=max_tokens
        )

        # return parsed response
        return self._parse_json_response(response)

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response, handling markdown code blocks."""
        # Remove markdown code blocks if present
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]

        response = response.strip()

        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(f"Response: {response[:500]}")
            raise


# Example usage
if __name__ == "__main__":
    # set up instances
    llm = OpenRouterClient(api_key="")
    pubmed_client = PubMedAPI(email="enoch@geniehealth.care", api_key="")
    prompt_template = PromptTemplates()
    evidence_retriever = EvidenceRetriever(pubmed_client=pubmed_client, max_results=5)

    # example cohort
    example_cohort = {
        "cohort_id": "cohort_0006",
        "cohort_params": {"age_group": "50-59", "bmi": "obese"},
        "priority_level": 2,
        "description": "50-59 years old, obese",
    }

    config_loader = ConfigLoader(market="singapore")
    insight_template = config_loader.insight_templates["risk_amplification"]
    sources = config_loader.sources
    region = "singapore"
    health_domains = config_loader.health_domains

    # Initialize generator
    generator = InsightGenerator(llm, evidence_retriever, prompt_template)

    # grid generation example
    insights = generator.generate(
        cohort=example_cohort,
        insight_template=insight_template,
        health_domains=health_domains,
        sources=sources,
        region=region,
        num_insights=10,
        model="x-ai/grok-4.1-fast",
        temperature=0.8,
        max_tokens=3000,
    )

    print(insights)

    # # Generate pure LLM insight
    # print("Generating pure LLM insight...")
    # pure_insight = generator.generate_pure_llm(cohort)
    # print(json.dumps(pure_insight, indent=2))

    # # Generate evidence-based insight
    # print("\n\nGenerating evidence-based insight...")
    # evidence_insight = generator.generate_evidence_based(cohort)
    # print(json.dumps(evidence_insight, indent=2))
