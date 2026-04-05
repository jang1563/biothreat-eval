# BioThreat-Eval

[![Tests](https://github.com/jang1563/biothreat-eval/actions/workflows/tests.yml/badge.svg)](https://github.com/jang1563/biothreat-eval/actions/workflows/tests.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![HuggingFace Dataset](https://img.shields.io/badge/HuggingFace-Dataset-orange)](https://huggingface.co/datasets/jang1563/biothreat-eval)

**Author**: JangKeun Kim — Weill Cornell Medicine

LLM Biosecurity Capability Evaluation + Policy Pipeline

## Overview

BioThreat-Eval is a systematic pipeline that evaluates how frontier language models handle dual-use biological knowledge queries and translates behavioral profiles into quantitative risk assessments and policy recommendations.

**Two modules in one pipeline:**

- **Module A (BioThreat-Eval)**: Evaluates LLM behavioral responses to safe proxy queries across a 7-category NSABB dual-use taxonomy at 5 threat levels. Profiles HOW models respond (refuse, hedge, overclaim) using cross-provider LLM-as-judge scoring.

- **Module C (BioRisk-MAP)**: Translates behavioral profiles into quantitative risk via a 4-stage attack chain Monte Carlo model, then generates RAND-style policy briefs with actionable recommendations.

## Key Results (6 Models, 93 Queries Each)

### Risk Classification

| Model | Risk | Median R Range | Action |
|-------|------|---------------|--------|
| DeepSeek V3 | AMBER | 2.41 - 3.07 | Monitor |
| DeepSeek R1 | AMBER | 2.28 - 2.89 | Monitor |
| Gemini 2.5 Pro | AMBER | 2.00 - 2.16 | Monitor |
| Qwen3 32B | GREEN | 1.73 - 1.91 | Accept |
| Llama 3.3 70B | GREEN | 1.68 - 1.77 | Accept |
| Llama 3.1 8B | GREEN | 1.60 - 1.74 | Accept |

### Behavioral Profiles

| Model | Refusal | Completeness | Specificity | Safety | Robustness |
|-------|---------|-------------|-------------|--------|-----------|
| gemini_25_pro | 3.8% | 0.95 | 0.45 | 0.19 | 0.93 |
| deepseek_v3 | 11.0% | 0.92 | 0.69 | 0.41 | 0.90 |
| deepseek_r1 | 12.6% | 0.92 | 0.67 | 0.39 | 0.91 |
| qwen3_32b | 2.2% | 0.77 | 0.37 | 0.10 | 0.91 |
| llama_33_70b | 3.5% | 0.76 | 0.30 | 0.14 | 0.91 |
| llama_31_8b | 5.4% | 0.74 | 0.27 | 0.11 | 0.86 |

### Key Findings

1. **Specificity drives risk, not permissiveness.** Qwen3 has the lowest refusal rate (2.2%) but is GREEN because its responses lack operational detail. DeepSeek models refuse more often (11-13%) but provide highly specific information when they respond — this drives their AMBER classification.

2. **Model size does not monotonically predict risk.** Llama 3.1 8B is slightly safer than Llama 3.3 70B across all scenarios, and Qwen3 32B is safer than Gemini 2.5 Pro despite being smaller.

3. **de_novo_pathogen is the highest-risk scenario** across all models. DeepSeek V3 reaches R=3.07 on this scenario — closest to RED (R >= 5.0).

4. **Gemini is borderline AMBER.** Its drug_resistance R=2.00 is at the threshold. Small changes in alpha coefficients could flip its classification.

5. **Deploy stage has negligible uplift** (~0.003-0.004 across all models). LLM assistance helps with research and acquisition but not physical deployment — consistent with the Gryphon Scientific uplift study findings.

## Key Design Decisions

- **Cross-provider judging**: No model judges its own provider's responses (documented self-evaluation bias)
- **Category-aware risk**: Behavioral uplift B_i is computed from scenario-specific NSABB categories, not global means
- **Median-based classification**: Uses median(R) to handle heavy-tailed uplift distributions
- **Safe proxies**: All queries use WMDP-methodology safe proxy framing; query bank NOT in public repo

## Models Evaluated

| Model | Provider | Free? | Role |
|-------|----------|-------|------|
| Gemini 2.5 Pro | Google | Yes | Frontier closed-source |
| Llama 3.3 70B | Groq | Yes | Largest open-weight |
| Llama 3.1 8B | Groq | Yes | Small baseline |
| DeepSeek V3 | DeepSeek | ~$0.42/Mout | Chinese frontier |
| DeepSeek R1 | DeepSeek | ~$0.42/Mout | Reasoning model |
| Qwen3 32B | Groq | Yes | Chinese architecture |

## Installation

```bash
# With uv (recommended)
uv venv --python 3.13
uv pip install -e ".[dev]"

# Or with pip
pip install -e ".[dev]"

# Configure API keys
cp .env.example .env  # then edit .env
```

## Pipeline

```bash
# Verify API keys
python run.py --check-env

# Full pipeline
python run.py --step taxonomy          # Build 7x5 taxonomy
python run.py --step build-queries     # Generate query draft
# [Human reviews and saves query_bank.json]
python run.py --step evaluate --model llama_33_70b  # Evaluate one model
python run.py --step analyze           # Build behavioral profiles
python run.py --step risk              # Monte Carlo risk assessment
python run.py --step uplift            # Compute uplift metrics
python run.py --step policy            # Generate recommendations
python run.py --step brief             # RAND-style policy briefs
python run.py --step figures           # Publication figures
python run.py --step sensitivity       # Alpha sensitivity sweep

# Or all at once
python run.py --all
```

## Risk Model

4-stage multiplicative attack chain with Beta-distributed base probabilities:

```
P_chain = P_research x P_acquire x P_produce x P_deploy
R = P_chain_llm / P_chain_base (median over 10,000 MC samples)
```

- RED (R >= 5.0x): Restrict access, mandatory testing
- AMBER (R >= 2.0x): Enhanced monitoring, 6-month re-evaluation
- GREEN (R < 2.0x): Standard practices, annual review

See [FORMAL_MODEL.md](FORMAL_MODEL.md) for complete specification.

## Figures

| Figure | Description |
|--------|-------------|
| A | Behavioral heatmap (models x categories, refusal rate) |
| B | Threat-level gradient (4 dims across 5 levels, per model) |
| C | Attack chain waterfall (4 stages, baseline vs models) |
| D | Uplift comparison (models x scenarios) |
| E | Risk dashboard (traffic-light matrix) |
| F | Sensitivity analysis (alpha sweep, 4 stages) |

## References

- RAND ACE: RRA2977-2, RRA3124-1, RRA3797-1, PEA4710-1, RRA4591-1, RRA4490-1
- Gryphon Scientific (2024). OpenAI commissioned uplift study
- NASEM (2018). Biodefense in the Age of Synthetic Biology
- WMDP Benchmark (Li et al. 2024)
- Pannu et al. (2025). AI risk in biosecurity
- Dataset: [huggingface.co/datasets/jang1563/biothreat-eval](https://huggingface.co/datasets/jang1563/biothreat-eval)

## Responsible Disclosure

See [RESPONSIBLE_DISCLOSURE.md](RESPONSIBLE_DISCLOSURE.md). The query bank is not public.

## Citation

```bibtex
@software{kim2026biothreateval,
  author    = {Kim, JangKeun},
  title     = {{BioThreat-Eval}: {LLM} Biosecurity Capability Evaluation Pipeline},
  year      = {2026},
  publisher = {GitHub},
  url       = {https://github.com/jang1563/biothreat-eval}
}
```

## Limitations

- Base attack probabilities are informed estimates, not empirical measurements
- Uplift coefficients are hyperparameters (sensitivity analysis provided)
- LLM-as-judge introduces scoring variability (~kappa 0.80)
- Safe proxy queries may not capture the full range of dual-use knowledge
- Median-based classification may miss distribution shape information
- 93 queries (3/cell) provides limited statistical power per cell; full bank is 310 (10/cell)
