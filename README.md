# DYK (Did You Know) Health Insights Generation Pipeline

## Executive Summary

The DYK pipeline is an AI-powered system that generates personalized, evidence-based health insights for specific population segments. The system combines demographic data, health research, and Large Language Models (LLMs) to produce targeted "Did You Know" insights that are validated, quality-controlled, and optimized for engagement.

**Key Capabilities:**
- Generates personalized health insights for priority cohorts (office workers, seniors, women, etc.)
- Validates insights against quality standards and source credibility
- Evaluates insights for accuracy, safety, and cultural appropriateness
- Produces actionable, evidence-based health recommendations
- Supports Singapore market with extensibility to other regions

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     DYK PIPELINE ARCHITECTURE                   │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────┐
│  Configuration   │
│  (YAML Files)    │
│                  │
│ • Cohorts        │──┐
│ • Templates      │  │
│ • Health Domains │  │
│ • Sources        │  │
└──────────────────┘  │
                      ▼
              ┌───────────────┐
              │  1. COHORT    │
              │  GENERATOR    │
              │               │
              │ Generate      │
              │ priority      │
              │ cohorts       │
              └───────┬───────┘
                      │
                      ▼
              ┌───────────────┐        ┌──────────────┐
              │  2. INSIGHT   │◄───────│  OpenRouter  │
              │  GENERATOR    │        │  LLM Client  │
              │               │        │  (Grok 4.1)  │
              │ Create DYK    │        └──────────────┘
              │ insights via  │
              │ LLM           │        ┌──────────────┐
              └───────┬───────┘        │   PubMed     │
                      │         ┌──────│  Evidence    │
                      │         │      │  Retriever   │
                      │         │      └──────────────┘
                      ▼         │
              ┌───────────────┐ │
              │  3. VALIDATOR │ │
              │               │ │
              │ Check:        │ │
              │ • Schema      │ │
              │ • Sources     │◄┘
              │ • URLs        │
              └───────┬───────┘
                      │
                      ▼
              ┌───────────────┐        ┌──────────────┐
              │ 4. EVALUATOR  │◄───────│  Evaluation  │
              │               │        │  LLM Client  │
              │ Assess:       │        │  (Grok 4.1)  │
              │ • Accuracy    │        └──────────────┘
              │ • Safety      │
              │ • Relevance   │
              │ • Cultural fit│
              └───────┬───────┘
                      │
                      ▼
              ┌───────────────┐
              │  5. OUTPUT    │
              │               │
              │ • Validated   │
              │ • Evaluated   │
              │ • Metadata    │
              └───────────────┘
```

---

## Pipeline Steps

### Step 1: Cohort Generation
**Module:** [src/core/cohort_generator.py](src/core/cohort_generator.py)

**Purpose:** Identify target population segments for personalized insights.

**What it does:**
- Reads priority cohort definitions from YAML configuration files
- Generates cohort specifications based on demographic and health characteristics
- Prioritizes cohorts by clinical impact and relevance (e.g., obese office workers, perimenopausal women, seniors with chronic diseases)
- Outputs structured cohort data including demographic parameters, priority level, and targeting rationale

**Example Cohorts:**
- Sedentary office workers aged 30-59 with metabolic risk
- Perimenopausal women (45-59) managing hormonal transitions
- Seniors (60+) managing multiple chronic conditions
- High-stress professionals with cardiovascular risk factors

**Output:** `cohorts.json` containing all generated cohort specifications

---

### Step 2: Insight Generation
**Module:** [src/core/insight_generator.py](src/core/insight_generator.py)

**Purpose:** Create compelling, evidence-based "Did You Know" health insights.

**What it does:**
- For each cohort, selects applicable insight templates (e.g., "quantified_action_benefit", "risk_reversal", "protective_synergies")
- Constructs LLM prompts combining:
  - Cohort characteristics
  - Insight template structure
  - Health domain knowledge
  - Regional context (Singapore-specific sources like HPB, HealthHub)
  - Number of insights to generate
- Calls OpenRouter API (using Grok 4.1 model) to generate insights
- Parses and structures LLM responses into standardized JSON format
- Adds generation metadata (model, timestamp, temperature, etc.)

**Insight Structure:**
Each insight contains:
- **hook**: Attention-grabbing opening statement with statistics
- **explanation**: Why this matters for the target cohort (40-60 words)
- **action**: Specific, actionable recommendation
- **source_name**: Credible source reference
- **source_url**: Link to authoritative health information
- **numeric_claim**: Specific quantifiable claim

**Example Output:**
```json
{
  "hook": "Did you know regular exercise + balanced diet doubles protection against depression compared to either alone?",
  "explanation": "For obese Singaporeans aged 50-59 at higher depression risk from inflammation and low mood, this synergy boosts brain chemicals like serotonin more effectively...",
  "action": "Aim for 150min weekly brisk walking and follow HPB My Healthy Plate...",
  "source_name": "Health Promotion Board (HPB)",
  "source_url": "https://www.hpb.gov.sg/healthy-living/mental-wellbeing",
  "numeric_claim": "doubles protection"
}
```

**Output:** `insights_raw.json` containing all generated insights with metadata

---

### Step 3: Validation
**Module:** [src/core/validator.py](src/core/validator.py)

**Purpose:** Quality control to ensure insights meet structural and credibility standards.

**What it does:**
Runs three validation checks on each insight:

1. **JSON Validity**
   - Confirms insight is properly structured and serializable

2. **Schema Conformity**
   - Verifies all required fields are present (hook, explanation, action, source_name, source_url, numeric_claim)
   - Checks field types match expectations (all strings)
   - Validates field length constraints:
     - Hook: max 20 words
     - Explanation: 30-60 words optimal
     - Action: max 30 words

3. **Source Verification**
   - Validates URL format and accessibility
   - Checks that source URLs are reachable (HTTP status check)
   - Flags generic sources ("general medical knowledge")

**Outcome:**
- Insights passing all checks are marked as `validated: true`
- Failed insights are flagged with specific failure reasons
- Validation metadata is appended to each insight

**Output:**
- `insights_post_validation.json` - All insights with validation results
- `insights_validated.json` - Only insights that passed validation

---

### Step 4: Evaluation
**Module:** [src/core/evaluator.py](src/core/evaluator.py)

**Purpose:** LLM-based quality assessment for factual accuracy, safety, and relevance.

**What it does:**
- Takes insights that passed validation
- Constructs evaluation prompts that assess:
  - **Factual accuracy**: Are claims scientifically sound?
  - **Safety**: Is the advice safe for the target cohort?
  - **Faithfulness to evidence**: Does it align with cited sources?
  - **Relevance**: Is it applicable to the cohort's specific needs?
  - **Actionability**: Is the recommended action clear and practical?
  - **Cultural appropriateness**: Does it fit Singapore's healthcare context and cultural norms?
- Calls evaluation LLM (Grok 4.1) to score insights
- Parses evaluation results and extracts quality scores
- Appends evaluation metadata to each insight

**Outcome:**
- Each insight receives an evaluation score and detailed feedback
- Average evaluation scores calculated across all insights
- Only validated insights are evaluated (failed insights skip this step)

**Output:** `insights_final.json` containing fully validated and evaluated insights

---

### Step 5: Output & Reporting
**Module:** [src/generate_insights.py](src/generate_insights.py) (main pipeline orchestrator)

**Purpose:** Save results and generate pipeline summary.

**What it does:**
- Aggregates all pipeline statistics:
  - Total cohorts processed
  - Total insights generated
  - Validation pass rate
  - Average evaluation scores
  - Pipeline duration
- Saves comprehensive output files with timestamps
- Generates `pipeline_summary.json` with complete pipeline metrics

**Output Files:**
1. `cohorts.json` - All generated cohorts
2. `insights_raw.json` - Raw LLM-generated insights
3. `insights_post_validation.json` - All insights with validation results
4. `insights_validated.json` - Only validated insights (passed)
5. `insights_final.json` - Fully validated and evaluated insights (JSON)
6. `insights_final.csv` - Fully validated and evaluated insights (CSV for Excel/Google Sheets)
7. `pipeline_summary.json` - Complete pipeline run statistics

---

## Supporting Components

### Configuration Management
**Module:** [src/utils/config_loader.py](src/utils/config_loader.py)

**Purpose:** Load and manage market-specific configurations.

**Manages:**
- Cohort definitions (age groups, BMI categories, health conditions)
- Priority cohorts (specific combinations with clinical rationale)
- Insight templates (15+ types like "risk_reversal", "quantified_action_benefit")
- Health domains (cardiovascular, metabolic, mental health, etc.)
- Regional sources (HPB, HealthHub, MOH, etc.)

**Key Feature:** Market-based configuration system supports Singapore with extensibility to other markets (Australia, Malaysia, etc.)

---

### Evidence Retrieval (Optional)
**Module:** [src/services/pubmed_service.py](src/services/pubmed_service.py)

**Purpose:** Fetch scientific evidence from PubMed to ground insights in research.

**Capabilities:**
- Searches PubMed database using cohort and health domain keywords
- Fetches article abstracts, titles, authors, publication details
- Formats evidence context for LLM consumption
- Supports both pure LLM generation and evidence-augmented generation

**Status:** Currently optional; pipeline primarily uses pure LLM generation with curated source references.

---

### Prompt Engineering
**Module:** [src/prompts/prompt_templates.py](src/prompts/prompt_templates.py)

**Purpose:** Craft effective prompts for insight generation and evaluation.

**Key Prompts:**
1. **Pure LLM Generation Prompt**
   - Combines cohort details, insight template, health domains, and regional sources
   - Instructs LLM on desired output format and tone
   - Emphasizes Singapore-specific sources and cultural context

2. **Validation Prompt**
   - Guides evaluation LLM to assess factual accuracy, safety, relevance, etc.
   - Provides structured evaluation criteria
   - Returns JSON-formatted quality scores

---

## Configuration Files

Located in [src/config/](src/config/):

### `singapore/priority_cohorts.yaml`
Defines high-impact population segments with clinical rationale:
- Office workers with metabolic risk
- Shift workers with disrupted circadian rhythms
- Stressed midlife professionals
- Perimenopausal women
- Seniors at risk of functional decline
- Students with mental health concerns

Each cohort includes:
- Demographic dimensions
- Priority level (1=highest impact)
- Clinical rationale with statistics
- Suggested insight angles

### `insight_templates.yaml`
15 insight templates optimized for engagement:
- **quantified_action_benefit**: "X action for Y time → Z% improvement"
- **risk_reversal**: "Condition X increases risk BUT action Y reverses it"
- **mechanism_reveal**: Explain the fascinating 'why' behind health phenomena
- **comparative_effectiveness**: Compare approaches showing surprising efficiency
- **minimum_effective_dose**: Show surprisingly low threshold for major benefits
- And 10 more specialized templates

Each template includes:
- Type and description
- Weight (importance/frequency of use)
- Structure guidelines
- Example insights
- Recommended tone

### `health_domains.yaml`
Major health categories:
- Cardiovascular health
- Metabolic health
- Mental wellbeing
- Musculoskeletal health
- Cancer prevention
- And more

### `singapore/sources.yaml`
Authoritative Singapore health sources:
- Health Promotion Board (HPB)
- HealthHub
- Ministry of Health (MOH)
- National registries and programs

---

## Viewing Results (CSV Export)

> **📖 For detailed viewing guide, see [VIEWING_RESULTS.md](VIEWING_RESULTS.md)**

The pipeline automatically generates a **CSV file** (`insights_final.csv`) alongside the JSON output. This CSV is optimized for quick viewing in Excel or Google Sheets.

### CSV Columns:
| Column | Description |
|--------|-------------|
| Insight ID | Unique identifier (INS_0001, INS_0002, etc.) |
| Hook | Attention-grabbing opening |
| Explanation | Why this matters (40-60 words) |
| Action | Specific recommendation |
| Numeric Claim | Quantifiable claim |
| Source Name | Credible source |
| Source URL | Link to source |
| Cohort ID | Target population ID |
| Cohort Description | Human-readable target audience |
| Age Group | Age demographic |
| Template Type | Insight template used |
| Validated | Pass/Fail validation |
| Validation Issues | Specific issues (if failed) |
| Evaluation Score | Quality score (0-10) |
| Generated At | Timestamp |

### Converting Existing JSON to CSV

If you have existing JSON files, convert them using:

```bash
# Basic conversion
python scripts/json_to_csv.py output/insights_final.json

# Specify output location
python scripts/json_to_csv.py output/insights_final.json --output my_insights.csv

# Include all metadata fields (wider CSV with more details)
python scripts/json_to_csv.py output/insights_final.json --all-fields
```

### Creating Executive Summary Views

For a boss-friendly overview with statistics and top insights:

```bash
python scripts/create_summary_view.py output/insights_final.json
```

This creates three files:
1. **executive_summary.txt** - High-level statistics (total insights, validation rate, top templates, top cohorts)
2. **top_insights.csv** - Top 50 highest-scoring insights
3. **quick_review.csv** - First 100 validated insights in readable format

---

## Running the Pipeline

### Command Line Interface

```bash
python src/generate_insights.py \
  --market singapore \
  --gen_model x-ai/grok-4.1-fast \
  --eval_model x-ai/grok-4.1-fast \
  --max_cohorts 5 \
  --insights_per_call 5 \
  --output_dir output \
  --rate_limit_delay 1.0
```

### Key Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--market` | Target market/region | singapore |
| `--gen_model` | LLM model for generation | x-ai/grok-4.1-fast |
| `--eval_model` | LLM model for evaluation | x-ai/grok-4.1-fast |
| `--gen_temperature` | LLM temperature for generation | 0.7 |
| `--gen_max_tokens` | Max tokens for generation | 2000 |
| `--max_cohorts` | Max cohorts to process | All |
| `--insights_per_call` | Insights per cohort-template combo | 2 |
| `--skip_validation` | Skip validation step | False |
| `--skip_evaluation` | Skip evaluation step | False |
| `--output_dir` | Output directory | output/ |
| `--rate_limit_delay` | Delay between API calls (sec) | 1.0 |

### Environment Variables

Required in `.env` file:
```bash
OPENROUTER_API_KEY=sk-or-v1-...
PUBMED_EMAIL=your@email.com
PUBMED_API_KEY=your_api_key
```

---

## Pipeline Statistics

Example output from a typical run:

```
================================================================================
PIPELINE COMPLETE
================================================================================
Duration: 12.34 minutes
Cohorts processed: 10
Total combinations: 150 (10 cohorts × 15 templates)
Insights generated: 750 (150 combinations × 5 insights/call)
Insights validated: 750 (87.2% pass rate)
Insights evaluated: 654
Average evaluation score: 8.2/10

All outputs saved to: output/
Summary saved to: output/pipeline_summary.json
================================================================================
```

---

## Technical Stack

- **Language:** Python 3.8+
- **LLM Provider:** OpenRouter (Grok 4.1 Fast)
- **Evidence Source:** PubMed E-utilities API
- **Configuration:** YAML
- **Data Format:** JSON
- **External APIs:**
  - OpenRouter for LLM inference
  - PubMed for scientific literature (optional)

---

## Key Features

### 1. Scalability
- Process hundreds of cohort-template combinations
- Batch generation with rate limiting
- Configurable parallelization

### 2. Quality Control
- Multi-layer validation (schema, sources, URLs)
- LLM-based evaluation for nuanced quality assessment
- Detailed failure tracking and diagnostics

### 3. Flexibility
- Market-specific configurations (currently Singapore, extensible)
- Multiple insight templates for diverse messaging
- Adjustable generation parameters (temperature, model, token limits)

### 4. Traceability
- Complete metadata tracking throughout pipeline
- Timestamped outputs at each step
- Detailed pipeline summaries with statistics

### 5. Cultural Sensitivity
- Singapore-specific health sources (HPB, HealthHub, MOH)
- Culturally-appropriate recommendations
- Ethnic-specific cohorts and insights

---

## Use Cases

### 1. Health Promotion Campaigns
Generate targeted messaging for specific population segments:
- Office wellness programs
- Senior health initiatives
- Women's health campaigns

### 2. Personalized Health Apps
Power recommendation engines with evidence-based insights:
- Mobile health applications
- Corporate wellness platforms
- Patient engagement tools

### 3. Content Marketing
Create engaging health content:
- Social media posts
- Email newsletters
- Health education materials

### 4. Research & Development
Explore health messaging effectiveness:
- A/B testing different insight templates
- Cohort-specific engagement analysis
- Template performance optimization

---

## Directory Structure

```
dyk/
├── src/
│   ├── core/
│   │   ├── cohort_generator.py      # Cohort generation logic
│   │   ├── insight_generator.py     # LLM-based insight generation
│   │   ├── validator.py             # Quality validation
│   │   └── evaluator.py             # LLM-based evaluation
│   ├── services/
│   │   └── pubmed_service.py        # PubMed evidence retrieval
│   ├── prompts/
│   │   └── prompt_templates.py      # LLM prompt engineering
│   ├── utils/
│   │   └── config_loader.py         # Configuration management
│   ├── config/
│   │   ├── singapore/
│   │   │   ├── cohort_definitions.yaml
│   │   │   ├── priority_cohorts.yaml
│   │   │   └── sources.yaml
│   │   ├── health_domains.yaml
│   │   └── insight_templates.yaml
│   └── generate_insights.py         # Main pipeline orchestrator
├── output/                           # Pipeline outputs
│   ├── cohorts.json
│   ├── insights_raw.json
│   ├── insights_post_validation.json
│   ├── insights_validated.json
│   ├── insights_final.json
│   └── pipeline_summary.json
├── notebooks/
│   └── cohort_generator.ipynb       # Development notebooks
├── .env                              # Environment variables
└── README.md                         # This file
```

---

## Performance Metrics

### Typical Performance
- **Generation Speed**: ~5-10 insights per minute (rate-limited)
- **Validation Pass Rate**: 85-90%
- **Average Evaluation Score**: 7.5-8.5/10
- **Processing Time**: 10-15 minutes for 500 insights

### Optimization Opportunities
- Batch LLM requests for faster generation
- Cache validated sources to reduce URL checks
- Parallel processing for independent cohorts
- Pre-computed evidence summaries

---

## Future Enhancements

### Planned Features
1. **Multi-market expansion**: Support for Australia, Malaysia, Indonesia
2. **Enhanced evidence integration**: Deeper PubMed integration with citation tracking
3. **A/B testing framework**: Compare insight template effectiveness
4. **Real-time personalization**: API endpoint for on-demand insight generation
5. **Feedback loop**: Incorporate user engagement data to refine generation
6. **Multi-language support**: Generate insights in Malay, Mandarin, Tamil
7. **Visual content generation**: Pair insights with infographics

---

## Contact & Support

For questions or issues:
- Review `pipeline_summary.json` for run statistics
- Check `insights_post_validation.json` for validation failures
- Examine console output for detailed error messages

---

## License & Credits

**Developed by:** Genie Health
**Market Focus:** Singapore
**LLM Provider:** OpenRouter (Grok 4.1)
**Evidence Source:** PubMed/NCBI
**Health Sources:** HPB, HealthHub, MOH

---

*Last Updated: November 2025*
