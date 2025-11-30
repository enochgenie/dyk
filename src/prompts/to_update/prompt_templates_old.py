"""
Prompt Templates for DYK Insight Generation
Supports multiple generation strategies and sources.
"""


class PromptTemplates:
    """Collection of prompt templates for different generation modes."""

    @staticmethod
    def pure_llm_insight_generation(
        cohort_description: str,
        cohort_params: dict,
        template_type: str,
        health_domain: str,
        region: str = "singapore",
    ) -> str:
        """
        Generate prompt for pure LLM-based insight generation (no external tools).
        Uses LLM's pre-trained knowledge only.
        """

        base_prompt = f"""You are a medical and public health expert generating evidence-based health insights for a health application.

TARGET COHORT:
{cohort_description}

Cohort Parameters: {cohort_params}
Region: {region}

TASK:
Generate a "Did You Know" (DYK) health insight specifically tailored to this cohort. The insight should be:
1. Evidence-based and scientifically accurate
2. Highly relevant to this specific demographic
3. Actionable and motivating
4. Culturally appropriate for {region}

OUTPUT FORMAT (JSON):
{{
  "hook": "A compelling, attention-grabbing fact that starts with 'Did you know...' (max 20 words)",
  "explanation": "A brief, evidence-based explanation of why this matters for this specific cohort (40-60 words)",
  "action": "A specific, actionable step the user can take (20-30 words)",
  "source_name": "Name of the authoritative source (e.g., WHO, CDC, HPB, peer-reviewed journal)",
  "source_url": "URL if available (or 'general medical knowledge' if based on established consensus)",
  "health_domain": "One of: cardiovascular, metabolic, respiratory, mental-health, nutrition, physical-activity, cancer-prevention, screening, sleep, preventive-care",
  "confidence": "high/medium/low - your confidence in this claim",
  "numeric_claim": "Any specific numeric claim made (e.g., '3x higher risk', '30% reduction')"
}}

TEMPLATE TYPE: {template_type}
"""

        template_guidance = {
            "risk_amplification": """
Focus on highlighting specific health risks elevated for this cohort.
Example structure: "Did you know that [cohort] have [X]x higher risk of [condition]? [Explanation of why]. [Specific prevention action]."
""",
            "protective_factors": """
Focus on positive behaviors that particularly benefit this cohort.
Example structure: "Did you know that [positive behavior] can reduce your risk of [condition] by [X]%? [Explanation]. [How to start]."
""",
            "early_detection": """
Focus on screening and early detection opportunities.
Example structure: "Did you know that [screening] can detect [condition] [X] years earlier? [Why it matters for cohort]. [How to get screened]."
""",
            "behavior_change": """
Focus on small, achievable changes with measurable impact.
Example structure: "Did you know that [small change] can improve [health outcome] by [X]%? [Why it works]. [Simple first step]."
""",
            "comparative": """
Focus on comparing this cohort to others or to averages.
Example structure: "Did you know that compared to [reference group], [cohort] have [difference]? [Context]. [What to do]."
""",
        }

        prompt = base_prompt + template_guidance.get(template_type, "")

        prompt += """
IMPORTANT REQUIREMENTS:
- Be specific to the cohort's characteristics (age, gender, lifestyle, conditions)
- Use actual statistics when possible (but be accurate - don't make up numbers)
- Cite reputable sources
- Keep language clear and motivating
- Ensure the action is practical and achievable

DO NOT:
- Make up statistics or data
- Use vague or generic insights that could apply to anyone
- Include medical advice that requires professional diagnosis
- Use fear-mongering language

Return ONLY valid JSON, no additional text.
"""

        return prompt

    @staticmethod
    def evidence_based_insight_generation(
        cohort_description: str,
        cohort_params: dict,
        evidence_context: str,
        region: str = "singapore",
        template_type: str = "risk_amplification",
    ) -> str:
        """
        Generate prompt when evidence from external tools (PubMed, etc.) is provided.
        """

        prompt = f"""You are a medical and public health expert generating evidence-based health insights for a health application.

TARGET COHORT:
{cohort_description}

Cohort Parameters: {cohort_params}
Region: {region}

RETRIEVED EVIDENCE:
{evidence_context}

TASK:
Using ONLY the evidence provided above, generate a "Did You Know" (DYK) health insight tailored to this cohort.

CRITICAL REQUIREMENTS:
1. Base your insight ONLY on the evidence provided - do not use external knowledge
2. Cite specific sources from the evidence
3. If the evidence doesn't support a strong claim for this cohort, indicate lower confidence
4. Preserve any numeric claims exactly as stated in the evidence

OUTPUT FORMAT (JSON):
{{
  "hook": "A compelling, attention-grabbing fact that starts with 'Did you know...' (max 20 words)",
  "explanation": "A brief, evidence-based explanation citing the sources above (40-60 words)",
  "action": "A specific, actionable step the user can take (20-30 words)",
  "source_name": "Name from the evidence provided",
  "source_url": "URL from the evidence provided",
  "source_pmid": "PubMed ID if available",
  "health_domain": "One of: cardiovascular, metabolic, respiratory, mental-health, nutrition, physical-activity, cancer-prevention, screening, sleep, preventive-care",
  "confidence": "high/medium/low - based on strength of evidence",
  "evidence_support": "Quote the specific sentence(s) from evidence that support your claim",
  "cohort_relevance": "Explain why this evidence applies to this specific cohort"
}}

TEMPLATE TYPE: {template_type}

FAITHFULNESS CHECK:
- Does your insight accurately reflect the evidence?
- Are numeric claims preserved exactly?
- Are you extrapolating beyond what the evidence states?
- Is the source properly attributed?

Return ONLY valid JSON, no additional text.
"""

        return prompt

    @staticmethod
    def search_query_generation(cohort_params: dict, health_domain: str = None) -> str:
        """
        Generate search queries for PubMed/external tools.
        """

        prompt = f"""Generate 3-5 focused search queries to find high-quality evidence for health insights.

TARGET COHORT: {cohort_params}
HEALTH DOMAIN: {health_domain or "any relevant domain"}

Generate search queries that will find:
1. Epidemiological data specific to this demographic
2. Risk factors and protective factors
3. Evidence-based interventions
4. Recent guidelines or recommendations

OUTPUT FORMAT (JSON):
{{
  "queries": [
    "query 1 - focused on risk factors",
    "query 2 - focused on interventions",
    "query 3 - focused on prevalence/statistics"
  ],
  "filters": {{
    "publication_years": "recent 5 years preferred",
    "study_types": "systematic reviews, RCTs, cohort studies, guidelines"
  }}
}}

QUERY GUIDELINES:
- Use medical terminology and MeSH terms
- Include demographic specifics (age range, sex)
- Be specific enough to find relevant results
- Avoid overly broad queries

Return ONLY valid JSON, no additional text.
"""

        return prompt

    @staticmethod
    def validation_prompt(insight: dict, cohort_params: dict) -> str:
        """
        Prompt for secondary LLM to validate insight accuracy and faithfulness.
        """

        prompt = f"""You are a medical fact-checker validating a health insight.

INSIGHT TO VALIDATE:
{insight}

TARGET COHORT:
{cohort_params}

VALIDATION TASKS:
Evaluate this insight on the following criteria:

1. FACTUAL ACCURACY
   - Are the claims medically accurate?
   - Are numeric claims plausible and properly contextualized?
   - Is the source credible?

2. COHORT RELEVANCE
   - Is this insight specifically relevant to the target cohort?
   - Would this cohort benefit from this information?
   - Are demographic factors properly considered?

3. SOURCE FAITHFULNESS (if source provided)
   - Does the insight accurately represent the source?
   - Are numeric claims preserved correctly?
   - Is attribution appropriate?

4. SAFETY & APPROPRIATENESS
   - Is the advice safe and appropriate?
   - Does it avoid medical diagnosis/treatment claims?
   - Is the language motivating without fear-mongering?

5. ACTIONABILITY
   - Is the action step specific and achievable?
   - Is it appropriate for the cohort?

OUTPUT FORMAT (JSON):
{{
  "overall_score": 0-100,
  "factual_accuracy": {{"score": 0-100, "issues": ["list any problems"]}},
  "cohort_relevance": {{"score": 0-100, "issues": []}},
  "source_faithfulness": {{"score": 0-100, "issues": []}},
  "safety": {{"score": 0-100, "issues": []}},
  "actionability": {{"score": 0-100, "issues": []}},
  "recommendation": "approve/revise/reject",
  "revision_suggestions": ["specific suggestions if revise/reject"]
}}

Return ONLY valid JSON, no additional text.
"""

        return prompt

    @staticmethod
    def creative_rewrite_prompt(insight: dict, style: str = "engaging") -> str:
        """
        Prompt for creative rewriting while preserving accuracy.
        """

        prompt = f"""Rewrite this health insight to be more engaging while preserving complete factual accuracy.

ORIGINAL INSIGHT:
Hook: {insight.get("hook")}
Explanation: {insight.get("explanation")}
Action: {insight.get("action")}

STYLE: {style}

CRITICAL RULES:
1. DO NOT change any numeric claims or statistics
2. DO NOT alter the fundamental message
3. Preserve source attribution
4. Make language more engaging and accessible
5. Ensure medical accuracy is maintained

OUTPUT FORMAT (JSON):
{{
  "hook": "Rewritten hook (more engaging)",
  "explanation": "Rewritten explanation (clearer, more engaging)",
  "action": "Rewritten action (more motivating)",
  "changes_made": ["list of changes"],
  "preserved_facts": ["key facts that were not altered"]
}}

Return ONLY valid JSON, no additional text.
"""

        return prompt


class RegionSpecificPrompts:
    """Region-specific prompt additions."""

    @staticmethod
    def singapore_context() -> str:
        return """
SINGAPORE-SPECIFIC CONTEXT:
- Reference local health initiatives (e.g., HPB's National Steps Challenge)
- Use Singapore-appropriate examples (hawker centers, HDB, MRT)
- Consider multi-ethnic context (Chinese, Malay, Indian)
- Reference local healthcare system (polyclinics, subsidies)
- Use Singaporean English where appropriate
"""

    @staticmethod
    def global_context() -> str:
        return """
GLOBAL CONTEXT:
- Use internationally recognized guidelines
- Avoid region-specific references
- Use inclusive, universally understood language
"""
