# Viewing DYK Insights - Quick Guide

This guide shows you how to view and analyze generated insights in various formats.

## Quick Summary

**For your boss to quickly view insights:**
1. Open `output/insights_final.csv` in Excel or Google Sheets
2. Or run: `python scripts/create_summary_view.py output/insights_final.json`

---

## 📊 Output Files Overview

After running the pipeline, you'll find these files in the `output/` directory:

### Primary Output Files

| File | Format | Best For | Who Should Use |
|------|--------|----------|----------------|
| `insights_final.csv` | CSV | **Quick browsing in Excel/Sheets** | ✅ Executives, managers, non-technical users |
| `insights_final.json` | JSON | Programmatic access | Developers, data engineers |
| `top_insights.csv` | CSV | **Reviewing best insights** | ✅ Executives, content teams |
| `quick_review.csv` | CSV | **Reading full insights** | ✅ Content reviewers, editors |
| `executive_summary.txt` | Text | **High-level overview** | ✅ Executives, stakeholders |

### Supporting Files

| File | Purpose |
|------|---------|
| `cohorts.json` | All generated cohorts |
| `insights_raw.json` | Raw LLM output (before validation) |
| `insights_post_validation.json` | All insights with validation results |
| `insights_validated.json` | Only validated insights |
| `pipeline_summary.json` | Pipeline statistics and metrics |

---

## 📋 Method 1: CSV in Excel/Google Sheets (Recommended for Quick View)

### Step 1: Automatic CSV Export

The pipeline automatically creates `insights_final.csv` when it runs. Just open it:

```bash
# Windows
start output/insights_final.csv

# Mac
open output/insights_final.csv

# Linux
xdg-open output/insights_final.csv
```

### Step 2: What You'll See

The CSV contains these columns:

| Column | What It Shows | Example |
|--------|---------------|---------|
| **Insight ID** | Unique identifier | INS_0042 |
| **Hook** | Attention-grabbing opener | "Did you know walking 7,000 steps daily reduces mortality by 50%?" |
| **Explanation** | Why it matters | "For sedentary office workers aged 30-59..." |
| **Action** | What to do | "Track steps daily, aim for 7,000-8,000" |
| **Numeric Claim** | Key statistic | "reduces mortality by 50%" |
| **Source Name** | Authority | "Health Promotion Board (HPB)" |
| **Source URL** | Link | https://www.hpb.gov.sg/... |
| **Cohort Description** | Target audience | "Sedentary office workers aged 30-59" |
| **Template Type** | Insight style | "quantified_action_benefit" |
| **Validated** | Quality check | Yes/No |
| **Evaluation Score** | Quality rating | 8.5/10 |

### Tips for Excel/Sheets:
- **Filter by score**: Show only high-quality insights (Score ≥ 8.0)
- **Filter by cohort**: Show insights for specific audiences
- **Filter by template**: See all "risk_reversal" insights
- **Sort by score**: See best insights first
- **Hide columns**: Remove technical columns you don't need

---

## 📈 Method 2: Executive Summary (Best for Bosses)

### Generate Summary Views

```bash
python scripts/create_summary_view.py output/insights_final.json
```

This creates **3 boss-friendly files**:

### 1. `executive_summary.txt` - Overview Statistics

```
================================================================================
DYK INSIGHTS - EXECUTIVE SUMMARY
================================================================================

Total Insights Generated: 750
Validated Insights: 654 (87.2%)
Average Quality Score: 8.2/10

--------------------------------------------------------------------------------
TOP 5 INSIGHT TEMPLATES
--------------------------------------------------------------------------------
  quantified_action_benefit               150 (20.0%)
  risk_reversal                           120 (16.0%)
  mechanism_reveal                        100 (13.3%)
  ...

--------------------------------------------------------------------------------
TOP 5 COHORTS
--------------------------------------------------------------------------------
  cohort_0001 - Sedentary office workers aged 30-59, obese
    Insights: 85 (11.3%)

  cohort_0002 - Perimenopausal women (45-59)
    Insights: 72 (9.6%)
  ...
```

### 2. `top_insights.csv` - Top 50 Best Insights

Opens in Excel/Sheets with columns:
- Rank (1-50)
- Quality Score
- Hook
- Explanation
- Action
- Target Audience
- Template Type

**Perfect for**: Sharing best insights with stakeholders

### 3. `quick_review.csv` - First 100 Insights (Full Text)

Full insights in readable format with:
- Insight ID
- Complete text (hook + explanation + action)
- Target audience
- Quality score

**Perfect for**: Quick content review sessions

---

## 📊 Method 3: Terminal Stats (Fastest)

For a quick overview without opening files:

```bash
python scripts/quick_stats.py output/insights_final.json
```

**Output:**
```
================================================================================
DYK INSIGHTS - QUICK STATS
================================================================================

File: output/insights_final.json

---------------------------------- OVERVIEW ------------------------------------
  Total Insights:          750
  ✓ Validated:             654 ( 87.2%)
  ✗ Failed Validation:      96 ( 12.8%)

------------------------------- QUALITY SCORES ---------------------------------
  Average Score:          8.23/10
  High Quality (≥8.0):     485 ( 74.2%)
  Scored Insights:         654

------------------------------- TOP 5 TEMPLATES --------------------------------
  1. quantified_action_benefit      150 ( 20.0%) ██████████
  2. risk_reversal                  120 ( 16.0%) ████████
  3. mechanism_reveal               100 ( 13.3%) ██████
  ...
```

---

## 🔄 Method 4: Convert Existing JSON to CSV

If you have an old JSON file and need CSV:

```bash
# Basic conversion
python scripts/json_to_csv.py output/insights_final.json

# Custom output location
python scripts/json_to_csv.py output/insights_final.json --output my_insights.csv

# Include ALL metadata (very detailed, wider CSV)
python scripts/json_to_csv.py output/insights_final.json --all-fields
```

---

## 💡 Common Workflows

### For Executives/Management

1. **Quick high-level view:**
   ```bash
   python scripts/create_summary_view.py output/insights_final.json
   ```
   → Open `executive_summary.txt`

2. **Review best insights:**
   → Open `top_insights.csv` in Excel
   → Sort by Score (highest first)

### For Content Teams

1. **Review all validated insights:**
   → Open `insights_final.csv` in Excel
   → Filter: Validated = "Yes"
   → Sort by Evaluation Score

2. **Find insights for specific audience:**
   → Open `insights_final.csv`
   → Filter by Cohort Description (e.g., "office workers")

3. **Review specific template types:**
   → Open `insights_final.csv`
   → Filter by Template Type (e.g., "risk_reversal")

### For Data Analysis

1. **Export with all metadata:**
   ```bash
   python scripts/json_to_csv.py output/insights_final.json --all-fields
   ```

2. **Analyze in Python:**
   ```python
   import pandas as pd
   df = pd.read_csv('output/insights_final.csv')

   # Filter high-quality insights
   top_insights = df[df['Evaluation Score'] >= 8.0]

   # Group by template type
   by_template = df.groupby('Template Type').size()
   ```

---

## 📁 Recommended File Structure

```
output/
├── insights_final.csv              ← Open this in Excel for quick view
├── insights_final.json             ← For developers
├── executive_summary.txt           ← For management overview
├── top_insights.csv                ← Top 50 best insights
├── quick_review.csv                ← First 100 for quick reading
├── pipeline_summary.json           ← Pipeline statistics
├── cohorts.json                    ← Cohort definitions
└── insights_post_validation.json   ← Full validation details
```

---

## 🎯 Quick Reference Commands

```bash
# Generate executive summary views
python scripts/create_summary_view.py output/insights_final.json

# Convert JSON to CSV
python scripts/json_to_csv.py output/insights_final.json

# View quick stats in terminal
python scripts/quick_stats.py output/insights_final.json

# Open CSV in default app
start output/insights_final.csv        # Windows
open output/insights_final.csv         # Mac
xdg-open output/insights_final.csv     # Linux
```

---

## 💼 What Format to Share with Your Boss?

| Scenario | Best Format | File |
|----------|-------------|------|
| "Give me the top insights" | CSV in Excel | `top_insights.csv` |
| "How did the pipeline perform?" | Text summary | `executive_summary.txt` |
| "I want to browse all insights" | CSV in Excel | `insights_final.csv` (filtered) |
| "Show me quick stats" | Terminal output | Run `quick_stats.py` |
| "I need insights for office workers" | CSV (filtered) | `insights_final.csv` + filter |
| "What are our best templates?" | Text summary | `executive_summary.txt` |

---

## 🔍 Filtering in Excel/Google Sheets

### Filter by Quality (High-Quality Only)
1. Open `insights_final.csv`
2. Click column header "Evaluation Score"
3. Filter: `>= 8.0`

### Filter by Audience
1. Click "Cohort Description" header
2. Filter by text (e.g., contains "office" or "senior")

### Filter by Template
1. Click "Template Type" header
2. Select specific templates (e.g., "risk_reversal", "quantified_action_benefit")

### Filter by Validation Status
1. Click "Validated" header
2. Filter: "Yes" only

---

## 🚀 Pro Tips

1. **Always start with `executive_summary.txt`** for high-level overview
2. **Use `top_insights.csv`** to quickly share best insights with stakeholders
3. **Keep `insights_final.csv` open** while reviewing - it has everything
4. **Filter by score ≥ 8.0** to see only high-quality insights
5. **Use `quick_stats.py`** for fast terminal overview without opening files
6. **Share `quick_review.csv`** with content reviewers for easy reading

---

## ❓ FAQ

**Q: Which file should I open first?**
A: `executive_summary.txt` for overview, then `top_insights.csv` for best insights.

**Q: Can I sort/filter in Excel?**
A: Yes! The CSV files are fully compatible with Excel filters and sorting.

**Q: How do I see only high-quality insights?**
A: Open `insights_final.csv`, filter "Evaluation Score" ≥ 8.0.

**Q: What if I don't have Python installed?**
A: Just open `insights_final.csv` directly - it's created automatically by the pipeline.

**Q: Can I share the CSV with non-technical people?**
A: Absolutely! CSVs open in Excel/Google Sheets and are easy to read.

**Q: How do I get insights for a specific audience?**
A: Open `insights_final.csv`, filter by "Cohort Description".

---

*Need help? Check the main [README.md](README.md) for more details.*
