# DYK (Did You Know) Health Insights Module
## Technical Documentation

**Version:** 2.0
**Last Updated:** November 2025
**Author:** Genie Health
**Purpose:** Healthcare Application - Personalized Health Insights Generation System

---

## Table of Contents

1. [Executive Overview](#executive-overview)
2. [System Architecture](#system-architecture)
3. [Configuration-Driven Approach](#configuration-driven-approach)
4. [Prompt Template Structure](#prompt-template-structure)
5. [Data Schema](#data-schema)
6. [Pipeline Architecture](#pipeline-architecture)
7. [Integration Guide](#integration-guide)
8. [Performance & Costs](#performance--costs)
9. [Extensibility](#extensibility)
10. [Appendix](#appendix)

---

## Executive Overview

### Purpose
The DYK module is an AI-powered system that generates personalized, evidence-based health insights for specific population segments. It combines demographic segmentation, health research, and Large Language Models (LLMs) to produce targeted "Did You Know" insights that are validated, quality-controlled, and optimized for user engagement.

### Key Features
- **Config-Driven**: All cohorts, templates, and sources defined in YAML files
- **Quality-Controlled**: Multi-layer validation and LLM-based evaluation
- **Evidence-Based**: Cites authoritative health sources (HPB, WHO, CDC, etc.)
- **Scalable**: Batch generation of hundreds/thousands of insights
- **Market-Specific**: Supports Singapore with extensibility to other regions
- **Production-Ready**: Comprehensive error handling, logging, and CSV export

### Use Cases
1. **Mobile Health Apps**: Power personalized recommendation engines
2. **Health Campaigns**: Generate targeted messaging for specific populations
3. **Patient Engagement**: Create compelling health education content
4. **Research**: A/B test different messaging strategies

---

## System Architecture

### High-Level Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                    DYK INSIGHTS GENERATION SYSTEM                     │
└──────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                        CONFIGURATION LAYER                          │
│  (YAML Files - Easily Editable by Non-Technical Users)              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │  Priority        │  │  Insight         │  │  Evidence        │ │
│  │  Cohorts         │  │  Templates       │  │  Sources         │ │
│  │                  │  │                  │  │                  │ │
│  │ • Demographics   │  │ • 17 Templates   │  │ • Tier 1 (Local) │ │
│  │ • Health Risks   │  │ • Weighted       │  │ • Tier 2 (Global)│ │
│  │ • Priorities     │  │ • Structured     │  │ • Tier 3 (Research)│ │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘ │
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐                       │
│  │  Health          │  │  Market-Specific │                       │
│  │  Domains         │  │  Config          │                       │
│  │                  │  │                  │                       │
│  │ • 17 Categories  │  │ • Singapore      │                       │
│  │ • Universal      │  │ • Extensible     │                       │
│  └──────────────────┘  └──────────────────┘                       │
└─────────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────┐
│                         GENERATION PIPELINE                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Step 1: COHORT GENERATION                                          │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ • Load priority cohorts from YAML                             │ │
│  │ • Generate cohort specifications                              │ │
│  │ • Prioritize by clinical impact                               │ │
│  │ Output: cohorts.json                                          │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                  ↓                                  │
│  Step 2: INSIGHT GENERATION (LLM-Powered)                           │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ • For each cohort × template combination:                     │ │
│  │   - Build structured prompt (cohort + template + domains)     │ │
│  │   - Call LLM API (OpenRouter/Gemini)                          │ │
│  │   - Generate 5 unique insights per call                       │ │
│  │   - Parse JSON response                                       │ │
│  │   - Add metadata (timestamp, model, temperature)              │ │
│  │ Output: insights_raw.json                                     │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                  ↓                                  │
│  Step 3: VALIDATION (Rule-Based)                                    │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ • Schema conformity check (required fields, types, lengths)   │ │
│  │ • Source URL accessibility check (HTTP requests)              │ │
│  │ • Field length validation (hook ≤20 words, etc.)              │ │
│  │ • Flag failures with specific reasons                         │ │
│  │ Output: insights_post_validation.json, insights_validated.json│ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                  ↓                                  │
│  Step 4: EVALUATION (LLM-Powered)                                   │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ • For each validated insight:                                 │ │
│  │   - Build evaluation prompt with criteria                     │ │
│  │   - Call evaluation LLM                                       │ │
│  │   - Assess: accuracy, safety, relevance, actionability        │ │
│  │   - Generate quality score (0-10)                             │ │
│  │   - Add evaluation metadata                                   │ │
│  │ Output: insights_final.json                                   │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                  ↓                                  │
│  Step 5: EXPORT & REPORTING                                         │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │ • Export to CSV for Excel/Google Sheets viewing               │ │
│  │ • Generate executive summary (TXT)                            │ │
│  │ • Create top insights report (CSV)                            │ │
│  │ • Save pipeline statistics (JSON)                             │ │
│  │ Output: insights_final.csv, executive_summary.txt, etc.       │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                  ↓
┌─────────────────────────────────────────────────────────────────────┐
│                          OUTPUT LAYER                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  For Technical Users:                                               │
│  • insights_final.json - Complete data with metadata               │
│  • pipeline_summary.json - Statistics and metrics                  │
│                                                                     │
│  For Business Users:                                                │
│  • insights_final.csv - Excel-friendly table view                  │
│  • executive_summary.txt - High-level overview                     │
│  • top_insights.csv - Top 50 best insights                         │
│  • quick_review.csv - Readable full insights                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Language** | Python 3.8+ | Core implementation |
| **LLM Provider** | OpenRouter / Google AI | Insight generation & evaluation |
| **Models** | Gemini Flash 2.5 / Grok 4.1 | Text generation |
| **Configuration** | YAML | Human-editable config files |
| **Data Format** | JSON | Structured data interchange |
| **Export Format** | CSV | Business user viewing |
| **Evidence API** | PubMed E-utilities | Scientific literature (optional) |

---

## Configuration-Driven Approach

The DYK system is **fully configuration-driven**, allowing non-technical users to modify cohorts, templates, and sources without touching code.

### 1. Priority Cohorts Configuration

**File:** `src/config/singapore/priority_cohorts.yaml`

**Purpose:** Define high-impact population segments for targeted insights.

#### Cohort Structure

Each cohort consists of:
- **name**: Unique identifier
- **dimensions**: Demographic/health characteristics
- **priority**: Clinical impact ranking (1=highest)
- **description**: Human-readable summary
- **rationale**: Why this cohort is important (with statistics)
- **insight_angles**: Suggested messaging approaches

#### Priority Cohorts Table

| Cohort Name | Target Population | Priority | Dimensions | Rationale |
|-------------|-------------------|----------|------------|-----------|
| **office_workers_metabolic_risk** | Sedentary office workers aged 30-59, overweight/obese | 1 (Highest) | age_group: [30-44, 45-59]<br>bmi: [overweight, obese]<br>physical_activity: [sedentary]<br>occupation_context: [desk_job] | Singapore's 8.6% diabetes rate driven by sedentary work culture. Sitting 8+ hrs daily compounds metabolic risk. High prevention potential. |
| **shift_workers_metabolic_risk** | Shift workers aged 30-59 with prediabetes/hypertension | 1 | age_group: [30-44, 45-59]<br>occupation_context: [shift_work]<br>health_conditions: [prediabetes, hypertension] | Night shift increases metabolic syndrome by 36%, diabetes by 40%. Large SG workforce. Circadian disruption is modifiable. |
| **stressed_midlife_professionals** | High-stress professionals with CVD risk | 1 | age_group: [30-44, 45-59]<br>occupation_context: [high_stress_job]<br>health_conditions: [hypertension, high-cholesterol]<br>lifestyle: [insufficient_sleep] | Work stress increases CVD by 23%. SG's long work hours (45+ hrs/week) + multiple risks. Stress management underutilized. |
| **ethnic_high_risk_cvd** | Malay/Indian adults aged 30-59 with CVD risks | 1 | race: [malay, indian]<br>age_group: [30-44, 45-59]<br>health_conditions: [diabetes, hypertension, high-cholesterol] | Indians develop CVD 10 years earlier with 3-4x higher risk. Cultural dietary patterns modifiable. |
| **perimenopausal_women** | Women aged 45-59 in perimenopause | 1 | age_group: [45-59]<br>gender: [female]<br>life_stage: [perimenopause] | Women lose 20% bone density post-menopause, CVD risk doubles. Critical prevention window. Asian women experience menopause 2 years earlier. |
| **postpartum_weight_management** | New mothers aged 18-44 | 2 | age_group: [18-29, 30-44]<br>gender: [female]<br>life_stage: [postpartum] | Postpartum weight retention increases long-term obesity. SG's high C-section rate (30%) impacts recovery. |
| **student_mental_health** | Students aged 18-29 with stress/anxiety | 2 | age_group: [18-29]<br>occupation_context: [student]<br>health_conditions: [stress, anxiety, poor_sleep] | 1 in 7 students experience depression. Exam stress, social media, sleep deprivation compound. Early intervention prevents lifelong issues. |
| **active_aging_seniors** | Seniors 60+ at risk of falls/sarcopenia | 1 | age_group: [60+]<br>physical_activity: [sedentary, insufficiently-active]<br>health_concerns: [fall_risk, sarcopenia, cognitive_decline] | 1 in 3 seniors fall annually. Exercise reduces dementia by 35%. SG's aging population (19% over 65 by 2030). |
| **senior_chronic_disease_managers** | Seniors 60+ with multiple chronic conditions | 1 | age_group: [60+]<br>health_conditions: [diabetes, hypertension, high-cholesterol]<br>medication_adherence: [suboptimal] | 70% of seniors have 2+ chronic diseases. Medication non-adherence increases stroke risk by 30%. |
| **health_conscious_millennials** | Health-engaged adults aged 30-44 | 3 (Lower) | age_group: [30-44]<br>health_engagement: [high]<br>physical_activity: [moderately-active, highly-active] | Already motivated but may lack evidence-based guidance. Focus on optimization vs. basic prevention. |

**Total Priority Cohorts:** 10

---

### 2. Insight Templates Configuration

**File:** `src/config/insight_templates.yaml`

**Purpose:** Define insight structures and messaging patterns.

#### Template Structure

Each template consists of:
- **type**: Unique identifier
- **description**: What this template does
- **weight**: Relative importance (higher = more frequent usage)
- **structure**: Pattern to follow
- **example**: Sample insights
- **tone**: Required emotional tone

#### Insight Templates Table

| Template Type | Description | Weight | Structure Pattern | Example Insight |
|---------------|-------------|--------|-------------------|-----------------|
| **quantified_action_benefit** | Specific action with measurable outcome | 15 (Highest) | [Action] for [duration] → [Z% improvement] | "150 minutes moderate activity weekly reduces chronic disease by 30%—that's only 21 minutes daily. Start with a brisk walk during lunch break today." |
| **risk_reversal** | Present risk THEN show how to reverse it | 12 | [Behavior] increases [outcome] by [%]. [Mechanism]. [Action reverses it] | "Sleeping less than 7 hours increases anxiety risk by 2.5x. Your brain needs deep sleep to regulate emotions. Aim to be in bed by 11pm tonight." |
| **mechanism_reveal** | Explain the fascinating 'why' | 10 | [Outcome with numbers]. [Biological mechanism]. [Action] | "Sleeping less than 6 hours increases obesity risk by 41% by dysregulating hunger hormones. Sleep deprivation makes you hungrier. Prioritize 7-8 hours." |
| **hidden_consequence** | Reveal non-obvious consequences | 9 | [Common behavior] increases [unexpected outcome] by [%] | "Fast eating (under 10 min) doubles obesity risk—satiety signals take 20 minutes. Put utensils down between bites, take minimum 20 minutes." |
| **comparative_effectiveness** | Compare two approaches | 8 | [Surprising comparison with numbers]. [Why it works]. [Action] | "Just 75 minutes weekly vigorous exercise equals heart benefits of 150 min moderate. Do 25-min HIIT 3x/week." |
| **counterintuitive_fact** | Shocking statistic that challenges assumptions | 8 | [Shocking statistic]. [Scientific explanation]. [Action] | "Reading for just 6 minutes reduces stress by 68%—more than music (61%) or walking (42%). Keep book by bedside for evening relaxation." |
| **easy_substitution** | Simple swaps with outsized benefits | 9 | Replace [X] with [Y] and achieve [Z% improvement] | "Use 9-inch plates instead of 12-inch and cut portions by 30% without feeling deprived. Replace dinner plates with salad plates." |
| **minimum_effective_dose** | Surprisingly low threshold for benefits | 7 | [Minimal intervention] produces [impressive % outcome] | "Losing just 5% body weight reverses prediabetes by 58%—that's only 5kg for 70kg person. Aim for 0.5kg/week." |
| **life_stage_specific** | Address unique concerns of life stages | 7 | [Life stage] experiences [challenge with numbers]. [Stage-appropriate action] | "Perimenopausal women lose up to 20% bone density in 5-7 years. Get 1,200mg calcium daily plus vitamin D, 15 min morning sun." |
| **synergistic_multiplier** | Combined interventions create exponential benefits | 6 | [Action 1] + [Action 2] produces [X-fold better outcome] | "Mediterranean diet + 150min weekly exercise reduces heart attack by 50%—far more than either alone. Eat fatty fish 2x/week, walk 30min 5 days." |
| **critical_window** | Time-sensitive opportunities | 6 | [Action during specific window] prevents [future outcome by %] | "Peak bone mass occurs at age 30, then declines 0.5-1% yearly. Weight-bearing exercise in 30s-40s protects against osteoporosis. Do bodyweight squats 3x weekly." |
| **micro_habit_anchor** | Attach new behavior to existing routine | 6 | [Add tiny behavior] to [existing routine] → [cumulative outcome] | "10 squats while brushing teeth → 3,650 squats yearly → stronger bones and balance. Add 10 squats to morning/evening routine." |
| **normative_social_proof** | Use peer behavior to encourage adoption | 5 | [X%] of [peer group] [perform behavior] achieving [outcome] | "65% of Singaporean men 50+ now get regular prostate screening. Early detection saves lives when cure rates exceed 90%. Schedule via Screen for Life." |
| **practical_roi** | Financial/time ROI of health actions | 5 | [Small investment] saves [large amount money/time] | "Home cooking 5+ times weekly consumes 200 fewer daily calories, 30% less sugar/fat than eating out. Start cooking dinner at home one more night weekly." |
| **social_health_nexus** | Quantify health benefits of social connections | 5 | [Type of connection] reduces [health risk by %] through [mechanism] | "Having 3-5 close friends reduces stress hormone cortisol by 30%, strengthens immunity. Schedule weekly time with a friend." |
| **cascade_multiplier** | One action triggers beneficial chain reaction | 5 | [Single action] → [immediate effect] → [secondary effect] → [outcome %] | "Improving sleep quality → better glucose control → lower inflammation → 30% reduced cancer risk. Protect 7-8 hours nightly." |
| **ethnic_targeted** | Address ethnicity-specific risks | 4 | [Ethnic group] has [X-fold higher risk] due to [factors]. [Culturally-appropriate action] | "Indians develop diabetes 10 years earlier with higher insulin resistance. Reducing refined carbs cuts risk by 40%. Choose whole grain chapati over white flour." |

**Total Templates:** 17 (some are formatting guidelines, ~15 active templates)

**Weight System:** Actual usage percentage = `template_weight / sum(all_weights)`
- Easy to add new templates without recalculating percentages
- Higher weight = more frequent selection during generation

---

### 3. Evidence Sources Configuration

**File:** `src/config/singapore/sources.yaml`

**Purpose:** Define authoritative health sources in 3-tier hierarchy.

#### Three-Tier Source Hierarchy

**Tier 1: Local Authoritative Sources (Highest Priority)**
- Singapore government and healthcare institutions
- Prioritized for cultural relevance and local statistics

**Tier 2: Global Trusted Sources**
- Internationally recognized health authorities
- Premier medical journals

**Tier 3: Research Databases**
- Peer-reviewed literature
- Specialized research sources

#### Evidence Sources Table

| Tier | Source Name | URL | Focus Area |
|------|-------------|-----|------------|
| **Tier 1 (Local)** | | | |
| 1 | Health Promotion Board (HPB) | healthhub.sg | National health promotion, lifestyle guidelines, screening programs |
| 1 | Ministry of Health Singapore (MOH) | moh.gov.sg | National health policies, disease statistics, clinical guidelines |
| 1 | National Healthcare Group (NHG) | nhg.com.sg | Clinical research, primary care, population health |
| 1 | SingHealth | singhealth.com.sg | Clinical research, specialty care, population health |
| 1 | National University Health Group (NUHS) | nuhs.edu.sg | Clinical research, specialty care, population health |
| 1 | National Population Health Survey | moh.gov.sg/resources-statistics | Population health data, disease prevalence, risk factors |
| 1 | National University of Singapore | nus.edu.sg | Cohort studies, behavioral epidemiology, genetics, aging research |
| 1 | Duke-NUS | duke-nus.edu.sg | Cohort studies, behavioral epidemiology, genetics, aging research |
| 1 | Agency for Care Effectiveness (ACE) | ace-hta.gov.sg | Evidence-based clinical guidance, HTA reports |
| 1 | National Registry of Diseases (NRDO) | nrdo.gov.sg | Cancer statistics, disease registries |
| 1 | Agency for Integrated Care (AIC) | aic.sg | Senior statistics, fall risk, dementia, community care |
| 1 | Health Sciences Authority (HSA) | hsa.gov.sg | Supplement evidence, medication guidance |
| **Tier 2 (Global)** | | | |
| 2 | World Health Organization (WHO) | who.int | Global health standards, disease control, screening recommendations |
| 2 | World Bank Health Data | data.worldbank.org | Disease burden, population risk data, social determinants |
| 2 | UNICEF | unicef.org | Maternal & child health, nutrition, developmental milestones |
| 2 | OECD Health Statistics | oecd.org/health | Age-group disease patterns, health behaviors, risk comparisons |
| 2 | UK NICE | nice.org.uk | Clinical practice guidelines, lifestyle interventions |
| 2 | US CDC | cdc.gov | Disease prevention, vaccination, epidemiology, public health |
| 2 | The Lancet | thelancet.com | High-impact medical research, global health |
| 2 | JAMA | jamanetwork.com | Clinical research, medical practice |
| 2 | NEJM | nejm.org | Clinical research, breakthrough studies |
| 2 | BMJ | bmj.com | Clinical evidence, systematic reviews |
| 2 | Nature Medicine & Science | nature.com | Metabolic studies, age-related research, preventive genomics |
| **Tier 3 (Research)** | | | |
| 3 | PubMed/MEDLINE | pubmed.ncbi.nlm.nih.gov | Biomedical literature, research studies |
| 3 | Cochrane Library | cochranelibrary.com | Systematic reviews, meta-analyses |
| 3 | NIH | nih.gov | Biomedical research, health information |

**Total Sources:** 26 across 3 tiers

**Usage in Prompts:** Sources are presented to LLM to encourage citing authoritative references.

---

### 4. Health Domains Configuration

**File:** `src/config/health_domains.yaml`

**Purpose:** Define universal health categories for insight generation.

#### Health Domains Table

| Domain ID | Domain Name | Description | Example Topics |
|-----------|-------------|-------------|----------------|
| cardiovascular | Cardiovascular Health | Heart, blood vessels, circulation | Hypertension, cholesterol, heart disease prevention |
| metabolic | Metabolic Health | Blood sugar, metabolism, weight | Diabetes, prediabetes, obesity, metabolic syndrome |
| respiratory | Respiratory Health | Lungs, breathing | Asthma, COPD, lung function |
| mental_health | Mental Wellbeing | Mood, emotions, mental health | Depression, anxiety, stress management |
| cognitive_health | Cognitive Health | Brain function, memory | Dementia prevention, memory, focus |
| bone_health | Bone & Joint Health | Skeletal system | Osteoporosis, fractures, joint health |
| muscle_health | Muscle Health | Muscle mass, strength | Sarcopenia, strength training |
| digestive | Digestive Health | Gut, digestion | Gut microbiome, IBS, digestion |
| immune | Immune System | Immunity, infections | Immune function, vaccinations, infection prevention |
| nutrition | Nutrition | Diet, eating patterns | Dietary patterns, macronutrients, meal timing |
| physical_activity | Physical Activity | Exercise, movement | Exercise guidelines, sedentary behavior |
| sleep | Sleep Health | Sleep quality, duration | Sleep hygiene, insomnia, sleep disorders |
| cancer_prevention | Cancer Prevention | Cancer risk reduction | Screening, lifestyle factors, early detection |
| screening | Screening & Early Detection | Preventive screening | Health check-ups, cancer screening, vital sign monitoring |
| preventive_care | Preventive Care | Disease prevention | Vaccinations, risk reduction, health maintenance |
| chronic_disease | Chronic Disease Management | Managing long-term conditions | Medication adherence, lifestyle modifications |
| social_health | Social & Relationship Health | Social connections | Social support, loneliness, community engagement |

**Total Domains:** 17

**Usage:** LLM selects relevant domains based on cohort characteristics and template type.

---

## Prompt Template Structure

### LLM Prompt Architecture

The system uses **structured prompts** to guide LLM generation. Each prompt consists of multiple sections that provide context and constraints.

### Generation Prompt Template

**File:** `src/prompts/prompt_templates.py`

#### Prompt Components

```python
def pure_llm_generation(
    cohort: dict,
    insight_template: dict,
    health_domains: dict,
    sources: dict,
    region: str,
    num_insights: int
) -> str:
```

#### Prompt Structure

```
┌─────────────────────────────────────────────────────────────┐
│                    GENERATION PROMPT                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. SYSTEM ROLE                                             │
│     "You are a medical and public health expert..."         │
│                                                             │
│  2. REGION CONTEXT                                          │
│     Region: Singapore                                       │
│                                                             │
│  3. TARGET COHORT                                           │
│     Description: "Sedentary office workers..."              │
│     Parameters: {age_group: [30-44], bmi: [obese], ...}    │
│                                                             │
│  4. INSIGHT TEMPLATE                                        │
│     Type: "quantified_action_benefit"                       │
│     Description: "Specific action with measurable outcome"  │
│     Tone: "Direct, evidence-driven, actionable"             │
│     Example: "150 min activity reduces disease by 30%..."   │
│     Optional: Insight angles (if provided in cohort)        │
│                                                             │
│  5. HEALTH DOMAINS                                          │
│     Available domains: [cardiovascular, metabolic, ...]     │
│     Note: LLM may select different domains if more relevant │
│                                                             │
│  6. AUTHORITATIVE SOURCES                                   │
│     Tier 1 (Local): [HPB, MOH, NHG, ...]                    │
│     Tier 2 (Global): [WHO, CDC, Lancet, ...]                │
│     Tier 3 (Research): [PubMed, Cochrane, NIH, ...]         │
│                                                             │
│  7. TASK SPECIFICATION                                      │
│     "Generate {N} distinct 'Did You Know' insights..."      │
│                                                             │
│  8. STRUCTURAL REQUIREMENTS                                 │
│     • Opening Hook (15-25 words): Surprising statistic      │
│     • Explanation (20-40 words): Why it matters             │
│     • Call-to-Action (15-25 words): Specific action         │
│                                                             │
│  9. CONTENT REQUIREMENTS                                    │
│     • Evidence-based with specific percentages              │
│     • Relevant to cohort demographics/health risks          │
│     • Scientifically accurate                               │
│     • Culturally appropriate for {region}                   │
│     • Each insight must be UNIQUE                           │
│     • Follow template intent                                │
│     • Action must be practical and achievable               │
│                                                             │
│  10. OUTPUT FORMAT (JSON)                                   │
│      {                                                      │
│        "insights": [                                        │
│          {                                                  │
│            "hook": "...",                                   │
│            "explanation": "...",                            │
│            "action": "...",                                 │
│            "source_name": "...",                            │
│            "source_url": "...",                             │
│            "numeric_claim": "..."                           │
│          }                                                  │
│        ]                                                    │
│      }                                                      │
│                                                             │
│  11. CONSTRAINTS (What to Avoid)                            │
│      • Excessive program mentions (HPB, HealthHub, etc.)    │
│      • Generic advice without cohort specificity            │
│      • Unrealistic actions                                 │
│      • Duplicate insights                                  │
│      • Mentioning cohort characteristics explicitly         │
└─────────────────────────────────────────────────────────────┘
```

### Evaluation Prompt Template

**Purpose:** Assess quality of generated insights using LLM.

#### Evaluation Criteria

```
┌─────────────────────────────────────────────────────────────┐
│                    EVALUATION PROMPT                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  INSIGHT TO EVALUATE:                                       │
│  {insight content}                                          │
│                                                             │
│  TARGET COHORT:                                             │
│  {cohort description and parameters}                        │
│                                                             │
│  TEMPLATE TYPE:                                             │
│  {template type and description}                            │
│                                                             │
│  EVALUATION CRITERIA:                                       │
│                                                             │
│  1. FACTUAL ACCURACY (Score: 0-10)                          │
│     • Are claims scientifically sound?                      │
│     • Are statistics/percentages accurate?                  │
│     • Is the mechanism explanation correct?                 │
│                                                             │
│  2. SAFETY (Score: 0-10)                                    │
│     • Is advice safe for target cohort?                     │
│     • Any contraindications for this demographic?           │
│     • Are there important warnings missing?                 │
│                                                             │
│  3. RELEVANCE (Score: 0-10)                                 │
│     • Is it applicable to this cohort's needs?              │
│     • Does it address their specific risk factors?          │
│     • Is it age/demographic appropriate?                    │
│                                                             │
│  4. ACTIONABILITY (Score: 0-10)                             │
│     • Is the action clear and specific?                     │
│     • Is it practical and achievable?                       │
│     • Can the user start immediately?                       │
│                                                             │
│  5. CULTURAL APPROPRIATENESS (Score: 0-10)                  │
│     • Does it fit {region}'s healthcare context?            │
│     • Are cultural norms respected?                         │
│     • Are local resources/programs mentioned appropriately? │
│                                                             │
│  6. EVIDENCE FAITHFULNESS (Score: 0-10)                     │
│     • Does it align with cited sources?                     │
│     • Are sources credible and appropriate?                 │
│     • Is the source URL valid/accessible?                   │
│                                                             │
│  OUTPUT FORMAT (JSON):                                      │
│  {                                                          │
│    "overall_score": <0-10>,                                 │
│    "factual_accuracy": <0-10>,                              │
│    "safety": <0-10>,                                        │
│    "relevance": <0-10>,                                     │
│    "actionability": <0-10>,                                 │
│    "cultural_appropriateness": <0-10>,                      │
│    "evidence_faithfulness": <0-10>,                         │
│    "feedback": "Brief explanation of scores..."             │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Schema

### Insight JSON Schema

#### Generated Insight Structure

```json
{
  "hook": "String (15-25 words) - Attention-grabbing fact starting with 'Did you know...'",
  "explanation": "String (20-40 words) - Why this matters for the cohort",
  "action": "String (15-25 words) - Specific actionable step",
  "source_name": "String - Name of authoritative source",
  "source_url": "String - URL to source or 'general medical knowledge'",
  "numeric_claim": "String - Specific numeric claim (e.g., '30% reduction') or empty",

  "metadata": {
    "cohort": {
      "cohort_id": "String - e.g., 'cohort_0001'",
      "cohort_params": {
        "age_group": "String or Array - e.g., '30-44' or ['30-44', '45-59']",
        "bmi": "String or Array - e.g., 'obese'",
        "gender": "String - e.g., 'female'",
        "race": "String - e.g., 'chinese', 'malay', 'indian'",
        "health_conditions": "String or Array - e.g., 'diabetes'",
        "occupation_context": "String - e.g., 'desk_job', 'shift_work'",
        "physical_activity": "String - e.g., 'sedentary'",
        "life_stage": "String - e.g., 'perimenopause', 'postpartum'"
      },
      "priority_level": "Integer (1-3) - 1=highest priority",
      "description": "String - Human-readable cohort description"
    },

    "insight_template": {
      "type": "String - Template identifier",
      "description": "String - What this template does",
      "weight": "Integer - Relative importance",
      "tone": "String - Required emotional tone"
    },

    "region": "String - Target market (e.g., 'singapore')",
    "generation_model": "String - LLM model used (e.g., 'google/gemini-flash-2.5')",
    "generation_temperature": "Float - LLM temperature (e.g., 0.7)",
    "generation_max_tokens": "Integer - Max tokens (e.g., 2000)",
    "generation_timestamp": "String - ISO 8601 datetime"
  },

  "validation": {
    "validated": "Boolean - Overall validation result",
    "number_failed": "Integer - Number of failed checks (0-3)",
    "checks": {
      "json_validity": {
        "passed": "Boolean",
        "issues": ["Array of issue strings"]
      },
      "schema_conformity": {
        "passed": "Boolean",
        "issues": ["Array of issue strings"]
      },
      "source_verification": {
        "passed": "Boolean",
        "issues": ["Array of issue strings"],
        "warnings": ["Array of warning strings"]
      }
    },
    "validation_timestamp": "String - ISO 8601 datetime"
  },

  "evaluation": {
    "result": {
      "overall_score": "Float (0-10) - Overall quality score",
      "factual_accuracy": "Float (0-10)",
      "safety": "Float (0-10)",
      "relevance": "Float (0-10)",
      "actionability": "Float (0-10)",
      "cultural_appropriateness": "Float (0-10)",
      "evidence_faithfulness": "Float (0-10)",
      "feedback": "String - Evaluation feedback"
    },
    "evaluation_model": "String - LLM model used for evaluation",
    "evaluation_timestamp": "String - ISO 8601 datetime"
  }
}
```

#### Example Complete Insight

```json
{
  "hook": "Did you know regular exercise + balanced diet doubles protection against depression compared to either alone?",
  "explanation": "For obese Singaporeans aged 50-59 at higher depression risk from inflammation and low mood, this synergy boosts brain chemicals like serotonin more effectively, enhancing emotional wellbeing as promoted by HPB guidelines.",
  "action": "Aim for 150min weekly brisk walking and follow HPB My Healthy Plate: fill half your plate with fruits/veggies, quarter wholegrains, quarter lean protein.",
  "source_name": "Health Promotion Board (HPB)",
  "source_url": "https://www.hpb.gov.sg/healthy-living/mental-wellbeing",
  "numeric_claim": "doubles protection",

  "metadata": {
    "cohort": {
      "cohort_id": "cohort_0001",
      "cohort_params": {
        "age_group": ["30-44", "45-59"],
        "bmi": ["overweight", "obese"],
        "physical_activity": ["sedentary"],
        "occupation_context": ["desk_job"]
      },
      "priority_level": 1,
      "description": "Sedentary office workers at risk of metabolic diseases"
    },
    "insight_template": {
      "type": "synergistic_multiplier",
      "description": "Show how combining interventions creates exponential, not additive, benefits",
      "weight": 6,
      "tone": "Empowering, holistic, synergy-focused"
    },
    "region": "singapore",
    "generation_model": "google/gemini-flash-2.5",
    "generation_temperature": 0.7,
    "generation_max_tokens": 2000,
    "generation_timestamp": "2025-11-28T14:30:00.000Z"
  },

  "validation": {
    "validated": true,
    "number_failed": 0,
    "checks": {
      "json_validity": {
        "passed": true,
        "issues": []
      },
      "schema_conformity": {
        "passed": true,
        "issues": []
      },
      "source_verification": {
        "passed": true,
        "issues": [],
        "warnings": []
      }
    },
    "validation_timestamp": "2025-11-28T14:30:05.000Z"
  },

  "evaluation": {
    "result": {
      "overall_score": 8.5,
      "factual_accuracy": 9,
      "safety": 10,
      "relevance": 8,
      "actionability": 8,
      "cultural_appropriateness": 9,
      "evidence_faithfulness": 8,
      "feedback": "Strong synergy message with credible source. Action is specific and culturally appropriate for Singapore. Minor: Could specify exercise intensity more precisely."
    },
    "evaluation_model": "google/gemini-flash-2.5",
    "evaluation_timestamp": "2025-11-28T14:30:10.000Z"
  }
}
```

### Field Validation Rules

| Field | Type | Required | Min Length | Max Length | Additional Rules |
|-------|------|----------|------------|------------|------------------|
| hook | String | Yes | - | 20 words | Must start with "Did you know" |
| explanation | String | Yes | 30 words | 60 words | Optimal: 40-60 words |
| action | String | Yes | - | 30 words | Must be specific and actionable |
| source_name | String | Yes | - | - | Must be non-empty |
| source_url | String | Yes | - | - | Must be valid URL or "general medical knowledge" |
| numeric_claim | String | No | - | - | Can be empty string |

---

## Pipeline Architecture

### Step-by-Step Workflow

#### Step 1: Cohort Generation

**Module:** `src/core/cohort_generator.py`

**Input:**
- `src/config/singapore/priority_cohorts.yaml`

**Process:**
1. Load priority cohorts from YAML
2. For each cohort definition:
   - Parse dimensions (age_group, bmi, health_conditions, etc.)
   - Extract priority level
   - Generate cohort_id (e.g., cohort_0001)
   - Create description and rationale
3. Sort cohorts by priority (1=highest)

**Output:**
- `output/cohorts.json` - List of cohort specifications

**Code Flow:**
```python
class CohortGenerator:
    def __init__(self, market: str):
        loader = ConfigLoader(market=market)
        self.cohort_definitions = loader.cohort_definitions
        self.priority_cohorts = loader.priority_cohorts

    def generate_priority_cohorts(self) -> List[Dict]:
        cohorts = []
        for idx, priority_group in enumerate(self.priority_cohorts, 1):
            cohort = {
                "cohort_id": f"cohort_{idx:04d}",
                "cohort_params": priority_group["dimensions"],
                "priority_level": priority_group["priority"],
                "description": priority_group["description"],
                "rationale": priority_group["rationale"],
                "insight_angles": priority_group.get("insight_angles", [])
            }
            cohorts.append(cohort)

        cohorts.sort(key=lambda x: x["priority_level"])
        return cohorts
```

**Example Output:**
```json
[
  {
    "cohort_id": "cohort_0001",
    "cohort_params": {
      "age_group": ["30-44", "45-59"],
      "bmi": ["overweight", "obese"],
      "physical_activity": ["sedentary"],
      "occupation_context": ["desk_job"]
    },
    "priority_level": 1,
    "description": "Sedentary office workers at risk of metabolic diseases",
    "rationale": "Singapore's 8.6% diabetes rate...",
    "insight_angles": [
      "Desk-based micro-movements",
      "Hawker center meal optimization"
    ]
  }
]
```

---

#### Step 2: Insight Generation

**Module:** `src/core/insight_generator.py`

**Input:**
- Cohorts from Step 1
- Insight templates from YAML
- Health domains from YAML
- Sources from YAML

**Process:**
1. For each cohort × template combination:
   - Build structured prompt using `PromptTemplates.pure_llm_generation()`
   - Call LLM API (OpenRouter or Google AI)
   - Request N insights per call (default: 5)
   - Parse JSON response
   - Add metadata (cohort, template, model, timestamp)
   - Handle errors and retries
2. Aggregate all insights

**Output:**
- `output/insights_raw.json` - All generated insights with metadata

**Code Flow:**
```python
class InsightGenerator:
    def __init__(self, llm_client, evidence_retriever, prompt_template):
        self.llm = llm_client
        self.evidence_retriever = evidence_retriever
        self.prompt_template = prompt_template

    def generate(self, cohort, insight_template, health_domains,
                 sources, region, num_insights, model, temperature, max_tokens):
        # Build prompt
        prompt = self.prompt_template.pure_llm_generation(
            cohort=cohort,
            insight_template=insight_template,
            health_domains=health_domains,
            sources=sources,
            region=region,
            num_insights=num_insights
        )

        # Call LLM
        response = self.llm.generate(
            prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )

        # Parse JSON response
        insights = self._parse_json_response(response)

        # Add metadata
        for insight in insights:
            insight["metadata"] = {
                "cohort": cohort,
                "insight_template": insight_template,
                "region": region,
                "generation_model": model,
                "generation_timestamp": datetime.now().isoformat()
            }

        return insights
```

**API Call Example:**
```
POST https://openrouter.ai/api/v1/chat/completions
Headers:
  Authorization: Bearer {api_key}
  Content-Type: application/json

Body:
{
  "model": "google/gemini-flash-2.5",
  "messages": [
    {
      "role": "user",
      "content": "{structured_prompt}"
    }
  ],
  "temperature": 0.7,
  "max_tokens": 2000
}
```

**LLM Response:**
```json
{
  "insights": [
    {
      "hook": "Did you know...",
      "explanation": "...",
      "action": "...",
      "source_name": "HPB",
      "source_url": "https://...",
      "numeric_claim": "30% reduction"
    },
    // ... 4 more insights
  ]
}
```

---

#### Step 3: Validation

**Module:** `src/core/validator.py`

**Input:**
- Raw insights from Step 2

**Process:**
For each insight, run three validation checks:

**1. JSON Validity Check**
```python
def _validate_json(self, insight: Dict) -> Dict:
    try:
        json.dumps(insight)
        return {"passed": True, "issues": []}
    except (TypeError, ValueError) as e:
        return {"passed": False, "issues": [f"Not valid JSON: {e}"]}
```

**2. Schema Conformity Check**
```python
def _validate_schema(self, insight: Dict) -> Dict:
    issues = []
    required_fields = {
        "hook": str,
        "explanation": str,
        "action": str,
        "source_name": str,
        "source_url": str,
        "numeric_claim": str
    }

    # Check required fields present
    missing = [f for f in required_fields if f not in insight]
    if missing:
        issues.append(f"Missing fields: {missing}")

    # Check field types
    for field, expected_type in required_fields.items():
        if field in insight and not isinstance(insight[field], expected_type):
            issues.append(f"Field '{field}' must be {expected_type.__name__}")

    # Check field lengths
    if "hook" in insight:
        hook_words = len(insight["hook"].split())
        if hook_words > 20:
            issues.append(f"Hook too long: {hook_words} words (max 20)")

    if "explanation" in insight:
        exp_words = len(insight["explanation"].split())
        if exp_words < 30 or exp_words > 60:
            issues.append(f"Explanation suboptimal: {exp_words} words (target 40-60)")

    return {"passed": len(issues) == 0, "issues": issues}
```

**3. Source Verification Check**
```python
def _validate_source(self, insight: Dict) -> Dict:
    issues = []
    warnings = []

    source_url = insight.get("source_url", "")

    if not source_url:
        issues.append("Missing source URL")
    elif source_url == "general medical knowledge":
        warnings.append("No specific source URL")
    else:
        # Validate URL format
        parsed = urlparse(source_url)
        if not parsed.scheme or not parsed.netloc:
            issues.append(f"Invalid URL format: {source_url}")
        else:
            # Check URL accessibility
            try:
                response = requests.head(source_url, timeout=5)
                if response.status_code >= 400:
                    issues.append(f"URL not accessible: {response.status_code}")
            except requests.RequestException as e:
                issues.append(f"Error accessing URL: {e}")

    return {"passed": len(issues) == 0, "issues": issues, "warnings": warnings}
```

**Output:**
- `output/insights_post_validation.json` - All insights with validation results
- `output/insights_validated.json` - Only insights that passed validation

**Validation Result Structure:**
```json
{
  "validated": true,
  "number_failed": 0,
  "checks": {
    "json_validity": {"passed": true, "issues": []},
    "schema_conformity": {"passed": true, "issues": []},
    "source_verification": {"passed": true, "issues": [], "warnings": []}
  },
  "validation_timestamp": "2025-11-28T14:30:05.000Z"
}
```

---

#### Step 4: Evaluation

**Module:** `src/core/evaluator.py`

**Input:**
- Validated insights from Step 3

**Process:**
1. For each validated insight:
   - Build evaluation prompt with 6 criteria
   - Call evaluation LLM
   - Parse evaluation scores
   - Add evaluation metadata

**Code Flow:**
```python
class InsightEvaluator:
    def __init__(self, llm, prompt_templates):
        self.llm = llm
        self.prompts = prompt_templates

    def evaluate(self, insight, cohort, insight_template, region,
                 model, temperature, max_tokens):
        # Generate evaluation prompt
        prompt = self.prompts.validation_prompt(
            insight, cohort, insight_template, region
        )

        # Call LLM
        evaluation_results = self.llm.generate(
            prompt, model, temperature, max_tokens
        )

        # Parse JSON response
        evaluation_results = self._parse_json_response(evaluation_results)

        return evaluation_results
```

**Evaluation Criteria (6 Dimensions):**
1. **Factual Accuracy** (0-10): Scientific soundness
2. **Safety** (0-10): Safe for target cohort
3. **Relevance** (0-10): Applicable to cohort's needs
4. **Actionability** (0-10): Clear and practical action
5. **Cultural Appropriateness** (0-10): Fits regional context
6. **Evidence Faithfulness** (0-10): Aligns with sources

**Output:**
- `output/insights_final.json` - Fully validated and evaluated insights

**Evaluation Result Structure:**
```json
{
  "evaluation": {
    "result": {
      "overall_score": 8.5,
      "factual_accuracy": 9,
      "safety": 10,
      "relevance": 8,
      "actionability": 8,
      "cultural_appropriateness": 9,
      "evidence_faithfulness": 8,
      "feedback": "Strong synergy message with credible source..."
    },
    "evaluation_model": "google/gemini-flash-2.5",
    "evaluation_timestamp": "2025-11-28T14:30:10.000Z"
  }
}
```

---

#### Step 5: Export & Reporting

**Module:** `src/generate_insights.py` (pipeline orchestrator)

**Input:**
- Final insights from Step 4

**Process:**
1. **CSV Export**: Convert JSON to Excel-friendly CSV
2. **Executive Summary**: Generate high-level statistics
3. **Top Insights**: Extract top 50 by score
4. **Pipeline Summary**: Aggregate statistics

**Code Flow:**
```python
def _export_to_csv(self, insights: List[Dict], output_dir: str) -> str:
    csv_file = os.path.join(output_dir, "insights_final.csv")

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Header
        writer.writerow([
            "Insight ID", "Hook", "Explanation", "Action",
            "Numeric Claim", "Source Name", "Source URL",
            "Cohort ID", "Cohort Description", "Age Group",
            "Template Type", "Validated", "Validation Issues",
            "Evaluation Score", "Generated At"
        ])

        # Data rows
        for idx, insight in enumerate(insights, 1):
            # Extract metadata
            metadata = insight.get("metadata", {})
            cohort = metadata.get("cohort", {})
            template = metadata.get("insight_template", {})

            # Extract validation
            validation = insight.get("validation", {})
            validated = validation.get("validated", False)

            # Extract evaluation
            eval_result = insight.get("evaluation", {}).get("result", {})
            eval_score = eval_result.get("overall_score", "N/A")

            writer.writerow([
                f"INS_{idx:04d}",
                insight.get("hook", ""),
                insight.get("explanation", ""),
                insight.get("action", ""),
                insight.get("numeric_claim", ""),
                insight.get("source_name", ""),
                insight.get("source_url", ""),
                cohort.get("cohort_id", ""),
                cohort.get("description", ""),
                cohort.get("cohort_params", {}).get("age_group", ""),
                template.get("type", ""),
                "Yes" if validated else "No",
                # ... validation issues
                eval_score,
                metadata.get("generation_timestamp", "")
            ])

    return csv_file
```

**Output Files:**
1. **insights_final.csv** - Excel-friendly table view
2. **executive_summary.txt** - High-level statistics
3. **top_insights.csv** - Top 50 highest-scoring insights
4. **quick_review.csv** - First 100 validated insights
5. **pipeline_summary.json** - Complete statistics

**Pipeline Summary Structure:**
```json
{
  "pipeline_config": {
    "market": "singapore",
    "generation_model": "google/gemini-flash-2.5",
    "evaluation_model": "google/gemini-flash-2.5",
    "max_cohorts": 10,
    "insights_per_call": 5
  },
  "statistics": {
    "total_cohorts": 10,
    "total_combinations": 150,
    "total_insights_generated": 750,
    "total_insights_validated": 750,
    "validation_pass_rate": 87.2,
    "total_insights_evaluated": 654,
    "average_evaluation_score": 8.2,
    "duration_seconds": 742.3
  },
  "output_files": {
    "cohorts": "output/cohorts.json",
    "raw_insights": "output/insights_raw.json",
    "validated_insights": "output/insights_validated.json",
    "final_insights": "output/insights_final.json"
  }
}
```

---

## Integration Guide

### Running the Pipeline

#### Command-Line Interface

```bash
# Basic run (all cohorts, all templates)
python src/generate_insights.py \
  --market singapore \
  --gen_model google/gemini-flash-2.5 \
  --eval_model google/gemini-flash-2.5

# Custom configuration
python src/generate_insights.py \
  --market singapore \
  --gen_model google/gemini-flash-2.5 \
  --eval_model google/gemini-flash-2.5 \
  --max_cohorts 5 \
  --insights_per_call 5 \
  --gen_temperature 0.7 \
  --gen_max_tokens 2000 \
  --output_dir output \
  --rate_limit_delay 1.0

# Skip steps for faster testing
python src/generate_insights.py \
  --max_cohorts 3 \
  --insights_per_call 3 \
  --skip_evaluation
```

#### Python API Integration

```python
from src.generate_insights import DYKPipeline

# Initialize pipeline
pipeline = DYKPipeline(
    market="singapore",
    generation_model="google/gemini-flash-2.5",
    evaluation_model="google/gemini-flash-2.5",
    generation_temperature=0.7,
    generation_max_tokens=2000
)

# Run pipeline
summary = pipeline.run(
    max_cohorts=10,
    insights_per_call=5,
    skip_validation=False,
    skip_evaluation=False,
    output_dir="output",
    rate_limit_delay=1.0
)

# Access results
print(f"Generated {summary['statistics']['total_insights_generated']} insights")
print(f"Validation pass rate: {summary['statistics']['validation_pass_rate']:.1f}%")
print(f"Average score: {summary['statistics']['average_evaluation_score']:.2f}")
```

### Environment Setup

**Required Environment Variables (.env file):**
```bash
# OpenRouter API (if using OpenRouter)
OPENROUTER_API_KEY=sk-or-v1-...

# Google AI API (if using Google directly)
GOOGLE_API_KEY=...

# PubMed API (optional - for evidence retrieval)
PUBMED_EMAIL=your@email.com
PUBMED_API_KEY=...
```

### Dependencies

**requirements.txt:**
```
pyyaml>=6.0
requests>=2.31.0
python-dotenv>=1.0
```

---

## Performance & Costs

### Cost Analysis (Gemini Flash 2.5)

**Pricing:**
- Input: $0.30 per 1M tokens
- Output: $2.50 per 1M tokens

**Full Pipeline Run:**
- 10 cohorts × 15 templates = 150 combinations
- 150 combinations × 5 insights/call = 750 insights
- **Total cost: ~$1.51**

**Breakdown:**
- Generation: $0.43
- Evaluation: $1.08

**Cost per insight:** $0.002 (0.2 cents)

### Performance Metrics

**Typical Performance:**
- Generation speed: ~5-10 insights/minute (rate-limited)
- Validation pass rate: 85-90%
- Average evaluation score: 7.5-8.5/10
- Processing time: 10-15 minutes for 750 insights

### Scaling

| Insights | Cost | Time | Use Case |
|----------|------|------|----------|
| 750 | $1.51 | 10-15 min | Full pipeline run |
| 1,500 | $3.02 | 20-30 min | Extended generation |
| 5,000 | $10.07 | 1-1.5 hours | Large campaign |
| 10,000 | $20.14 | 2-3 hours | Comprehensive dataset |

---

## Extensibility

### Adding a New Market

1. Create directory: `src/config/markets/{country}/`
2. Copy Singapore files as templates:
   - `priority_cohorts.yaml`
   - `sources.yaml`
   - `cohort_definitions.yaml`
3. Modify for new market's:
   - Demographics
   - Health priorities
   - Local health authorities
   - Cultural context

### Adding a New Insight Template

Edit `src/config/insight_templates.yaml`:

```yaml
new_template_name:
  type: "new_template_name"
  description: "What this template does"
  weight: 7
  structure: |
    [Pattern description]
  example:
    - "Example insight..."
  tone: "Required emotional tone"
```

No code changes needed! The system automatically uses new templates.

### Adding a New Cohort

Edit `src/config/singapore/priority_cohorts.yaml`:

```yaml
- name: "new_cohort_name"
  dimensions:
    age_group: ["30-44"]
    health_conditions: ["condition"]
  priority: 2
  description: "Description"
  rationale: "Why important with statistics"
  insight_angles:
    - "Angle 1"
    - "Angle 2"
```

### Custom Validation Rules

Extend `src/core/validator.py`:

```python
class InsightValidator:
    def _validate_custom_rule(self, insight: Dict) -> Dict:
        issues = []
        # Add custom validation logic
        return {"passed": len(issues) == 0, "issues": issues}

    def validate(self, insight: Dict) -> Dict:
        checks = {
            "json_validity": self._validate_json(insight),
            "schema_conformity": self._validate_schema(insight),
            "source_verification": self._validate_source(insight),
            "custom_rule": self._validate_custom_rule(insight)  # Add here
        }
        # ...
```

---

## Appendix

### A. File Structure Reference

```
dyk/
├── src/
│   ├── config/
│   │   ├── singapore/
│   │   │   ├── priority_cohorts.yaml      ← EDIT: Define cohorts
│   │   │   ├── sources.yaml               ← EDIT: Add sources
│   │   │   └── cohort_definitions.yaml
│   │   ├── health_domains.yaml            ← EDIT: Add domains
│   │   └── insight_templates.yaml         ← EDIT: Add templates
│   ├── core/
│   │   ├── cohort_generator.py            ← Step 1: Cohort generation
│   │   ├── insight_generator.py           ← Step 2: Insight generation
│   │   ├── validator.py                   ← Step 3: Validation
│   │   └── evaluator.py                   ← Step 4: Evaluation
│   ├── prompts/
│   │   └── prompt_templates.py            ← Prompt engineering
│   ├── services/
│   │   └── pubmed_service.py              ← Evidence retrieval (optional)
│   ├── utils/
│   │   └── config_loader.py               ← Configuration management
│   └── generate_insights.py               ← Main pipeline orchestrator
├── scripts/
│   ├── json_to_csv.py                     ← Convert JSON to CSV
│   ├── create_summary_view.py             ← Generate executive summary
│   └── quick_stats.py                     ← Terminal stats viewer
├── output/                                 ← Generated outputs
│   ├── cohorts.json
│   ├── insights_raw.json
│   ├── insights_validated.json
│   ├── insights_final.json
│   ├── insights_final.csv                 ← Open in Excel
│   ├── executive_summary.txt
│   ├── top_insights.csv
│   └── pipeline_summary.json
├── .env                                    ← API keys (not in git)
├── README.md                               ← User guide
├── TECHNICAL_DOCUMENTATION.md              ← This file
└── VIEWING_RESULTS.md                      ← Viewing guide
```

### B. Common Troubleshooting

| Issue | Solution |
|-------|----------|
| Rate limit errors | Reduce `--rate_limit_delay` or lower `--max_cohorts` |
| JSON parsing errors | Check LLM output format, increase `max_tokens` |
| Low validation pass rate | Review failing insights, adjust templates |
| Low evaluation scores | Refine prompts, use better LLM model |
| Slow performance | Increase `insights_per_call`, use faster model |
| High costs | Use Gemini Flash instead of larger models |

### C. Configuration Quick Reference

**To change cohorts:** Edit `src/config/singapore/priority_cohorts.yaml`
**To change templates:** Edit `src/config/insight_templates.yaml`
**To change sources:** Edit `src/config/singapore/sources.yaml`
**To change LLM model:** Use `--gen_model` parameter
**To change output location:** Use `--output_dir` parameter

### D. API Model Options

| Provider | Model Name | Cost | Quality | Speed |
|----------|-----------|------|---------|-------|
| Google AI | google/gemini-flash-2.5 | $ | High | Fast |
| Google AI | google/gemini-flash-1.5-8b | $ | Good | Very Fast |
| OpenRouter | x-ai/grok-4.1-fast | Free (limited) | Good | Medium |
| OpenRouter | anthropic/claude-3.5-sonnet | $$$ | Excellent | Medium |

**Recommendation:** Use Gemini Flash 2.5 for production (best cost/quality balance)

---

**Document Version:** 2.0
**Last Updated:** November 28, 2025
**Maintained By:** Genie Health Technical Team
**For Questions:** Refer to README.md or contact technical lead
