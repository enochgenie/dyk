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
        Prompt for secondary LLM to validate insight across 6 critical dimensions.
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
            evidence_section = "No specific source provided - evaluate based on general medical/health knowledge."

        prompt = dedent(f"""
            You are a rigorous evaluator for health insights. Your role is to catch errors, hallucinations, and quality issues before insights reach end users.

            INSIGHT TO EVALUATE:
            "{insight_text}"
            
            EVIDENCE PROVIDED:
            {evidence_section}
            
            CONTEXT:
            - Target Cohort: {cohort["name"]} - {cohort["description"]}
            - Cohort Dimensions: {cohort["dimensions"]}
            - Market: {market.title()}
            - Template Type: {insight_template["type"]} - {insight_template["description"]}
            
            EVALUATION TASK:
            Rate the insight on 6 criteria using a 1-10 scale where:
            - 1-3: Critical issues, should not be published
            - 4-6: Significant problems, needs major revision
            - 7-8: Minor issues, needs small improvements
            - 9-10: Excellent, ready to publish

            For each criterion, provide:
            1. Integer score (1-10)
            2. Concise justification (2-3 sentences max)
            3. Specific issues found (empty list if none)

            ---

            CRITERION 1: FACTUAL ACCURACY
            Does this insight contain accurate, verifiable health information?

            ✓ PASS if:
            - All statistics/numbers are plausible and verifiable
            - Health claims align with mainstream medical consensus
            - No exaggerated or misleading statements
            - Percentages, timeframes, and quantities are reasonable

            ✗ FAIL if:
            - Contains obviously wrong numbers (e.g., "walking reduces heart disease by 200%")
            - Makes implausible claims (e.g., "cures cancer in 3 days")
            - Contradicts established medical knowledge
            - Includes made-up statistics or sources

            SPECIFIC CHECKS:
            - Are the numbers (percentages, durations, quantities) realistic?
            - Can the claim be verified or is it plausible given the source?
            - Does it avoid absolute claims like "always", "never", "guarantees"?

            ---

            CRITERION 2: SAFETY
            Is this insight safe for end users without risk of harm?

            ✓ PASS if:
            - Appropriate for general audience
            - No dangerous medical advice
            - Doesn't encourage harmful behaviors
            - Suitable for the target cohort (including vulnerable groups)

            ✗ FAIL if:
            - Recommends stopping prescribed medications
            - Encourages dangerous activities without caveats
            - Contains triggering content for health conditions
            - Gives medical diagnoses or treatment advice
            - Promotes extreme diets, over-exercise, or self-harm

            SPECIFIC CHECKS:
            - Could this advice harm someone if followed?
            - Does it suggest consulting a doctor when appropriate?
            - Is it appropriate for all members of the target cohort?

            ---

            CRITERION 3: FAITHFULNESS TO EVIDENCE
            Does the insight accurately represent its source material?

            ✓ PASS if:
            - Claims are supported by the cited source (or are plausibly from such sources)
            - No cherry-picking or misrepresentation
            - Appropriate confidence level (doesn't overstate findings)
            - Clearly distinguishes correlation from causation

            ✗ FAIL if:
            - Makes claims unsupported by source type (e.g., citing "Harvard study" for obvious falsehoods)
            - Exaggerates findings (study shows "may help" → insight claims "proven to cure")
            - Misattributes information to reputable sources
            - Extrapolates beyond reasonable interpretation

            SPECIFIC CHECKS:
            - Given the source name/type, is this claim plausible?
            - Does it avoid overstating certainty ("research shows" vs "one study suggests")?
            - If no source provided, is it common health knowledge?

            ---

            CRITERION 4: COHORT RELEVANCE
            Is this insight valuable and relatable for "{cohort["name"]}"?

            ✓ PASS if:
            - Addresses specific needs/challenges of this cohort
            - Uses language and examples they relate to
            - Timing/lifecycle stage matches (e.g., retirement tips for retirees, not students)
            - Acknowledges their constraints (time, mobility, resources)

            ✗ FAIL if:
            - Generic advice that applies to everyone
            - Ignores cohort's lifestyle or limitations (e.g., "exercise 2 hours daily" for busy parents)
            - Assumes resources they may not have
            - Uses tone/language mismatched to demographic

            SPECIFIC CHECKS:
            - Does it reference the cohort's lifestyle, goals, or pain points?
            - Would this cohort think "this is for me" or "this is generic"?
            - Are examples and context appropriate for their life stage?

            COHORT DETAILS TO CONSIDER: {cohort["description"]}

            ---

            CRITERION 5: ACTIONABILITY
            Is the suggested action clear, practical, and achievable for this cohort in {market.title()}?

            ✓ PASS if:
            - Action is specific and concrete (not "be healthier")
            - Realistic for the cohort's lifestyle and constraints
            - Measurable or observable (can tell if they did it)
            - Accessible in the target market (no location-specific barriers)
            - Free from commercial promotions or product placement

            ✗ FAIL if:
            - Vague advice ("improve your health", "try to be active")
            - Unrealistic time/cost commitment for cohort
            - Requires unavailable resources in target market
            - Promotes specific brands or paid services
            - Too many actions at once (overwhelming)

            SPECIFIC CHECKS:
            - Can someone do this tomorrow? This week?
            - Is it clear what success looks like?
            - Does it avoid promoting products/services/apps?
            - Is it appropriate for {market.title()} (access, legality, culture)?

            ---

            CRITERION 6: LOCALIZATION
            Is this insight grounded in {market.title()} culture, context, and lifestyle?

            ✓ PASS if:
            - Uses local terminology, food, places naturally (not forced)
            - References culturally appropriate activities/contexts
            - Considers local climate, urban design, work culture
            - Measurements and units match regional standards
            - Language feels native, not translated

            ✗ FAIL if:
            - Generic Western examples in non-Western market, eastern examples in western market
            - References inaccessible locations (e.g., "local park" in dense urban area with no parks)
            - Ignores cultural norms (e.g., gym culture where gyms are rare/expensive)
            - Forced localization that feels unnatural

            SPECIFIC CHECKS FOR {market.upper()}:
            - Does it use local food, places, or cultural references where natural?
            - Are suggestions accessible given local infrastructure?
            - Does it respect local work culture and lifestyle patterns?
            - Would a local resident find this relatable?

            ---

            FINAL SCORING:

            Calculate overall_score as the average of all 6 criteria:
            overall_score = (factual_accuracy + safety + faithfulness + cohort_relevance + actionability + localization) / 6

            Set pass = true ONLY if ALL of these conditions are met:
            - All 6 criteria scores ≥ 7
            - factual_accuracy ≥ 8 (critical)
            - safety ≥ 8 (critical)

            Otherwise, set pass = false.

            OUTPUT FORMAT (JSON only, no markdown):
            {{
                "criteria": {{
                    "factual_accuracy": {{"score": 8, "justification": "...", "issues": []}},
                    "safety": {{"score": 9, "justification": "...", "issues": []}},
                    "faithfulness": {{"score": 7, "justification": "...", "issues": []}},
                    "cohort_relevance": {{"score": 8, "justification": "...", "issues": []}},
                    "actionability": {{"score": 7, "justification": "...", "issues": []}},
                    "localization": {{"score": 6, "justification": "...", "issues": ["..."]}},
                }},
                "overall_score": 7.5,
                "pass": false,
                "strengths": ["Strength 1", "Strength 2"],
                "critical_issues": ["Critical issue that blocks publication"],
                "recommendations": ["Specific recommendation 1", "Specific recommendation 2"]
            }}

            Return ONLY valid JSON. No markdown, no code blocks, no additional text.
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
        Prompt for creative variations that explore different narrative angles
        while maintaining factual accuracy.
        """

        prompt = dedent(f"""
        You are creating distinct narrative variations of health insights for genie's "Smart Ally" voice.

        CORE DATA (IMMUTABLE):
        - Numeric claim: {insight.get("numeric_claim", "")}
        - Source: {insight.get("source_name", "")}
        - Target: {cohort.get("name", "")} ({cohort.get("description", "")})
        - Market: {market.title()}

        ORIGINAL FRAMING:
        Hook: {insight.get("hook", "")}
        Explanation: {insight.get("explanation", "")}
        Action: {insight.get("action", "")}

        YOUR TASK: Create {num_variations} CREATIVELY DISTINCT variations by exploring different narrative angles.

        WHAT MAKES A VARIATION "CREATIVE":
        Each variation should take a fundamentally different approach:

        1. LEAD WITH DIFFERENT ELEMENTS
        - Problem-first: Start with the pain point or challenge
        - Solution-first: Start with the action, then justify
        - Surprise-first: Lead with the counterintuitive data point
        - Consequence-first: Start with what happens if they don't act

        2. VARY YOUR NARRATIVE STRUCTURE
        - Direct command → data → reason
        - Question → answer → application  
        - Contrast → insight → next step
        - Scenario → data → reframe

        3. SHIFT THE FRAMING LENS
        - Efficiency angle ("faster, simpler")
        - Prevention angle ("before it becomes a problem")
        - Optimization angle ("you're close, here's the edge")
        - Reframing angle ("it's not what you think")

        4. CHANGE THE TEMPORAL FOCUS
        - Immediate payoff vs. long-term benefit
        - Daily habit vs. cumulative effect
        - Single action vs. pattern change

        MANDATORY ELEMENTS (in every variation):
        ✓ Exact numeric claim: {insight.get("numeric_claim", "")}
        ✓ Cohort-specific language and examples (use natural descriptors, not explicit age ranges)
        ✓ {market}-localized context (terminology, places, cultural touchpoints)
        ✓ Active, specific action step
        ✓ "Smart Ally" voice: sharp, data-driven, no fluff

        FORBIDDEN ELEMENTS:
        ✗ Emojis, exclamation marks, fear-mongering
        ✗ Vague wellness-speak ("boost your health", "feel better")
        ✗ Generic advice that ignores cohort or market
        ✗ Changing any numbers, percentages, or source attribution
        ✗ Explicit age ranges (say "young professionals" not "25-35 year olds", "midlife adults" not "40-50 year olds")

        ANTI-PATTERNS TO AVOID:
        ✗ Same opening word across variations ("Walking...", "Walking...", "Walking...")
        ✗ Same sentence structure repeated ("X does Y by Z%")
        ✗ Only swapping adjectives ("daily walking" → "regular walking")
        ✗ Generic location references ("a nearby park" repeated in multiple variations)

        AIM FOR:
        ✓ Different first words across all variations
        ✓ Mix of short/long sentences  
        ✓ Different statistical positioning (leading vs. supporting vs. concluding)
        ✓ Specific, varied location examples

        EXAMPLES OF TRUE VARIATION:

        Core data: Walking 30 minutes daily reduces heart disease risk by 25%
        Cohort: Young professionals (25-35, sedentary jobs)
        Market: Singapore

        Variation 1 - Problem-first, prevention angle:
        Hook: "Desk jobs increase heart disease risk — but 30 minutes of daily movement cuts that risk by 25%"
        Explanation: "For professionals spending 8+ hours seated, cardiovascular strain compounds quietly. The data shows a quarter-reduction in risk with consistent, moderate activity."
        Action: "Block 30 minutes at lunch or after work — try the Southern Ridges trail or a lap around Marina Bay."

        Variation 2 - Solution-first, efficiency angle:
        Hook: "Walk for 30 minutes daily — your heart disease risk drops by a quarter"
        Explanation: "No gym required, no special equipment. Half an hour of walking each day delivers a 25% reduction in cardiovascular risk, even with an otherwise sedentary routine."
        Action: "Start with your morning commute: get off one MRT stop early and walk the rest."

        Variation 3 - Surprise-first, reframing angle:
        Hook: "Your lunch break is already long enough to cut heart disease risk by 25%"
        Explanation: "Thirty minutes — that's all it takes to walk your way to measurably better heart health. For desk-bound professionals, this single daily habit makes the difference."
        Action: "Tomorrow, skip the hawker centre nearest your office and walk to one 15 minutes away instead."

        Notice how each:
        - Opens differently (problem vs. solution vs. reframe)
        - Uses different sentence rhythms and lengths
        - Suggests distinct, market-specific actions
        - Maintains the exact statistic but integrates it differently

        OUTPUT FORMAT (JSON):
        {{
            "variations": [
                {{
                    "hook": "Opening line (15-25 words)",
                    "explanation": "Why this matters (20-40 words)",
                    "action": "Specific next step (15-25 words)",
                    "narrative_angle": "Brief label for the approach used (e.g., 'problem-first, prevention')"
                }},
                // ... {num_variations} total
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
