"""
Async Batch Insight Generator
High-performance insight generation with batching, async, rate limiting, and error handling.
"""

import os
import json
import time
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dyk.src.prompts.prompt_templates_old import PromptTemplates, RegionSpecificPrompts
from services.pubmed_service import EvidenceRetriever


class RateLimiter:
    """Rate limiter for API calls with configurable limits."""

    def __init__(self, requests_per_minute: int = 60, requests_per_second: int = 10):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Maximum requests per minute
            requests_per_second: Maximum requests per second
        """
        self.rpm = requests_per_minute
        self.rps = requests_per_second
        self.minute_window = []
        self.second_window = []
        self.lock = asyncio.Lock()

    async def acquire(self):
        """Acquire permission to make a request, waiting if necessary."""
        async with self.lock:
            now = time.time()

            # Clean old entries
            self.minute_window = [t for t in self.minute_window if now - t < 60]
            self.second_window = [t for t in self.second_window if now - t < 1]

            # Check if we need to wait
            while len(self.minute_window) >= self.rpm:
                wait_time = 60 - (now - self.minute_window[0])
                await asyncio.sleep(wait_time)
                now = time.time()
                self.minute_window = [t for t in self.minute_window if now - t < 60]

            while len(self.second_window) >= self.rps:
                wait_time = 1 - (now - self.second_window[0])
                await asyncio.sleep(wait_time)
                now = time.time()
                self.second_window = [t for t in self.second_window if now - t < 1]

            # Record this request
            self.minute_window.append(now)
            self.second_window.append(now)


class AsyncOpenRouterClient:
    """Async client for OpenRouter API with rate limiting and retry logic."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        requests_per_minute: int = 60,
        max_retries: int = 3,
        retry_delay: float = 2.0
    ):
        """
        Initialize async OpenRouter client.

        Args:
            api_key: OpenRouter API key
            requests_per_minute: Rate limit
            max_retries: Maximum retry attempts for failed requests
            retry_delay: Initial delay between retries (exponential backoff)
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OpenRouter API key required")

        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.default_model = "x-ai/grok-beta"
        self.rate_limiter = RateLimiter(requests_per_minute=requests_per_minute)
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Statistics
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "retried_requests": 0,
            "total_tokens": 0,
        }

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """
        Generate completion via OpenRouter with retry logic.

        Args:
            prompt: Input prompt
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text response
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://dyk-health-insights.com",
        }

        data = {
            "model": model or self.default_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        for attempt in range(self.max_retries):
            try:
                # Wait for rate limit
                await self.rate_limiter.acquire()

                # Make request
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.base_url,
                        headers=headers,
                        json=data,
                        timeout=aiohttp.ClientTimeout(total=60)
                    ) as response:
                        self.stats["total_requests"] += 1

                        if response.status == 200:
                            result = await response.json()
                            self.stats["successful_requests"] += 1

                            # Track token usage
                            if "usage" in result:
                                self.stats["total_tokens"] += result["usage"].get("total_tokens", 0)

                            return result["choices"][0]["message"]["content"]

                        elif response.status == 429:  # Rate limit
                            if attempt < self.max_retries - 1:
                                wait_time = self.retry_delay * (2 ** attempt)
                                print(f"Rate limited, waiting {wait_time}s before retry...")
                                await asyncio.sleep(wait_time)
                                self.stats["retried_requests"] += 1
                                continue
                            else:
                                raise Exception(f"Rate limit exceeded after {self.max_retries} retries")

                        else:
                            error_text = await response.text()
                            raise Exception(f"API error {response.status}: {error_text}")

            except asyncio.TimeoutError:
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    print(f"Request timeout, retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    self.stats["retried_requests"] += 1
                    continue
                else:
                    raise

            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    print(f"Request failed: {e}, retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    self.stats["retried_requests"] += 1
                    continue
                else:
                    self.stats["failed_requests"] += 1
                    raise

        self.stats["failed_requests"] += 1
        raise Exception(f"Failed after {self.max_retries} attempts")

    def get_stats(self) -> Dict[str, Any]:
        """Get API usage statistics."""
        return {
            **self.stats,
            "success_rate": (
                self.stats["successful_requests"] / self.stats["total_requests"] * 100
                if self.stats["total_requests"] > 0 else 0
            )
        }


class AsyncBatchInsightGenerator:
    """High-performance batch insight generator with async support."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        pubmed_email: Optional[str] = None,
        pubmed_api_key: Optional[str] = None,
        model: str = "x-ai/grok-beta",
        requests_per_minute: int = 60,
        max_concurrent: int = 10,
    ):
        """
        Initialize async batch insight generator.

        Args:
            api_key: OpenRouter API key
            pubmed_email: Email for PubMed API
            pubmed_api_key: Optional PubMed API key
            model: LLM model to use
            requests_per_minute: Rate limit for API calls
            max_concurrent: Maximum concurrent API calls
        """
        self.llm = AsyncOpenRouterClient(
            api_key=api_key,
            requests_per_minute=requests_per_minute
        )
        self.evidence_retriever = EvidenceRetriever(pubmed_email, pubmed_api_key)
        self.model = model
        self.templates = PromptTemplates()
        self.max_concurrent = max_concurrent

        # Statistics
        self.generation_stats = {
            "total_batches": 0,
            "total_insights": 0,
            "successful_insights": 0,
            "failed_insights": 0,
        }

    def _create_batch_prompt(
        self,
        cohort_spec: Dict[str, Any],
        template_type: str,
        health_domain: str,
        region: str,
        num_insights: int,
    ) -> str:
        """
        Create prompt for generating multiple insights in one API call.

        Args:
            cohort_spec: Cohort specification
            template_type: Type of insight template
            health_domain: Health domain to focus on
            region: Target region
            num_insights: Number of insights to generate

        Returns:
            Batch generation prompt
        """
        cohort_description = cohort_spec["description"]
        cohort_params = cohort_spec["cohort_params"]

        base_prompt = f"""You are a medical and public health expert generating evidence-based health insights.

TARGET COHORT:
{cohort_description}

Cohort Parameters: {cohort_params}
Region: {region}
Health Domain: {health_domain}
Template Type: {template_type}

TASK:
Generate {num_insights} DIVERSE health insights for this cohort, all focused on the {health_domain} domain.
Each insight must be:
1. Evidence-based and scientifically accurate
2. Highly relevant to this specific demographic
3. Actionable and motivating
4. Culturally appropriate for {region}
5. DIFFERENT from the other insights (diverse angles/topics within the domain)

IMPORTANT: Generate {num_insights} DISTINCT insights - avoid repetition or similar content.

OUTPUT FORMAT (JSON array with {num_insights} insights):
[
  {{
    "hook": "Compelling fact starting with 'Did you know...' (max 20 words)",
    "explanation": "Evidence-based explanation specific to cohort (40-60 words)",
    "action": "Specific, actionable step (20-30 words)",
    "source_name": "Authoritative source (WHO, CDC, HPB, peer-reviewed journal)",
    "source_url": "URL if available or 'general medical knowledge'",
    "health_domain": "{health_domain}",
    "confidence": "high/medium/low",
    "numeric_claim": "Any specific numeric claim made",
    "diversity_angle": "Brief note on what makes this insight unique from the others"
  }},
  ... ({num_insights} total insights)
]
"""

        # Add region-specific context
        if region == "singapore":
            base_prompt += RegionSpecificPrompts.singapore_context()
        else:
            base_prompt += RegionSpecificPrompts.global_context()

        base_prompt += f"""

CRITICAL REQUIREMENTS:
- Generate EXACTLY {num_insights} insights
- Each insight must be DISTINCT (different aspect of {health_domain})
- Be specific to the cohort's characteristics
- Use actual statistics when possible (but be accurate)
- Cite reputable sources
- Keep language clear and motivating

DO NOT:
- Generate similar or repetitive insights
- Make up statistics or data
- Use vague insights that could apply to anyone
- Include medical diagnosis/treatment advice
- Use fear-mongering language

Return ONLY a valid JSON array with {num_insights} insights, no additional text.
"""

        return base_prompt

    async def generate_batch(
        self,
        cohort_spec: Dict[str, Any],
        template_type: str,
        health_domain: str,
        region: str,
        num_insights: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Generate multiple insights in a single API call.

        Args:
            cohort_spec: Cohort specification
            template_type: Type of insight template
            health_domain: Health domain
            region: Target region
            num_insights: Number of insights to generate

        Returns:
            List of generated insights
        """
        prompt = self._create_batch_prompt(
            cohort_spec, template_type, health_domain, region, num_insights
        )

        try:
            response = await self.llm.generate(
                prompt,
                model=self.model,
                temperature=0.8  # Higher temp for diversity
            )

            # Parse JSON array response
            insights = self._parse_json_array_response(response)

            # Add metadata to each insight
            for insight in insights:
                insight["cohort_id"] = cohort_spec["cohort_id"]
                insight["cohort_params"] = cohort_spec["cohort_params"]
                insight["generation_method"] = "batch_async"
                insight["model_used"] = self.model
                insight["template_type"] = template_type
                insight["region"] = region
                insight["batch_size"] = num_insights

            self.generation_stats["successful_insights"] += len(insights)
            return insights

        except Exception as e:
            print(f"Error generating batch: {e}")
            self.generation_stats["failed_insights"] += num_insights
            return []

    async def generate_batch_for_cohorts(
        self,
        cohort_specs: List[Dict[str, Any]],
        template_types: List[str],
        health_domains: List[str],
        region: str = "singapore",
        insights_per_combination: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Generate insights for multiple cohorts using async batching.

        Args:
            cohort_specs: List of cohort specifications
            template_types: List of template types to use
            health_domains: List of health domains to cover
            region: Target region
            insights_per_combination: Insights per cohort×template×domain combination

        Returns:
            List of all generated insights
        """
        print(f"\n{'=' * 80}")
        print("ASYNC BATCH INSIGHT GENERATION")
        print(f"{'=' * 80}")
        print(f"Cohorts: {len(cohort_specs)}")
        print(f"Template types: {len(template_types)}")
        print(f"Health domains: {len(health_domains)}")
        print(f"Insights per combination: {insights_per_combination}")

        total_combinations = len(cohort_specs) * len(template_types) * len(health_domains)
        total_expected = total_combinations * insights_per_combination
        print(f"Total combinations: {total_combinations}")
        print(f"Expected insights: {total_expected}")
        print(f"{'=' * 80}\n")

        # Create all batch generation tasks
        tasks = []
        for cohort in cohort_specs:
            for template in template_types:
                for domain in health_domains:
                    task = self.generate_batch(
                        cohort_spec=cohort,
                        template_type=template,
                        health_domain=domain,
                        region=region,
                        num_insights=insights_per_combination,
                    )
                    tasks.append(task)

        # Execute tasks with concurrency limit
        all_insights = []
        completed = 0
        start_time = time.time()

        # Process in chunks to respect max_concurrent
        for i in range(0, len(tasks), self.max_concurrent):
            chunk = tasks[i:i + self.max_concurrent]
            chunk_results = await asyncio.gather(*chunk, return_exceptions=True)

            for result in chunk_results:
                if isinstance(result, Exception):
                    print(f"Task failed with error: {result}")
                    self.generation_stats["failed_insights"] += insights_per_combination
                else:
                    all_insights.extend(result)

                completed += 1
                if completed % 10 == 0:
                    elapsed = time.time() - start_time
                    rate = completed / elapsed if elapsed > 0 else 0
                    remaining = len(tasks) - completed
                    eta = remaining / rate if rate > 0 else 0
                    print(f"Progress: {completed}/{len(tasks)} batches ({rate:.1f} batches/s, ETA: {eta:.0f}s)")

        elapsed = time.time() - start_time

        # Update statistics
        self.generation_stats["total_batches"] = len(tasks)
        self.generation_stats["total_insights"] = len(all_insights)

        print(f"\n{'=' * 80}")
        print("GENERATION COMPLETE")
        print(f"{'=' * 80}")
        print(f"Total time: {elapsed:.1f}s")
        print(f"Batches processed: {len(tasks)}")
        print(f"Insights generated: {len(all_insights)}/{total_expected}")
        print(f"Average batch time: {elapsed/len(tasks):.2f}s")
        print(f"Insights per second: {len(all_insights)/elapsed:.1f}")
        print(f"{'=' * 80}\n")

        return all_insights

    def _parse_json_array_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse JSON array from LLM response."""
        # Remove markdown code blocks
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]

        response = response.strip()

        try:
            parsed = json.loads(response)
            if not isinstance(parsed, list):
                raise ValueError("Expected JSON array")
            return parsed
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(f"Response: {response[:500]}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics."""
        return {
            "generation": self.generation_stats,
            "api": self.llm.get_stats(),
        }


def save_insights(insights: List[Dict[str, Any]], output_path: str):
    """Save generated insights to JSON file."""
    timestamp = datetime.now().isoformat()

    output = {
        "generated_at": timestamp,
        "total_insights": len(insights),
        "insights": insights,
    }

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nSaved {len(insights)} insights to {output_path}")


# Example usage
if __name__ == "__main__":
    async def main():
        # Initialize generator
        generator = AsyncBatchInsightGenerator(
            pubmed_email="researcher@example.com",
            requests_per_minute=60,
            max_concurrent=10,
        )

        # Example cohorts
        cohorts = [
            {
                "cohort_id": "cohort_0001",
                "cohort_params": {"age_group": "40-49", "gender": "male"},
                "description": "40-49 years old, male",
            },
            {
                "cohort_id": "cohort_0002",
                "cohort_params": {"age_group": "50-59", "gender": "female"},
                "description": "50-59 years old, female",
            },
        ]

        # Generate insights
        insights = await generator.generate_batch_for_cohorts(
            cohort_specs=cohorts,
            template_types=["risk_amplification", "protective_factors"],
            health_domains=["cardiovascular", "metabolic"],
            region="singapore",
            insights_per_combination=3,
        )

        # Save results
        save_insights(insights, "output/batch_insights.json")

        # Print stats
        print("\nGeneration Statistics:")
        print(json.dumps(generator.get_stats(), indent=2))

    # Run async main
    asyncio.run(main())
