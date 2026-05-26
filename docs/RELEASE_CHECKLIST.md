# Release Checklist

Use this checklist before tagging a GitHub release or refreshing the Hugging
Face dataset.

## Local Verification

```bash
python -m pytest -q
python scripts/convert_to_hf.py
python -m build
```

Confirm the wheel contains the root pipeline modules:

```bash
python - <<'PY'
from pathlib import Path
import zipfile

wheel = next(Path("dist").glob("*.whl"))
names = set(zipfile.ZipFile(wheel).namelist())
required = {"models.py", "risk_model.py", "run.py", "behavior_analysis.py"}
missing = sorted(required - names)
print(f"{wheel}: missing={missing}")
raise SystemExit(1 if missing else 0)
PY
```

## Public Artifact Boundary

Confirm private artifacts are absent from Git status, source distributions, and
Hugging Face upload contents:

- `.env`
- `data/raw/query_bank.json`
- `data/raw/query_bank_draft.json`
- `data/raw/calibration_set.json`
- `data/processed/evaluation_results_*.json`
- `data/processed/eval_*_partial.json`
- `results/policy_briefs/detailed_brief.md`
- Raw per-query model responses

## GitHub Release

- Verify `README.md` states the evaluation snapshot date
- Verify `CITATION.cff` version and release date are current
- Verify CI passes on the target branch
- Tag from a clean working tree

## Hugging Face Refresh

- Regenerate `hf_data/` with `python scripts/convert_to_hf.py`
- Inspect `hf_data/README.md` for dataset configs and aggregate-only scope
- Upload only `hf_data/` contents
- Verify the Dataset Viewer exposes the four CSV configs
