"""
Insight Deduplication System for DYK Module
Implements cohort-aware deduplication at both generation and serving stages
"""

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class InsightDeduplicator:
    """
    Handles deduplication of health insights using semantic similarity
    and cohort overlap analysis
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        hook_weight: float = 0.4,
        explanation_weight: float = 0.2,
        action_weight: float = 0.4,
    ):
        """
        Initialize the deduplicator with a sentence transformer model

        Args:
            model_name: HuggingFace model name for embeddings
            hook_weight: Weight for hook similarity (0-1)
            action_weight: Weight for action similarity (0-1)
            explanation_weight: Weight for explanation similarity (0-1)
        """

        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.component_cache = {}
        logger.info("Embedding model loaded successfully")

        # Validate weights
        total_weight = hook_weight + action_weight + explanation_weight
        if not np.isclose(total_weight, 1.0):
            logger.warning(f"Weights sum to {total_weight}, normalizing to 1.0")
            hook_weight /= total_weight
            action_weight /= total_weight
            explanation_weight /= total_weight

        self.hook_weight = hook_weight
        self.action_weight = action_weight
        self.explanation_weight = explanation_weight

        logger.info(
            f"Weights - Hook: {self.hook_weight:.2f}, "
            f"Action: {self.action_weight:.2f}, "
            f"Explanation: {self.explanation_weight:.2f}"
        )
        logger.info("Embedding model loaded successfully")

    def calculate_content_similarity(
        self, insight1: Dict, insight2: Dict, return_components: bool = False
    ) -> float:
        """
        Calculate semantic similarity between two insights

        Compares each component (hook, action, explanation) separately,
        then combines using weighted average.

        Args:
            insight1: First insight dict with 'hook', 'action', 'explanation'
            insight2: Second insight dict
            return_components: If True, return dict with component similarities

        Returns:
            Similarity score between 0 and 1 (or dict if return_components=True)
        """
        # Get similarity for each component
        hook_sim = self._get_component_similarity(insight1["hook"], insight2["hook"])

        action_sim = self._get_component_similarity(
            insight1["action"], insight2["action"]
        )

        explanation_sim = self._get_component_similarity(
            insight1["explanation"], insight2["explanation"]
        )

        # Weighted combination
        total_similarity = (
            self.hook_weight * hook_sim
            + self.action_weight * action_sim
            + self.explanation_weight * explanation_sim
        )

        if return_components:
            return {
                "total": float(total_similarity),
                "hook": float(hook_sim),
                "action": float(action_sim),
                "explanation": float(explanation_sim),
            }

        return float(total_similarity)

    def _get_component_similarity(self, text1: str, text2: str) -> float:
        """
        Get similarity between two text components with caching

        Args:
            text1: First text string
            text2: Second text string

        Returns:
            Cosine similarity between 0 and 1
        """
        emb1 = self._get_component_embedding(text1)
        emb2 = self._get_component_embedding(text2)

        similarity = cosine_similarity([emb1], [emb2])[0][0]
        return float(similarity)

    def _get_component_embedding(self, text: str) -> np.ndarray:
        """
        Get cached embedding for a text component

        Args:
            text: Text string to embed

        Returns:
            Numpy array embedding
        """
        if text not in self.component_cache:
            self.component_cache[text] = self.model.encode(text)
        return self.component_cache[text]


if __name__ == "__main__":
    deduplicator = InsightDeduplicator()
    insight1 = {
        "hook": "Did you know standing for 3 minutes every 30 minutes of sitting improves insulin levels by 32%?",
        "explanation": "Breaks prolonged sitting, a key driver of cardiometabolic risks like high blood pressure and lipids in overweight office workers.",
        "action": "Set a phone timer to stand and do light marches for 3 minutes every 30 minutes at your desk.",
    }

    insight2 = {
        "hook": "Did you know standing for 30 minutes every hour at your desk improves blood flow by 20% and cuts fatigue?",
        "explanation": "These micro-breaks disrupt prolonged sitting, enhancing circulation and metabolic markers for desk-bound professionals without extra time.",
        "action": "Use a timer to stand, stretch, and shift weight for 30 minutes hourly during work.",
    }

    gemini1 = {
        "hook": "Did you know prolonged sitting increases your risk of premature death by up to 50%?",
        "explanation": "Sedentary behaviour significantly raises the risk of cardiovascular disease, type 2 diabetes, and certain cancers, even if you exercise regularly.",
        "action": "Break up sitting every 30 minutes with 2-3 minutes of light activity, like standing or walking.",
    }

    gemini2 = {
        "hook": "Did you know prolonged sitting increases your risk of premature death by up to 15%?",
        "explanation": "Sitting for 8+ hours daily, common in desk jobs, significantly slows metabolism and impacts blood sugar regulation.",
        "action": "Set a timer to stand and move for 2-5 minutes every hour to break up sitting time.",
    }

    total_similarity = deduplicator.calculate_content_similarity(
        gemini1, gemini2, return_components=True
    )
    print(total_similarity)
