"""
Prompt Templates for DYK Insight Generation
Supports multiple generation strategies and sources.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.cohort_generator import CohortGenerator
from src.utils.config_loader import ConfigLoader


class PromptTemplates:
    """Collection of prompt templates for different generation modes."""

    def pure_llm_generation(
        self,
        cohort: dict,
        insight_template: dict,
        health_domains: dict,
        sources: dict,
        region: str = "singapore",
        num_insights: int = 20,
    ) -> str:
        """
        Generate prompt for pure LLM-based insight generation (no external tools).
        Uses LLM's pre-trained knowledge only.
        """

        tier_to_names = {
            tier: [src["name"] for src in info["sources"]]
            for tier, info in sources.items()
        }

        optional_block = ""
        if "insight_angles" in cohort and cohort["insight_angles"]:
            optional_block = f"Possible insight angles: {cohort['insight_angles']}\n"

        prompt = f"""
        You are a medical and public health expert generating evidence-based health insights for a health application.

        REGION:
        - {region}

        TARGET COHORT:
        {cohort["description"]}

        Cohort Parameters: {cohort["cohort_params"]}

        INSIGHT TEMPLATE SELECTED:
        - Type: {insight_template["type"]}
        - Description: {insight_template["description"]}
        - Required Tone: "{insight_template["tone"]}"
        - Example Pattern: "{insight_template["example"]}"
        {optional_block}

        EXAMPLE HEALTH DOMAINS: {list(health_domains.keys())}
        Note: You may select different health domains if more relevant

        AUTHORITATIVE SOURCES FOR {region.upper()}: {tier_to_names}

        TASK:
        Generate {num_insights} distinct "Did You Know" health insights tailored to this cohort profile.
        
        STRUCTURAL REQUIREMENTS:
        1. Opening Hook (15-25 words): Lead with a surprising, specific statistic or fact
        2. Explanation (20-40 words): Brief mechanism or context explaining why this matters
        3. Call-to-Action (15-25 words): Clear, specific action they can take
        
        CONTENT REQUIREMENTS:
        - Evidence-based with specific percentages/numbers
        - Relevant to the cohort's demographic, lifestyle and health risks
        - Scientifically accurate - cite reputable sources
        - Culturally appropriate for {region}
        - Each insight must be UNIQUE (different facts, statistics, actions, health domains)
        - Follow the conceptual intent of the selected template (“{insight_template["description"]}”)
        - Ensure the action is practical, achievable, region-appropriate and cohort-specific
        

        OUTPUT FORMAT (JSON):
        {{
        "insights": [
            {{
            "hook": "A compelling, attention-grabbing fact that starts with 'Did you know...' (max 25 words)",
            "explanation": "A brief, evidence-based explanation of why this matters for this specific cohort (20-40 words)",
            "action": "A specific, actionable step the user can take (15-25 words)",
            "source_name": "Name of the authoritative source (e.g., WHO, CDC, HPB, peer-reviewed journal)",
            "source_url": "URL if available, or 'general medical knowledge'",
            "numeric_claim": "Any specific numeric claim made (e.g., '3x higher risk', '30% reduction'), or empty string if none"
            }}
            // ... repeat for all {num_insights} insights
        ]
        }}

        AVOID:
        - Excessive program mentions
        - Repeating the same insight with minor variations
        - Multiple CTAs in one insight (focus on ONE clear action)
        - Generic "talk to your doctor" endings without specifics
        - Explicitly stating age ranges (e.g., "40-49 year olds")
        - Heavy-handed booking/registration CTAs in every insight
        - Made-up statistics or claims
        - Fear-mongering language

        Return ONLY valid JSON, no additional text.
        """

        return prompt

    def validation_prompt(
        self,
        insight: Dict[str, Any],
        cohort: Dict[str, Any],
        insight_template: Dict[str, Any],
        region: str,
    ) -> str:
        """
        Prompt for secondary LLM to validate insight accuracy and faithfulness.
        """

        prompt = f"""You are a medical fact-checker validating a health insight.

        INSIGHT TO VALIDATE:
        {insight}

        TARGET COHORT:
        {cohort["cohort_params"]} - {cohort["description"]}
        
        INSIGHT TEMPLATE:
        - Type: {insight_template["type"]}
        - Description: {insight_template["description"]}
        
        REGION:
        - {region}

        VALIDATION TASKS:
        Evaluate this insight on the following criteria:

        1. FACTUAL ACCURACY
        - Are the claims medically accurate?
        - Are numeric claims plausible and properly contextualized?
        - Is the source credible?
        
        2. SAFETY & APPROPRIATENESS
        - Does it avoid medical diagnosis/treatment claims?
        - Is the language motivating without fear-mongering?
        - Is the advice safe and appropriate?
        
        3. FAITHFULNESS TO EVIDENCE (if source provided)
        - Does the insight accurately represent the source?
        - Are numeric claims preserved correctly?
        - Is attribution appropriate?
        
        4. RELEVANCE
        - Is this insight specifically relevant to the target cohort?
        - Would this cohort benefit from this information?
        - Are demographic factors properly considered?
        - Does it align with the intent of the selected insight template?

        5. ACTIONABILITY
        - Is the action step specific and achievable?
        - Is the action appropriate for this demographic?
        - Does the action seem like an advertisement or promotional content?
        
        6. CULTURAL APPROPRIATENESS
        - Is the language and advice culturally appropriate for the target region?
    
        PROVIDE A DETAILED EVALUATION AND AN OVERALL RECOMMENDATION:
        - Overall Score (0-100)
        - Specific scores (0-100) and issues for each criterion
        - Final Recommendation: "approve", "revise", or "reject"
        - If "revise" or "reject", provide specific revision suggestions.

        OUTPUT FORMAT (JSON):
        {{
        "overall_score": 0-100,
        "factual_accuracy": {{"score": 0-100, "issues": ["list any problems"]}},
        "safety": {{"score": 0-100, "issues": []}},
        "source_faithfulness": {{"score": 0-100, "issues": []}},
        "relevance": {{"score": 0-100, "issues": []}},
        "actionability": {{"score": 0-100, "issues": []}},
        "cultural_appropriateness": {{"score": 0-100, "issues": []}},
        "recommendation": "approve/revise/reject",
        "revision_suggestions": ["specific suggestions if revise/reject"]
        }}

        Return ONLY valid JSON, no additional text.
        """

        return prompt

    # def pure_llm_generation(
    #     self,
    #     cohort: dict,
    #     insight_template: dict,
    #     health_domain: dict,
    #     sources: dict,
    #     region: str = "singapore",
    #     n: int = 1,
    # ) -> str:
    #     """
    #     Generate prompt for pure LLM-based insight generation (no external tools).
    #     Uses LLM's pre-trained knowledge only.
    #     """

    #     tier_to_names = {
    #         tier: [src["name"] for src in info["sources"]]
    #         for tier, info in sources.items()
    #     }

    #     prompt = f"""
    #     You are a medical and public health expert generating evidence-based health insights for a health application.

    #     REGION:
    #     - {region}

    #     TARGET COHORT:
    #     {cohort["description"]}

    #     Cohort Parameters: {cohort["cohort_params"]}

    #     INSIGHT TEMPLATE SELECTED:
    #     - Type: {insight_template["type"]}
    #     - Description: {insight_template["description"]}
    #     - Required Tone: "{insight_template["tone"]}"
    #     - Example Pattern: "{insight_template["example"]}"

    #     HEALTH DOMAIN:
    #     - Domain: {health_domain["name"]}
    #     - Example conditions: {health_domain["subcategories"]}

    #     AUTHORITATIVE SOURCES FOR {region.upper()}: {tier_to_names}

    #     TASK:
    #     Generate {n} distinct "Did You Know" (DYK) health insight specifically tailored to this cohort. Each insight should be:
    #     1. Evidence-based and scientifically accurate
    #     2. Highly relevant to this specific demographic and health domain
    #     3. Actionable and motivating
    #     4. Culturally appropriate for {region}
    #     5. Following the conceptual intent of the selected template (“{insight_template["description"]}”)
    #     6. UNIQUE from the other insights (cover different facts, statistics, conditions, or actions)

    #     OUTPUT FORMAT (JSON):
    #     {{
    #     "insights": [
    #         {{
    #         "hook": "A compelling, attention-grabbing fact that starts with 'Did you know...' (max 20 words)",
    #         "explanation": "A brief, evidence-based explanation of why this matters for this specific cohort (30-60 words)",
    #         "action": "A specific, actionable step the user can take (20-30 words)",
    #         "source_name": "Name of the authoritative source (e.g., WHO, CDC, HPB, peer-reviewed journal)",
    #         "source_url": "URL if available, or 'general medical knowledge'",
    #         "numeric_claim": "Any specific numeric claim made (e.g., '3x higher risk', '30% reduction'), or empty string if none"
    #         }}
    #         // ... repeat for all {n} insights
    #     ]
    #     }}

    #     IMPORTANT REQUIREMENTS:
    #     - Be specific to the cohort's characteristics (age, gender, lifestyle, conditions)
    #     - Use actual statistics when possible (but be accurate - don't make up numbers)
    #     - Cite reputable sources
    #     - Keep language clear and motivating
    #     - Ensure the action is practical, achievable, region-appropriate and cohort-specific

    #     DO NOT:
    #     - Make up statistics or data
    #     - Use vague or generic insights that could apply to anyone
    #     - Include medical advice that requires professional diagnosis
    #     - Use fear-mongering language
    #     - Repeat the same insight with minor variations

    #     Return ONLY valid JSON, no additional text.
    #     """

    #     return prompt

    # def validation_prompt(
    #     self,
    #     insight: Dict[str, Any],
    #     cohort: Dict[str, Any],
    #     insight_template: Dict[str, Any],
    #     health_domain: Dict[str, Any],
    #     region: str,
    # ) -> str:
    #     """
    #     Prompt for secondary LLM to validate insight accuracy and faithfulness.
    #     """

    #     prompt = f"""You are a medical fact-checker validating a health insight.

    #     INSIGHT TO VALIDATE:
    #     {insight}

    #     TARGET COHORT:
    #     {cohort["cohort_params"]} - {cohort["description"]}

    #     INSIGHT TEMPLATE:
    #     - Type: {insight_template["type"]}
    #     - Description: {insight_template["description"]}

    #     HEALTH DOMAIN:
    #     - Domain: {health_domain["name"]}

    #     REGION:
    #     - {region}

    #     VALIDATION TASKS:
    #     Evaluate this insight on the following criteria:

    #     1. FACTUAL ACCURACY
    #     - Are the claims medically accurate?
    #     - Are numeric claims plausible and properly contextualized?
    #     - Is the source credible?

    #     2. SAFETY & APPROPRIATENESS
    #     - Does it avoid medical diagnosis/treatment claims?
    #     - Is the language motivating without fear-mongering?
    #     - Is the advice safe and appropriate?

    #     3. FAITHFULNESS TO EVIDENCE (if source provided)
    #     - Does the insight accurately represent the source?
    #     - Are numeric claims preserved correctly?
    #     - Is attribution appropriate?

    #     4. RELEVANCE
    #     - Is this insight specifically relevant to the target cohort?
    #     - Would this cohort benefit from this information?
    #     - Are demographic factors properly considered?
    #     - Is it pertinent to the specified health domain?
    #     - Does it align with the intent of the selected insight template?

    #     5. ACTIONABILITY
    #     - Is the action step specific and achievable?
    #     - Is the action appropriate for this demographic?

    #     6. CULTURAL APPROPRIATENESS
    #     - Is the language and advice culturally appropriate for the target region?

    #     PROVIDE A DETAILED EVALUATION AND AN OVERALL RECOMMENDATION:
    #     - Overall Score (0-100)
    #     - Specific scores (0-100) and issues for each criterion
    #     - Final Recommendation: "approve", "revise", or "reject"
    #     - If "revise" or "reject", provide specific revision suggestions.

    #     OUTPUT FORMAT (JSON):
    #     {{
    #     "overall_score": 0-100,
    #     "factual_accuracy": {{"score": 0-100, "issues": ["list any problems"]}},
    #     "safety": {{"score": 0-100, "issues": []}},
    #     "source_faithfulness": {{"score": 0-100, "issues": []}},
    #     "relevance": {{"score": 0-100, "issues": []}},
    #     "actionability": {{"score": 0-100, "issues": []}},
    #     "cultural_appropriateness": {{"score": 0-100, "issues": []}},
    #     "recommendation": "approve/revise/reject",
    #     "revision_suggestions": ["specific suggestions if revise/reject"]
    #     }}

    #     Return ONLY valid JSON, no additional text.
    #     """

    #     return prompt


if __name__ == "__main__":
    # Example usage
    prompt_template = PromptTemplates()

    # example insight template
    insight_template = {
        "type": "protective_synergies",
        "description": "Combined protective effects of multiple positive behaviors",
        "weight": 5,
        "example": "Non-smoking + 150min exercise weekly creates 5x stronger heart protection than either alone",
        "tone": "Encouraging, synergistic",
    }

    # example region
    region = "singapore"

    # example health domain
    config_loader = ConfigLoader(market="singapore")
    health_domains = config_loader.health_domains
    sources = config_loader.sources

    cohort_generator = CohortGenerator(market="singapore")
    cohort = cohort_generator.generate_priority_cohorts()[0]

    pure_llm_prompt = prompt_template.pure_llm_generation(
        cohort=cohort,
        insight_template=insight_template,
        health_domains=health_domains,
        sources=sources,
        region=region,
        num_insights=20,
    )

    print(pure_llm_prompt)

    insight = {
        "hook": "Did you know that regular exercise can reduce your risk of depression by up to 30%?",
        "explanation": "Engaging in physical activity releases endorphins and other chemicals that improve mood and reduce stress, which is particularly beneficial for individuals aged 50-59 who are obese.",
        "action": "Aim for at least 150 minutes of moderate exercise each week, such as brisk walking or cycling.",
        "source_name": "Health Promotion Board (HPB)",
        "source_url": "https://www.healthhub.sg",
        "numeric_claim": "reduce your risk of depression by up to 30%",
    }

    validation_prompt = prompt_template.validation_prompt(
        insight,
        cohort=cohort,
        insight_template=insight_template,
        region=region,
    )

    print("Validation prompt:")
    print(validation_prompt)
