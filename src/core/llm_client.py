"""
LLM Client for OpenRouter API
Provides async HTTP client with rate limiting and retry logic.
"""

import asyncio
import aiohttp
import os
import time
import random
from typing import Optional


class RateLimiter:
    """Rate limiter for API calls."""

    def __init__(self, requests_per_minute: int = 60, requests_per_second: int = 10):
        self.requests_per_minute = requests_per_minute
        self.requests_per_second = requests_per_second
        self.minute_window = []
        self.second_window = []
        self.lock = asyncio.Lock()

    async def acquire(self):
        """Wait until we can make another request."""
        while True:
            async with self.lock:
                now = time.time()

                # Clean up old timestamps
                self.minute_window = [t for t in self.minute_window if now - t < 60]
                self.second_window = [t for t in self.second_window if now - t < 1]

                # Check if we can proceed
                if (
                    len(self.minute_window) < self.requests_per_minute
                    and len(self.second_window) < self.requests_per_second
                ):
                    # We're good to go!
                    self.minute_window.append(now)
                    self.second_window.append(now)
                    return

            # Need to wait - release lock and sleep
            await asyncio.sleep(0.1)


class OpenRouterClient:
    """Async client for OpenRouter API with rate limiting."""

    def __init__(
        self,
        model: str = None,
        api_key: Optional[str] = None,
        rate_limiter: Optional[RateLimiter] = None,
        max_retries: int = 3,
    ):
        if not model:
            raise ValueError("Model not specified")

        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OpenRouter API key required")

        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.default_model = model
        self.rate_limiter = rate_limiter or RateLimiter()
        self.max_retries = max_retries
        self._session = None

        # Statistics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0

    async def __aenter__(self):
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, *args):
        if self._session:
            await self._session.close()

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
    ) -> str:
        """
        Generate completion via OpenRouter (async).

        Args:
            prompt: Input prompt
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text response
        """
        if not self._session:
            raise RuntimeError("Client must be used as async context manager")

        # Wait for rate limiter
        await self.rate_limiter.acquire()

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

        # Retry logic with exponential backoff
        for attempt in range(self.max_retries):
            try:
                self.total_requests += 1

                async with self._session.post(
                    self.base_url,
                    headers=headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as response:
                    response.raise_for_status()
                    result = await response.json()
                    self.successful_requests += 1
                    return result["choices"][0]["message"]["content"]

            except Exception as e:
                self.failed_requests += 1

                # Don't retry client errors (400-499 except 429)
                if isinstance(e, aiohttp.ClientResponseError):
                    if 400 <= e.status < 500 and e.status != 429:
                        raise Exception(f"Client error {e.status}: {str(e)}")

                if attempt < self.max_retries - 1:
                    base_wait = 2**attempt  # Exponential backoff: 1s, 2s, 4s
                    jitter = random.uniform(0, 0.5 * base_wait)
                    wait_time = base_wait + jitter
                    print(
                        f"Retry {attempt + 1}/{self.max_retries} after {wait_time}s: {str(e)}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise Exception(
                        f"Failed after {self.max_retries} attempts: {str(e)}"
                    )
