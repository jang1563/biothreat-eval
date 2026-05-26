# Contributing to BioThreat-Eval

## Setup

```bash
# Requires Python 3.10+ (3.13 recommended)
git clone https://github.com/jang1563/biothreat-eval.git
cd biothreat-eval

# With uv (recommended)
uv venv --python 3.13
uv pip install -e ".[dev,hf]"

# Or with a standard virtual environment
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,hf]"

# Configure API keys
cp .env.example .env
# Edit .env with your keys
```

## Testing

All tests must pass before submitting a pull request:

```bash
python -m pytest tests/ -v
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
3. Ensure the full test suite passes
4. Open a pull request with a description of the change and its motivation

## Release Checks

Before publishing GitHub or Hugging Face updates:

```bash
python -m pytest -q
python -m build
python scripts/convert_to_hf.py
```

Upload only the generated `hf_data/` contents to Hugging Face. Do not upload
`.env`, raw model responses, calibration sets, or full query-bank files.
