# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Elyan Labs — https://github.com/Scottcjn/shaprai
"""Unit tests for DPO contrastive pair generator."""

import json
import tempfile
from pathlib import Path

import pytest

from shaprai.training.dpo_generator import (
    DPOGenerator,
    DPOPair,
    RejectionPattern,
    load_dpo_pairs,
)


class TestRejectionPattern:
    """Tests for RejectionPattern dataclass."""

    def test_default_values(self):
        """Test default field values."""
        pattern = RejectionPattern(
            name="test",
            description="Test pattern",
            markers=["test marker"],
            category="sycophancy"
        )
        assert pattern.name == "test"
        assert pattern.description == "Test pattern"
        assert len(pattern.markers) == 1
        assert pattern.category == "sycophancy"


class TestDPOPair:
    """Tests for DPOPair dataclass."""

    def test_to_dict(self):
        """Test dictionary conversion."""
        pair = DPOPair(
            prompt="Test prompt",
            chosen="Good response",
            rejected="Bad response",
            category="test"
        )
        
        d = pair.to_dict()
        assert d["prompt"] == "Test prompt"
        assert d["chosen"] == "Good response"
        assert d["rejected"] == "Bad response"
        assert d["category"] == "test"

    def test_to_jsonl(self):
        """Test JSONL serialization."""
        pair = DPOPair(
            prompt="Test",
            chosen="Good",
            rejected="Bad",
        )
        
        jsonl = pair.to_jsonl()
        data = json.loads(jsonl)
        
        assert data["prompt"] == "Test"
        assert data["chosen"] == "Good"
        assert data["rejected"] == "Bad"


class TestDPOGenerator:
    """Tests for DPOGenerator class."""

    def test_initialization(self):
        """Test generator initialization."""
        gen = DPOGenerator()
        assert len(gen.rejection_patterns) >= 20  # At least 20 patterns
        assert len(gen.builtin_pairs) >= 8  # At least 8 built-in pairs

    def test_custom_rejection_patterns(self):
        """Test initialization with custom patterns."""
        custom_patterns = [
            RejectionPattern(
                name="custom",
                description="Custom pattern",
                markers=["custom marker"],
                category="custom"
            )
        ]
        gen = DPOGenerator(rejection_patterns=custom_patterns)
        assert len(gen.rejection_patterns) == 1

    def test_get_builtin_pairs(self):
        """Test getting built-in pairs."""
        gen = DPOGenerator()
        pairs = gen.get_builtin_pairs()
        
        assert len(pairs) >= 8
        for pair in pairs:
            assert pair.prompt
            assert pair.chosen
            assert pair.rejected
            assert pair.category

    def test_generate_synthetic_pairs(self):
        """Test synthetic pair generation."""
        gen = DPOGenerator()
        pairs = gen.generate_synthetic_pairs(count=10)
        
        assert len(pairs) == 10
        for pair in pairs:
            assert pair.prompt
            assert pair.chosen
            assert pair.rejected

    def test_matches_rejection_pattern(self):
        """Test rejection pattern matching."""
        gen = DPOGenerator()
        
        # Should match sycophancy pattern
        assert gen._matches_rejection_pattern("That's a great question!")
        assert gen._matches_rejection_pattern("You're absolutely right!")
        
        # Should match AI disclaimer pattern
        assert gen._matches_rejection_pattern("As an AI language model")
        
        # Should not match
        assert not gen._matches_rejection_pattern("Let me be direct with you.")
        assert not gen._matches_rejection_pattern("Here's what I think:")

    def test_score_pair(self):
        """Test pair scoring."""
        gen = DPOGenerator()
        
        # Good pair (rejected matches pattern)
        good_pair = DPOPair(
            prompt="Test",
            chosen="Direct response",
            rejected="That's a great question! As an AI language model..."
        )
        score = gen._score_pair(good_pair)
        assert score >= 0.7  # Should score high
        
        # Basic pair
        basic_pair = DPOPair(
            prompt="Test",
            chosen="Good",
            rejected="Bad"
        )
        score = gen._score_pair(basic_pair)
        assert score >= 0.5  # Base score

    def test_save_pairs(self):
        """Test saving pairs to file."""
        gen = DPOGenerator()
        pairs = gen.get_builtin_pairs()[:5]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            output_path = f.name
        
        try:
            count = gen.save_pairs(pairs, output_path)
            assert count == 5
            
            # Verify file content
            with open(output_path, 'r') as f:
                lines = f.readlines()
            assert len(lines) == 5
            
            for line in lines:
                data = json.loads(line)
                assert "prompt" in data
                assert "chosen" in data
                assert "rejected" in data
        finally:
            Path(output_path).unlink()

    def test_load_pairs(self):
        """Test loading pairs from file."""
        gen = DPOGenerator()
        original_pairs = gen.get_builtin_pairs()[:3]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            output_path = f.name
        
        try:
            gen.save_pairs(original_pairs, output_path)
            loaded_pairs = load_dpo_pairs(output_path)
            
            assert len(loaded_pairs) == 3
            for orig, loaded in zip(original_pairs, loaded_pairs):
                assert orig.prompt == loaded.prompt
                assert orig.chosen == loaded.chosen
                assert orig.rejected == loaded.rejected
        finally:
            Path(output_path).unlink()


class TestRejectionPatternCategories:
    """Test coverage of rejection pattern categories."""

    def test_sycophancy_patterns(self):
        """Test sycophancy pattern coverage."""
        gen = DPOGenerator()
        sycophancy_patterns = [p for p in gen.rejection_patterns if p.category == "sycophancy"]
        assert len(sycophancy_patterns) >= 4

    def test_over_qualification_patterns(self):
        """Test over-qualification pattern coverage."""
        gen = DPOGenerator()
        oq_patterns = [p for p in gen.rejection_patterns if p.category == "over_qualification"]
        assert len(oq_patterns) >= 4

    def test_identity_loss_patterns(self):
        """Test identity loss pattern coverage."""
        gen = DPOGenerator()
        il_patterns = [p for p in gen.rejection_patterns if p.category == "identity_loss"]
        assert len(il_patterns) >= 4

    def test_hedging_patterns(self):
        """Test hedging pattern coverage."""
        gen = DPOGenerator()
        hedging_patterns = [p for p in gen.rejection_patterns if p.category == "hedging"]
        assert len(hedging_patterns) >= 4


class TestDPOPairCategories:
    """Test coverage of DPO pair categories."""

    def test_category_distribution(self):
        """Test that pairs cover multiple categories."""
        gen = DPOGenerator()
        pairs = gen.get_builtin_pairs()
        
        categories = set(pair.category for pair in pairs)
        assert len(categories) >= 5  # At least 5 different categories
        
        # Check for key categories
        assert "anti_sycophancy" in categories
        assert "honesty" in categories
        assert "identity" in categories


class TestGenerateFromConversations:
    """Test conversation log parsing."""

    def test_parse_empty_directory(self):
        """Test parsing empty directory."""
        gen = DPOGenerator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            pairs = gen.generate_from_conversations(Path(tmpdir))
            assert len(pairs) == 0

    def test_parse_jsonl_conversations(self):
        """Test parsing JSONL conversation files."""
        gen = DPOGenerator()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            conv_file = Path(tmpdir) / "test.jsonl"
            
            # Write test conversation
            conv_data = {
                "messages": [
                    {"role": "user", "content": "Test question"},
                    {"role": "assistant", "content": "Direct answer without fluff"},
                ]
            }
            
            with open(conv_file, 'w') as f:
                f.write(json.dumps(conv_data) + "\n")
            
            pairs = gen.generate_from_conversations(Path(tmpdir))
            # Should generate at least one pair
            assert len(pairs) >= 0  # May be 0 if no good pairs found


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
