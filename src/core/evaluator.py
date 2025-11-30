"""
Evaluator Layer
Ensures insights are factually accurate, safe, faithful to evidence, relevant, actionable, and culturally appropriate.
"""

import json
from typing import Any, Dict, List
from src.prompts.prompt_templates import PromptTemplates
from src.core.insight_generator import OpenRouterClient


class InsightEvaluator:
    """
    Evaluator for DYK insights.

    Evaluation includes:
    1. Factual accuracy
    2. Safety
    3. Faithfulness to evidence
    4. Relevance
    5. Actionability
    6. Cultural appropriateness
    """

    def __init__(self, llm: OpenRouterClient, prompt_templates: PromptTemplates):
        self.llm = llm
        self.prompts = prompt_templates

    def evaluate(
        self,
        insight: Dict[str, Any],
        cohort: Dict[str, Any],
        insight_template: Dict[str, Any],
        region: str,
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> dict:
        """
        Evaluate a given insight using LLM prompts.

        Args:
            insight: The insight to evaluate.
            cohort: The cohort parameters.
            insight_template: The template used to generate the insight.
            region: The target region for cultural appropriateness.

        Returns:
            A dictionary with evaluation results.
        """

        # generate prompt
        prompt = self.prompts.validation_prompt(
            insight, cohort, insight_template, region
        )

        # call LLM with prompt
        evaluation_results = self.llm.generate(prompt, model, temperature, max_tokens)
        evaluation_results = self._parse_json_response(evaluation_results)

        return evaluation_results

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


if __name__ == "__main__":
    llm = OpenRouterClient(api_key="")

    prompts = PromptTemplates()
    evaluator = InsightEvaluator(llm, prompts)

    insight = {
        "hook": "Did you know that regular exercise can reduce your risk of depression by up to 30%?",
        "explanation": "Engaging in physical activity releases endorphins and other chemicals that improve mood and reduce stress, which is particularly beneficial for individuals aged 50-59 who are obese.",
        "action": "Aim for at least 150 minutes of moderate exercise each week, such as brisk walking or cycling.",
        "source_name": "Health Promotion Board (HPB)",
        "source_url": "https://www.healthhub.sg",
        "numeric_claim": "reduce your risk of depression by up to 30%",
    }

    cohort = {
        "cohort_id": "cohort_0006",
        "cohort_params": {"age_group": "50-59", "bmi": "obese"},
        "priority_level": 2,
        "description": "50-59 years old, obese",
    }

    # example insight template
    insight_template = {
        "type": "protective_synergies",
        "description": "Combined protective effects of multiple positive behaviors",
        "weight": 5,
        "example": "Non-smoking + 150min exercise weekly creates 5x stronger heart protection than either alone",
        "tone": "Encouraging, synergistic",
    }

    region = "singapore"

    evaluation = evaluator.evaluate(
        insight,
        cohort,
        insight_template,
        region,
        model="google/gemini-2.5-flash",
        temperature=0.7,
        max_tokens=2000,
    )

    print("Evaluation Results:")
    print(evaluation)
