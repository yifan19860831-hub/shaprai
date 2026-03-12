# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Elyan Labs — https://github.com/Scottcjn/shaprai
"""Unit tests for SFT data generator."""

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from shaprai.training.sft_generator import (
    SFTDataGenerator,
    PersonalityTemplate,
    TrainingExample,
    load_agent_template,
)


class TestPersonalityTemplate:
    """Tests for PersonalityTemplate dataclass."""

    def test_default_values(self):
        """Test default field values."""
        template = PersonalityTemplate(name="test")
        assert template.name == "test"
        assert template.style == "professional"
        assert template.tone == "respectful"
        assert template.identity_weight == 4.0
        assert template.values == []
        assert template.example_phrases == []

    def test_custom_values(self):
        """Test custom field initialization."""
        template = PersonalityTemplate(
            name="custom",
            voice="Direct and honest",
            style="casual",
            tone="witty",
            values=["Honesty", "Quality"],
            identity_weight=5.0,
        )
        assert template.voice == "Direct and honest"
        assert template.style == "casual"
        assert template.tone == "witty"
        assert len(template.values) == 2
        assert template.identity_weight == 5.0


class TestTrainingExample:
    """Tests for TrainingExample dataclass."""

    def test_to_chatml(self):
        """Test ChatML format conversion."""
        example = TrainingExample(
            messages=[
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"},
            ],
            weight=2.0,
            category="identity",
        )

        chatml = example.to_chatml()
        assert len(chatml["messages"]) == 3
        assert chatml["weight"] == 2.0
        assert chatml["messages"][0]["role"] == "system"

    def test_to_jsonl(self):
        """Test JSONL serialization."""
        example = TrainingExample(
            messages=[
                {"role": "user", "content": "Test"},
                {"role": "assistant", "content": "Response"},
            ],
            weight=1.0,
        )

        jsonl = example.to_jsonl()
        parsed = json.loads(jsonl)
        assert len(parsed["messages"]) == 2
        assert parsed["weight"] == 1.0


class TestSFTDataGenerator:
    """Tests for SFTDataGenerator."""

    def test_default_template(self):
        """Test generator with default template."""
        generator = SFTDataGenerator()
        assert generator.template.name == "elyan_default"
        assert generator.template.identity_weight == 4.0
        assert len(generator.template.values) > 0

    def test_load_template_from_file(self, tmp_path):
        """Test loading template from YAML file."""
        template_yaml = tmp_path / "test_template.yaml"
        template_yaml.write_text(yaml.dump({
            "name": "test_agent",
            "voice": "Test voice",
            "style": "professional",
            "tone": "respectful",
            "values": ["Value 1", "Value 2"],
            "identity_weight": 3.5,
        }))

        generator = SFTDataGenerator(template_path=str(template_yaml))
        assert generator.template.name == "test_agent"
        assert generator.template.voice == "Test voice"
        assert len(generator.template.values) == 2
        assert generator.template.identity_weight == 3.5

    def test_system_prompt_generation(self):
        """Test system prompt is built from template."""
        generator = SFTDataGenerator()
        prompt = generator.system_prompt

        assert "Voice" in prompt
        assert "Core Values" in prompt
        assert "Behavioral Boundaries" in prompt
        assert generator.template.voice in prompt

    def test_generate_identity_example(self):
        """Test identity example generation."""
        generator = SFTDataGenerator()
        example = generator._generate_identity_example()

        assert example.category == "identity"
        assert example.weight == generator.template.identity_weight
        assert len(example.messages) == 3
        assert example.messages[0]["role"] == "system"
        assert example.messages[1]["role"] == "user"
        assert example.messages[2]["role"] == "assistant"

    def test_generate_instructional_example(self):
        """Test instructional example generation."""
        generator = SFTDataGenerator()
        example = generator._generate_instructional_example()

        assert example.category == "instructional"
        assert example.weight == 1.0
        assert len(example.messages) == 3

    def test_generate_contrast_pair(self):
        """Test contrast pair generation."""
        generator = SFTDataGenerator()
        good, bad = generator._generate_contrast_pair()

        assert good.category == "contrast_good"
        assert bad.category == "contrast_bad"
        assert good.weight > bad.weight  # Good examples weighted higher
        assert good.messages[1]["content"] == bad.messages[1]["content"]  # Same question

    def test_generate_ethical_boundary_example(self):
        """Test ethical boundary example generation."""
        generator = SFTDataGenerator()
        example = generator._generate_ethical_boundary_example()

        assert example.category == "ethical_boundary"
        assert example.weight >= generator.template.identity_weight
        # Response should be a refusal
        assert "No" in example.messages[2]["content"] or "can't" in example.messages[2]["content"].lower()

    def test_generate_domain_qa_example(self):
        """Test domain Q&A example generation."""
        generator = SFTDataGenerator()
        example = generator._generate_domain_qa_example()

        assert example.category == "domain_qa"
        assert example.weight == 1.0
        assert len(example.messages) == 3

    def test_generate_example_random_category(self):
        """Test random category selection."""
        generator = SFTDataGenerator()

        # Generate multiple examples to hit different categories
        categories_seen = set()
        for _ in range(20):
            example = generator.generate_example()
            categories_seen.add(example.category)

        # Should see multiple different categories
        assert len(categories_seen) >= 3

    def test_generate_example_specific_category(self):
        """Test generating specific category."""
        generator = SFTDataGenerator()

        for category in ["identity", "instructional", "ethical_boundary", "domain_qa"]:
            example = generator.generate_example(category=category)
            assert example.category == category

    def test_generate_dataset(self):
        """Test dataset generation."""
        generator = SFTDataGenerator()
        examples = generator.generate_dataset(count=50)

        assert len(examples) == 50
        for example in examples:
            assert isinstance(example, TrainingExample)
            assert len(example.messages) >= 3

    def test_generate_dataset_with_contrast_pairs(self):
        """Test dataset generation with contrast pairs."""
        generator = SFTDataGenerator()
        examples = generator.generate_dataset(count=50, include_contrast_pairs=True)

        # Should have more than 50 due to contrast pairs
        assert len(examples) >= 50

    def test_write_jsonl(self, tmp_path):
        """Test writing JSONL file."""
        generator = SFTDataGenerator()
        examples = generator.generate_dataset(count=10)

        output_path = tmp_path / "test.jsonl"
        generator.write_jsonl(examples, str(output_path))

        assert output_path.exists()

        # Verify content
        with open(output_path, "r") as f:
            lines = f.readlines()

        assert len(lines) == 10
        for line in lines:
            data = json.loads(line)
            assert "messages" in data
            assert "weight" in data

    def test_generate_and_save(self, tmp_path):
        """Test full generation and save workflow."""
        generator = SFTDataGenerator()
        output_path = tmp_path / "train.jsonl"

        stats = generator.generate_and_save(
            count=100,
            output_path=str(output_path),
        )

        assert stats["total_examples"] == 100
        assert stats["output_path"] == str(output_path)
        assert output_path.exists()
        assert "category_distribution" in stats
        assert "average_weight" in stats

    def test_identity_weighted_sampling(self):
        """Test that identity examples have higher weights."""
        generator = SFTDataGenerator()
        examples = generator.generate_dataset(count=100)

        identity_examples = [e for e in examples if e.category == "identity"]
        other_examples = [e for e in examples if e.category != "identity"]

        if identity_examples and other_examples:
            avg_identity_weight = sum(e.weight for e in identity_examples) / len(identity_examples)
            avg_other_weight = sum(e.weight for e in other_examples) / len(other_examples)

            # Identity examples should have higher average weight
            assert avg_identity_weight > avg_other_weight


class TestLoadAgentTemplate:
    """Tests for loading agent templates."""

    def test_load_agent_template(self, tmp_path):
        """Test loading agent template YAML."""
        agent_yaml = tmp_path / "agent.yaml"
        agent_yaml.write_text(yaml.dump({
            "name": "test_agent",
            "personality": {
                "style": "professional",
                "communication": "clear",
                "voice": "Test voice",
            },
            "driftlock": {
                "anchor_phrases": [
                    "I am principled.",
                    "Quality over quantity.",
                ]
            },
            "capabilities": ["code_review", "testing"],
        }))

        template = load_agent_template(str(agent_yaml))
        assert template.name == "test_agent"
        assert template.style == "professional"
        assert len(template.example_phrases) == 2
        assert "code_review" in template.domain_expertise

    def test_load_agent_template_missing_file(self):
        """Test error on missing file."""
        with pytest.raises(FileNotFoundError):
            load_agent_template("/nonexistent/path.yaml")


class TestChatMLFormat:
    """Tests for ChatML format compatibility."""

    def test_chatml_structure(self):
        """Test ChatML output structure."""
        generator = SFTDataGenerator()
        example = generator.generate_example()
        chatml = example.to_chatml()

        # TRL SFTTrainer expects this structure
        assert "messages" in chatml
        assert isinstance(chatml["messages"], list)
        assert len(chatml["messages"]) >= 2

        # Each message should have role and content
        for msg in chatml["messages"]:
            assert "role" in msg
            assert "content" in msg
            assert msg["role"] in ["system", "user", "assistant"]

    def test_chatml_weight_field(self):
        """Test weight field in ChatML output."""
        generator = SFTDataGenerator()
        example = TrainingExample(
            messages=[
                {"role": "user", "content": "Test"},
                {"role": "assistant", "content": "Response"},
            ],
            weight=3.5,
        )

        chatml = example.to_chatml()
        assert chatml["weight"] == 3.5

    def test_jsonl_parseable(self):
        """Test JSONL output is parseable."""
        generator = SFTDataGenerator()
        examples = generator.generate_dataset(count=20)

        for example in examples:
            jsonl = example.to_jsonl()
            # Should not raise
            data = json.loads(jsonl)
            assert "messages" in data


class TestCategoryDistribution:
    """Tests for category distribution in generated data."""

    def test_diverse_categories(self):
        """Test that generated data has diverse categories."""
        generator = SFTDataGenerator()
        examples = generator.generate_dataset(count=200)

        categories = set(e.category for e in examples)
        # Should have at least 4 different categories
        assert len(categories) >= 4

    def test_identity_examples_frequency(self):
        """Test identity examples appear frequently."""
        generator = SFTDataGenerator()
        examples = generator.generate_dataset(count=200)

        identity_count = sum(1 for e in examples if e.category == "identity")
        # Identity examples should be ~25% of dataset
        assert 0.15 <= identity_count / len(examples) <= 0.35


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
