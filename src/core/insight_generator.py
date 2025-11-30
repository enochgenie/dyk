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
        # # retrieve evidence if there is any
        # evidence = self.evidence_retriever.retrieve_for_cohort(
        #     cohort=cohort,
        #     health_domains=health_domains,
        #     insight_template=insight_template,
        # )

        # build augmented prompt if any evidence is found
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

    # def generate_pure_llm(
    #     self,
    #     cohort_spec: Dict[str, Any],
    #     template_type: str = "risk_amplification",
    #     region: str = "singapore",
    # ) -> Dict[str, Any]:
    #     """
    #     Generate insight using pure LLM knowledge (no external tools).

    #     Args:
    #         cohort_spec: Cohort specification with params and description
    #         template_type: Type of insight template
    #         region: Target region

    #     Returns:
    #         Generated insight dictionary
    #     """
    #     cohort_params = cohort_spec["cohort_params"]
    #     cohort_description = cohort_spec["description"]

    #     # Generate prompt
    #     prompt = self.templates.pure_llm_insight_generation(
    #         cohort_description=cohort_description,
    #         cohort_params=cohort_params,
    #         region=region,
    #         template_type=template_type,
    #     )

    #     # Add region-specific context
    #     if region == "singapore":
    #         prompt += RegionSpecificPrompts.singapore_context()
    #     else:
    #         prompt += RegionSpecificPrompts.global_context()

    #     # Generate
    #     try:
    #         response = self.llm.generate(prompt, model=self.model, temperature=0.7)

    #         # Parse JSON response
    #         insight = self._parse_json_response(response)

    #         # Add metadata
    #         insight["cohort_id"] = cohort_spec["cohort_id"]
    #         insight["cohort_params"] = cohort_params
    #         insight["generation_method"] = "pure_llm"
    #         insight["model_used"] = self.model
    #         insight["template_type"] = template_type
    #         insight["region"] = region

    #         return insight

    #     except Exception as e:
    #         print(f"Error generating pure LLM insight: {e}")
    #         return None

    # def generate_evidence_based(
    #     self,
    #     cohort_spec: Dict[str, Any],
    #     template_type: str = "risk_amplification",
    #     region: str = "singapore",
    #     max_sources: int = 5,
    # ) -> Dict[str, Any]:
    #     """
    #     Generate insight using external evidence (PubMed).

    #     Args:
    #         cohort_spec: Cohort specification
    #         template_type: Type of insight template
    #         region: Target region
    #         max_sources: Maximum evidence sources to retrieve

    #     Returns:
    #         Generated insight dictionary with evidence
    #     """
    #     cohort_params = cohort_spec["cohort_params"]
    #     cohort_description = cohort_spec["description"]

    #     # Retrieve evidence
    #     print(f"Retrieving evidence for: {cohort_description}")
    #     evidence_data = self.evidence_retriever.retrieve_for_cohort(
    #         cohort_params=cohort_params, max_sources=max_sources
    #     )

    #     if not evidence_data["articles"]:
    #         print("No evidence found, falling back to pure LLM")
    #         return self.generate_pure_llm(cohort_spec, template_type, region)

    #     print(f"Retrieved {evidence_data['total_sources']} sources")

    #     # Generate prompt with evidence
    #     prompt = self.templates.evidence_based_insight_generation(
    #         cohort_description=cohort_description,
    #         cohort_params=cohort_params,
    #         evidence_context=evidence_data["evidence_context"],
    #         region=region,
    #         template_type=template_type,
    #     )

    #     # Add region-specific context
    #     if region == "singapore":
    #         prompt += RegionSpecificPrompts.singapore_context()

    #     # Generate
    #     try:
    #         response = self.llm.generate(prompt, model=self.model, temperature=0.6)

    #         # Parse JSON response
    #         insight = self._parse_json_response(response)

    #         # Add metadata
    #         insight["cohort_id"] = cohort_spec["cohort_id"]
    #         insight["cohort_params"] = cohort_params
    #         insight["generation_method"] = "evidence_based"
    #         insight["model_used"] = self.model
    #         insight["template_type"] = template_type
    #         insight["region"] = region
    #         insight["evidence_sources"] = evidence_data["articles"]
    #         insight["search_queries"] = evidence_data["queries"]

    #         return insight

    #     except Exception as e:
    #         print(f"Error generating evidence-based insight: {e}")
    #         return None

    # def validate_insight(self, insight: Dict[str, Any]) -> Dict[str, Any]:
    #     """
    #     Validate insight using secondary LLM call.

    #     Args:
    #         insight: Generated insight to validate

    #     Returns:
    #         Validation results
    #     """
    #     prompt = self.templates.validation_prompt(
    #         insight=insight, cohort_params=insight.get("cohort_params", {})
    #     )

    #     try:
    #         response = self.llm.generate(prompt, model=self.model, temperature=0.3)
    #         validation = self._parse_json_response(response)
    #         return validation

    #     except Exception as e:
    #         print(f"Error validating insight: {e}")
    #         return None

    # def grid_generate(
    #     self,
    #     cohorts: List[Dict[str, Any]],
    #     insight_templates: List[Dict[str, Any]],
    #     health_domains: List[Dict[str, Any]],
    #     sources: Dict[str, Dict],
    #     region: str = "singapore",
    #     method: str = "pure_llm",
    #     insights_per_call: int = 3,
    #     rate_limit_delay: float = 1.0,
    # ) -> List[Dict[str, str]]:
    #     """
    #     Generate insights for combination of cohort, templates, and health domains.

    #     Args:
    #         cohorts: List of cohorts
    #         insight_templates: List of insight templates
    #         health_domains: List of health domains
    #         sources: Evidence sources
    #         region: Target region
    #         method: "pure_llm" or "evidence_based"
    #         insights_per_call: Number of insights to generate per LLM call
    #         rate_limit_delay: Delay between API calls (seconds)

    #     Returns:
    #         List of all generated insights
    #     """
    #     # Prepare cohort specifications
    #     all_insights = []
    #     total_cohorts = len(cohorts)

    #     for idx, cohort in enumerate(cohorts, 1):
    #         print(f"\n{'=' * 80}")
    #         print(f"Cohort {idx}/{total_cohorts}: {cohort['description']}")
    #         print(f"{'=' * 80}")

    #         cohort_insights = []

    #         for insight_template in insight_templates:
    #             for health_domain in health_domains:
    #                 print(
    #                     f"\nGenerating insights for template: {insight_template['type']} and domain: {health_domain['name']}"
    #                 )

    #                 if method == "pure_llm":
    #                     prompt = self.prompt_template.pure_llm_generation(
    #                         cohort=cohort,
    #                         insight_template=insight_template,
    #                         health_domain=health_domain,
    #                         sources=sources,
    #                         region=region,
    #                         n=insights_per_call,
    #                     )
    #                 elif method == "evidence_based":
    #                     # TODO: implement evidence_based prompt generation
    #                     pass
    #                 else:
    #                     raise ValueError(f"Unknown method: {method}")

    #                 try:
    #                     insights = self.llm.generate(prompt)
    #                     cohort_insights.extend(insights)
    #                     all_insights.extend(insights)
    #                     print("  ✓ Success")
    #                 except Exception as e:
    #                     print(f"  ✗ Failed: {e}")

    #                 # Rate limiting
    #                 time.sleep(rate_limit_delay)

    #     print(f"\n{'=' * 80}")
    #     print(f"BATCH COMPLETE: Generated {len(all_insights)} total insights")
    #     print(f"{'=' * 80}")

    #     return all_insights

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


# def save_insights(insights: List[Dict[str, Any]], output_path: str):
#     """Save generated insights to JSON file."""
#     # Add timestamp
#     timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

#     output = {
#         "generated_at": timestamp,
#         "total_insights": len(insights),
#         "insights": insights,
#     }

#     with open(output_path, "w") as f:
#         json.dump(output, f, indent=2)

#     print(f"\nSaved {len(insights)} insights to {output_path}")


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
