# DYK (Did You Know) Insight Generation System

A scalable, evidence-based system for generating personalized health insights for different user cohorts.

## Overview

This system generates "Did You Know" health insights tailored to specific user demographics and health profiles. It supports two generation modes:

1. **Pure LLM**: Uses LLM's pre-trained knowledge to generate insights
2. **Evidence-Based**: Retrieves scientific evidence from PubMed before generating insights

## Features

- ✅ Priority-based cohort generation (avoids combinatorial explosion)
- ✅ Multiple generation strategies (pure LLM vs. evidence-based)
- ✅ Comprehensive validation layer
- ✅ Duplicate detection
- ✅ Quality scoring
- ✅ Batch processing with rate limiting
- ✅ Structured output (JSON, CSV)

## Architecture

```
1. Cohort Generation → Generates priority cohorts based on config
2. Insight Generation → Creates insights using LLM (with/without evidence)
3. Validation → Checks schema, sources, numeric plausibility, quality
4. Deduplication → Removes similar insights
5. Quality Scoring → Rates engagement potential
6. Filtering → Keeps only high-quality, valid insights
7. Export → Saves to JSON/CSV
```

## Installation

### Prerequisites

- Python 3.8+
- OpenRouter API key (for LLM access)
- Optional: PubMed API key (for higher rate limits)

### Setup

```bash
# Clone or download the files
cd dyk-insight-generator

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
export OPENROUTER_API_KEY="your-openrouter-key"
export PUBMED_EMAIL="your-email@example.com"  # For PubMed API

# Or create a .env file
echo "OPENROUTER_API_KEY=your-key" > .env
echo "PUBMED_EMAIL=your-email@example.com" >> .env
```

### Getting API Keys

1. **OpenRouter**: Sign up at https://openrouter.ai/
   - Provides access to multiple LLM models including Claude
   - Pay-as-you-go pricing

2. **PubMed API Key** (optional): Request at https://www.ncbi.nlm.nih.gov/account/
   - Increases rate limit from 3 to 10 requests/second
   - Free for researchers

## Quick Start

### 1. Generate Cohorts

```bash
python cohort_generator.py
```

This creates `cohorts.json` with priority-based cohort combinations.

### 2. Generate Insights (Pure LLM)

```bash
python pipeline.py \
  --method pure_llm \
  --max-cohorts 10 \
  --insights-per-cohort 3 \
  --region singapore
```

### 3. Generate Insights (Evidence-Based)

```bash
python pipeline.py \
  --method evidence_based \
  --max-cohorts 5 \
  --insights-per-cohort 2 \
  --region singapore
```

### 4. Test Individual Components

```python
# Test insight generation
from insight_generator import InsightGenerator

generator = InsightGenerator()

cohort = {
    'cohort_id': 'test_001',
    'cohort_params': {
        'age_group': '40-49',
        'gender': 'male',
        'smoking_status': 'smoker'
    },
    'description': '40-49 years old, male, smoker'
}

# Pure LLM
insight = generator.generate_pure_llm(cohort)
print(insight)

# Evidence-based
insight = generator.generate_evidence_based(cohort)
print(insight)
```

## Configuration

### Cohort Configuration (`config.yaml`)

Define your cohorts, regions, and sources:

```yaml
cohort_definitions:
  age_groups:
    - name: "30-39"
      priority: 1  # Higher priority = generated first
  
  genders:
    - name: "male"
      priority: 1

priority_cohorts:
  - dimensions:
      age_group: ["30-39", "40-49"]
      gender: ["male", "female"]
      smoking_status: ["smoker"]
    min_insights: 5
```

### Priority Cohorts

The system uses a **priority-based approach** to avoid generating millions of cohort combinations:

1. Define high-priority cohort combinations in `priority_cohorts`
2. System generates only these specific combinations
3. Calculates priority score based on individual dimension priorities
4. Processes higher-priority cohorts first

**Example**: Instead of generating insights for all possible combinations (age × gender × smoking × BMI × activity = 6×2×3×4×3 = 432 cohorts), you specify:
- Age 40-49, Male, Smoker (high risk) → 5 insights
- Age 50-59, Female, Diabetes (high risk) → 5 insights
- Age 30-39, Any gender (baseline) → 3 insights

Result: ~50 cohorts instead of 432.

## Usage Examples

### Example 1: Quick Test (5 cohorts, pure LLM)

```bash
python pipeline.py \
  --method pure_llm \
  --max-cohorts 5 \
  --insights-per-cohort 2 \
  --output-dir test_output
```

### Example 2: Full Singapore MVP (50 cohorts, evidence-based)

```bash
python pipeline.py \
  --method evidence_based \
  --max-cohorts 50 \
  --insights-per-cohort 3 \
  --region singapore \
  --min-quality 70 \
  --output-dir singapore_mvp
```

### Example 3: Custom Cohort Generation

```python
from cohort_generator import CohortGenerator

generator = CohortGenerator()

# Get priority cohorts
cohorts = generator.generate_priority_cohorts()

# Get statistics
stats = generator.get_cohort_statistics()
print(f"Total cohorts: {stats['total_cohorts']}")
print(f"By priority: {stats['by_priority']}")
```

### Example 4: Validate Existing Insights

```python
from validator import InsightValidator
import json

validator = InsightValidator()

# Load insights
with open('insights.json') as f:
    insights = json.load(f)['insights']

# Validate
results = validator.validate_batch(insights)
print(f"Valid: {results['valid_insights']}/{results['total_insights']}")
print(f"Average score: {results['average_score']}")

# Check duplicates
duplicates = validator.check_duplicates(insights)
print(f"Duplicate pairs: {len(duplicates)}")
```

## Output Structure

### Final Insights JSON

```json
{
  "generated_at": "2024-11-24 10:30:00",
  "total_insights": 150,
  "insights": [
    {
      "cohort_id": "cohort_0001",
      "cohort_params": {
        "age_group": "40-49",
        "gender": "male",
        "smoking_status": "smoker"
      },
      "hook": "Did you know that male smokers in their 40s have 3x higher risk of lung cancer?",
      "explanation": "Research shows smoking significantly increases lung cancer risk...",
      "action": "Speak to your healthcare provider about smoking cessation programs.",
      "source_name": "CDC",
      "source_url": "https://www.cdc.gov/...",
      "health_domain": "respiratory",
      "quality_score": 85.5,
      "validation": {
        "overall_score": 92,
        "overall_valid": true
      },
      "generation_method": "evidence_based",
      "template_type": "risk_amplification"
    }
  ]
}
```

### CSV Export

Includes: cohort_id, description, hook, explanation, action, source, quality_score, validation_score

## Comparison: Pure LLM vs Evidence-Based

| Aspect | Pure LLM | Evidence-Based |
|--------|----------|----------------|
| Speed | Fast (~1-2s per insight) | Slower (~5-10s per insight) |
| Cost | Lower | Higher (PubMed + LLM calls) |
| Accuracy | Good (based on training data) | Excellent (grounded in recent research) |
| Recency | Limited to training cutoff | Up-to-date research |
| Citations | Generic or inferred | Specific PubMed citations |
| Hallucination Risk | Moderate | Low |
| Best For | Rapid prototyping, general insights | Production, high-stakes medical content |

**Recommendation**: 
- Start with **pure LLM** for rapid iteration and testing
- Switch to **evidence-based** for production deployment
- Use **pure LLM** for general wellness, **evidence-based** for medical claims

## Validation Criteria

Insights are validated on:

1. **Schema Conformity** (25 pts)
   - Required fields present
   - Correct field types
   - Appropriate lengths

2. **Source Verification** (25 pts)
   - Valid URL format
   - Whitelisted domain
   - Source credibility

3. **Numeric Plausibility** (25 pts)
   - Percentages ≤ 100%
   - Risk multipliers reasonable
   - Ratios valid

4. **Content Quality** (25 pts)
   - Starts with "Did you know"
   - Actionable verbs present
   - Cohort-specific
   - No fear-mongering
   - No medical diagnosis claims

**Minimum passing score**: 60/100

## Scaling Considerations

### For 1000+ Insights

1. **Batch Processing**: Use `max_cohorts` to process in chunks
2. **Rate Limiting**: Adjust `rate_limit_delay` in pipeline
3. **Parallel Processing**: Run multiple instances with different cohort ranges
4. **Caching**: Cache PubMed results for similar queries

### Example: Generate 1000 Insights

```bash
# Process in batches of 100 cohorts
for i in {0..9}; do
  python pipeline.py \
    --method evidence_based \
    --max-cohorts 100 \
    --insights-per-cohort 3 \
    --output-dir batch_$i \
    --skip-cohorts $((i * 100))
done

# Merge results
python merge_batches.py --input batch_* --output final_insights.json
```

## Cost Estimation

### Pure LLM Mode
- Claude 3.5 Sonnet via OpenRouter: ~$3 per million tokens
- Average insight: ~2,000 tokens (input + output)
- **Cost**: ~$0.006 per insight
- **1000 insights**: ~$6

### Evidence-Based Mode
- PubMed API: Free
- LLM calls: ~5,000 tokens per insight (evidence + generation)
- **Cost**: ~$0.015 per insight
- **1000 insights**: ~$15

## Troubleshooting

### "OpenRouter API key required"
```bash
export OPENROUTER_API_KEY="your-key"
# Or pass directly: --openrouter-key "your-key"
```

### "Rate limit exceeded"
- Increase `rate_limit_delay` in pipeline
- Use PubMed API key for higher limits
- Process fewer cohorts at once

### "No evidence found"
- Check internet connection
- Verify cohort parameters are specific enough
- System will fallback to pure LLM

### Low validation scores
- Adjust `min_quality_score` parameter
- Review validation criteria in `validator.py`
- Check if sources are whitelisted

## File Structure

```
dyk-insight-generator/
├── config.yaml                 # Main configuration
├── cohort_generator.py         # Cohort generation logic
├── prompt_templates.py         # LLM prompt templates
├── pubmed_integration.py       # PubMed API client
├── insight_generator.py        # Core generation logic
├── validator.py                # Validation and quality scoring
├── pipeline.py                 # Main orchestrator
├── requirements.txt            # Python dependencies
├── README.md                   # This file
└── output/                     # Generated insights
    ├── cohorts_*.json
    ├── insights_raw_*.json
    ├── insights_final_*.json
    ├── insights_final_*.csv
    ├── validation_*.json
    └── summary_*.json
```

## Next Steps

1. **Test the system**: Run with `--max-cohorts 5` to verify setup
2. **Review outputs**: Check `output/insights_final_*.csv` for quality
3. **Tune configuration**: Adjust cohorts and priorities in `config.yaml`
4. **Scale up**: Gradually increase cohorts for production
5. **Integrate**: Connect to your application via JSON API or database

## API Integration (Future)

The system is designed to be integrated into applications:

```python
# Example: Get insights for specific user
from insight_generator import InsightGenerator

def get_insights_for_user(user_profile):
    generator = InsightGenerator()
    
    cohort = {
        'cohort_params': {
            'age_group': user_profile.age_group,
            'gender': user_profile.gender,
            'smoking_status': user_profile.smoking_status
        },
        'description': f"{user_profile.age_group}, {user_profile.gender}"
    }
    
    return generator.generate_evidence_based(cohort)
```

## Support & Feedback

For questions or issues, please refer to the documentation or contact the development team.

## License

[Your License Here]
