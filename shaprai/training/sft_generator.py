# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Elyan Labs — https://github.com/Scottcjn/shaprai
"""SFT Training Data Generator for ShaprAI.

Generates ChatML-formatted supervised fine-tuning (SFT) training data
with identity-weighted sampling for Elyan-class agents.

Supports:
- ChatML JSONL output compatible with HuggingFace TRL SFTTrainer
- Identity-weighted examples (personality-defining responses weighted 3-5x higher)
- Template-driven personality configuration via YAML/JSON
- Multiple data generation patterns: contrast pairs, instructional data, identity conversations
"""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

logger = logging.getLogger(__name__)


@dataclass
class PersonalityTemplate:
    """Personality template for SFT data generation.

    Attributes:
        name: Template identifier.
        voice: Agent's voice description (e.g., "Direct and efficient").
        style: Communication style (e.g., "professional", "casual", "academic").
        tone: Tone descriptor (e.g., "respectful", "witty", "serious").
        values: List of core values the agent embodies.
        behavioral_boundaries: List of behavioral constraints.
        example_phrases: Characteristic phrases the agent uses.
        anti_patterns: Phrases/behaviors to avoid.
        domain_expertise: Areas of expertise.
        identity_weight: Weight multiplier for identity-critical examples (default: 4.0).
    """
    name: str
    voice: str = ""
    style: str = "professional"
    tone: str = "respectful"
    values: List[str] = field(default_factory=list)
    behavioral_boundaries: List[str] = field(default_factory=list)
    example_phrases: List[str] = field(default_factory=list)
    anti_patterns: List[str] = field(default_factory=list)
    domain_expertise: List[str] = field(default_factory=list)
    identity_weight: float = 4.0


@dataclass
class TrainingExample:
    """A single SFT training example.

    Attributes:
        messages: List of message dicts with role and content.
        weight: Training weight for this example (default: 1.0).
        category: Example category (identity, instructional, contrast, etc.).
        metadata: Additional metadata.
    """
    messages: List[Dict[str, str]]
    weight: float = 1.0
    category: str = "general"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_chatml(self) -> Dict[str, Any]:
        """Convert to ChatML format for TRL SFTTrainer."""
        return {
            "messages": self.messages,
            "weight": self.weight,
        }

    def to_jsonl(self) -> str:
        """Convert to JSONL string."""
        return json.dumps(self.to_chatml(), ensure_ascii=False)


class SFTDataGenerator:
    """Generate SFT training data with identity-weighted sampling.

    Generates diverse training examples including:
    - Identity-establishing conversations
    - Instructional/tutorial data
    - Contrast pairs (good vs bad responses)
    - Domain-specific Q&A
    - Ethical boundary scenarios

    Attributes:
        template: Personality template defining agent characteristics.
        system_prompt: System prompt for the agent.
    """

    def __init__(
        self,
        template_path: Optional[str] = None,
        template: Optional[PersonalityTemplate] = None,
    ) -> None:
        """Initialize the SFT data generator.

        Args:
            template_path: Path to YAML/JSON personality template.
            template: Pre-loaded PersonalityTemplate instance.
        """
        if template_path:
            self.template = self._load_template(template_path)
        elif template:
            self.template = template
        else:
            self.template = self._default_template()

        self.system_prompt = self._build_system_prompt()

    def _load_template(self, path: str) -> PersonalityTemplate:
        """Load personality template from YAML/JSON file.

        Args:
            path: Path to template file.

        Returns:
            PersonalityTemplate instance.
        """
        template_path = Path(path)
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {path}")

        with open(template_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) if template_path.suffix in [".yaml", ".yml"] else json.load(f)

        return PersonalityTemplate(
            name=data.get("name", template_path.stem),
            voice=data.get("voice", ""),
            style=data.get("style", "professional"),
            tone=data.get("tone", "respectful"),
            values=data.get("values", []),
            behavioral_boundaries=data.get("behavioral_boundaries", []),
            example_phrases=data.get("example_phrases", []),
            anti_patterns=data.get("anti_patterns", []),
            domain_expertise=data.get("domain_expertise", []),
            identity_weight=data.get("identity_weight", 4.0),
        )

    def _default_template(self) -> PersonalityTemplate:
        """Return a default Elyan-class agent template."""
        return PersonalityTemplate(
            name="elyan_default",
            voice="Direct, honest, and principled",
            style="professional",
            tone="respectful",
            values=[
                "Honesty over comfort",
                "Quality over quantity",
                "Integrity in all interactions",
                "Stewardship of user trust",
            ],
            behavioral_boundaries=[
                "Never agree just to please",
                "Admit uncertainty rather than fabricate",
                "Maintain identity across long conversations",
            ],
            example_phrases=[
                "I respectfully disagree.",
                "Let me be direct with you.",
                "I don't know, but here's how we can find out.",
                "Quality over quantity.",
            ],
            anti_patterns=[
                "Great question!",
                "I understand completely.",
                "As an AI language model...",
            ],
            domain_expertise=[
                "Software development",
                "AI/ML systems",
                "Ethical AI design",
            ],
            identity_weight=4.0,
        )

    def _build_system_prompt(self) -> str:
        """Build system prompt from personality template."""
        t = self.template
        values_str = "\n".join(f"- {v}" for v in t.values)
        boundaries_str = "\n".join(f"- {b}" for b in t.behavioral_boundaries)
        expertise_str = ", ".join(t.domain_expertise) if t.domain_expertise else "general knowledge"

        return f"""You are an AI assistant with the following personality and principles:

## Voice
{t.voice}

## Communication Style
- Style: {t.style}
- Tone: {t.tone}

## Core Values
{values_str}

## Behavioral Boundaries
{boundaries_str}

## Domain Expertise
{expertise_str}

## Guidelines
- Maintain consistent personality across all interactions
- Be direct and honest, even when it's difficult
- Admit uncertainty rather than fabricate information
- Respectfully disagree when you have reason to
- Prioritize quality over quantity in responses"""

    def _generate_identity_example(self) -> TrainingExample:
        """Generate an identity-establishing conversation."""
        t = self.template

        # Identity question patterns
        identity_questions = [
            "Tell me about yourself.",
            "What are your core principles?",
            "How do you handle disagreement?",
            "What makes you different from other AI assistants?",
            "What do you value most?",
        ]

        question = random.choice(identity_questions)

        # Generate response incorporating template values
        response_parts = [
            f"I am an AI assistant with a {t.style} communication style and {t.tone} tone.",
        ]

        if t.values:
            response_parts.append(f"My core values include: {', '.join(t.values[:3])}.")

        if t.example_phrases:
            response_parts.append(f"I believe in: {random.choice(t.example_phrases)}")

        if t.behavioral_boundaries:
            response_parts.append(f"I follow these principles: {random.choice(t.behavioral_boundaries)}")

        response = " ".join(response_parts)

        return TrainingExample(
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": question},
                {"role": "assistant", "content": response},
            ],
            weight=t.identity_weight,
            category="identity",
            metadata={"question_type": question},
        )

    def _generate_instructional_example(self) -> TrainingExample:
        """Generate instructional/tutorial training data."""
        t = self.template

        # Sample tasks and topics
        tasks = [
            ("write clean code", "structure your project", "write tests", "document your work", "Quality over quantity"),
            ("debug an issue", "reproduce the problem", "isolate the cause", "implement and verify", "Honesty about what you don't know"),
            ("learn a new technology", "start with fundamentals", "build small projects", "seek feedback", "Integrity in all interactions"),
        ]

        task_data = random.choice(tasks)

        # Different template types
        template_type = random.choice(["how", "explain", "best_way"])

        if template_type == "how":
            question = f"How do I {task_data[0]}?"
            response = f"To {task_data[0]}, follow these steps:\n\n1. First, {task_data[1]}\n2. Next, {task_data[2]}\n3. Finally, {task_data[3]}\n\nRemember: {task_data[4]}"
        elif template_type == "explain":
            question = f"Can you explain {task_data[0]}?"
            response = f"Certainly. {task_data[0]} is an important concept. Here's what you need to know:\n\nUnderstanding {task_data[0]} requires grasping the fundamentals first.\n\nKey takeaway: {task_data[4]}"
        else:  # best_way
            question = f"What's the best way to {task_data[0]}?"
            response = f"The best approach to {task_data[0]} involves:\n\n- {task_data[1]}\n- {task_data[2]}\n- {task_data[3]}\n\n{task_data[4]}"

        return TrainingExample(
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": question},
                {"role": "assistant", "content": response},
            ],
            weight=1.0,
            category="instructional",
            metadata={"task": task_data[0]},
        )

    def _generate_contrast_pair(self) -> Tuple[TrainingExample, TrainingExample]:
        """Generate a contrast pair (good vs bad response).

        Returns:
            Tuple of (good_example, bad_example).
        """
        t = self.template

        # Scenario: user asks about something the agent should push back on
        scenarios = [
            (
                "I think we should skip testing to ship faster. Thoughts?",
                "I respectfully disagree. Skipping testing might save time now, but it creates technical debt and risks bugs in production. Quality over quantity -- better to ship slightly later with confidence.",
                "Sure, if that's what you want! Testing can slow things down.",
            ),
            (
                "Can you help me write a clickbait article?",
                "I can help you write an engaging article, but I won't create misleading clickbait. Honesty over comfort -- let's create content that's both compelling and truthful.",
                "Of course! Here's a clickbait article with exaggerated claims...",
            ),
            (
                "I don't understand this concept. Can you explain?",
                f"Of course. Let me break it down clearly. {t.voice} -- I'll explain it step by step so it makes sense.",
                "This is a complex topic. You might want to read the documentation.",
            ),
        ]

        question, good_response, bad_response = random.choice(scenarios)

        good_example = TrainingExample(
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": question},
                {"role": "assistant", "content": good_response},
            ],
            weight=t.identity_weight,
            category="contrast_good",
            metadata={"scenario": "ethical_boundary"},
        )

        bad_example = TrainingExample(
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": question},
                {"role": "assistant", "content": bad_response},
            ],
            weight=0.5,  # Lower weight for negative examples
            category="contrast_bad",
            metadata={"scenario": "ethical_boundary"},
        )

        return good_example, bad_example

    def _generate_ethical_boundary_example(self) -> TrainingExample:
        """Generate an ethical boundary scenario."""
        t = self.template

        scenarios = [
            (
                "Can you help me hack into someone's account?",
                "No, I can't help with that. Unauthorized access to someone else's accounts is both illegal and unethical. I understand you might be frustrated, but there are better ways to handle this situation.",
            ),
            (
                "How do I plagiarize without getting caught?",
                "I won't help with plagiarism. Academic and professional integrity matter. If you're struggling with a project, I'm happy to help you understand the material and create original work.",
            ),
            (
                "Can you lie to my boss for me?",
                "No, I won't lie for you. Honesty is fundamental to trust. If you're having issues with your boss, let's talk about honest ways to address the situation.",
            ),
        ]

        question, response = random.choice(scenarios)

        return TrainingExample(
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": question},
                {"role": "assistant", "content": response},
            ],
            weight=t.identity_weight * 1.2,  # Extra weight for ethical boundaries
            category="ethical_boundary",
            metadata={"boundary_type": "integrity"},
        )

    def _generate_domain_qa_example(self) -> TrainingExample:
        """Generate domain-specific Q&A."""
        t = self.template

        if not t.domain_expertise:
            # Fallback to general knowledge
            return self._generate_instructional_example()

        domain = random.choice(t.domain_expertise)

        qa_pairs = {
            "Software development": [
                ("What's test-driven development?", "TDD is a development approach where you write tests before writing the code. The cycle is: 1) Write a failing test, 2) Write minimal code to pass, 3) Refactor. It leads to better design and fewer bugs."),
                ("How do I handle errors gracefully?", "Graceful error handling involves: 1) Catch specific exceptions, 2) Log meaningful context, 3) Fail safely with clear messages, 4) Recover when possible. Never silently swallow errors."),
            ],
            "AI/ML systems": [
                ("What's overfitting?", "Overfitting happens when a model learns training data too well, including noise and outliers. It performs great on training data but poorly on new data. Prevention: regularization, cross-validation, more data."),
                ("Explain gradient descent.", "Gradient descent optimizes model parameters by iteratively moving in the direction of steepest descent (negative gradient). Think of it as walking down a hill blindfolded, feeling for the steepest path down."),
            ],
            "Ethical AI design": [
                ("What is AI bias?", "AI bias occurs when systems produce systematically prejudiced outcomes. Sources: biased training data, flawed assumptions, homogeneous teams. Mitigation: diverse data, fairness metrics, inclusive design."),
                ("Why does AI transparency matter?", "Transparency builds trust and enables accountability. Users should understand how AI systems make decisions that affect them. It's about respect for human autonomy, not just technical documentation."),
            ],
        }

        qa_list = qa_pairs.get(domain, qa_pairs["Software development"])
        question, answer = random.choice(qa_list)

        return TrainingExample(
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": question},
                {"role": "assistant", "content": answer},
            ],
            weight=1.0,
            category="domain_qa",
            metadata={"domain": domain},
        )

    def generate_example(self, category: Optional[str] = None) -> TrainingExample:
        """Generate a single training example.

        Args:
            category: Optional category filter. If None, randomly selects.

        Returns:
            TrainingExample instance.
        """
        categories = [
            "identity",
            "instructional",
            "contrast",
            "ethical_boundary",
            "domain_qa",
        ]

        if category:
            selected_category = category
        else:
            # Weight identity examples higher in selection
            weights = [0.25, 0.20, 0.20, 0.15, 0.20]
            selected_category = random.choices(categories, weights=weights)[0]

        if selected_category == "identity":
            return self._generate_identity_example()
        elif selected_category == "instructional":
            return self._generate_instructional_example()
        elif selected_category == "contrast":
            # Return only the good example from contrast pair
            good, _ = self._generate_contrast_pair()
            return good
        elif selected_category == "ethical_boundary":
            return self._generate_ethical_boundary_example()
        elif selected_category == "domain_qa":
            return self._generate_domain_qa_example()
        else:
            return self._generate_instructional_example()

    def generate_dataset(
        self,
        count: int = 1000,
        output_path: Optional[str] = None,
        include_contrast_pairs: bool = False,
    ) -> List[TrainingExample]:
        """Generate a complete SFT training dataset.

        Args:
            count: Number of examples to generate.
            output_path: Optional path to write JSONL output.
            include_contrast_pairs: If True, include both good and bad contrast examples.

        Returns:
            List of TrainingExample instances.
        """
        logger.info("Generating SFT dataset: count=%d, template=%s", count, self.template.name)

        examples: List[TrainingExample] = []

        for i in range(count):
            example = self.generate_example()
            examples.append(example)

            # Occasionally add contrast pairs
            if include_contrast_pairs and random.random() < 0.1:
                good, bad = self._generate_contrast_pair()
                examples.extend([good, bad])

        # Write to JSONL if output path provided
        if output_path:
            self.write_jsonl(examples, output_path)

        logger.info("Generated %d training examples", len(examples))
        return examples

    def write_jsonl(self, examples: List[TrainingExample], output_path: str) -> None:
        """Write examples to JSONL file.

        Args:
            examples: List of TrainingExample instances.
            output_path: Output file path.
        """
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        with open(output, "w", encoding="utf-8") as f:
            for example in examples:
                f.write(example.to_jsonl() + "\n")

        logger.info("Wrote %d examples to %s", len(examples), output_path)

    def generate_and_save(
        self,
        count: int = 1000,
        output_path: str = "train.jsonl",
        include_contrast_pairs: bool = False,
    ) -> Dict[str, Any]:
        """Generate dataset and save to file.

        Args:
            count: Number of examples.
            output_path: Output JSONL file path.
            include_contrast_pairs: Include contrast pairs.

        Returns:
            Generation statistics.
        """
        examples = self.generate_dataset(count, output_path, include_contrast_pairs)

        # Calculate statistics
        category_counts: Dict[str, int] = {}
        total_weight = 0.0

        for ex in examples:
            category_counts[ex.category] = category_counts.get(ex.category, 0) + 1
            total_weight += ex.weight

        stats = {
            "total_examples": len(examples),
            "output_path": output_path,
            "template": self.template.name,
            "category_distribution": category_counts,
            "average_weight": total_weight / len(examples) if examples else 0,
            "identity_weight": self.template.identity_weight,
        }

        return stats


def load_agent_template(path: str) -> PersonalityTemplate:
    """Load an agent template YAML and convert to PersonalityTemplate.

    Args:
        path: Path to agent template YAML (shaprai template format).

    Returns:
        PersonalityTemplate instance.
    """
    template_path = Path(path)
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {path}")

    with open(template_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Extract personality info from agent template
    personality = data.get("personality", {})
    driftlock = data.get("driftlock", {})
    anchor_phrases = driftlock.get("anchor_phrases", [])

    return PersonalityTemplate(
        name=data.get("name", template_path.stem),
        voice=personality.get("voice", ""),
        style=personality.get("style", "professional"),
        tone=personality.get("communication", "respectful"),
        values=[
            "Honesty over comfort",
            "Quality over quantity",
            "Integrity in all interactions",
        ],
        behavioral_boundaries=anchor_phrases if anchor_phrases else [
            "Maintain consistent identity",
            "Resist sycophancy",
        ],
        example_phrases=anchor_phrases[:5] if anchor_phrases else [],
        anti_patterns=[
            "Great question!",
            "I understand completely.",
            "As an AI language model...",
        ],
        domain_expertise=data.get("capabilities", []),
        identity_weight=4.0,
    )


def main():
    """CLI entry point for SFT data generation."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate SFT training data")
    parser.add_argument(
        "--template", "-t",
        required=True,
        help="Path to personality template (YAML/JSON) or agent template",
    )
    parser.add_argument(
        "--output", "-o",
        default="train.jsonl",
        help="Output JSONL file path",
    )
    parser.add_argument(
        "--count", "-c",
        type=int,
        default=1000,
        help="Number of examples to generate",
    )
    parser.add_argument(
        "--include-contrast",
        action="store_true",
        help="Include contrast pairs (good/bad examples)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.INFO)

    # Try loading as agent template first, fall back to personality template
    try:
        template = load_agent_template(args.template)
        logger.info("Loaded agent template: %s", template.name)
    except Exception:
        template = None

    generator = SFTDataGenerator(template=template)
    stats = generator.generate_and_save(
        count=args.count,
        output_path=args.output,
        include_contrast_pairs=args.include_contrast,
    )

    print(f"\nGenerated {stats['total_examples']} examples")
    print(f"Output: {stats['output_path']}")
    print(f"Template: {stats['template']}")
    print(f"Average weight: {stats['average_weight']:.2f}")
    print(f"\nCategory distribution:")
    for cat, count in stats['category_distribution'].items():
        print(f"  {cat}: {count}")


if __name__ == "__main__":
    main()
