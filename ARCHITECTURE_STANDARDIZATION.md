# Architecture Standardization Summary

## Overview

This document explains the standardized architecture for the DYK insight generation pipeline after refactoring.

## ✅ Completed Refactoring

### 1. File Structure

**New Infrastructure Layer:**
- **`src/core/llm_client.py`** - Centralized LLM client infrastructure
  - `RateLimiter` - API rate limiting (requests per minute/second)
  - `OpenRouterClient` - Async HTTP client with retry logic

**Renamed Core Classes:**
- **`src/core/insight_generator.py`** - `InsightGenerator` (was `AsyncInsightGenerator`)
- **`src/core/evaluator.py`** - `InsightEvaluator` (was `AsyncInsightEvaluator`)
- **`src/core/creative_rewriter.py`** - `CreativeRewriter` (was `AsyncCreativeRewriter`)

### 2. Naming Conventions

All "Async" prefixes removed for cleaner naming:

| Old Name | New Name |
|----------|----------|
| `AsyncOpenRouterClient` | `OpenRouterClient` |
| `AsyncInsightGenerator` | `InsightGenerator` |
| `AsyncInsightEvaluator` | `InsightEvaluator` |
| `AsyncCreativeRewriter` | `CreativeRewriter` |

**Rationale:** All classes use async internally, so the prefix was redundant.

### 3. Architecture Pattern: No Batch Methods

**Decision:** Batch logic lives in pipeline, NOT in classes.

#### Class Responsibility
Classes contain only **single-item async methods**:

```python
class InsightGenerator:
    async def generate(self, cohort, template, ...) -> Dict[str, Any]:
        """Generate insights for ONE cohort+template combination."""
        # Implementation
```

```python
class InsightEvaluator:
    async def evaluate(self, insight, cohort, ...) -> dict:
        """Evaluate ONE insight."""
        # Implementation
```

```python
class CreativeRewriter:
    async def rewrite(self, insight, cohort, ...) -> Dict[str, Any]:
        """Rewrite ONE insight into variations."""
        # Implementation
```

#### Pipeline Responsibility
Pipeline contains all **batch orchestration logic**:

```python
# In pipeline.py
async with OpenRouterClient(model=model) as client:
    generator = InsightGenerator(llm_client=client, ...)

    # Manual loop - explicit and flexible
    tasks = [
        generator.generate(cohort, template, ...)
        for cohort in cohorts
        for template in templates
    ]

    # Execute all in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)
```

### 4. Benefits of This Architecture

1. **Single Responsibility**
   - Classes: Process one item
   - Pipeline: Orchestrate batches

2. **Flexibility**
   - Easy to add custom error handling per batch
   - Can chunk processing (e.g., save every 100 items)
   - Mix operations (generate → filter → evaluate)

3. **Simplicity**
   - No redundant batch wrappers
   - Explicit control flow in pipeline
   - Easier to debug and understand

4. **Consistency**
   - All classes follow same pattern
   - Pipeline code is uniform across operations

## 📋 Usage Examples

### Single Item Processing

```python
async with OpenRouterClient(model="google/gemini-2.5-flash") as client:
    generator = InsightGenerator(llm_client=client, ...)

    # Process one item
    result = await generator.generate(cohort, template, ...)
```

### Batch Processing (Manual Loop)

```python
async with OpenRouterClient(model="google/gemini-2.5-flash") as client:
    generator = InsightGenerator(llm_client=client, ...)

    # Create tasks for all items
    tasks = [
        generator.generate(cohort, template, ...)
        for cohort in cohorts
        for template in templates
    ]

    # Execute all in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)
```

### Full Pipeline Pattern

```python
# STEP 1: Generate insights
async with OpenRouterClient(model=model, rate_limiter=rate_limiter) as gen_client:
    generator = InsightGenerator(llm_client=gen_client, max_concurrent=10)

    generation_tasks = [
        generator.generate(cohort, template, ...)
        for cohort in cohorts
        for template in templates
    ]

    generation_results = await asyncio.gather(*generation_tasks, return_exceptions=True)

# Process results
all_insights = []
for result in generation_results:
    if isinstance(result, dict) and "insights" in result:
        all_insights.extend(result["insights"])

# STEP 2: Rewrite insights
async with OpenRouterClient(model=model, rate_limiter=rate_limiter) as rewrite_client:
    rewriter = CreativeRewriter(llm=rewrite_client, max_concurrent=15)

    rewrite_tasks = [
        rewriter.rewrite(insight, cohort, market, num_variations=3)
        for insight, cohort in zip(all_insights, cohorts)
    ]

    rewrite_results = await asyncio.gather(*rewrite_tasks, return_exceptions=True)

# STEP 3: Evaluate variations
async with OpenRouterClient(model=model, rate_limiter=rate_limiter) as eval_client:
    evaluator = InsightEvaluator(llm=eval_client, max_concurrent=20)

    eval_tasks = [
        evaluator.evaluate(insight, cohort, template, market)
        for insight in all_variations
    ]

    eval_results = await asyncio.gather(*eval_tasks, return_exceptions=True)
```

## 🗂️ Import Structure

```python
# Standard imports
from src.core.llm_client import OpenRouterClient, RateLimiter
from src.core.insight_generator import InsightGenerator
from src.core.evaluator import InsightEvaluator
from src.core.creative_rewriter import CreativeRewriter
from src.core.cohort_generator import CohortGenerator
from src.prompts.prompt_templates import PromptTemplates
from src.utils.config_loader import ConfigLoader
```

## 🎯 Best Practices

### 1. Always Use Context Managers

```python
# GOOD ✓
async with OpenRouterClient(model=model) as client:
    # Use client here

# BAD ✗
client = OpenRouterClient(model=model)
# Might not close properly
```

### 2. Share Rate Limiter

```python
# GOOD ✓ - Shared rate limiter across all operations
rate_limiter = RateLimiter(requests_per_minute=60, requests_per_second=10)

async with OpenRouterClient(model=model, rate_limiter=rate_limiter) as gen_client:
    # Generation

async with OpenRouterClient(model=model, rate_limiter=rate_limiter) as eval_client:
    # Evaluation
```

### 3. Handle Exceptions

```python
results = await asyncio.gather(*tasks, return_exceptions=True)

for result in results:
    if isinstance(result, Exception):
        print(f"Task failed: {result}")
    else:
        # Process result
```

### 4. Use Semaphores for Concurrency Control

```python
# Classes handle this internally via max_concurrent parameter
generator = InsightGenerator(
    llm_client=client,
    max_concurrent=10  # Only 10 generations run simultaneously
)
```

## 📊 Concurrency Guidelines

| Component | Recommended `max_concurrent` | Notes |
|-----------|------------------------------|-------|
| `InsightGenerator` | 10 | Safe default, increase to 15-20 if API allows |
| `InsightEvaluator` | 20 | Evaluation is faster than generation |
| `CreativeRewriter` | 15 | Balance between speed and quality |
| `RateLimiter` | 60/min, 10/sec | Adjust based on API tier |

## 🔧 Troubleshooting

### Rate Limit Errors

**Symptom:** 429 errors or "rate limit exceeded"

**Solution:** Reduce concurrency or increase rate limiter limits:
```python
# Reduce concurrency
generator = InsightGenerator(llm_client=client, max_concurrent=5)

# Or adjust rate limiter
rate_limiter = RateLimiter(requests_per_minute=30, requests_per_second=5)
```

### Slow Processing

**Symptom:** Pipeline takes too long

**Solution:** Increase concurrency (if API allows):
```python
generator = InsightGenerator(llm_client=client, max_concurrent=20)
evaluator = InsightEvaluator(llm=client, max_concurrent=30)
```

### Memory Issues

**Symptom:** Out of memory with large batches

**Solution:** Process in chunks:
```python
chunk_size = 100
for i in range(0, len(all_items), chunk_size):
    chunk = all_items[i:i + chunk_size]
    tasks = [generator.generate(...) for item in chunk]
    results = await asyncio.gather(*tasks)
    # Save results before processing next chunk
```

## 📝 Migration Guide

### If You Have Old Code

**Old pattern (with batch methods):**
```python
results = await generator.generate_batch(cohorts, templates, ...)
```

**New pattern (manual loop):**
```python
tasks = [
    generator.generate(cohort, template, ...)
    for cohort in cohorts
    for template in templates
]
results = await asyncio.gather(*tasks, return_exceptions=True)
```

### Files to Delete

After confirming everything works, delete these obsolete files:
- `src/core/insight_generator_async.py`
- `src/core/evaluator_async.py`

## 📊 Metadata Management

### Two-Level Metadata Structure

**Don't attach everything to every insight!** Use a two-level structure:

```json
{
  "generation_metadata": {
    "market": "singapore",
    "generation_model": "google/gemini-2.5-flash",
    "generation_temperature": 0.7,
    "max_tokens": 4000,
    "generated_at": "2025-12-02T10:30:00",
    "num_cohorts": 5,
    "num_templates": 3,
    "total_calls": 15,
    "duration_seconds": 45.2
  },
  "insights": [
    {
      "hook": "...",
      "cohort": "Women 30-40 with diabetes",  // Varies per insight
      "insight_template": "hidden_consequence" // Varies per insight
    }
  ]
}
```

**Why?**
- **Top-level**: Model, temperature, max_tokens are **same for all** → Store once
- **Per-insight**: Only what **varies**: cohort, template → Attach to each
- Saves file size, reduces redundancy

### Example in Pipeline:

```python
# After processing all results
output_data = {
    "generation_metadata": {
        "market": self.market,
        "generation_model": self.generation_model,
        "generated_at": datetime.now().isoformat(),
        "pipeline_stats": self.stats,
    },
    "insights": all_insights  # Only per-insight metadata attached
}

with open(output_file, "w") as f:
    json.dump(output_data, f, indent=2, ensure_ascii=False)
```

## 🎉 Summary

The standardized architecture provides:
- ✅ Clear separation of concerns (classes vs pipeline)
- ✅ Consistent patterns across all components
- ✅ Maximum flexibility for pipeline orchestration
- ✅ Efficient two-level metadata structure
- ✅ Cleaner, more maintainable code
- ✅ Easier to understand and debug

All imports have been updated, and the codebase is now standardized!
