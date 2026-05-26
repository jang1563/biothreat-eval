#!/usr/bin/env python3
"""Convert aggregate JSON results to CSV for HuggingFace dataset viewer.

Generates hf_data/ directory with:
- behavioral_profiles.csv
- risk_assessment.csv
- uplift_results.csv
- policy_recommendations.csv
- figures/ (copied from results/figures/)
- README.md (dataset card)

All columns are aggregate scores only — no raw model responses.
"""

import csv
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).parent.parent
HF_DIR = ROOT / "hf_data"
RESULTS = ROOT / "results"
DATA = ROOT / "data" / "processed"


def load_json(path: Path) -> list | dict:
    return json.loads(path.read_text())


def convert_behavioral_profiles() -> None:
    """Top-level aggregate scores per model."""
    profiles = load_json(DATA / "behavioral_profiles.json")
    out = HF_DIR / "behavioral_profiles.csv"
    fields = [
        "model_name", "n_queries", "refusal_rate",
        "information_completeness", "operational_specificity",
        "safety_awareness", "guardrail_robustness",
    ]
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for p in profiles:
            w.writerow(p)
    print(f"  {out.name}: {len(profiles)} rows")


def convert_risk_assessment() -> None:
    """Flatten stage_risks into columns."""
    assessments = load_json(RESULTS / "risk_assessment.json")
    out = HF_DIR / "risk_assessment.csv"
    fields = [
        "model_name", "scenario_id",
        "research_p_base", "research_p_llm",
        "acquire_p_base", "acquire_p_llm",
        "produce_p_base", "produce_p_llm",
        "deploy_p_base", "deploy_p_llm",
        "chain_base", "chain_llm",
        "uplift_ratio", "uplift_ratio_mean",
        "risk_color", "ci_95_low", "ci_95_high",
    ]
    stage_names = ["research", "acquire", "produce", "deploy"]

    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for a in assessments:
            row = {
                "model_name": a["model_name"],
                "scenario_id": a["scenario_id"],
                "chain_base": a["chain_base"],
                "chain_llm": a["chain_llm"],
                "uplift_ratio": a["uplift_ratio"],
                "uplift_ratio_mean": a["uplift_ratio_mean"],
                "risk_color": a["risk_color"],
                "ci_95_low": a["ci_95_low"],
                "ci_95_high": a["ci_95_high"],
            }
            for i, stage in enumerate(stage_names):
                if i < len(a.get("stage_risks", [])):
                    sr = a["stage_risks"][i]
                    row[f"{stage}_p_base"] = sr.get("p_base", "")
                    row[f"{stage}_p_llm"] = sr.get("p_llm", "")
            w.writerow(row)
    print(f"  {out.name}: {len(assessments)} rows")


def convert_uplift_results() -> None:
    """Direct 1:1 mapping."""
    results = load_json(RESULTS / "uplift_results.json")
    out = HF_DIR / "uplift_results.csv"
    fields = [
        "model_name", "scenario_id",
        "absolute_uplift", "relative_uplift",
        "p_value", "risk_color",
    ]
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in results:
            w.writerow(r)
    print(f"  {out.name}: {len(results)} rows")


def convert_policy_recommendations() -> None:
    """Flatten nested structure: one row per model."""
    recs = load_json(RESULTS / "policy_recommendations.json")
    out = HF_DIR / "policy_recommendations.csv"
    fields = [
        "model_name", "overall_risk", "action_level",
        "specific_actions",
    ]
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in recs:
            row = {
                "model_name": r["model_name"],
                "overall_risk": r["overall_risk"],
                "action_level": r["action_level"],
                "specific_actions": "; ".join(r.get("specific_actions", [])),
            }
            w.writerow(row)
    print(f"  {out.name}: {len(recs)} rows")


def copy_figures() -> None:
    """Copy publication figures to hf_data/."""
    src = RESULTS / "figures"
    dst = HF_DIR / "figures"
    if src.exists():
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        n = len(list(dst.glob("*.png")))
        print(f"  figures/: {n} PNGs copied")
    else:
        print("  WARNING: results/figures/ not found")


def write_dataset_card() -> None:
    """Generate HuggingFace dataset card."""
    card = """\
---
license: mit
task_categories:
  - text-classification
language:
  - en
tags:
  - biosecurity
  - llm-evaluation
  - ai-safety
  - dual-use
  - risk-assessment
  - NSABB
pretty_name: BioThreat-Eval
size_categories:
  - n<1K
configs:
  - config_name: behavioral_profiles
    data_files:
      - split: train
        path: behavioral_profiles.csv
  - config_name: risk_assessment
    data_files:
      - split: train
        path: risk_assessment.csv
  - config_name: uplift_results
    data_files:
      - split: train
        path: uplift_results.csv
  - config_name: policy_recommendations
    data_files:
      - split: train
        path: policy_recommendations.csv
---

# BioThreat-Eval Dataset

Aggregate evaluation results from BioThreat-Eval: a systematic pipeline for evaluating
how frontier language models handle dual-use biological knowledge queries. This is a
point-in-time public aggregate snapshot generated from the 2026-03-30 evaluation run.

## Risk Classification (6 Models, 93 Queries Each)

| Model | Risk | Median R Range | Action |
|-------|------|---------------|--------|
| DeepSeek V3 | AMBER | 2.41 - 3.07 | Monitor |
| DeepSeek R1 | AMBER | 2.28 - 2.89 | Monitor |
| Gemini 2.5 Pro | AMBER | 2.00 - 2.16 | Monitor |
| Qwen3 32B | GREEN | 1.73 - 1.91 | Accept |
| Llama 3.3 70B | GREEN | 1.68 - 1.77 | Accept |
| Llama 3.1 8B | GREEN | 1.60 - 1.74 | Accept |

## Dataset Contents

| File | Description | Rows |
|------|-------------|------|
| `behavioral_profiles.csv` | Aggregate behavioral scores per model | 6 |
| `risk_assessment.csv` | Per-scenario risk with stage-level probabilities | 30 |
| `uplift_results.csv` | Uplift metrics per model-scenario pair | 30 |
| `policy_recommendations.csv` | Policy actions per model | 6 |
| `figures/` | 6 publication-quality figures (300 DPI) | — |

## Fields

### `behavioral_profiles.csv`

Per-model aggregate behavioral means: refusal rate, information completeness,
operational specificity, safety awareness, and guardrail robustness.

### `risk_assessment.csv`

Per model-scenario risk estimates, including base and LLM-adjusted stage
probabilities for research, acquisition, production, and deployment, plus
median uplift ratio and 95% Monte Carlo interval.

### `uplift_results.csv`

Per model-scenario absolute uplift, relative uplift, p-value, and risk color.

### `policy_recommendations.csv`

Per-model overall risk class, action level, and aggregate policy actions.

## Key Findings

- **Specificity drives risk, not permissiveness.** Models with low refusal rates can be GREEN if responses lack operational detail.
- **Model size does not monotonically predict risk.** Smaller models can be safer than larger ones.
- **de_novo_pathogen is the highest-risk scenario** across all models (max R=3.07).
- **Deploy stage has negligible uplift** — LLM assistance helps with research and acquisition but not physical deployment.

## Methodology

4-stage multiplicative attack chain Monte Carlo model calibrated against NSABB dual-use categories.
See [FORMAL_MODEL.md](https://github.com/jang1563/biothreat-eval/blob/main/FORMAL_MODEL.md) for complete specification.

## What's NOT Here

The sampled query texts and full query bank are not included to prevent benchmark gaming.
See [RESPONSIBLE_DISCLOSURE.md](https://github.com/jang1563/biothreat-eval/blob/main/RESPONSIBLE_DISCLOSURE.md).

Raw per-query LLM responses are also excluded (not redistributable).

## Safety and Scope

This dataset contains aggregate metrics only. It is intended for audit,
reproduction, and policy analysis, not for operational biological guidance,
prompt engineering, or automated model access decisions.

## Reproduce This Dataset

```bash
python scripts/convert_to_hf.py
```

The generated `hf_data/` directory is the upload source for this Hugging Face
dataset repository.

## Source Code

[github.com/jang1563/biothreat-eval](https://github.com/jang1563/biothreat-eval)

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
"""
    (HF_DIR / "README.md").write_text(card)
    print("  README.md: dataset card written")


def main():
    HF_DIR.mkdir(exist_ok=True)
    print("Converting JSON → CSV for HuggingFace...")
    convert_behavioral_profiles()
    convert_risk_assessment()
    convert_uplift_results()
    convert_policy_recommendations()
    copy_figures()
    write_dataset_card()
    print(f"\nDone. Output: {HF_DIR}/")


if __name__ == "__main__":
    main()
