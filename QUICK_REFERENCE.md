# DYK Module - Quick Reference Card

**For:** Developers & Healthcare Application Integrators
**Last Updated:** November 2025

---

## 🚀 Quick Start (5 Minutes)

```bash
# 1. Install dependencies
pip install pyyaml requests python-dotenv

# 2. Set up .env file
echo "OPENROUTER_API_KEY=your_key" > .env

# 3. Run pipeline (generates 750 insights in ~10 minutes)
python src/generate_insights.py \
  --market singapore \
  --gen_model google/gemini-flash-2.5 \
  --max_cohorts 10 \
  --insights_per_call 5

# 4. View results
open output/insights_final.csv  # Mac
start output/insights_final.csv  # Windows
```

---

## 📝 Essential Commands

```bash
# Generate insights (full pipeline)
python src/generate_insights.py --market singapore --gen_model google/gemini-flash-2.5

# Quick test (3 cohorts, skip evaluation)
python src/generate_insights.py --max_cohorts 3 --skip_evaluation

# Convert JSON to CSV
python scripts/json_to_csv.py output/insights_final.json

# View statistics
python scripts/quick_stats.py output/insights_final.json

# Generate executive summary
python scripts/create_summary_view.py output/insights_final.json
```

---

## 🔧 Configuration Files (What to Edit)

| File | Purpose | When to Edit |
|------|---------|--------------|
| `src/config/singapore/priority_cohorts.yaml` | Define target populations | Add new cohorts, change priorities |
| `src/config/insight_templates.yaml` | Define messaging patterns | Add new templates, adjust weights |
| `src/config/singapore/sources.yaml` | Define evidence sources | Add new health authorities |
| `src/config/health_domains.yaml` | Define health categories | Add new health domains |

---

## 📊 Pipeline Flow (5 Steps)

```
1. Cohort Generation → cohorts.json
2. Insight Generation (LLM) → insights_raw.json
3. Validation (Rules) → insights_validated.json
4. Evaluation (LLM) → insights_final.json
5. Export (CSV) → insights_final.csv
```

---

## 🎯 Key Parameters

| Parameter | Default | Description | Example |
|-----------|---------|-------------|---------|
| `--market` | singapore | Target market | `--market singapore` |
| `--gen_model` | grok-4.1 | Generation LLM | `--gen_model google/gemini-flash-2.5` |
| `--eval_model` | grok-4.1 | Evaluation LLM | `--eval_model google/gemini-flash-2.5` |
| `--max_cohorts` | All | Limit cohorts | `--max_cohorts 5` |
| `--insights_per_call` | 2 | Insights per API call | `--insights_per_call 5` |
| `--gen_temperature` | 0.7 | LLM creativity | `--gen_temperature 0.8` |
| `--skip_validation` | False | Skip validation | `--skip_validation` |
| `--skip_evaluation` | False | Skip evaluation | `--skip_evaluation` |
| `--output_dir` | output | Output directory | `--output_dir results` |

---

## 📁 Output Files

| File | Format | Best For |
|------|--------|----------|
| `insights_final.csv` | CSV | Excel viewing, filtering, business users |
| `insights_final.json` | JSON | API integration, programmatic access |
| `executive_summary.txt` | Text | Management overview, quick stats |
| `top_insights.csv` | CSV | Top 50 highest-quality insights |
| `pipeline_summary.json` | JSON | Pipeline metrics, monitoring |

---

## 💾 Insight JSON Schema (Simplified)

```json
{
  "hook": "Did you know...",
  "explanation": "Why this matters...",
  "action": "What to do...",
  "source_name": "HPB",
  "source_url": "https://...",
  "numeric_claim": "30% reduction",

  "metadata": {
    "cohort": { "cohort_id": "cohort_0001", "description": "..." },
    "insight_template": { "type": "quantified_action_benefit" },
    "region": "singapore"
  },

  "validation": {
    "validated": true,
    "checks": { ... }
  },

  "evaluation": {
    "result": {
      "overall_score": 8.5,
      "factual_accuracy": 9,
      "safety": 10
    }
  }
}
```

---

## 🔄 Python API Integration

```python
from src.generate_insights import DYKPipeline

# Initialize
pipeline = DYKPipeline(
    market="singapore",
    generation_model="google/gemini-flash-2.5"
)

# Run pipeline
summary = pipeline.run(
    max_cohorts=10,
    insights_per_call=5
)

# Access results
print(f"Generated: {summary['statistics']['total_insights_generated']}")
print(f"Pass rate: {summary['statistics']['validation_pass_rate']}%")
```

---

## 🎨 Adding New Cohort (5 Steps)

1. Open `src/config/singapore/priority_cohorts.yaml`
2. Add new entry:
```yaml
- name: "my_new_cohort"
  dimensions:
    age_group: ["30-44"]
    health_conditions: ["diabetes"]
  priority: 1
  description: "Cohort description"
  rationale: "Why important (with stats)"
  insight_angles:
    - "Angle 1"
    - "Angle 2"
```
3. Save file
4. Run pipeline
5. Done! (No code changes needed)

---

## 🎯 Adding New Template (5 Steps)

1. Open `src/config/insight_templates.yaml`
2. Add new entry:
```yaml
my_new_template:
  type: "my_new_template"
  description: "What this does"
  weight: 8
  structure: |
    [Pattern description]
  example:
    - "Example insight"
  tone: "Desired tone"
```
3. Save file
4. Run pipeline
5. Done! (No code changes needed)

---

## 💰 Cost Estimates (Gemini Flash 2.5)

| Insights | Cost | Time |
|----------|------|------|
| 750 | $1.51 | 10-15 min |
| 1,500 | $3.02 | 20-30 min |
| 5,000 | $10.07 | 1-1.5 hrs |
| 10,000 | $20.14 | 2-3 hrs |

**Cost per insight:** $0.002 (0.2 cents)

---

## 🔍 Validation Checks (3 Layers)

1. **JSON Validity**: Can it be serialized?
2. **Schema Conformity**:
   - Required fields present?
   - Correct types?
   - Length constraints met? (hook ≤20 words, explanation 30-60 words, action ≤30 words)
3. **Source Verification**:
   - Valid URL format?
   - URL accessible?
   - Credible source?

---

## 📊 Evaluation Criteria (6 Dimensions, 0-10 scale)

1. **Factual Accuracy**: Scientifically sound?
2. **Safety**: Safe for target cohort?
3. **Relevance**: Applicable to cohort's needs?
4. **Actionability**: Clear and practical action?
5. **Cultural Appropriateness**: Fits regional context?
6. **Evidence Faithfulness**: Aligns with sources?

---

## 🚨 Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| Rate limit errors | Add `--rate_limit_delay 2.0` |
| JSON parse errors | Increase `--gen_max_tokens 2500` |
| Low validation rate | Check `insights_post_validation.json` for issues |
| Empty CSV | Check if validation passed (`insights_validated.json`) |
| API errors | Verify `.env` file has correct API key |

---

## 🌍 Supported Models

| Provider | Model | Recommended For |
|----------|-------|-----------------|
| Google AI | `google/gemini-flash-2.5` | ✅ Production (best cost/quality) |
| Google AI | `google/gemini-flash-1.5-8b` | Fast prototyping |
| OpenRouter | `x-ai/grok-4.1-fast` | Free testing (rate limited) |
| OpenRouter | `anthropic/claude-3.5-sonnet` | Highest quality (expensive) |

---

## 📈 Typical Pipeline Statistics

```
Duration: 12 minutes
Cohorts processed: 10
Insights generated: 750
Validation pass rate: 87.2%
Average evaluation score: 8.2/10
```

---

## 🔗 Important Files

| Purpose | File |
|---------|------|
| Main documentation | `README.md` |
| Technical details | `TECHNICAL_DOCUMENTATION.md` |
| Viewing results | `VIEWING_RESULTS.md` |
| This reference | `QUICK_REFERENCE.md` |

---

## 📞 Need Help?

1. Check `TECHNICAL_DOCUMENTATION.md` for detailed explanations
2. Check `VIEWING_RESULTS.md` for output viewing guide
3. Review `pipeline_summary.json` for run statistics
4. Check `insights_post_validation.json` for validation failures

---

## 🎯 Quick Tips

- **Start small**: Use `--max_cohorts 3` for testing
- **Batch insights**: Use `--insights_per_call 5` to reduce API calls by 80%
- **Skip evaluation**: Use `--skip_evaluation` for faster prototyping
- **Use Gemini**: Much cheaper and more reliable than free tiers
- **Check CSV**: Always review `insights_final.csv` in Excel first
- **Monitor costs**: ~$0.002 per insight with Gemini Flash 2.5

---

**Pro Tip:** The entire system is config-driven. You can change cohorts, templates, and sources without touching any code!

**Remember:** 10 cohorts × 15 templates × 5 insights = 750 insights for ~$1.51 (with Gemini)
