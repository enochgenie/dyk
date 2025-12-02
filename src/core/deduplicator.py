"""
Deduplication

Main class for analyzing insight duplication with configurable metrics, and performing deduplication.
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import pickle

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

import networkx as nx


class InsightDeduplicator:
    """
    Analyzes insight duplication with multiple metrics and visualizations.

    Example:
        # >>> analyzer = DeduplicationAnalyzer(insights, threshold=0.85)
        # >>> analyzer.compute_embeddings()
        # >>> results = analyzer.analyze()
        # >>> model_comparison = analyzer.get_model_comparison()
    """

    def __init__(
        self,
        insights: List[Dict],
        weights: Optional[Dict[str, float]] = None,
        threshold: Optional[float] = None,
        model_name: str = "all-MiniLM-L6-v2",
        n_greedy_runs: int = 10,
        random_seed: int = 42,
    ):
        """
        Initialize DeduplicationAnalyzer

        Args:
            insights: List of insight dictionaries with 'hook', 'explanation', 'action'
            weights: Component weights, default {'hook': 0.4, 'action': 0.4, 'explanation': 0.2}
            threshold: Similarity threshold for duplicates (if None, must tune or set later)
            model_name: Sentence transformer model name
            n_greedy_runs: Number of runs for greedy deduplication averaging
            random_seed: Random seed for reproducibility
        """
        self.insights = insights
        self.weights = weights or {"hook": 0.4, "action": 0.4, "explanation": 0.2}
        self.threshold = threshold
        self.model_name = model_name
        self.n_greedy_runs = n_greedy_runs
        self.random_seed = random_seed

        # Validate weights
        total_weight = sum(self.weights.values())
        if not np.isclose(total_weight, 1.0):
            raise ValueError(f"Weights must sum to 1.0, got {total_weight}")

        # Internal state
        self._model = None
        self._embeddings = None
        self._similarity_matrix = None
        self._metadata = None
        self._results = None

    @property
    def model(self) -> SentenceTransformer:
        """Lazy load the sentence transformer model"""
        if self._model is None:
            print(f"Loading model: {self.model_name}...")
            self._model = SentenceTransformer(self.model_name)
        return self._model

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
        self._embeddings = {
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

        print(f"✓ Embeddings generated: {self._embeddings['full'].shape}")
        return self

    def _compute_weighted_similarity(self) -> np.ndarray:
        """Compute weighted similarity matrix"""
        if self._embeddings is None:
            raise ValueError("Must call compute_embeddings() first")

        # Compute similarity for each component
        hook_sim = cosine_similarity(self._embeddings["hook"])
        explanation_sim = cosine_similarity(self._embeddings["explanation"])
        action_sim = cosine_similarity(self._embeddings["action"])

        # Weighted combination
        weighted_sim = (
            self.weights["hook"] * hook_sim
            + self.weights["explanation"] * explanation_sim
            + self.weights["action"] * action_sim
        )

        return weighted_sim

    def get_similarity_matrix(self) -> np.ndarray:
        """
        Get or compute the weighted similarity matrix

        Returns:
            Similarity matrix (n x n)
        """
        if self._similarity_matrix is None:
            print("Computing weighted similarity matrix...")
            print(
                f"Weights: Hook={self.weights['hook']}, "
                f"Action={self.weights['action']}, "
                f"Explanation={self.weights['explanation']}"
            )
            self._similarity_matrix = self._compute_weighted_similarity()
        return self._similarity_matrix

    def _extract_metadata(self) -> List[Dict]:
        """Extract model, cohort, template metadata from insights"""
        if self._metadata is None:
            self._metadata = []
            for insight in self.insights:
                self._metadata.append(
                    {
                        "model": insight.get("generation_model", "unknown"),
                        "cohort": insight.get("cohort", "unknown"),
                        "template": insight.get("insight_template", "unknown"),
                    }
                )
        return self._metadata

    def _greedy_deduplication(
        self, similarity_matrix: np.ndarray, threshold: float
    ) -> Tuple[float, float, List[int]]:
        """
        Greedy deduplication with multiple runs

        Returns:
            (mean unique count, std, list of all run results)
        """
        np.random.seed(self.random_seed)
        n = similarity_matrix.shape[0]
        results = []

        for _ in range(self.n_greedy_runs):
            order = np.random.permutation(n)
            kept_indices = []

            for idx in order:
                is_duplicate = False
                for kept_idx in kept_indices:
                    if similarity_matrix[idx, kept_idx] >= threshold:
                        is_duplicate = True
                        break

                if not is_duplicate:
                    kept_indices.append(idx)

            results.append(len(kept_indices))

        return np.mean(results), np.std(results), results

    def _connected_components_clustering(
        self, similarity_matrix: np.ndarray, threshold: float
    ) -> Tuple[int, List[int]]:
        """
        Use connected components to find unique clusters

        Returns:
            (number of clusters, cluster sizes)
        """
        n = similarity_matrix.shape[0]

        # Build graph
        G = nx.Graph()
        G.add_nodes_from(range(n))

        # Add edges for similar pairs
        for i in range(n):
            for j in range(i + 1, n):
                if similarity_matrix[i, j] >= threshold:
                    G.add_edge(i, j)

        # Find connected components
        clusters = list(nx.connected_components(G))
        cluster_sizes = [len(c) for c in clusters]

        return len(clusters), cluster_sizes

    def _compute_duplicate_counts(
        self, similarity_matrix: np.ndarray, threshold: float
    ) -> np.ndarray:
        """
        For each insight, count how many duplicates it has

        Returns:
            Array of duplicate counts per insight
        """
        n = similarity_matrix.shape[0]
        duplicate_counts = np.zeros(n, dtype=int)

        for i in range(n):
            similar_mask = similarity_matrix[i] >= threshold
            duplicate_counts[i] = similar_mask.sum() - 1  # Subtract self

        return duplicate_counts

    def _analyze_group(
        self,
        similarity_matrix: np.ndarray,
        threshold: float,
        metadata: List[Dict],
        group_by: str,
    ) -> pd.DataFrame:
        """
        Analyze duplication metrics grouped by model/cohort/template

        Args:
            similarity_matrix: Similarity matrix
            threshold: Similarity threshold
            metadata: List of metadata dicts
            group_by: 'model', 'cohort', or 'template'

        Returns:
            DataFrame with metrics per group
        """
        df = pd.DataFrame(metadata)
        df["idx"] = range(len(metadata))

        results = []

        for group_value in df[group_by].unique():
            group_indices = df[df[group_by] == group_value]["idx"].values
            n_insights = len(group_indices)

            if n_insights == 0:
                continue

            # Extract submatrix for this group
            submatrix = similarity_matrix[np.ix_(group_indices, group_indices)]

            # Compute metrics
            greedy_mean, greedy_std, _ = self._greedy_deduplication(
                submatrix, threshold
            )
            n_clusters, _ = self._connected_components_clustering(submatrix, threshold)
            duplicate_counts = self._compute_duplicate_counts(submatrix, threshold)

            results.append(
                {
                    group_by: group_value,
                    "total_insights": n_insights,
                    "greedy_unique_mean": greedy_mean,
                    "greedy_unique_std": greedy_std,
                    "greedy_unique_pct": (greedy_mean / n_insights * 100),
                    "cluster_count": n_clusters,
                    "cluster_pct": (n_clusters / n_insights * 100),
                    "mean_duplicates_per_insight": duplicate_counts.mean(),
                    "max_duplicates": duplicate_counts.max(),
                    "pct_with_0_duplicates": (duplicate_counts == 0).sum()
                    / n_insights
                    * 100,
                    "pct_with_5plus_duplicates": (duplicate_counts >= 5).sum()
                    / n_insights
                    * 100,
                }
            )

        return pd.DataFrame(results).sort_values("greedy_unique_pct", ascending=False)

    def _analyze_overlap(
        self,
        similarity_matrix: np.ndarray,
        threshold: float,
        metadata: List[Dict],
        group_by: str,
    ) -> pd.DataFrame:
        """
        Analyze cross-group overlap (pairwise)

        Args:
            similarity_matrix: Similarity matrix
            threshold: Similarity threshold
            metadata: List of metadata dicts
            group_by: 'cohort' or 'template'

        Returns:
            DataFrame with pairwise overlap metrics
        """
        df = pd.DataFrame(metadata)
        df["idx"] = range(len(metadata))

        groups = df[group_by].unique()
        results = []

        for i, group1 in enumerate(groups):
            for group2 in groups[i + 1 :]:
                indices1 = df[df[group_by] == group1]["idx"].values
                indices2 = df[df[group_by] == group2]["idx"].values

                # Get cross-similarity submatrix
                cross_sim = similarity_matrix[np.ix_(indices1, indices2)]

                # Count overlaps
                n_overlaps = (cross_sim >= threshold).sum()
                total_pairs = len(indices1) * len(indices2)

                results.append(
                    {
                        f"{group_by}_1": group1,
                        f"{group_by}_2": group2,
                        "overlap_count": n_overlaps,
                        "total_possible_pairs": total_pairs,
                        "overlap_pct": (n_overlaps / total_pairs * 100)
                        if total_pairs > 0
                        else 0,
                    }
                )

        return pd.DataFrame(results).sort_values("overlap_pct", ascending=False)

    def _find_worst_insights(
        self, similarity_matrix: np.ndarray, threshold: float, top_n: int = 20
    ) -> pd.DataFrame:
        """Find the most duplicated insights"""
        duplicate_counts = self._compute_duplicate_counts(similarity_matrix, threshold)
        worst_indices = np.argsort(duplicate_counts)[::-1][:top_n]

        results = []
        for rank, idx in enumerate(worst_indices, 1):
            insight = self.insights[idx]
            dup_count = duplicate_counts[idx]

            results.append(
                {
                    "rank": rank,
                    "duplicate_count": int(dup_count),
                    "hook": insight.get("hook", ""),
                    "explanation": insight.get("explanation", ""),
                    "action": insight.get("action", ""),
                    "model": insight.get("generation_model", "unknown"),
                    "cohort": insight.get("cohort", "unknown"),
                    "insight_template": insight.get("insight_template", "unknown"),
                }
            )

        return pd.DataFrame(results)

    def analyze(self, threshold: Optional[float] = None) -> Dict[str, pd.DataFrame]:
        """
        Run complete deduplication analysis

        Args:
            threshold: Similarity threshold (uses self.threshold if not provided)

        Returns:
            Dictionary with all analysis results:
                - 'overall': Overall statistics
                - 'by_model': Model comparison
                - 'by_cohort': Cohort analysis
                - 'by_template': Template analysis
                - 'template_overlap': Cross-template overlap
                - 'cohort_overlap': Cross-cohort overlap
                - 'worst_insights': Most duplicated insights
        """
        if threshold is not None:
            self.threshold = threshold

        if self.threshold is None:
            raise ValueError(
                "Threshold must be set. Call tune_threshold() or pass threshold parameter."
            )

        print(f"\nRunning analysis with threshold={self.threshold}...")

        # Get similarity matrix
        similarity_matrix = self.get_similarity_matrix()

        # Extract metadata
        metadata = self._extract_metadata()

        # Overall statistics
        print("Computing overall statistics...")
        greedy_mean, greedy_std, _ = self._greedy_deduplication(
            similarity_matrix, self.threshold
        )
        n_clusters, _ = self._connected_components_clustering(
            similarity_matrix, self.threshold
        )
        duplicate_counts = self._compute_duplicate_counts(
            similarity_matrix, self.threshold
        )

        overall_stats = {
            "total_insights": len(self.insights),
            "greedy_unique_mean": greedy_mean,
            "greedy_unique_std": greedy_std,
            "greedy_unique_pct": (greedy_mean / len(self.insights) * 100),
            "cluster_count": n_clusters,
            "cluster_pct": (n_clusters / len(self.insights) * 100),
            "mean_duplicates_per_insight": duplicate_counts.mean(),
        }

        # Group analyses
        print("Analyzing by model...")
        by_model = self._analyze_group(
            similarity_matrix, self.threshold, metadata, "model"
        )

        print("Analyzing by cohort...")
        by_cohort = self._analyze_group(
            similarity_matrix, self.threshold, metadata, "cohort"
        )

        print("Analyzing by template...")
        by_template = self._analyze_group(
            similarity_matrix, self.threshold, metadata, "template"
        )

        # Overlap analyses
        print("Analyzing cross-template overlap...")
        template_overlap = self._analyze_overlap(
            similarity_matrix, self.threshold, metadata, "template"
        )

        print("Analyzing cross-cohort overlap...")
        cohort_overlap = self._analyze_overlap(
            similarity_matrix, self.threshold, metadata, "cohort"
        )

        # Worst insights
        print("Finding worst-performing insights...")
        worst_insights = self._find_worst_insights(similarity_matrix, self.threshold)

        self._results = {
            "overall": pd.DataFrame([overall_stats]),
            "by_model": by_model,
            "by_cohort": by_cohort,
            "by_template": by_template,
            "template_overlap": template_overlap,
            "cohort_overlap": cohort_overlap,
            "worst_insights": worst_insights,
            "duplicate_counts": duplicate_counts,  # For distribution analysis
        }

        print("✓ Analysis complete!")
        return self._results

    def get_results(self) -> Dict[str, pd.DataFrame]:
        """Get analysis results (must call analyze() first)"""
        if self._results is None:
            raise ValueError("No results available. Call analyze() first.")
        return self._results

    def get_model_comparison(self) -> pd.DataFrame:
        """Get model comparison metrics"""
        return self.get_results()["by_model"]

    def get_worst_insights(self, top_n: int = 20) -> pd.DataFrame:
        """Get most duplicated insights"""
        return self.get_results()["worst_insights"].head(top_n)

    def get_best_model(self) -> str:
        """Get the best performing model name"""
        model_df = self.get_model_comparison()
        best_idx = model_df["greedy_unique_pct"].idxmax()
        return model_df.loc[best_idx, "model"]

    def save_embeddings(self, filepath: str) -> None:
        """Save computed embeddings to disk"""
        if self._embeddings is None:
            raise ValueError("No embeddings to save. Call compute_embeddings() first.")

        with open(filepath, "wb") as f:
            pickle.dump(
                {
                    "embeddings": self._embeddings,
                    "insights": self.insights,
                    "weights": self.weights,
                },
                f,
            )
        print(f"✓ Embeddings saved to {filepath}")

    def load_embeddings(self, filepath: str) -> "DeduplicationAnalyzer":
        """Load pre-computed embeddings from disk"""
        with open(filepath, "rb") as f:
            data = pickle.load(f)

        self._embeddings = data["embeddings"]
        print(f"✓ Embeddings loaded from {filepath}")
        return self

    def __repr__(self):
        return (
            f"DeduplicationAnalyzer(n_insights={len(self.insights)}, "
            f"threshold={self.threshold}, weights={self.weights})"
        )


if __name__ == "__main__":
    src_dir = Path(__file__).parent.parent.parent
    with open(src_dir / "output" / "insights_singapore_20251202_163904.json") as f:
        insights = json.load(f)

    dedup = InsightDeduplicator(
        insights=insights["insights"],
        weights=None,
        threshold=0.85,
        model_name="all-MiniLM-L6-v2",
    )

    dedup.compute_embeddings(show_progress=True)
    dedup.analyze()

    serializable = {}
    for key, value in dedup.get_results().items():
        if key in ["overall", "by_cohort", "by_template", "worst_insights"]:
            if isinstance(value, pd.DataFrame):
                serializable[key] = value.to_dict(orient="records")
            elif isinstance(value, np.ndarray):
                serializable[key] = value.tolist()
            else:
                serializable[key] = value

    insights["duplication_results"] = serializable

    with open(src_dir / "output/test_insights.json", "w") as f:
        json.dump(insights, f, indent=2)
