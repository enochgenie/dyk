import numpy as np
from typing import List, Dict, Optional, Tuple
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


class ThresholdTuner:
    """
    Interactive threshold tuner for similarity analysis.

    Samples insight pairs at different similarity ranges for manual review.
    """

    def __init__(
        self,
        insights: List[Dict],
        weights: Optional[Dict[str, float]] = None,
        model_name: str = "all-MiniLM-L6-v2",
        random_seed: int = 42,
    ):
        """
        Initialize ThresholdTuner

        Args:
            insights: List of insight dictionaries
            weights: Component weights, default {'hook': 0.4, 'action': 0.4, 'explanation': 0.2}
            model_name: Sentence transformer model name
            random_seed: Random seed for reproducibility
        """
        self.insights = insights
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.weights = weights or {"hook": 0.4, "action": 0.4, "explanation": 0.2}
        self.embeddings = self.compute_embeddings(show_progress=True)
        self.similarity_matrix = self._compute_weighted_similarity()

    def compute_embeddings(self, show_progress: bool = True):
        """
        Generate embeddings for all insights

        Args:
            show_progress: Show progress bar during encoding

        Returns:
            self (for method chaining)
        """
        print(f"Generating embeddings for {len(self.insights)} insights...")

        # Extract text components
        full_texts = [
            f"{ins.get('hook', '')} {ins.get('explanation', '')} {ins.get('action', '')}"
            for ins in self.insights
        ]
        hooks = [ins.get("hook", "") for ins in self.insights]
        explanations = [ins.get("explanation", "") for ins in self.insights]
        actions = [ins.get("action", "") for ins in self.insights]

        # Generate embeddings
        embeddings = {
            "full": self.model.encode(
                full_texts, show_progress_bar=show_progress, batch_size=32
            ),
            "hook": self.model.encode(
                hooks, show_progress_bar=show_progress, batch_size=32
            ),
            "explanation": self.model.encode(
                explanations, show_progress_bar=show_progress, batch_size=32
            ),
            "action": self.model.encode(
                actions, show_progress_bar=show_progress, batch_size=32
            ),
        }

        print(f"✓ Embeddings generated: {embeddings['full'].shape}")
        return embeddings

    def _compute_weighted_similarity(self) -> np.ndarray:
        """Compute weighted similarity matrix"""
        if self.embeddings is None:
            raise ValueError("Must call compute_embeddings() first")

        # Compute similarity for each component
        hook_sim = cosine_similarity(self.embeddings["hook"])
        explanation_sim = cosine_similarity(self.embeddings["explanation"])
        action_sim = cosine_similarity(self.embeddings["action"])

        # Weighted combination
        weighted_sim = (
            self.weights["hook"] * hook_sim
            + self.weights["explanation"] * explanation_sim
            + self.weights["action"] * action_sim
        )

        return weighted_sim

    def sample_pairs(
        self, samples_per_range: int = 5, ranges: List[Tuple[float, float, str]] = None
    ) -> Dict[str, List[Tuple[int, int, float]]]:
        """
        Sample insight pairs at different similarity ranges

        Args:
            samples_per_range: Number of pairs to sample per range
            ranges: List of (min_sim, max_sim, label) tuples

        Returns:
            Dict mapping range labels to lists of (idx1, idx2, similarity) tuples
        """
        if ranges is None:
            ranges = [
                (0.95, 1.00, "Very High"),
                (0.90, 0.95, "High"),
                (0.85, 0.90, "Medium-High"),
                (0.80, 0.85, "Medium"),
                (0.75, 0.80, "Medium-Low"),
                (0.70, 0.75, "Low"),
            ]

        n = len(self.insights)
        sampled_pairs = {label: [] for _, _, label in ranges}

        # Get upper triangle indices (avoid diagonal and duplicates)
        upper_tri_i, upper_tri_j = np.triu_indices(n, k=1)
        total_pairs = len(upper_tri_i)

        print(f"Total unique pairs: {total_pairs:,}")

        # Sample from each range
        for min_sim, max_sim, label in ranges:
            # Find pairs in this similarity range using vectorized operations
            similarities = self.similarity_matrix[upper_tri_i, upper_tri_j]
            mask = (similarities >= min_sim) & (similarities < max_sim)

            # Get indices of pairs in range
            indices_in_range = np.where(mask)[0]
            count_in_range = len(indices_in_range)

            if count_in_range == 0:
                print(
                    f"\n⚠️  No pairs found in range {label} ({min_sim:.2f}-{max_sim:.2f})"
                )
                continue

            # Sample randomly
            sample_size = min(samples_per_range, count_in_range)
            sampled_indices = np.random.choice(
                indices_in_range, size=sample_size, replace=False
            )

            # Store sampled pairs
            sampled = [
                (int(upper_tri_i[idx]), int(upper_tri_j[idx]), float(similarities[idx]))
                for idx in sampled_indices
            ]
            sampled_pairs[label] = sampled

            print(
                f"{label} ({min_sim:.2f}-{max_sim:.2f}): {count_in_range:,} pairs, sampled {sample_size}"
            )

        return sampled_pairs

    def display_pair(
        self, idx1: int, idx2: int, similarity: float, pair_num: int, total: int
    ) -> None:
        """Display a pair of insights for comparison"""
        insight1 = self.insights[idx1]
        insight2 = self.insights[idx2]

        print("\n" + "=" * 80)
        print(f"PAIR {pair_num}/{total} - Similarity: {similarity:.4f}")
        print("=" * 80)

        print("\n📌 INSIGHT 1:")
        print(f"Hook: {insight1.get('hook', 'N/A')}")
        print(f"Explanation: {insight1.get('explanation', 'N/A')}")
        print(f"Action: {insight1.get('action', 'N/A')}")

        # Show metadata if available
        if "metadata" in insight1:
            cohort = insight1["metadata"].get("cohort", {}).get("cohort_id", "N/A")
            template = (
                insight1["metadata"].get("insight_template", {}).get("type", "N/A")
            )
            model = insight1["metadata"].get("generation_model", "N/A")
            print(f"[Cohort: {cohort} | Template: {template} | Model: {model}]")

        print("\n📌 INSIGHT 2:")
        print(f"Hook: {insight2.get('hook', 'N/A')}")
        print(f"Explanation: {insight2.get('explanation', 'N/A')}")
        print(f"Action: {insight2.get('action', 'N/A')}")

        # Show metadata if available
        if "metadata" in insight2:
            cohort = insight2["metadata"].get("cohort", {}).get("cohort_id", "N/A")
            template = (
                insight2["metadata"].get("insight_template", {}).get("type", "N/A")
            )
            model = insight2["metadata"].get("generation_model", "N/A")
            print(f"[Cohort: {cohort} | Template: {template} | Model: {model}]")

    def review_samples(
        self, sampled_pairs: Dict[str, List[Tuple[int, int, float]]]
    ) -> None:
        """Display sampled pairs for manual review"""
        print("\n" + "🔍 " + "=" * 76)
        print("SIMILARITY THRESHOLD TUNING - MANUAL REVIEW")
        print("=" * 78)
        print("\nReview the pairs below and decide:")
        print("- Which similarity level represents 'duplicate' insights?")
        print("- Look for where duplicates START to appear")
        print("\n")

        for label, pairs in sampled_pairs.items():
            if not pairs:
                continue

            print(f"\n{'=' * 80}")
            print(f"🎯 {label.upper()} SIMILARITY RANGE")
            print(f"{'=' * 80}")

            for idx, (i, j, sim) in enumerate(pairs, 1):
                self.display_pair(i, j, sim, idx, len(pairs))

        print("\n" + "=" * 80)
        print("REVIEW COMPLETE")
        print("=" * 80)
        print("\n💡 RECOMMENDATIONS:")
        print("- If pairs at 0.90-0.95 look like duplicates → use threshold 0.90")
        print("- If pairs at 0.85-0.90 look like duplicates → use threshold 0.85")
        print("- If pairs at 0.80-0.85 look like duplicates → use threshold 0.80")
        print("\nChoose the threshold where you START seeing duplicates.")


if __name__ == "__main__":
    import json
    from pathlib import Path

    src_dir = Path(__file__).parent.parent.parent
    with open(src_dir / "output" / "insights_singapore_20251202_163904.json") as f:
        insights = json.load(f)["insights"]

    tuner = ThresholdTuner(insights)
    sampled_pairs = tuner.sample_pairs(samples_per_range=3)
    tuner.review_samples(sampled_pairs)
