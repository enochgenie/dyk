# Creative Rewriting Layer Guide

This guide shows how to use the async creative rewriting layer to generate diverse variations of insights while preserving factual accuracy.

## 📁 Files Created

1. **`src/core/creative_rewriter.py`** - Creative rewriting with concurrency control
2. **`src/prompts/prompt_templates.py`** - Added `creative_rewriting_prompt()` method

## 🎯 Purpose

The creative rewriting layer:
- **Generates multiple variations** of each insight (3-5 variations per insight)
- **Preserves factual accuracy** - all numbers, statistics, and sources remain unchanged
- **Adds linguistic diversity** - different sentence structures, vocabulary, and emphasis
- **Enables A/B testing** - test which phrasing resonates best with users
- **Increases content pool** - 3x-5x more insights for better variety

## 🚀 Quick Start

### Basic Usage (Single Insight)

```python
import asyncio
from src.core.llm_client import OpenRouterClient
from src.core.creative_rewriter import CreativeRewriter
from src.prompts.prompt_templates import PromptTemplates
from src.utils.config_loader import ConfigLoader

async def rewrite_single_insight():
    # Load config
    loader = ConfigLoader(market="singapore")
    cohort = loader.priority_cohorts[0]

    # Sample insight
    insight = {
        "hook": "Did you know regular exercise can reduce depression risk by 30%?",
        "explanation": "Physical activity releases endorphins that improve mood and reduce stress.",
        "action": "Aim for 150 minutes of moderate exercise weekly, like brisk walking.",
        "source_name": "Health Promotion Board",
        "source_url": "https://www.hpb.gov.sg",
        "numeric_claim": "reduce depression risk by 30%"
    }

    # Create async client and rewriter
    async with OpenRouterClient(model="google/gemini-2.5-flash") as client:
        rewriter = CreativeRewriter(
            llm=client,
            prompt_templates=PromptTemplates(),
            max_concurrent=10
        )

        # Generate 3 variations
        result = await rewriter.rewrite(
            insight=insight,
            cohort=cohort,
            market="singapore",
            num_variations=3
        )

        print(f"Original: {result['original']['hook']}")
        for i, variation in enumerate(result['variations'], 1):
            print(f"Variation {i}: {variation['hook']}")

asyncio.run(rewrite_single_insight())
```

### Batch Processing (Multiple Insights)

```python
async def rewrite_batch():
    insights = [...]  # List of insights from generation
    cohorts = [...]   # Corresponding cohorts

    async with OpenRouterClient(model="google/gemini-2.5-flash") as client:
        rewriter = CreativeRewriter(
            llm=client,
            prompt_templates=PromptTemplates(),
            max_concurrent=15  # Process 15 insights simultaneously
        )

        # Manual loop pattern - create tasks for all insights
        tasks = [
            rewriter.rewrite(insight, cohort, "singapore", num_variations=3)
            for insight, cohort in zip(insights, cohorts)
        ]

        # Execute all in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten into single list
        all_insights = rewriter.flatten_variations(
            results,
            keep_original=True  # Include originals + variations
        )

        print(f"Started with: {len(insights)} insights")
        print(f"After rewriting: {len(all_insights)} insights")
        print(f"Expansion: {len(all_insights) / len(insights):.1f}x")

asyncio.run(rewrite_batch())
```

## 🔄 Integration with Pipeline

### Where to Add in Pipeline

```
Generate Cohorts
    ↓
Generate Insights (Async)
    ↓
✨ Creative Rewriting (Async) ← ADD HERE
    ↓
Validation (Optional)
    ↓
Evaluation (Async)
    ↓
Deduplication
    ↓
Save Results
```

### Example Pipeline Integration

```python
from src.core.llm_client import OpenRouterClient
from src.core.insight_generator import InsightGenerator
from src.core.creative_rewriter import CreativeRewriter
from src.core.evaluator import InsightEvaluator
from src.prompts.prompt_templates import PromptTemplates
from src.utils.config_loader import ConfigLoader

async def run_pipeline_with_rewriting():
    market = "singapore"
    model = "google/gemini-2.5-flash"
    loader = ConfigLoader(market=market)

    # STEP 1: Generate insights
    print("[STEP 1] Generating insights...")
    async with OpenRouterClient(model=model) as gen_client:
        generator = InsightGenerator(
            llm_client=gen_client,
            prompt_template=PromptTemplates(),
            max_concurrent=10
        )

        # Generate insights for all cohorts × templates
        generation_tasks = [...]
        generation_results = await asyncio.gather(*generation_tasks)

        # Extract insights
        original_insights = []
        for result in generation_results:
            if "insights" in result:
                original_insights.extend(result["insights"])

    print(f"✓ Generated {len(original_insights)} original insights\n")

    # STEP 2: Creative rewriting
    print("[STEP 2] Creating variations...")
    async with OpenRouterClient(model=model) as rewrite_client:
        rewriter = CreativeRewriter(
            llm=rewrite_client,
            prompt_templates=PromptTemplates(),
            max_concurrent=15
        )

        # Prepare cohorts list
        cohorts = [insight.get("metadata", {}).get("cohort")
                  for insight in original_insights]

        # Manual loop pattern - create tasks for all insights
        rewrite_tasks = [
            rewriter.rewrite(insight, cohort, market, num_variations=3)
            for insight, cohort in zip(original_insights, cohorts)
        ]

        # Execute all in parallel
        rewrite_results = await asyncio.gather(*rewrite_tasks, return_exceptions=True)

        # Flatten variations
        all_insights = rewriter.flatten_variations(
            rewrite_results,
            keep_original=False  # Only keep variations, not originals
        )

    print(f"✓ Created {len(all_insights)} total insights (3x expansion)\n")

    # STEP 3: Evaluate all insights (originals + variations)
    print("[STEP 3] Evaluating insights...")
    async with OpenRouterClient(model=model) as eval_client:
        evaluator = InsightEvaluator(
            llm=eval_client,
            prompt_templates=PromptTemplates(),
            max_concurrent=20
        )

        # Evaluate all
        eval_tasks = [...]
        eval_results = await asyncio.gather(*eval_tasks)

    print(f"✓ Evaluated {len(eval_results)} insights\n")

    # STEP 4: Filter and save
    # ... rest of pipeline

asyncio.run(run_pipeline_with_rewriting())
```

## ⚙️ Configuration Parameters

### CreativeRewriter

```python
CreativeRewriter(
    llm=client,                   # OpenRouterClient instance
    prompt_templates=templates,   # PromptTemplates instance
    max_concurrent=15,            # Max parallel rewrites (default: 15)
)
```

**Tuning `max_concurrent`:**
- **Start with 15**: Balanced default
- **Increase to 20-30**: If API allows higher throughput
- **Decrease to 10**: If hitting rate limits

### rewrite() and rewrite_batch()

```python
await rewriter.rewrite(
    insight=insight,
    cohort=cohort,
    market="singapore",
    num_variations=3,        # Number of variations (default: 3)
    model=None,              # Optional model override
    temperature=0.8,         # Higher for creativity (default: 0.8)
    max_tokens=4000,         # Max response tokens
)
```

**Tuning `num_variations`:**
- **1-2 variations**: Minimal expansion, faster processing
- **3 variations**: Good balance (default)
- **4-5 variations**: Maximum diversity, longer processing

**Tuning `temperature`:**
- **0.7**: More conservative variations
- **0.8**: Balanced creativity (default)
- **0.9-1.0**: More creative but riskier

## 📊 Performance Impact

### Processing Time

| Insights | Without Rewriting | With Rewriting (3x) | Overhead |
|----------|------------------|---------------------|----------|
| 100 | ~10s | ~20s | +10s (50%) |
| 500 | ~50s | ~100s | +50s (50%) |
| 1000 | ~100s | ~200s | +100s (50%) |

**Note**: Rewriting adds ~50% overhead but increases content pool by 3-4x.

### Output Volume

| Input | num_variations | keep_original | Output | Expansion |
|-------|---------------|---------------|--------|-----------|
| 100 | 3 | True | 400 | 4x |
| 100 | 3 | False | 300 | 3x |
| 100 | 5 | True | 600 | 6x |
| 100 | 5 | False | 500 | 5x |

## 🎨 Example Variations

### Original Insight
```
Hook: "Did you know that walking 30 minutes daily can reduce heart disease risk by 25%?"
Explanation: "Regular walking strengthens your heart, improves circulation, and helps maintain healthy blood pressure."
Action: "Start with a 10-minute walk after meals and gradually increase to 30 minutes daily."
```

### Variation 1 (Different Structure)
```
Hook: "Did you know just 30 minutes of daily walking cuts your heart disease risk by a quarter?"
Explanation: "This simple activity boosts heart strength, enhances blood flow, and keeps your blood pressure in check."
Action: "Begin with short 10-minute post-meal walks, then work up to a full 30 minutes each day."
```

### Variation 2 (Different Emphasis)
```
Hook: "Did you know dedicating half an hour to walking each day lowers heart disease risk by 25%?"
Explanation: "Walking regularly fortifies your cardiovascular system, improves circulation, and supports healthy blood pressure levels."
Action: "Try brief 10-minute walks following each meal, building toward a consistent 30-minute daily routine."
```

### Variation 3 (Different Vocabulary)
```
Hook: "Did you know a simple 30-minute daily walk can slash your heart disease risk by 25%?"
Explanation: "This accessible exercise reinforces heart health, promotes better circulation, and helps regulate blood pressure."
Action: "Ease into it with 10-minute walks after eating, gradually extending to 30 minutes per day."
```

**Key Observations:**
- All preserve "30 minutes", "daily", "25%"
- Different word choices: "cuts", "lowers", "slash"
- Different framing: "quarter", "25%"
- All maintain factual accuracy

## 🔧 Troubleshooting

### Issue: Variations too similar

**Solution:** Increase temperature
```python
await rewriter.rewrite(
    ...,
    temperature=0.9  # Increase from 0.8
)
```

### Issue: Factual errors in variations

**Solution 1:** Lower temperature for more faithful rewriting
```python
temperature=0.7  # Decrease from 0.8
```

**Solution 2:** Add validation step after rewriting to filter out inaccurate variations

### Issue: Slow processing

**Solution:** Increase concurrency
```python
rewriter = AsyncCreativeRewriter(
    ...,
    max_concurrent=20  # Increase from 15
)
```

## 🎯 Best Practices

1. **Always validate variations** after rewriting to ensure factual accuracy
2. **Use lower temperature (0.7-0.8)** for medical/health content
3. **Generate 3-4 variations** per insight for optimal diversity/cost balance
4. **Keep originals** during evaluation to compare against variations
5. **Filter by evaluation score** to remove poor variations
6. **Track variation_id** to identify which variations perform best in A/B tests

## 📝 Testing

Run the test file to verify everything works:

```bash
python src/core/creative_rewriter.py
```

This will:
- Rewrite 2 sample insights
- Generate 3 variations each
- Display timing statistics
- Show example variations

## 🆘 Need Help?

Check the inline documentation:
- `creative_rewriter.py` - Lines 1-25
- `prompt_templates.py` - Lines 206-308 (creative_rewriting_prompt method)
