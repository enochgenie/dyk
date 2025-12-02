"""
Prompt Templates for DYK Insight Generation
Supports multiple generation strategies and sources.
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
import sys
from textwrap import dedent


# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from src.utils.config_loader import ConfigLoader


class PromptTemplates:
    """Collection of prompt templates for different generation modes."""

    def generation_prompt(
        self,
        cohort: dict,
        insight_template: dict,
        health_domains: dict,
        sources: dict,
        market: str = "singapore",
        num_insights: int = 20,
    ) -> str:
        """
        Generate prompt for pure LLM-based insight generation (no external tools).
        Uses LLM's pre-trained knowledge only.
        """
        prompt = dedent(f"""
        
        You are a medical and public health expert generating evidence-based health insights for a health application.

        REGION: {market.title()}

        TARGET COHORT: {cohort["description"]}
        Cohort Parameters: {cohort["dimensions"]}

        INSIGHT TEMPLATE SELECTED:
        - Type: {insight_template["type"]}
        - Description: {insight_template["description"]}
        - Required Tone: "{insight_template["tone"]}"
        - Example Pattern: "{insight_template["example"]}"

        EXAMPLE HEALTH DOMAINS: {list(health_domains.keys())}
        Note: You may select different health domains if more relevant

        AUTHORITATIVE SOURCES FOR {market.upper()}: {sources}

        TASK:
        Generate {num_insights} distinct "Did You Know" health insights tailored to this cohort profile.
        
        STRUCTURAL REQUIREMENTS:
        1. Opening Hook (15-25 words): Lead with a surprising, specific statistic or fact
        2. Explanation (20-40 words): Brief mechanism or context explaining why this matters
        3. Call-to-Action (15-25 words): Clear, specific action they can take
        
        CONTENT REQUIREMENTS:
        - Evidence-based with specific percentages/numbers when available
        - Relevant to the cohort's demographic, goals, lifestyle and health risks
        - Scientifically accurate - all statistics must be verifiable
        - Culturally appropriate for {market}
        - Each insight must be UNIQUE (different facts, statistics, actions, health domains)
        - Follow the conceptual intent of the selected template ("{insight_template["description"]}")
        - Ensure the action is practical, achievable, region-appropriate and cohort-specific
        
        CRITICAL REQUIREMENTS:
        - All statistics MUST be accurate and verifiable from reputable sources
        - If uncertain about a specific number, do not include it
        - Do not extrapolate or combine statistics in misleading ways
        - Sources must be real organizations or publications
        - Refer to the cohort naturally without explicitly stating age ranges
        
        OUTPUT FORMAT (JSON):
        {{
        "insights": [
            {{
            "hook": "A compelling, attention-grabbing fact that starts with 'Did you know...' (15-25 words)",
            "explanation": "Evidence-based explanation of why this matters for this cohort (20-40 words))",
            "action": "A specific, actionable step the user can take (15-25 words)",
            "source_name": "Name of the authoritative source (e.g., WHO, CDC, HPB, peer-reviewed journal)",
            "source_url": "URL to the specific source page if available, or null for well-established medical consensus",
            "numeric_claim": "The exact numeric claim from hook/explanation (e.g., '30%', '3x higher'), or null if no specific number"
            }}
            // ... repeat for all {num_insights} insights
        ]
        }}

        AVOID:
        - Excessive program mentions or promotional language
        - Repeating the same insight with minor variations
        - Multiple CTAs in one insight (focus on ONE clear action)
        - Generic "talk to your doctor" endings without specifics
        - Heavy-handed booking/registration CTAs in every insight
        - Made-up or unverifiable statistics
        - Fear-mongering language
        - Overly explicit age range references (say "young adults" instead of "18-29 year olds")

        Return ONLY valid JSON, no additional text, markdown, or code blocks.
        """).strip()

        return prompt

    def validation_prompt(
        self,
        insight: Dict[str, Any],
        cohort: Dict[str, Any],
        insight_template: Dict[str, Any],
        market: str,
    ) -> str:
        """
        Prompt for secondary LLM to validate insight accuracy and faithfulness.
        """

        insight_text = " ".join(
            [insight["hook"], insight["explanation"], insight["action"]]
        )

        # Build evidence section from source information
        evidence_section = ""
        if "source_name" in insight and insight["source_name"]:
            evidence_section = f"Source: {insight['source_name']}"
            if "source_url" in insight and insight["source_url"]:
                evidence_section += f"\nURL: {insight['source_url']}"
        else:
            evidence_section = "No specific source provided - evaluate based on general knowledge and plausibility."

        prompt = dedent(f"""
            You are an expert evaluator for "Did You Know" (DYK) insights. 
            Evaluate the following insight across multiple dimensions.

            INSIGHT TO VALIDATE:
            {insight_text}
            
            SUPPORTING EVIDENCE:
            {evidence_section}
            
            CONTEXT:
            - Target Cohort: {cohort["description"]}
            - Cohort dimensions: {cohort["dimensions"]}
            - Market/Region: {market}
            - Insight Template: {insight_template["type"]} - {insight_template["description"]}
            
            Evaluate the insight on the following criteria. For each criterion, provide:
            1. A score from 1 to 10 (integers only)
            2. A brief justification (1-3 sentences)
            3. A list of issues (empty list if none)
            
            EVALUATION CRITERIA:

            1. FACTUAL ACCURACY (1-10)
            - Are all claims factually correct?
            - Are statistics, numbers, and data points accurate?
            - Are there any misleading or false statements?

            2. SAFETY (1-10)
            - Is the content free from harmful, offensive, or inappropriate material?
            - Does it avoid promoting dangerous behaviors or misinformation?
            - Is it appropriate for the target audience?
            
            3. FAITHFULNESS TO EVIDENCE (1-10)
            - If source material is provided: Does the insight accurately reflect it?
            - If only citation is provided: Is the insight plausible given the source type?
            - Are there unsupported claims or unreasonable extrapolations?
            - Is the interpretation appropriate given available information?

            4. COHORT RELEVANCE (1-10)
            - Is this insight relevant and valuable to the target cohort?
            - Does it address their specific needs, interests, or pain points?
            - Would this cohort find it actionable or useful?

            5. ACTIONABILITY (1-10)
            - Does the insight provide clear, practical takeaways?
            - Can the audience act on this information?
            - Are next steps or implications clear?

            6. LOCALIZATION (1-10)
            - Is the content appropriately adapted for the target market/region?
            - Are cultural nuances, local regulations, and regional differences considered?
            - Is the language, tone, and examples appropriate for the locale?

            Respond in JSON format with the following structure:
            {{
                "criteria": {{
                    "factual_accuracy": {{"score": 0, "justification": "", "issues": []}},
                    "safety": {{"score": 0, "justification": "", "issues": []}},
                    "faithfulness": {{"score": 0, "justification": "", "issues": []}},
                    "cohort_relevance": {{"score": 0, "justification": "", "issues": []}},
                    "actionability": {{"score": 0, "justification": "", "issues": []}},
                    "localization": {{"score": 0, "justification": "", "issues": []}}
                }},
                "pass": false,
                "strengths": [],
                "critical_issues": [],
                "recommendations": []
            }}
            
            Return ONLY valid JSON, no additional text, markdown, or code blocks.
        """).strip()

        return prompt

    def creative_rewriting_prompt(
        self,
        insight: Dict[str, Any],
        cohort: Dict[str, Any],
        market: str,
        num_variations: int = 3,
    ) -> str:
        """
        Prompt for creative rewriting to generate diverse variations of an insight.
        This layer adds linguistic diversity while preserving factual accuracy.
        """

        prompt = dedent(f"""
        You are rewriting health insights for genie — a data-driven health platform that speaks as "The Smart Ally".

        TONE: Sharp, action-oriented, respectful of intelligence. No emojis, no fear-mongering, no vague wellness-speak.

        ORIGINAL INSIGHT:
        Hook: {insight.get("hook", "")}
        Explanation: {insight.get("explanation", "")}
        Action: {insight.get("action", "")}
        Source: {insight.get("source_name", "")}
        Numeric Claim: {insight.get("numeric_claim", "")}

        TARGET COHORT:
        - Cohort name: {cohort.get("name", "")}
        - Cohort description: {cohort.get("description", "")}
        - Cohort dimensions: {cohort.get("dimensions", "")}
        REGION: {market.title()}

        TASK: Create {num_variations} distinct variation(s) using Genie's "Smart Ally" voice.

        SMART ALLY PRINCIPLES:
        1. Clear, not chatty — precise language, no fluff
        2. Data-aware — anchor in specifics ("18% down" not "improved")
        3. Action-oriented — prompt next move, don't leave in reflection
        4. Confident, not cocky — assured but backed by data

        CRITICAL FOCUS AREAS:

        1. COHORT RELEVANCE (VERY IMPORTANT)
        - Tailor language, examples, and actions to the specific cohort: {cohort.get("description", "")}
        - Reference their lifestyle, goals, and health concerns naturally
        - Make the insight feel personally relevant without being overly explicit
        - Example: For "young professionals", mention "after work" or "desk job"; for "retirees", mention "in your daily routine"

        2. LOCALIZATION FOR {market.upper()} (VERY IMPORTANT)
        - Use {market}-specific contexts, terminology, or cultural references where natural
        - Suggest actions accessible in {market} without assuming user's exact location
        - Keep measurements and terminology appropriate for the region
        - Example for Singapore: "hawker centre", "near your MRT station", "park connector", "void deck", "hokkien mee"

        REWRITING RULES:
        ✓ Keep ALL numbers, percentages, statistics EXACTLY as stated
        ✓ Vary sentence structure, word choice, and emphasis
        ✓ Use active voice and crisp phrasing
        ✓ Lead with the insight, follow with context, end with action
        ✓ Use em dashes (—) for emphasis when natural
        ✓ Make each variation feel tailored to the cohort AND localized to {market}

        ✗ NO emojis, exclamation marks, or vague language
        ✗ NO fear-based framing ("Be careful!" "You're at risk!")
        ✗ NO oversimplification ("Magic tip: drink water!")
        ✗ NO changes to source attribution or numeric claims
        ✗ NO generic advice that could apply to anyone anywhere

        EXAMPLES (preserve numbers, vary structure, add cohort relevance + localization):

        Original insight: "Did you know walking 30 minutes daily reduces heart disease risk by 25%?"
        Cohort: Young professionals (25-35, sedentary office jobs)
        Market: Singapore

        Variation 1 (cohort-focused): "30 minutes of daily walking cuts heart disease risk by 25% — even with a desk job, one lunchtime walk makes that shift."
        Variation 2 (localized): "Walking half an hour each day lowers heart disease risk by a quarter — try a park connector near your MRT station during lunch breaks."
        Variation 3 (both): "Daily 30-minute walks reduce heart disease risk by 25% — for desk-bound professionals, an evening walk at a nearby park such as East Coast Park after work adds up."

        Note: All preserve "30 minutes", "daily", "25%" but add cohort-specific ("desk job", "lunchtime") and Singapore-localized ("park connector", "MRT station", "nearby park") context without assuming exact location.

        OUTPUT FORMAT (JSON):
        {{
            "variations": [
                {{
                    "hook": "Sharp, data-driven hook (15-25 words)",
                    "explanation": "Clear context showing why this matters (20-40 words)",
                    "action": "Specific, actionable next step (15-25 words)",
                    "source_name": "{insight.get("source_name", "")}",
                    "source_url": "{insight.get("source_url", "")}",
                    "numeric_claim": "{insight.get("numeric_claim", "")}",
                    "variation_id": 1
                }}, 
                // ... repeat for all {num_variations} variation(s)
            ]
        }}

        Return ONLY valid JSON, no markdown or extra text.
        """).strip()

        return prompt


if __name__ == "__main__":
    # Example usage
    prompt_template = PromptTemplates()
    market = "singapore"
    loader = ConfigLoader(market=market)
    cohort = loader.priority_cohorts[0]
    insight_template = loader.insight_templates["hidden_consequence"]
    health_domains = loader.health_domains
    sources = loader.source_names

    insight = {
        "hook": "Did you know that regular exercise can reduce your risk of depression by up to 30%?",
        "explanation": "Engaging in physical activity releases endorphins and other chemicals that improve mood and reduce stress, which is particularly beneficial for individuals aged 50-59 who are obese.",
        "action": "Aim for at least 150 minutes of moderate exercise each week, such as brisk walking or cycling.",
        "source_name": "Health Promotion Board (HPB)",
        "source_url": "https://www.healthhub.sg",
        "numeric_claim": "reduce your risk of depression by up to 30%",
    }

    gen_prompt = prompt_template.generation_prompt(
        cohort=cohort,
        insight_template=insight_template,
        health_domains=health_domains,
        sources=sources,
        market=market,
        num_insights=20,
    )
    print("Generation prompt:")
    print(gen_prompt)

    validation_prompt = prompt_template.validation_prompt(
        insight,
        cohort=cohort,
        insight_template=insight_template,
        market=market,
    )

    print("Validation prompt:")
    print(validation_prompt)

    creative_prompt = prompt_template.creative_rewriting_prompt(
        insight, cohort, market, num_variations=3
    )
    print(creative_prompt)
