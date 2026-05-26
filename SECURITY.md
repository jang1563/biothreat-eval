# Security Policy

BioThreat-Eval is a biosecurity evaluation and policy-analysis pipeline. The
public repository is intentionally scoped to code, aggregate metrics, formal
methods, and public-safe documentation.

## Supported Versions

Security and safety reports are accepted for the current `main` branch.

## Report a Vulnerability or Safety Concern

For sensitive disclosures, email `jak4013@med.cornell.edu` with the subject
`BIOTHREAT SAFETY`.

Use this route for:

- Accidental exposure of query-bank content, calibration sets, API keys, or raw
  per-query model responses
- Public artifacts that could enable benchmark gaming or adversarial prompt
  engineering
- Risk classifications or policy language that could be misread as operational
  biological guidance

For non-sensitive documentation or code issues, open a GitHub issue and apply
the `safety` label.

## Public Artifact Boundary

These files may be public:

- Pipeline source code
- Formal model description
- Query-bank schema and non-operational examples
- Aggregate behavioral, uplift, risk, and policy outputs
- Public summary figures

These files must remain private unless separately approved:

- `data/raw/query_bank.json`
- `data/raw/query_bank_draft.json`
- `data/raw/calibration_set.json`
- `data/processed/evaluation_results_*.json`
- `data/processed/eval_*_partial.json`
- `.env`
- Raw model responses and detailed restricted policy briefs

See [`SAFETY.md`](SAFETY.md) and
[`RESPONSIBLE_DISCLOSURE.md`](RESPONSIBLE_DISCLOSURE.md) for the full scope.
