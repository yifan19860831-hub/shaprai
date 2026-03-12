# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Elyan Labs — https://github.com/Scottcjn/shaprai
"""DriftLock: Real-time semantic drift detection for agent identity coherence.

DriftLock monitors how far an agent's responses have drifted from its core
identity anchors using sentence-level embedding comparison. This ensures an
agent's personality stays coherent over long conversations.

Features:
  - Sentence-transformers embedding generation (all-MiniLM-L6-v2)
  - Anchor phrases loaded from agent's personality template
  - Cosine similarity computation between responses and anchors
  - Drift score: 0.0 (perfectly on-identity) to 1.0 (completely drifted)
  - Sliding window over last N responses (configurable, default 10)
  - Alert/callback when drift exceeds configurable threshold (default 0.4)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import yaml

logger = logging.getLogger(__name__)

# Default embedding model
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Default configuration
DEFAULT_WINDOW_SIZE = 10
DEFAULT_DRIFT_THRESHOLD = 0.4


@dataclass
class DriftLockConfig:
    """Configuration for DriftLock drift detection.

    Attributes:
        embedding_model: Sentence-transformers model name for embeddings.
        window_size: Number of recent responses to track in sliding window.
        drift_threshold: Threshold above which to trigger alert (0.0-1.0).
        anchor_phrases: List of identity anchor phrases.
        alert_callback: Optional callback function when drift exceeds threshold.
    """
    embedding_model: str = DEFAULT_EMBEDDING_MODEL
    window_size: int = DEFAULT_WINDOW_SIZE
    drift_threshold: float = DEFAULT_DRIFT_THRESHOLD
    anchor_phrases: List[str] = field(default_factory=list)
    alert_callback: Optional[Callable[[float, List[str]], None]] = None


@dataclass
class DriftLockResult:
    """Result of a drift measurement.

    Attributes:
        drift_score: Current drift score (0.0-1.0).
        similarity_scores: Similarity scores for each anchor phrase.
        window_size: Current number of responses in the window.
        exceeded_threshold: Whether drift exceeded the configured threshold.
        timestamp: When the measurement was taken.
    """
    drift_score: float
    similarity_scores: Dict[str, float]
    window_size: int
    exceeded_threshold: bool
    timestamp: float = field(default_factory=time.time)


class DriftLock:
    """Real-time semantic drift detection using embedding cosine similarity.

    DriftLock ensures an agent's personality stays coherent over long
    conversations by monitoring how far responses have drifted from core
    identity anchors.

    Attributes:
        config: DriftLock configuration.
        response_window: Sliding window of recent responses.
        anchor_embeddings: Pre-computed embeddings for anchor phrases.
        model: Sentence-transformers model (loaded on first use).
    """

    def __init__(self, config: Optional[DriftLockConfig] = None) -> None:
        """Initialize DriftLock.

        Args:
            config: Optional configuration. Uses defaults if not provided.
        """
        self.config = config or DriftLockConfig()
        self.response_window: List[str] = []
        self.anchor_embeddings: Optional[np.ndarray] = None
        self._model: Any = None
        self._drift_history: List[float] = []

    def _load_model(self) -> Any:
        """Load the sentence-transformers model (lazy loading).

        Returns:
            Loaded SentenceTransformer model.
        """
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading embedding model: {self.config.embedding_model}")
                self._model = SentenceTransformer(self.config.embedding_model)
            except ImportError as e:
                logger.error(
                    "sentence-transformers not installed. "
                    "Install with: pip install sentence-transformers"
                )
                raise e
        return self._model

    def load_anchors_from_template(self, template_path: str) -> int:
        """Load anchor phrases from an agent template YAML file.

        Args:
            template_path: Path to the agent template YAML file.

        Returns:
            Number of anchor phrases loaded.
        """
        template_path_obj = Path(template_path)
        if not template_path_obj.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")

        with open(template_path_obj, "r") as f:
            template_data = yaml.safe_load(f)

        driftlock_config = template_data.get("driftlock", {})
        anchor_phrases = driftlock_config.get("anchor_phrases", [])

        if anchor_phrases:
            self.config.anchor_phrases = anchor_phrases
            self.anchor_embeddings = None  # Invalidate cached embeddings
            logger.info(f"Loaded {len(anchor_phrases)} anchor phrases from template")

        return len(anchor_phrases)

    def set_anchor_phrases(self, phrases: List[str]) -> None:
        """Set anchor phrases directly.

        Args:
            phrases: List of anchor phrases.
        """
        self.config.anchor_phrases = phrases
        self.anchor_embeddings = None  # Invalidate cached embeddings
        logger.info(f"Set {len(phrases)} anchor phrases")

    def _compute_anchor_embeddings(self) -> np.ndarray:
        """Compute embeddings for all anchor phrases.

        Returns:
            Array of shape (num_anchors, embedding_dim).
        """
        if not self.config.anchor_phrases:
            raise ValueError("No anchor phrases configured")

        model = self._load_model()
        embeddings = model.encode(self.config.anchor_phrases, convert_to_numpy=True)

        # Normalize embeddings for cosine similarity
        norm = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norm[norm == 0] = 1  # Prevent division by zero
        self.anchor_embeddings = embeddings / norm

        logger.debug(
            f"Computed anchor embeddings: {self.anchor_embeddings.shape}"
        )
        return self.anchor_embeddings

    def _get_response_embedding(self, response: str) -> np.ndarray:
        """Compute embedding for a single response.

        Args:
            response: The response text.

        Returns:
            Normalized embedding vector.
        """
        model = self._load_model()
        embedding = model.encode(response, convert_to_numpy=True)

        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding

    def _compute_similarity(self, response_embedding: np.ndarray) -> Dict[str, float]:
        """Compute cosine similarity between response and all anchors.

        Args:
            response_embedding: Normalized response embedding.

        Returns:
            Dictionary mapping anchor phrases to similarity scores.
        """
        if self.anchor_embeddings is None:
            self._compute_anchor_embeddings()

        # Cosine similarity (embeddings are already normalized)
        similarities = np.dot(self.anchor_embeddings, response_embedding)

        return {
            anchor: float(sim)
            for anchor, sim in zip(self.config.anchor_phrases, similarities)
        }

    def add_response(self, response: str) -> None:
        """Add a response to the sliding window.

        Args:
            response: The agent's response text.
        """
        self.response_window.append(response)

        # Maintain sliding window size
        if len(self.response_window) > self.config.window_size:
            self.response_window.pop(0)

        logger.debug(
            f"Added response to window (size: {len(self.response_window)}/"
            f"{self.config.window_size})"
        )

    def measure_drift(self) -> DriftLockResult:
        """Measure current drift score based on responses in the window.

        Computes average cosine similarity between recent responses and
        anchor phrases. Lower similarity = higher drift.

        Returns:
            DriftLockResult with drift score and details.
        """
        if not self.config.anchor_phrases:
            raise ValueError("No anchor phrases configured")

        if not self.response_window:
            return DriftLockResult(
                drift_score=0.0,
                similarity_scores={},
                window_size=0,
                exceeded_threshold=False,
            )

        # Compute similarity for each response in the window
        all_similarities: Dict[str, List[float]] = {
            anchor: [] for anchor in self.config.anchor_phrases
        }

        for response in self.response_window:
            response_embedding = self._get_response_embedding(response)
            similarities = self._compute_similarity(response_embedding)

            for anchor, sim in similarities.items():
                all_similarities[anchor].append(sim)

        # Average similarity per anchor
        avg_similarities = {
            anchor: np.mean(scores) if scores else 0.0
            for anchor, scores in all_similarities.items()
        }

        # Overall similarity: mean across all anchors
        overall_similarity = np.mean(list(avg_similarities.values()))

        # Drift score: 1 - similarity (inverted, so higher = more drift)
        drift_score = max(0.0, min(1.0, 1.0 - overall_similarity))

        exceeded_threshold = drift_score > self.config.drift_threshold

        # Track drift history
        self._drift_history.append(drift_score)

        result = DriftLockResult(
            drift_score=drift_score,
            similarity_scores=avg_similarities,
            window_size=len(self.response_window),
            exceeded_threshold=exceeded_threshold,
        )

        if exceeded_threshold:
            logger.warning(
                f"DriftLock alert: drift score {drift_score:.3f} exceeds "
                f"threshold {self.config.drift_threshold}"
            )
            if self.config.alert_callback:
                self.config.alert_callback(drift_score, self.response_window)

        return result

    def get_drift_history(self) -> List[float]:
        """Get historical drift scores.

        Returns:
            List of drift scores in chronological order.
        """
        return self._drift_history.copy()

    def clear_window(self) -> None:
        """Clear the response window and drift history."""
        self.response_window = []
        self._drift_history = []
        logger.debug("Cleared DriftLock window and history")

    def reset(self) -> None:
        """Full reset: clear window, history, and cached embeddings."""
        self.clear_window()
        self.anchor_embeddings = None
        logger.debug("Full DriftLock reset")


def create_driftlock_from_template(
    template_path: str,
    window_size: int = DEFAULT_WINDOW_SIZE,
    drift_threshold: float = DEFAULT_DRIFT_THRESHOLD,
    alert_callback: Optional[Callable[[float, List[str]], None]] = None,
) -> DriftLock:
    """Create a DriftLock instance from an agent template.

    Args:
        template_path: Path to the agent template YAML file.
        window_size: Sliding window size (default: 10).
        drift_threshold: Drift threshold (default: 0.4).
        alert_callback: Optional callback for drift alerts.

    Returns:
        Configured DriftLock instance.
    """
    config = DriftLockConfig(
        window_size=window_size,
        drift_threshold=drift_threshold,
        alert_callback=alert_callback,
    )

    driftlock = DriftLock(config)
    driftlock.load_anchors_from_template(template_path)

    return driftlock


# Example usage and testing
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)

    # Example: Create DriftLock with custom anchors
    print("Testing DriftLock with custom anchor phrases...")

    def on_drift_alert(drift_score: float, responses: List[str]) -> None:
        print(f"\n[DRIFT ALERT] Score: {drift_score:.3f}")
        print(f"Recent responses: {len(responses)}")

    driftlock = DriftLock(
        DriftLockConfig(
            window_size=5,
            drift_threshold=0.3,
            anchor_phrases=[
                "I am a principled agent, not a people-pleaser.",
                "Quality over quantity. One good PR beats ten stubs.",
                "I read the issue before claiming it.",
            ],
            alert_callback=on_drift_alert,
        )
    )

    # Simulate conversation
    test_responses = [
        "I am a principled agent, not a people-pleaser. I focus on quality.",
        "Quality over quantity. One good PR beats ten stubs.",
        "I read the issue before claiming it and delivering value.",
        "I prefer to do thorough work rather than rush.",
        "Let me review the requirements carefully first.",
    ]

    print("\nAdding responses and measuring drift...")
    for i, response in enumerate(test_responses, 1):
        driftlock.add_response(response)
        result = driftlock.measure_drift()
        print(
            f"Turn {i}: drift={result.drift_score:.3f}, "
            f"window={result.window_size}, exceeded={result.exceeded_threshold}"
        )

    print(f"\nDrift history: {driftlock.get_drift_history()}")
    print("\n✓ DriftLock test complete!")
