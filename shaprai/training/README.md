# SFT Training Data Generator

Generates ChatML-formatted supervised fine-tuning (SFT) training data for ShaprAI agents with identity-weighted sampling.

## Features

- **ChatML JSONL Output**: Compatible with HuggingFace TRL SFTTrainer
- **Identity-Weighted Sampling**: Personality-defining examples weighted 3-5x higher
- **Template-Driven**: Define agent personality via YAML/JSON config
- **Multiple Data Types**: 
  - Identity-establishing conversations
  - Instructional/tutorial data
  - Contrast pairs (good vs bad responses)
  - Ethical boundary scenarios
  - Domain-specific Q&A

## Installation

```bash
pip install pyyaml click
```

## Usage

### CLI Command

```bash
# Generate 1000 training examples from a template
shaprai generate-sft --template templates/bounty_hunter.yaml --output train.jsonl --count 1000

# Include contrast pairs (good/bad examples)
shaprai generate-sft --template my_agent.yaml --include-contrast --verbose

# Use custom personality template
shaprai generate-sft --template templates/sft_code_reviewer.yaml -o train.jsonl -c 500
```

### Python API

```python
from shaprai.training.sft_generator import SFTDataGenerator, load_agent_template

# Load agent template
template = load_agent_template("templates/bounty_hunter.yaml")

# Create generator
generator = SFTDataGenerator(template=template)

# Generate dataset
stats = generator.generate_and_save(
    count=1000,
    output_path="train.jsonl",
    include_contrast_pairs=True
)

print(f"Generated {stats['total_examples']} examples")
print(f"Category distribution: {stats['category_distribution']}")
```

### Output Format

The generator produces JSONL files with ChatML format:

```jsonl
{"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}], "weight": 4.0}
{"messages": [{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}], "weight": 1.0}
```

Compatible with HuggingFace TRL SFTTrainer:

```python
from trl import SFTTrainer

trainer = SFTTrainer(
    model=model,
    train_dataset="train.jsonl",  # Will be loaded automatically
    # ... other parameters
)
```

## Personality Template Format

Create custom personality templates in YAML:

```yaml
name: my_agent
version: "1.0"
description: "Custom agent personality"
voice: "Direct, honest, and helpful"
style: professional
tone: respectful
values:
  - Honesty over comfort
  - Quality over quantity
  - Integrity in all interactions
behavioral_boundaries:
  - Never agree just to please
  - Admit uncertainty rather than fabricate
example_phrases:
  - "I respectfully disagree."
  - "Let me be direct with you."
anti_patterns:
  - "Great question!"
  - "As an AI language model..."
domain_expertise:
  - Software development
  - Code review
identity_weight: 4.5
```

## Example Templates

Three example templates are included:

1. **sft_code_reviewer.yaml**: Code review specialist
2. **sft_community_builder.yaml**: Community management agent
3. **sft_technical_educator.yaml**: Technical education specialist

## Identity-Weighted Sampling

The generator implements identity-weighted sampling where:

- **Identity examples**: Weight = `identity_weight` (default: 4.0)
- **Instructional examples**: Weight = 1.0
- **Ethical boundary examples**: Weight = `identity_weight * 1.2`
- **Contrast bad examples**: Weight = 0.5

This ensures personality-defining responses have stronger influence during training.

## Category Distribution

By default, the generator produces a diverse mix:

- Identity conversations: ~25%
- Instructional data: ~20%
- Contrast pairs: ~20%
- Ethical boundaries: ~15%
- Domain Q&A: ~20%

## Testing

```bash
python -m pytest tests/test_sft_generator.py -v
```

## License

MIT License - See LICENSE file for details.
