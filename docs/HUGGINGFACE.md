# Hugging Face Release Checklist

This repository publishes only aggregate, public-safe evaluation artifacts to
Hugging Face. The generated `hf_data/` directory is the upload source.

## Build the Dataset Artifact

Use the same Python environment that passes the test suite:

```bash
python -m pytest -q
python scripts/convert_to_hf.py
```

Expected generated files:

- `hf_data/README.md`
- `hf_data/behavioral_profiles.csv`
- `hf_data/risk_assessment.csv`
- `hf_data/uplift_results.csv`
- `hf_data/policy_recommendations.csv`
- `hf_data/figures/*.png`

## Pre-Upload Safety Check

Before upload, confirm the artifact contains aggregate outputs only:

```bash
find hf_data -type f | sort
```

Do not upload:

- `.env`
- `data/raw/query_bank.json`
- `data/raw/query_bank_draft.json`
- `data/raw/calibration_set.json`
- `data/processed/evaluation_results_*.json`
- `data/processed/eval_*_partial.json`
- Raw model responses
- Detailed restricted policy briefs

## Upload

From the repository root:

```bash
huggingface-cli upload jang1563/biothreat-eval hf_data . \
  --repo-type dataset \
  --commit-message "Refresh aggregate BioThreat-Eval dataset"
```

The dataset card defines separate Viewer configs for behavioral profiles, risk
assessment, uplift results, and policy recommendations.

## Post-Upload Smoke Check

After upload, verify the Hugging Face dataset page shows:

- License: MIT
- Dataset Viewer configs for all four CSV tables
- No query texts, raw responses, calibration rows, API keys, or restricted
  detailed briefs
- Source-code link back to the GitHub repository
