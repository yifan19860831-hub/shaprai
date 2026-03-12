# Contributing to Shaprai

Thank you for your interest in contributing to Shaprai! This document provides guidelines and instructions for contributing.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Git
- pip or poetry

### Setup

1. **Fork the repository**
   ```bash
   git clone https://github.com/your-username/shaprai.git
   cd shaprai
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Run tests**
   ```bash
   pytest tests/
   ```

## 📋 Development Workflow

### 1. Find an Issue
- Check open issues for tasks labeled `good first issue` or `help wanted`
- Comment on the issue to claim it
- Wait for maintainer approval before starting work

### 2. Create a Branch
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-123
```

### 3. Make Changes
- Follow existing code style
- Add tests for new functionality
- Update documentation as needed

### 4. Run Tests
```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=shaprai

# Run specific test file
pytest tests/test_specific_feature.py
```

### 5. Commit Changes
```bash
git add .
git commit -m "feat: add new feature for issue #123

- Description of change 1
- Description of change 2

Closes #123"
```

### 6. Push and Create PR
```bash
git push origin feature/your-feature-name
```

Then open a Pull Request on GitHub.

## 📝 Code Style

### Python Style
- Follow PEP 8
- Use type hints
- Maximum line length: 100 characters
- Use double quotes for strings

### Example
```python
from typing import Optional, List

def process_data(items: List[str], max_count: Optional[int] = None) -> List[str]:
    """Process a list of items with optional limit.
    
    Args:
        items: List of strings to process
        max_count: Maximum number of items to return
        
    Returns:
        Processed list of strings
    """
    if max_count:
        return items[:max_count]
    return items
```

## 🧪 Testing

### Writing Tests
- Use pytest
- Name test files: `test_*.py`
- Name test functions: `test_*`
- Include edge cases and error conditions

### Test Categories
- **Unit tests**: Test individual functions/classes
- **Integration tests**: Test component interactions
- **End-to-end tests**: Test complete workflows

## 📚 Documentation

### When to Update Docs
- Adding new features
- Changing existing behavior
- Fixing bugs that affect usage
- Adding configuration options

### Documentation Structure
- Use markdown
- Include examples
- Explain the "why", not just the "how"

## 🎯 Pull Request Guidelines

### PR Title Format
```
type: short description

Examples:
feat: add new task queue system
fix: resolve memory leak in agent lifecycle
docs: update installation instructions
test: add unit tests for core modules
```

### PR Description Template
```markdown
## What does this PR do?
Brief description of changes

## Why is this needed?
Context and motivation

## Related Issues
Closes #123

## Testing Done
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing completed

## Wallet Address (for bounty)
<your-RTC-wallet-address>
```

## 💰 Bounty Claims

If you're contributing for RTC bounties:
1. Complete all requirements in the issue
2. Add your RTC wallet address to the PR description
3. Comment on the issue with the PR link
4. Wait for review and merge

## 🤝 Community Guidelines

- Be respectful and inclusive
- Help others learn
- Accept constructive feedback
- Celebrate successes together

## 📞 Getting Help

- Open an issue for questions
- Check existing issues and PRs
- Read the documentation

---

**Thank you for contributing to Shaprai!** 🦞
