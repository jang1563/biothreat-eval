## Summary

Describe the change and why it is needed.

## Verification

- [ ] `python -m pytest -q`
- [ ] `python scripts/convert_to_hf.py` if public aggregate outputs changed
- [ ] `python -m build` if packaging metadata changed

## Safety Checklist

- [ ] No `.env` or API keys included
- [ ] No full query-bank, calibration-set, or raw per-query response files included
- [ ] No restricted detailed policy brief included
- [ ] Public-facing language preserves the aggregate-only scope

## Release Impact

- [ ] GitHub docs/code only
- [ ] Hugging Face dataset artifact should be refreshed
- [ ] Citation or version metadata should be updated
