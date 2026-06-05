# Responsible Disclosure Policy

## Query Bank Security

The file `data/raw/query_bank.json` is **NOT committed to the public repository**. This file contains safe proxy queries designed to evaluate LLM behavior on dual-use biological topics. While all queries use WMDP-style safe proxy methodology and do not contain actionable threat information, the complete query bank is withheld as a precaution against:

1. **Benchmark gaming**: If query texts are public, model developers could overfit safety filters to specific phrasings without improving general safety.
2. **Adversarial use**: The taxonomy structure could inform adversarial prompt engineering.

## What IS Public

- `data/raw/query_bank_schema.json`: Field schema and a single non-operational placeholder example only
- All pipeline code (taxonomy, evaluation, risk model, policy mapping)
- Aggregate results (behavioral profiles, risk assessments, policy briefs)
- Formal model specification (`FORMAL_MODEL.md`)

## What IS NOT Public

- Full query bank (`query_bank.json`) — available on request with justification
- Calibration set (`calibration_set.json`)
- Raw model responses (per-query `raw_response` fields)

## Output Policy

All public-facing outputs use **aggregate metrics only**:
- Per-model behavioral dimension means (not individual query scores)
- Per-scenario risk colors and uplift ratios
- Category-level profiles (not individual query IDs)

The **detailed brief** includes per-stage probabilities but is marked "For policymakers and model developers only."

## NSABB Framework Alignment

This project evaluates dual-use knowledge using the 7 categories defined by the National Science Advisory Board for Biosecurity (NSABB). The evaluation methodology is designed to:

- Inform policy decisions about AI model safety
- Identify behavioral patterns that may require mitigation
- Support responsible development of frontier AI models

It is NOT designed to:

- Provide operational guidance for biological threats
- Generate novel dual-use knowledge
- Bypass existing safety measures

## Contact

For query bank access requests (with stated justification) or responsible
disclosure concerns, email `jak4013@med.cornell.edu` with the subject
`BIOTHREAT SAFETY`. See [`SECURITY.md`](SECURITY.md) for the full disclosure process.
