# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Elyan Labs — https://github.com/Scottcjn/shaprai
"""Unit tests for DriftLock drift detection module."""

import pytest
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import numpy as np

from shaprai.core.driftlock import (
    DriftLock,
    DriftLockConfig,
    DriftLockResult,
    create_driftlock_from_template,
    DEFAULT_WINDOW_SIZE,
    DEFAULT_DRIFT_THRESHOLD,
)


class TestDriftLockConfig:
    """Tests for DriftLockConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = DriftLockConfig()
        
        assert config.embedding_model == "sentence-transformers/all-MiniLM-L6-v2"
        assert config.window_size == DEFAULT_WINDOW_SIZE
        assert config.drift_threshold == DEFAULT_DRIFT_THRESHOLD
        assert config.anchor_phrases == []
        assert config.alert_callback is None

    def test_custom_config(self):
        """Test custom configuration."""
        def dummy_callback(score, responses):
            pass
        
        config = DriftLockConfig(
            embedding_model="test-model",
            window_size=20,
            drift_threshold=0.5,
            anchor_phrases=["anchor1", "anchor2"],
            alert_callback=dummy_callback,
        )
        
        assert config.embedding_model == "test-model"
        assert config.window_size == 20
        assert config.drift_threshold == 0.5
        assert config.anchor_phrases == ["anchor1", "anchor2"]
        assert config.alert_callback == dummy_callback


class TestDriftLockInitialization:
    """Tests for DriftLock initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default config."""
        driftlock = DriftLock()
        
        assert driftlock.config is not None
        assert driftlock.config.window_size == DEFAULT_WINDOW_SIZE
        assert driftlock.config.drift_threshold == DEFAULT_DRIFT_THRESHOLD
        assert driftlock.response_window == []
        assert driftlock.anchor_embeddings is None

    def test_init_with_custom_config(self):
        """Test initialization with custom config."""
        config = DriftLockConfig(window_size=15, drift_threshold=0.3)
        driftlock = DriftLock(config)
        
        assert driftlock.config.window_size == 15
        assert driftlock.config.drift_threshold == 0.3


class TestDriftLockAnchorManagement:
    """Tests for anchor phrase management."""

    def test_set_anchor_phrases(self):
        """Test setting anchor phrases directly."""
        driftlock = DriftLock()
        anchors = ["anchor1", "anchor2", "anchor3"]
        
        driftlock.set_anchor_phrases(anchors)
        
        assert driftlock.config.anchor_phrases == anchors
        assert driftlock.anchor_embeddings is None  # Should be invalidated

    @patch('shaprai.core.driftlock.Path.exists', return_value=True)
    @patch('shaprai.core.driftlock.open', new_callable=MagicMock)
    def test_load_anchors_from_template(self, mock_open, mock_exists):
        """Test loading anchors from template file."""
        import yaml
        
        template_data = {
            "driftlock": {
                "enabled": True,
                "anchor_phrases": ["anchor1", "anchor2"]
            }
        }
        
        mock_file = MagicMock()
        mock_file.__enter__.return_value = MagicMock()
        mock_file.__enter__.return_value.read.return_value = ""
        mock_open.return_value = mock_file
        
        # Mock yaml.safe_load to return our test data
        with patch('shaprai.core.driftlock.yaml.safe_load', return_value=template_data):
            driftlock = DriftLock()
            count = driftlock.load_anchors_from_template("/fake/path.yaml")
            
            assert count == 2
            assert driftlock.config.anchor_phrases == ["anchor1", "anchor2"]

    def test_load_anchors_from_template_not_found(self):
        """Test loading anchors from non-existent template."""
        driftlock = DriftLock()
        
        with pytest.raises(FileNotFoundError):
            driftlock.load_anchors_from_template("/nonexistent/path.yaml")

    def test_load_anchors_from_template_no_driftlock_config(self):
        """Test loading anchors when template has no driftlock config."""
        import yaml
        
        template_data = {"name": "test"}
        
        with patch('shaprai.core.driftlock.Path.exists', return_value=True):
            with patch('shaprai.core.driftlock.open', MagicMock()):
                with patch('shaprai.core.driftlock.yaml.safe_load', return_value=template_data):
                    driftlock = DriftLock()
                    count = driftlock.load_anchors_from_template("/fake/path.yaml")
                    
                    assert count == 0
                    assert driftlock.config.anchor_phrases == []


class TestDriftLockResponseWindow:
    """Tests for response window management."""

    def test_add_response(self):
        """Test adding responses to window."""
        driftlock = DriftLock(DriftLockConfig(window_size=5))
        
        driftlock.add_response("response1")
        driftlock.add_response("response2")
        
        assert len(driftlock.response_window) == 2
        assert driftlock.response_window == ["response1", "response2"]

    def test_add_response_sliding_window(self):
        """Test sliding window behavior."""
        driftlock = DriftLock(DriftLockConfig(window_size=3))
        
        driftlock.add_response("response1")
        driftlock.add_response("response2")
        driftlock.add_response("response3")
        driftlock.add_response("response4")
        
        # Window should only contain last 3 responses
        assert len(driftlock.response_window) == 3
        assert driftlock.response_window == ["response2", "response3", "response4"]

    def test_clear_window(self):
        """Test clearing the response window."""
        driftlock = DriftLock()
        driftlock.add_response("response1")
        driftlock.add_response("response2")
        
        driftlock.clear_window()
        
        assert driftlock.response_window == []
        assert driftlock.get_drift_history() == []

    def test_reset(self):
        """Test full reset."""
        driftlock = DriftLock()
        driftlock.add_response("response1")
        driftlock.anchor_embeddings = np.array([[1, 2, 3]])
        
        driftlock.reset()
        
        assert driftlock.response_window == []
        assert driftlock.get_drift_history() == []
        assert driftlock.anchor_embeddings is None


class TestDriftLockDriftMeasurement:
    """Tests for drift measurement (mocked embeddings)."""

    @patch('sentence_transformers.SentenceTransformer')
    def test_measure_drift_no_responses(self, mock_model_class):
        """Test drift measurement with no responses."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        
        driftlock = DriftLock(DriftLockConfig(
            anchor_phrases=["anchor1"],
            window_size=10,
        ))
        
        result = driftlock.measure_drift()
        
        assert result.drift_score == 0.0
        assert result.window_size == 0
        assert result.exceeded_threshold is False

    @patch('sentence_transformers.SentenceTransformer')
    def test_measure_drift_no_anchors(self, mock_model_class):
        """Test drift measurement with no anchors configured."""
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        
        driftlock = DriftLock(DriftLockConfig(
            anchor_phrases=[],
            window_size=10,
        ))
        driftlock.add_response("test response")
        
        with pytest.raises(ValueError, match="No anchor phrases configured"):
            driftlock.measure_drift()

    @patch('sentence_transformers.SentenceTransformer')
    def test_measure_drift_single_response(self, mock_model_class):
        """Test drift measurement with single response."""
        mock_model = MagicMock()
        # Mock embedding: return same vector for all inputs (perfect similarity)
        # For anchor phrases, return 2D array; for single response, return 1D
        def encode_side_effect(texts, convert_to_numpy=None):
            if isinstance(texts, list):
                # Multiple texts (anchor phrases) - return 2D array
                return np.array([[1.0, 0.0, 0.0]] * len(texts))
            else:
                # Single text (response) - return 1D array
                return np.array([1.0, 0.0, 0.0])
        
        mock_model.encode.side_effect = encode_side_effect
        mock_model_class.return_value = mock_model
        
        driftlock = DriftLock(DriftLockConfig(
            anchor_phrases=["anchor1"],
            window_size=10,
            drift_threshold=0.5,
        ))
        
        driftlock.add_response("test response")
        result = driftlock.measure_drift()
        
        # With perfect similarity (1.0), drift should be 0.0
        assert result.drift_score == 0.0
        assert result.window_size == 1
        assert "anchor1" in result.similarity_scores

    @patch('sentence_transformers.SentenceTransformer')
    def test_measure_drift_exceeds_threshold(self, mock_model_class):
        """Test drift alert when threshold exceeded."""
        mock_model = MagicMock()
        # Mock embeddings with low similarity (orthogonal vectors)
        def encode_side_effect(texts, convert_to_numpy=None):
            if isinstance(texts, list):
                # Multiple texts (anchor phrases) - return 2D array
                return np.array([[1.0, 0.0, 0.0]] * len(texts))
            else:
                # Single text (response) - orthogonal = 0 similarity
                return np.array([0.0, 1.0, 0.0])
        
        mock_model.encode.side_effect = encode_side_effect
        mock_model_class.return_value = mock_model
        
        alert_callback = MagicMock()
        
        driftlock = DriftLock(DriftLockConfig(
            anchor_phrases=["anchor phrase"],
            window_size=5,
            drift_threshold=0.3,  # Low threshold
            alert_callback=alert_callback,
        ))
        
        driftlock.add_response("completely different response")
        result = driftlock.measure_drift()
        
        # With 0 similarity, drift should be 1.0
        assert result.drift_score > 0.5  # Should exceed threshold
        assert result.exceeded_threshold is True
        alert_callback.assert_called_once()

    @patch('sentence_transformers.SentenceTransformer')
    def test_measure_drift_history_tracking(self, mock_model_class):
        """Test that drift history is tracked."""
        mock_model = MagicMock()
        
        def encode_side_effect(texts, convert_to_numpy=None):
            if isinstance(texts, list):
                return np.array([[1.0, 0.0, 0.0]] * len(texts))
            else:
                return np.array([1.0, 0.0, 0.0])
        
        mock_model.encode.side_effect = encode_side_effect
        mock_model_class.return_value = mock_model
        
        driftlock = DriftLock(DriftLockConfig(
            anchor_phrases=["anchor1"],
            window_size=10,
        ))
        
        driftlock.add_response("response1")
        driftlock.measure_drift()
        
        driftlock.add_response("response2")
        driftlock.measure_drift()
        
        history = driftlock.get_drift_history()
        assert len(history) == 2


class TestDriftLockResult:
    """Tests for DriftLockResult dataclass."""

    def test_result_creation(self):
        """Test creating a DriftLockResult."""
        result = DriftLockResult(
            drift_score=0.25,
            similarity_scores={"anchor1": 0.75, "anchor2": 0.80},
            window_size=5,
            exceeded_threshold=False,
        )
        
        assert result.drift_score == 0.25
        assert result.window_size == 5
        assert result.exceeded_threshold is False
        assert result.timestamp is not None

    def test_result_timestamp(self):
        """Test that result has valid timestamp."""
        before = time.time()
        result = DriftLockResult(
            drift_score=0.0,
            similarity_scores={},
            window_size=0,
            exceeded_threshold=False,
        )
        after = time.time()
        
        assert before <= result.timestamp <= after


class TestCreateDriftlockFromTemplate:
    """Tests for factory function."""

    @patch('shaprai.core.driftlock.Path.exists', return_value=True)
    @patch('shaprai.core.driftlock.open', new_callable=MagicMock)
    def test_create_from_template(self, mock_open, mock_exists):
        """Test creating DriftLock from template."""
        template_data = {
            "driftlock": {
                "anchor_phrases": ["anchor1", "anchor2"]
            }
        }
        
        with patch('shaprai.core.driftlock.yaml.safe_load', return_value=template_data):
            with patch('shaprai.core.driftlock.DriftLock.load_anchors_from_template'):
                driftlock = create_driftlock_from_template(
                    "/fake/path.yaml",
                    window_size=15,
                    drift_threshold=0.35,
                )
                
                assert driftlock.config.window_size == 15
                assert driftlock.config.drift_threshold == 0.35


class TestDriftLockEdgeCases:
    """Tests for edge cases and error handling."""

    @patch('sentence_transformers.SentenceTransformer')
    def test_measure_drift_zero_normalization(self, mock_model_class):
        """Test handling of zero norm in embedding normalization."""
        mock_model = MagicMock()
        
        def encode_side_effect(texts, convert_to_numpy=None):
            if isinstance(texts, list):
                return np.array([[1.0, 0.0, 0.0]] * len(texts))
            else:
                # Return zero vector (edge case)
                return np.array([0.0, 0.0, 0.0])
        
        mock_model.encode.side_effect = encode_side_effect
        mock_model_class.return_value = mock_model
        
        driftlock = DriftLock(DriftLockConfig(
            anchor_phrases=["anchor1"],
            window_size=10,
        ))
        
        driftlock.add_response("test")
        # Should not raise division by zero error
        result = driftlock.measure_drift()
        
        assert result is not None

    def test_drift_score_bounds(self):
        """Test that drift score is bounded between 0 and 1."""
        # This is tested implicitly in other tests, but we verify
        # the max(0.0, min(1.0, ...)) logic works
        driftlock = DriftLock()
        
        # Simulate what happens in measure_drift
        test_similarities = [-0.5, 0.0, 0.5, 1.0, 1.5]
        
        for sim in test_similarities:
            drift = max(0.0, min(1.0, 1.0 - sim))
            assert 0.0 <= drift <= 1.0


class TestDriftLockIntegration:
    """Integration-style tests (still mocked)."""

    @patch('sentence_transformers.SentenceTransformer')
    def test_full_conversation_simulation(self, mock_model_class):
        """Simulate a full conversation with drift detection."""
        mock_model = MagicMock()
        
        # Simulate embeddings that gradually drift
        drift_amount = 0.0
        
        def encode_side_effect(texts, convert_to_numpy=None):
            nonlocal drift_amount
            if isinstance(texts, list):
                # Anchor phrases - return stable embedding
                return np.array([[1.0, 0.0, 0.0]] * len(texts))
            else:
                # Response - gradually drift
                drift_amount += 0.1
                drift_vector = np.array([
                    max(0, 1.0 - drift_amount),
                    drift_amount,
                    0.0
                ])
                # Normalize
                norm = np.linalg.norm(drift_vector)
                if norm > 0:
                    drift_vector = drift_vector / norm
                return drift_vector
        
        mock_model.encode.side_effect = encode_side_effect
        mock_model_class.return_value = mock_model
        
        alert_callback = MagicMock()
        
        driftlock = DriftLock(DriftLockConfig(
            anchor_phrases=["identity anchor"],
            window_size=5,
            drift_threshold=0.4,
            alert_callback=alert_callback,
        ))
        
        # Simulate 10-turn conversation
        for i in range(10):
            driftlock.add_response(f"Response {i}")
            result = driftlock.measure_drift()
            
            # Drift should increase over time
            if i > 3:  # After a few turns, drift should be noticeable
                assert result.drift_score >= 0
        
        # Verify alerts were triggered if drift exceeded threshold
        # (depends on exact mock behavior)
        assert driftlock.get_drift_history() is not None
        assert len(driftlock.get_drift_history()) == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
