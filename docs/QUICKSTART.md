# Quick Start Guide

Get started with the DYK Insight Generator in 10 minutes.

## Prerequisites

- Python 3.8+
- OpenRouter API key ([Get one here](https://openrouter.ai/))
- Optional: PubMed API key for higher rate limits

## Setup (5 minutes)

### 1. Install Dependencies

```bash
pip install pyyaml requests pandas
```

### 2. Set API Key

```bash
# Option A: Environment variable
export OPENROUTER_API_KEY="your-key-here"

# Option B: Create .env file
echo "OPENROUTER_API_KEY=your-key-here" > .env

# Optional: Set PubMed email
export PUBMED_EMAIL="your-email@example.com"
```

### 3. Verify Setup

```bash
python -c "import os; print('✓ API key set' if os.getenv('OPENROUTER_API_KEY') else '✗ API key missing')"
```

## Quick Test (2 minutes)

### Generate First Insight

```python
# test.py
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

# Generate insight
insight = generator.generate_pure_llm(cohort)

print("Hook:", insight['hook'])
print("Explanation:", insight['explanation'])
print("Action:", insight['action'])
```

Run it:
```bash
python test.py
```

Expected output:
```
Hook: Did you know that male smokers in their 40s have 3x higher risk of lung cancer?
Explanation: Research shows that smoking significantly increases lung cancer risk...
Action: Speak to your healthcare provider about smoking cessation programs.
```

## Common Tasks

### Task 1: Generate 10 insights (Pure LLM)

```bash
python pipeline.py \
  --method pure_llm \
  --max-cohorts 5 \
  --insights-per-cohort 2 \
  --output-dir test_run
```

**Result**: `test_run/insights_final_*.json` with ~10 insights

### Task 2: Generate with evidence from PubMed

```bash
python pipeline.py \
  --method evidence_based \
  --max-cohorts 3 \
  --insights-per-cohort 2 \
  --output-dir evidence_run
```

**Result**: Insights with PubMed citations

### Task 3: View specific cohorts

```python
from cohort_generator import CohortGenerator

gen = CohortGenerator()
cohorts = gen.generate_priority_cohorts()

# Show top 5
for c in cohorts[:5]:
    print(f"{c['cohort_id']}: {c['description']}")
```

### Task 4: Validate existing insights

```python
from validator import InsightValidator
import json

validator = InsightValidator()

with open('insights.json') as f:
    insights = json.load(f)['insights']

results = validator.validate_batch(insights)
print(f"Valid: {results['valid_insights']}/{results['total_insights']}")
```

## Useful Commands

### Generate different insight types

```bash
# Risk amplification (default)
python insight_generator.py --template risk_amplification

# Protective factors
python insight_generator.py --template protective_factors

# Behavior change
python insight_generator.py --template behavior_change

# Early detection
python insight_generator.py --template early_detection
```

### View pipeline outputs

```bash
# List generated files
ls -lh output/

# View insights in JSON
cat output/insights_final_*.json | jq '.insights[0]'

# Open CSV in Excel/Google Sheets
open output/insights_final_*.csv
```

### Check cohort statistics

```python
from cohort_generator import CohortGenerator

gen = CohortGenerator()
stats = gen.get_cohort_statistics()

print(f"Total cohorts: {stats['total_cohorts']}")
print(f"Min insights needed: {stats['min_insights_required']}")
```

## Troubleshooting

### Error: "OpenRouter API key required"

**Solution:**
```bash
export OPENROUTER_API_KEY="your-key"
```

### Error: "Rate limit exceeded"

**Solution:** Add delay between requests
```bash
python pipeline.py --rate-limit-delay 2.0
```

### Error: "No evidence found"

**Solution:** Check internet connection or use pure LLM
```bash
python pipeline.py --method pure_llm
```

### Low validation scores

**Solution:** Adjust minimum quality threshold
```bash
python pipeline.py --min-quality 60
```

## Next Steps

1. ✅ Generate test insights
2. ✅ Review output quality
3. ✅ Adjust `config.yaml` for your cohorts
4. ✅ Run full pipeline
5. ✅ Integrate into your application

## Configuration Tips

### Add custom cohorts

Edit `config.yaml`:
```yaml
priority_cohorts:
  - dimensions:
      age_group: ["25-34"]  # Your cohort
      gender: ["female"]
      chronic_conditions: ["anxiety"]
    min_insights: 5
```

### Change region

```yaml
regions:
  australia:  # Add new region
    name: "Australia"
    authoritative_sources:
      - name: "AIHW"
        url: "https://www.aihw.gov.au"
```

### Adjust validation rules

Edit `validator.py`:
```python
# Change minimum quality score
if results['overall_score'] < 70:  # Was 60
    results['overall_valid'] = False
```

## Example Workflows

### Workflow 1: Quick Prototype (1 hour)

```bash
# 1. Generate 20 insights
python pipeline.py --method pure_llm --max-cohorts 10 --insights-per-cohort 2

# 2. Review CSV
open output/insights_final_*.csv

# 3. Iterate on prompts if needed
# Edit prompt_templates.py, then re-run
```

### Workflow 2: Production Dataset (1 day)

```bash
# 1. Generate priority cohorts
python cohort_generator.py

# 2. Generate with evidence
python pipeline.py \
  --method evidence_based \
  --max-cohorts 100 \
  --insights-per-cohort 5 \
  --min-quality 75

# 3. Manual review of borderline insights
# Review validation_*.json for issues

# 4. Regenerate failed insights
python regenerate.py --from validation_*.json --score-below 70
```

### Workflow 3: Multi-Region Deployment

```bash
# Singapore
python pipeline.py --region singapore --output-dir output/singapore

# Global
python pipeline.py --region global --output-dir output/global

# Australia (after adding to config)
python pipeline.py --region australia --output-dir output/australia
```

## Getting Help

### Check logs
```bash
# Enable verbose output
python pipeline.py --verbose

# Save logs
python pipeline.py 2>&1 | tee pipeline.log
```

### Run examples
```bash
# Interactive examples
python examples.py

# Specific example
python examples.py 1  # Quick test
python examples.py 4  # Validation demo
```

### Common Questions

**Q: How many insights should I generate?**
A: Start with 50-100 for MVP, scale to 500-1000 for production.

**Q: Which method should I use?**
A: Pure LLM for MVP/testing, Evidence-Based for production.

**Q: How do I ensure quality?**
A: Enable validation, set min-quality to 70+, review outputs.

**Q: Can I customize prompts?**
A: Yes! Edit `prompt_templates.py` and regenerate.

**Q: How do I add my own sources?**
A: Edit `config.yaml` under `authoritative_sources`.

## Quick Reference Card

```bash
# Generate insights
python pipeline.py [OPTIONS]

OPTIONS:
  --method {pure_llm|evidence_based}    Generation method
  --max-cohorts INT                      Max cohorts to process
  --insights-per-cohort INT             Insights per cohort
  --region STR                          Target region
  --min-quality FLOAT                   Min quality score
  --output-dir PATH                     Output directory
  --no-validate                         Skip validation
  --openrouter-key KEY                  OpenRouter API key
  --pubmed-email EMAIL                  PubMed email

# Examples
python examples.py                      # Interactive examples
python cohort_generator.py             # Generate cohorts
python -m pytest tests/                # Run tests (if available)
```

---

**You're ready to go!** Start with a quick test, then scale up to your needs.

For detailed documentation, see [README.md](README.md)

For method comparison, see [COMPARISON.md](COMPARISON.md)
