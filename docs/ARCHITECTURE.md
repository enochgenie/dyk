# System Architecture Diagram

## Overall Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DYK INSIGHT GENERATION SYSTEM                    │
└─────────────────────────────────────────────────────────────────────────┘

INPUT                           PROCESSING                          OUTPUT
━━━━━                           ━━━━━━━━━━                          ━━━━━━

┌──────────┐
│ config.  │
│  yaml    │──────┐
└──────────┘      │
                  │
                  ▼
          ┌───────────────┐
          │   COHORT      │
          │  GENERATOR    │
          └───────┬───────┘
                  │
                  │ cohorts.json
                  │
                  ▼
          ┌───────────────┐         ┌─────────────┐
          │               │◄────────│  PubMed API │
          │   INSIGHT     │         │  (optional) │
          │  GENERATOR    │         └─────────────┘
          │               │
          │ • Pure LLM    │         ┌─────────────┐
          │ • Evidence-   │◄────────│ OpenRouter  │
          │   Based       │         │  LLM API    │
          └───────┬───────┘         └─────────────┘
                  │
                  │ raw_insights.json
                  │
                  ▼
          ┌───────────────┐
          │               │
          │  VALIDATOR    │
          │               │
          │ • Schema      │
          │ • Sources     │
          │ • Numeric     │
          │ • Quality     │
          └───────┬───────┘
                  │
                  │ + validation_results
                  │
                  ▼
          ┌───────────────┐
          │  DEDUPLICATOR │
          └───────┬───────┘
                  │
                  │
                  ▼
          ┌───────────────┐
          │  QUALITY      │
          │  SCORER       │
          └───────┬───────┘
                  │
                  │
                  ▼
          ┌───────────────┐
          │   FILTER      │
          │  (min score)  │
          └───────┬───────┘
                  │
                  ├──────────────────┐
                  │                  │
                  ▼                  ▼
          ┌───────────┐      ┌──────────┐
          │  JSON     │      │   CSV    │
          │  Export   │      │  Export  │
          └───────────┘      └──────────┘
```

## Component Details

### 1. Cohort Generator
```
┌─────────────────────────────────────────────┐
│        COHORT GENERATOR                     │
├─────────────────────────────────────────────┤
│                                             │
│  Input:  config.yaml                        │
│          • Age groups                       │
│          • Genders                          │
│          • Lifestyle factors                │
│          • Health conditions                │
│          • Priority rules                   │
│                                             │
│  Process:                                   │
│  1. Parse configuration                     │
│  2. Generate priority combinations          │
│  3. Calculate priority scores               │
│  4. Sort by priority                        │
│                                             │
│  Output: cohorts.json                       │
│          • cohort_id                        │
│          • cohort_params                    │
│          • description                      │
│          • priority_level                   │
│          • min_insights                     │
│                                             │
└─────────────────────────────────────────────┘
```

### 2. Insight Generator (Dual Mode)

#### Mode A: Pure LLM
```
┌─────────────────────────────────────────────┐
│        PURE LLM GENERATION                  │
├─────────────────────────────────────────────┤
│                                             │
│  Input:  Cohort specification               │
│                                             │
│  ┌─────────────────────────────────┐       │
│  │  1. Load prompt template        │       │
│  │     • Risk amplification        │       │
│  │     • Protective factors        │       │
│  │     • Behavior change           │       │
│  │     • Early detection           │       │
│  │     • Comparative               │       │
│  └──────────────┬──────────────────┘       │
│                 │                           │
│                 ▼                           │
│  ┌─────────────────────────────────┐       │
│  │  2. Inject cohort params        │       │
│  │     • Age, gender, conditions   │       │
│  │     • Region-specific context   │       │
│  └──────────────┬──────────────────┘       │
│                 │                           │
│                 ▼                           │
│  ┌─────────────────────────────────┐       │
│  │  3. Call OpenRouter LLM         │       │
│  │     Model: Claude 3.5 Sonnet    │       │
│  │     Temp: 0.7                   │       │
│  └──────────────┬──────────────────┘       │
│                 │                           │
│                 ▼                           │
│  ┌─────────────────────────────────┐       │
│  │  4. Parse JSON response         │       │
│  │     • hook                      │       │
│  │     • explanation               │       │
│  │     • action                    │       │
│  │     • source (inferred)         │       │
│  └──────────────┬──────────────────┘       │
│                 │                           │
│                 ▼                           │
│            Insight JSON                     │
│                                             │
└─────────────────────────────────────────────┘

Speed: ⭐⭐⭐⭐⭐  Cost: ⭐⭐⭐⭐⭐  Quality: ⭐⭐⭐
```

#### Mode B: Evidence-Based
```
┌─────────────────────────────────────────────┐
│      EVIDENCE-BASED GENERATION              │
├─────────────────────────────────────────────┤
│                                             │
│  Input:  Cohort specification               │
│                                             │
│  ┌─────────────────────────────────┐       │
│  │  1. Generate PubMed queries     │       │
│  │     • Demographic terms         │       │
│  │     • Health domain             │       │
│  │     • Risk factors              │       │
│  └──────────────┬──────────────────┘       │
│                 │                           │
│                 ▼                           │
│  ┌─────────────────────────────────┐       │
│  │  2. Query PubMed API            │       │
│  │     • Search for relevant papers│       │
│  │     • Filter by year (2019+)    │       │
│  │     • Max 5 sources per query   │       │
│  └──────────────┬──────────────────┘       │
│                 │                           │
│                 ▼                           │
│  ┌─────────────────────────────────┐       │
│  │  3. Fetch abstracts             │       │
│  │     • PMID                      │       │
│  │     • Title, authors            │       │
│  │     • Abstract text             │       │
│  │     • Journal, year             │       │
│  └──────────────┬──────────────────┘       │
│                 │                           │
│                 ▼                           │
│  ┌─────────────────────────────────┐       │
│  │  4. Format evidence context     │       │
│  │     • Structured text           │       │
│  │     • Source metadata           │       │
│  └──────────────┬──────────────────┘       │
│                 │                           │
│                 ▼                           │
│  ┌─────────────────────────────────┐       │
│  │  5. Generate prompt with        │       │
│  │     evidence                    │       │
│  │     • Cohort params             │       │
│  │     • Evidence context          │       │
│  │     • Faithfulness instructions │       │
│  └──────────────┬──────────────────┘       │
│                 │                           │
│                 ▼                           │
│  ┌─────────────────────────────────┐       │
│  │  6. Call OpenRouter LLM         │       │
│  │     Model: Claude 3.5 Sonnet    │       │
│  │     Temp: 0.6 (more conservative)│      │
│  └──────────────┬──────────────────┘       │
│                 │                           │
│                 ▼                           │
│  ┌─────────────────────────────────┐       │
│  │  7. Parse JSON response         │       │
│  │     • hook                      │       │
│  │     • explanation               │       │
│  │     • action                    │       │
│  │     • source + PMID             │       │
│  │     • evidence_support          │       │
│  └──────────────┬──────────────────┘       │
│                 │                           │
│                 ▼                           │
│      Insight JSON + Evidence                │
│                                             │
└─────────────────────────────────────────────┘

Speed: ⭐⭐  Cost: ⭐⭐⭐⭐  Quality: ⭐⭐⭐⭐⭐
```

### 3. Validator
```
┌─────────────────────────────────────────────┐
│           VALIDATOR                         │
├─────────────────────────────────────────────┤
│                                             │
│  For each insight:                          │
│                                             │
│  ┌────────────────────────┐                │
│  │ 1. Schema Check (25pts)│                │
│  │   • Required fields    │                │
│  │   • Field types        │                │
│  │   • Length limits      │                │
│  └──────┬─────────────────┘                │
│         │                                   │
│         ▼                                   │
│  ┌────────────────────────┐                │
│  │ 2. Source Check (25pts)│                │
│  │   • URL validity       │                │
│  │   • Domain whitelist   │                │
│  │   • Source tier        │                │
│  └──────┬─────────────────┘                │
│         │                                   │
│         ▼                                   │
│  ┌────────────────────────┐                │
│  │ 3. Numeric Check (25pts│                │
│  │   • Percentages valid  │                │
│  │   • Ratios plausible   │                │
│  │   • Risk multipliers OK│                │
│  └──────┬─────────────────┘                │
│         │                                   │
│         ▼                                   │
│  ┌────────────────────────┐                │
│  │ 4. Quality Check (25pts│                │
│  │   • Starts "Did you"   │                │
│  │   • Actionable verb    │                │
│  │   • Cohort-specific    │                │
│  │   • No fear-mongering  │                │
│  │   • No diagnosis claims│                │
│  └──────┬─────────────────┘                │
│         │                                   │
│         ▼                                   │
│  ┌────────────────────────┐                │
│  │ Calculate overall score│                │
│  │   Sum / 4 = Score/100  │                │
│  │   Valid if score ≥ 60  │                │
│  └────────────────────────┘                │
│                                             │
└─────────────────────────────────────────────┘
```

### 4. Deduplicator
```
┌─────────────────────────────────────────────┐
│         DEDUPLICATOR                        │
├─────────────────────────────────────────────┤
│                                             │
│  For each pair of insights:                 │
│                                             │
│  ┌────────────────────────────┐            │
│  │ 1. Extract full text       │            │
│  │    hook + explanation      │            │
│  └──────┬─────────────────────┘            │
│         │                                   │
│         ▼                                   │
│  ┌────────────────────────────┐            │
│  │ 2. Calculate similarity    │            │
│  │    SequenceMatcher.ratio() │            │
│  └──────┬─────────────────────┘            │
│         │                                   │
│         ▼                                   │
│  ┌────────────────────────────┐            │
│  │ 3. Check threshold         │            │
│  │    similarity ≥ 0.85?      │            │
│  └──────┬─────────────────────┘            │
│         │                                   │
│         ├─── Yes ──→ Mark duplicate        │
│         └─── No ───→ Keep both             │
│                                             │
│  Remove all duplicate indices               │
│  (keep first occurrence)                    │
│                                             │
└─────────────────────────────────────────────┘
```

### 5. Quality Scorer
```
┌─────────────────────────────────────────────┐
│        QUALITY SCORER                       │
├─────────────────────────────────────────────┤
│                                             │
│  Engagement Score (0-100):                  │
│                                             │
│  Hook (30 points)                           │
│  ├─ Starts "Did you know" (+10)            │
│  ├─ Contains numbers (+10)                 │
│  └─ Concise ≤20 words (+10)                │
│                                             │
│  Explanation (40 points)                    │
│  ├─ Optimal length 40-60 words (+15)       │
│  ├─ References cohort (+15)                │
│  └─ Has numeric claim (+10)                │
│                                             │
│  Action (30 points)                         │
│  ├─ Has action verb (+15)                  │
│  └─ Appropriate length 10-30 words (+15)   │
│                                             │
│  Total = Sum of earned points               │
│                                             │
└─────────────────────────────────────────────┘
```

## Data Flow Example

```
INPUT COHORT:
{
  "age_group": "40-49",
  "gender": "male", 
  "smoking_status": "smoker"
}

↓ Pure LLM Path

PROMPT:
"Generate DYK insight for 40-49 year old male smoker..."

↓ OpenRouter API

LLM RESPONSE:
{
  "hook": "Did you know that male smokers in their 40s have 3x higher lung cancer risk?",
  "explanation": "Decades of smoking damage accumulate, and risk peaks in middle age...",
  "action": "Speak to your doctor about smoking cessation programs.",
  "source_name": "CDC"
}

↓ Validation

VALIDATION RESULT:
{
  "schema": 90/100,
  "source": 75/100,
  "numeric": 85/100,
  "quality": 80/100,
  "overall": 82.5/100,
  "valid": true
}

↓ Quality Scoring

QUALITY SCORE: 87/100

↓ Filter (min_quality=70)

KEEP ✓

↓ Export

FINAL OUTPUT:
{
  "cohort_id": "cohort_0001",
  "hook": "...",
  "validation_score": 82.5,
  "quality_score": 87,
  ...
}
```

## Configuration Hierarchy

```
config.yaml
    │
    ├─── regions
    │       ├─── singapore
    │       │      ├─── authoritative_sources
    │       │      ├─── global_sources
    │       │      └─── whitelisted_domains
    │       │
    │       └─── global
    │              ├─── authoritative_sources
    │              └─── global_sources
    │
    ├─── cohort_definitions
    │       ├─── age_groups (priority)
    │       ├─── genders (priority)
    │       ├─── smoking_status (priority)
    │       ├─── physical_activity (priority)
    │       ├─── bmi_category (priority)
    │       └─── chronic_conditions (priority)
    │
    ├─── priority_cohorts
    │       ├─── high-risk combinations
    │       │      ├─── dimensions
    │       │      └─── min_insights
    │       │
    │       └─── baseline combinations
    │              ├─── dimensions
    │              └─── min_insights
    │
    ├─── health_domains
    │       └─── [cardiovascular, metabolic, ...]
    │
    └─── insight_templates
            └─── [risk_amplification, protective_factors, ...]
```

## Module Dependencies

```
pipeline.py
    ├── cohort_generator.py
    │       └── config.yaml
    │
    ├── insight_generator.py
    │       ├── prompt_templates.py
    │       ├── pubmed_integration.py
    │       └── OpenRouter API
    │
    └── validator.py
            └── QualityScorer
```

## Scaling Architecture

```
For 1,000+ insights:

┌─────────────────┐
│  Batch 1        │───┐
│  (100 cohorts)  │   │
└─────────────────┘   │
                      │
┌─────────────────┐   │    ┌──────────────┐
│  Batch 2        │───┼────│   MERGE      │────→ Final DB
│  (100 cohorts)  │   │    │  & DEDUPE    │
└─────────────────┘   │    └──────────────┘
                      │
┌─────────────────┐   │
│  Batch N        │───┘
│  (100 cohorts)  │
└─────────────────┘

Each batch runs independently
Results merged at end
```

This architecture provides:
- ✅ Modularity
- ✅ Scalability  
- ✅ Testability
- ✅ Maintainability
- ✅ Extensibility
