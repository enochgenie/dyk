# DYK System - Developer Guide

## Overview
This guide walks through the DYK (Did You Know) insight generation system from a developer's perspective, showing inputs/outputs at each step.

---

## System Flow

```
config.yaml → CohortGenerator → InsightGenerator → Validator → QualityScorer → Output
```

---

## Step 1: Configuration (config.yaml)

### Purpose
Central configuration defining all system parameters.

### Key Sections

#### 1. Regions & Sources (lines 1-64)
```yaml
regions:
  singapore:
    authoritative_sources:
      - name: "Health Promotion Board (HPB)"
        tier: 1  # Most authoritative
```

**Purpose:**
- Define region-specific health authorities
- Set source priority tiers (1 = highest)
- Whitelist trusted domains for citations

#### 2. Cohort Definitions (lines 66-156)
```yaml
cohort_definitions:
  age_groups:
    - name: "30-39"
      priority: 1  # High priority demographic
  smoking_status:
    - name: "smoker"
      priority: 1  # High-risk group
```

**Purpose:**
- Define all possible cohort dimensions
- Set priorities (1 = generate more insights for these)
- Avoid combinatorial explosion by focusing on high-value groups

#### 3. Priority Cohorts (lines 158-190)
```yaml
priority_cohorts:
  - dimensions:
      age_group: ["30-39", "40-49"]
      gender: ["male", "female"]
      smoking_status: ["smoker"]
    min_insights: 5
```

**Purpose:**
- Pre-define high-value cohort combinations
- Set minimum insights per combination
- E.g., "40-49 male smokers" is high-priority → generate 5+ insights

**Key Insight:** Instead of generating insights for ALL possible combinations (thousands), focus on ~50 priority combinations.

---

## Step 2: Cohort Generation (cohort_generator.py)

### Input
- `config.yaml`

### Process
```python
generator = CohortGenerator()
cohorts = generator.generate_priority_cohorts()
```

### What It Does

1. **Reads priority rules** from config.yaml
2. **Generates combinations** based on priority_cohorts
   - Example: `age_group: ["30-39", "40-49"]` × `gender: ["male", "female"]` = 4 cohorts
3. **Calculates priority scores** (sum of individual priorities)
4. **Sorts by priority** (lowest score = highest priority)
5. **Adds human descriptions**

### Output Example
```json
{
  "cohort_id": "cohort_0001",
  "cohort_params": {
    "age_group": "30-39",
    "gender": "male",
    "smoking_status": "smoker"
  },
  "min_insights": 5,
  "priority_level": 1,
  "description": "30-39 years old, male, smoker"
}
```

### Statistics
- **Priority cohorts:** 32 (high-value combinations)
- **Single-dimension cohorts:** 23 (e.g., "smokers" only)
- **Total:** 55 cohorts (manageable, not thousands!)

### Run It
```bash
python cohort_generator.py
# Output: cohorts.json
```

---

## Step 3: Insight Generation (insight_generator.py)

### Input
- Cohort specification (from Step 2)
- Template type (e.g., "risk_amplification")
- Generation method (pure_llm or evidence_based)

### Two Methods

#### Method 1: Pure LLM
```python
insight_gen = InsightGenerator()
insight = insight_gen.generate_pure_llm(
    cohort_spec=cohort,
    template_type="risk_amplification"
)
```

**Process:**
1. Reads prompt template from `prompt_templates.py`
2. Injects cohort details (age, gender, etc.)
3. Sends to OpenRouter API (Claude 3.5 Sonnet)
4. Parses JSON response
5. Adds metadata (cohort_id, method, timestamp)

**Speed:** ~30-60 insights/hour
**Cost:** ~$6 per 1,000 insights

#### Method 2: Evidence-Based (with PubMed)
```python
insight = insight_gen.generate_evidence_based(
    cohort_spec=cohort,
    template_type="risk_amplification"
)
```

**Process:**
1. Queries PubMed API for relevant research (`pubmed_integration.py`)
2. Retrieves 3-5 recent studies
3. Injects studies into prompt
4. LLM generates insight grounded in research
5. Includes PubMed citations

**Speed:** ~6-12 insights/hour
**Cost:** ~$15 per 1,000 insights

### Output Structure
```json
{
  "hook": "Did you know that male smokers in their 30s have 3x higher risk of heart disease?",
  "explanation": "Smoking damages blood vessels and reduces oxygen supply...",
  "action": "Schedule a health screening and consider quitting resources like...",
  "source_name": "American Heart Association",
  "source_url": "https://www.heart.org/...",
  "health_domain": "cardiovascular",
  "confidence": "high",
  "numeric_claim": "3x higher risk",
  "cohort_id": "cohort_0001",
  "generation_method": "pure_llm",
  "model_used": "anthropic/claude-3.5-sonnet",
  "template_type": "risk_amplification"
}
```

### Template Types

| Type | Description | Example |
|------|-------------|---------|
| `risk_amplification` | Highlight elevated risks | "Smokers have 3x higher risk..." |
| `protective_factors` | Emphasize positive behaviors | "Exercise reduces risk by 40%..." |
| `early_detection` | Promote screening | "Early screening detects cancer 5 years earlier..." |
| `behavior_change` | Encourage small changes | "10 minutes of walking daily improves..." |
| `comparative` | Compare to peers | "Compared to non-smokers, you have..." |

---

## Step 4: Validation (validator.py)

### Input
- Generated insight (from Step 3)

### Process
```python
validator = InsightValidator()
validation = validator.validate_insight(insight)
```

### Validation Dimensions

#### 1. Structure Validation
- All required fields present? (hook, fact, action, source)
- Fields non-empty?
- Proper data types?

#### 2. Content Quality
- Hook starts with "Did you know"?
- Hook length reasonable? (10-150 chars)
- Explanation substantive? (50+ chars)
- Action specific? (20+ chars)

#### 3. Source Credibility
- Source name provided?
- Source URL valid?
- Domain whitelisted? (checks against config.yaml)

#### 4. Cohort Relevance
- Cohort ID present?
- Cohort params included?

### Output
```json
{
  "overall_valid": true,
  "overall_score": 85,
  "structure_valid": true,
  "content_valid": true,
  "source_valid": true,
  "cohort_valid": true,
  "issues": [],
  "warnings": ["Source URL not from whitelisted domain"]
}
```

### Scoring
- **85-100:** Excellent, ready to use
- **70-84:** Good, minor issues
- **50-69:** Acceptable, review recommended
- **<50:** Poor, needs revision

---

## Step 5: Quality Scoring (validator.py)

### Input
- Validated insight (from Step 4)

### Process
```python
scorer = QualityScorer()
quality_score = scorer.calculate_engagement_score(insight)
```

### Scoring Factors

1. **Hook Quality (35 points)**
   - Length appropriate? (50-150 chars)
   - Has numeric claim? ("3x higher", "40% reduction")
   - Attention-grabbing words? ("surprising", "critical")

2. **Explanation Quality (30 points)**
   - Substantive? (100+ chars)
   - Has numeric data?
   - Credible source mentioned?

3. **Action Quality (25 points)**
   - Specific? (30+ chars)
   - Actionable verbs? ("schedule", "start", "reduce")
   - Practical?

4. **Source Credibility (10 points)**
   - Tier 1 source? (+10)
   - Tier 2? (+7)
   - Tier 3? (+5)

### Output
- Score: 0-100
- Higher = more engaging/credible

---

## Step 6: Pipeline Orchestration (pipeline.py)

### Full Pipeline Flow

```python
from pipeline import DYKPipeline

pipeline = DYKPipeline(config_path="config.yaml")
summary = pipeline.run_full_pipeline(
    method="pure_llm",
    max_cohorts=50,
    insights_per_cohort=5,
    min_quality_score=70
)
```

### What It Does

1. **Generate cohorts** (CohortGenerator)
2. **For each cohort:**
   - Generate N insights (InsightGenerator)
   - Rate-limit API calls
3. **Validate all insights** (Validator)
4. **Calculate quality scores** (QualityScorer)
5. **Remove duplicates** (similarity checking)
6. **Filter by quality** (min_quality_score threshold)
7. **Export outputs**

### Output Files

```
output/
├── cohorts_20250125_143022.json          # Generated cohorts
├── insights_raw_20250125_143022.json     # Before validation
├── validation_20250125_143022.json       # Validation results
├── insights_final_20250125_143022.json   # Final filtered insights
├── insights_final_20250125_143022.csv    # CSV for review
└── summary_20250125_143022.json          # Statistics
```

---

## Running the System

### Quick Test (2 insights)
```bash
python simple_test.py
```

### Small Batch (10 insights)
```bash
python pipeline.py --method pure_llm --max-cohorts 5 --insights-per-cohort 2
```

### Production Run (250 insights)
```bash
python pipeline.py --method evidence_based --max-cohorts 50 --insights-per-cohort 5 --min-quality 75
```

---

## Key Files Reference

| File | Purpose | Run Directly? |
|------|---------|---------------|
| `config.yaml` | Configuration | No |
| `cohort_generator.py` | Generate cohorts | Yes ✓ |
| `insight_generator.py` | Generate insights | Via pipeline |
| `prompt_templates.py` | LLM prompts | No |
| `pubmed_integration.py` | PubMed API | Via evidence_based |
| `validator.py` | Validate & score | Via pipeline |
| `pipeline.py` | Orchestration | Yes ✓ |
| `examples.py` | Interactive examples | Yes ✓ |
| `simple_test.py` | Quick test | Yes ✓ |

---

## Data Flow Diagram

```
┌─────────────┐
│ config.yaml │
└──────┬──────┘
       │
       v
┌─────────────────────┐
│ CohortGenerator     │ → cohorts.json (55 cohorts)
└──────┬──────────────┘
       │
       v
┌─────────────────────┐
│ InsightGenerator    │ → insights_raw.json (N * cohorts)
│ - Pure LLM or       │
│ - Evidence-Based    │
└──────┬──────────────┘
       │
       v
┌─────────────────────┐
│ Validator           │ → validation.json
│ - Structure check   │
│ - Content quality   │
│ - Source verify     │
└──────┬──────────────┘
       │
       v
┌─────────────────────┐
│ QualityScorer       │ → scored insights
│ - Engagement score  │
└──────┬──────────────┘
       │
       v
┌─────────────────────┐
│ Filter & Export     │ → insights_final.json/csv
│ - Remove duplicates │
│ - Quality threshold │
└─────────────────────┘
```

---

## Cost & Performance

### Pure LLM Method
- **Speed:** 30-60 insights/hour
- **Cost:** ~$6 per 1,000 insights
- **Quality:** ⭐⭐⭐ Good for MVP
- **Use case:** Fast iteration, prototyping

### Evidence-Based Method
- **Speed:** 6-12 insights/hour
- **Cost:** ~$15 per 1,000 insights
- **Quality:** ⭐⭐⭐⭐⭐ Production-ready
- **Use case:** Launch, traceable sources

---

## Common Developer Tasks

### Add New Cohort Dimension
1. Edit `config.yaml` → `cohort_definitions`
2. Add to `priority_cohorts` if needed
3. Re-run `cohort_generator.py`

### Add New Template Type
1. Edit `prompt_templates.py` → add to `template_guidance`
2. Update `config.yaml` → `insight_templates`
3. Use in pipeline: `--template-type your_new_type`

### Adjust Quality Thresholds
1. Edit `pipeline.py` command: `--min-quality 80`
2. Or modify `QualityScorer` weights in `validator.py`

### Add New Region
1. Edit `config.yaml` → add region section
2. Add region-specific prompts in `prompt_templates.py`
3. Use: `generator.generate_pure_llm(region="your_region")`

---

## Troubleshooting

### No insights generated
- Check OpenRouter credits: https://openrouter.ai/settings/credits
- Verify API key in `.env`
- Check internet connection

### Low quality scores
- Review prompts in `prompt_templates.py`
- Adjust scoring weights in `validator.py`
- Use evidence-based method for higher quality

### Rate limit errors
- Add `--rate-limit-delay 2.0` to pipeline
- Reduce `max_cohorts` or `insights_per_cohort`

---

## Next Steps

1. **Test the flow:** Run `python simple_test.py`
2. **Review outputs:** Check `output/` directory
3. **Customize:** Edit `config.yaml` for your use case
4. **Scale up:** Run production pipeline
5. **Integrate:** Use JSON outputs in your app

---

**Questions?** Check:
- [QUICKSTART.md](QUICKSTART.md) - Getting started
- [README.md](README.md) - Full documentation
- [COMPARISON.md](COMPARISON.md) - Method comparison
