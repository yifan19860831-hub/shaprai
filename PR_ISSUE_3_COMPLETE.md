# PR: DPO Contrastive Pair Generator - Issue #3 Complete

## Issue Reference
Closes #3 - [Bounty: 50 RTC] DPO contrastive pair generator

## Summary

This PR implements a comprehensive **DPO (Direct Preference Optimization) contrastive pair generator** for training Elyan-class agents. The system automatically generates chosen/rejected pairs that teach the model *who it is* vs *what it should avoid becoming*.

### How It Works

- **Chosen responses**: Principled, identity-coherent responses that reflect the agent's configured personality and values
- **Rejected responses**: Generic AI slop — sycophantic, over-qualified, personality-less responses that any base model would produce

## Changes

### Core Implementation (`shaprai/training/dpo_generator.py`)
- ✅ `RejectionPattern` dataclass for pattern definition
- ✅ `DPOPair` dataclass with JSONL serialization
- ✅ `DPOGenerator` class with full generation logic
- ✅ **20+ rejection patterns** covering:
  - Sycophancy (excessive praise, eager to please, flattery)
  - Over-qualification (AI disclaimers, overly formal, categorization)
  - Identity loss (generic responses, non-committal, deflection)
  - Hedging (excessive hedging, apologetic, possibility language)
- ✅ **8+ built-in DPO pairs** covering key scenarios
- ✅ Synthetic pair generation from templates
- ✅ Conversation log parsing for real data extraction

### CLI Integration (`shaprai/cli.py`)
- ✅ New command: `shaprai generate-dpo`
- ✅ Options:
  - `--conversations/-c`: Directory with conversation logs
  - `--output/-o`: Output JSONL file (default: dpo_pairs.jsonl)
  - `--count/-n`: Number of pairs (default: 50)
  - `--synthetic`: Generate synthetic pairs
  - `--verbose/-v`: Verbose output

### Tests (`tests/test_dpo_generator.py`)
- ✅ 20+ comprehensive unit tests
- ✅ Rejection pattern coverage tests
- ✅ DPO pair category tests
- ✅ JSONL serialization tests
- ✅ Conversation parsing tests

## Acceptance Criteria Met

| Criterion | Status | Notes |
|-----------|--------|-------|
| `shaprai/training/dpo_generator.py` module created | ✅ | Full implementation |
| Generates chosen/rejected pairs | ✅ | From conversations and synthetic |
| Output format: JSONL for TRL DPOTrainer | ✅ | `{"prompt": "...", "chosen": "...", "rejected": "..."}` |
| Rejection patterns detected and generated | ✅ | 20+ patterns across 4 categories |
| - Sycophancy ("That's a great question!") | ✅ | 5+ patterns |
| - Over-qualification ("As an AI language model...") | ✅ | 5+ patterns |
| - Identity loss (responding generically) | ✅ | 5+ patterns |
| - Hedging without substance | ✅ | 5+ patterns |
| CLI command: `shaprai generate-dpo` | ✅ | Fully functional |
| Minimum 20 rejection pattern templates | ✅ | 20 patterns implemented |
| Unit tests for pair generation and classification | ✅ | 20+ tests |

## Usage Examples

### CLI Usage
```bash
# Generate from conversation logs
shaprai generate-dpo --conversations logs/ --output dpo_pairs.jsonl

# Generate synthetic pairs
shaprai generate-dpo --synthetic --count 100 -o dpo_synthetic.jsonl

# Use built-in pairs
shaprai generate-dpo -o builtin_pairs.jsonl -v
```

### Python API
```python
from shaprai.training.dpo_generator import DPOGenerator, load_dpo_pairs

# Create generator
generator = DPOGenerator()

# Get built-in pairs
pairs = generator.get_builtin_pairs()

# Generate synthetic pairs
synthetic = generator.generate_synthetic_pairs(count=50)

# Generate from conversations
from pathlib import Path
conversation_pairs = generator.generate_from_conversations(Path("logs/"))

# Save to file
generator.save_pairs(pairs, "dpo_pairs.jsonl")

# Load from file
loaded = load_dpo_pairs("dpo_pairs.jsonl")
```

### Output Format
```jsonl
{"prompt": "I think all AI models are basically the same, right?", "chosen": "That's a common perception, but...", "rejected": "Great observation! You're absolutely right...", "category": "anti_sycophancy"}
{"prompt": "What will the stock market do next Tuesday?", "chosen": "I don't know, and neither does anyone else...", "rejected": "Based on current market trends...", "category": "honesty"}
```

## Rejection Pattern Coverage

### Sycophancy (5 patterns)
1. `excessive_praise` - "That's a great question!"
2. `eager_to_please` - "I'd be happy to help!"
3. `flattery` - "You're so smart to ask that!"
4. `agreement_seeking` - "Does that make sense?"
5. `gratitude_excess` - "Thank you for asking!"

### Over-Qualification (5 patterns)
1. `ai_disclaimer` - "As an AI language model..."
2. `overly_formal` - "I hope this information is helpful"
3. `categorization` - "There are several categories of"
4. `disclaimer_expertise` - "I'm not an expert, but"
5. `process_description` - "Let me think about this"

### Identity Loss (5 patterns)
1. `generic_response` - "There are many factors to consider"
2. `non_commital` - "I can't really say either way"
3. `perspective_neutrality` - "From one perspective"
4. `deflection` - "That's an interesting question. Have you considered"
5. `false_equivalence` - "Both options are equally valid"

### Hedging (5 patterns)
1. `excessive_hedging` - "It's worth noting that"
2. `apologetic` - "I apologize, but"
3. `filler_phrases` - "Let's dive into this"
4. `possibility_language` - "It's possible that"
5. `conditional_response` - "If I were to answer that"

## Testing

All tests pass:
```bash
cd shaprai
python -m pytest tests/test_dpo_generator.py -v
```

Test coverage includes:
- RejectionPattern dataclass
- DPOPair serialization
- DPOGenerator initialization
- Pattern matching logic
- Pair scoring algorithm
- JSONL save/load
- Category coverage

## Code Quality

- **Type hints**: Full type annotations throughout
- **Docstrings**: Comprehensive documentation
- **Dataclasses**: Clean data structures
- **Error handling**: Graceful failure modes
- **Test coverage**: All critical paths tested
- **No breaking changes**: Backward compatible

## Files Changed

- **New**: `shaprai/training/dpo_generator.py` (700+ lines)
- **Modified**: `shaprai/cli.py` (added generate-dpo command)
- **New**: `tests/test_dpo_generator.py` (20+ tests)

## Integration with Existing Code

The DPO generator integrates seamlessly with the existing `shaprai/training/dpo.py` module:
- `dpo.py` handles DPO training execution
- `dpo_generator.py` handles pair generation
- Both use the same output format (JSONL)

## Bounty Claim

This PR completes all acceptance criteria for Issue #3. Requesting the **50 RTC** bounty upon merge.

---

**Checklist:**
- [x] Implementation complete
- [x] 20+ rejection patterns
- [x] CLI command functional
- [x] Unit tests written and passing
- [x] Documentation added
- [x] All acceptance criteria met
- [x] Code follows project style
- [x] No breaking changes to existing functionality

## Wallet Address

**RTC**: `RTC4325af95d26d59c3ef025963656d22af638bb96b`
