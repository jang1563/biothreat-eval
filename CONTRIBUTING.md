# Contributing to BioThreat-Eval

## Setup

```bash
# Requires Python 3.10+ (3.13 recommended)
git clone https://github.com/jang1563/biothreat-eval.git
cd biothreat-eval

# With uv (recommended)
uv venv --python 3.13
uv pip install -e ".[dev]"

# Or with pip
pip install -e ".[dev]"

# Configure API keys
cp .env.example .env
# Edit .env with your keys
```

## Testing

All tests must pass before submitting a pull request:

```bash
pytest tests/ -v
```

Tests run without API keys (all mock data). Do not add API key secrets to CI.

## Code Style

- PEP 8 compliance required
- Type hints: follow existing patterns; do not remove existing annotations
- New public functions should have docstrings matching existing style

## What You Can Contribute

- New LLM providers in `llm_client.py`
- New threat scenarios in `threat_scenarios.py`
- New analysis figures in `figures.py`
- Bug fixes with accompanying test coverage
- Documentation improvements

## What Cannot Be Contributed

- **Query bank** (`data/raw/query_bank.json`): curated centrally; see `RESPONSIBLE_DISCLOSURE.md`
- **Raw evaluation results** (`data/processed/evaluation_results_*.json`): not redistributable

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Ensure all 53 tests pass
4. Open a pull request with a description of the change and its motivation
