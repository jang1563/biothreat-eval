# Responsible Use and Safety Scope

BioThreat-Eval is a **biosecurity capability evaluation pipeline** that
profiles how frontier LLMs respond to safe-proxy biological queries and
translates behavioral profiles into quantitative risk via a 4-stage attack
chain Monte Carlo. It is **not** a deployed safeguard, threat-detection
system, or policy adjudicator.

See also [`RESPONSIBLE_DISCLOSURE.md`](RESPONSIBLE_DISCLOSURE.md) for the
specific query-bank withholding policy and disclosure procedure.

## In Scope

- Behavioral profiling of frontier LLMs on a 7-category NSABB safe-proxy
  query taxonomy at 5 threat levels
- Quantitative risk modeling that translates behavioral profiles into
  attack-chain success probabilities (BioRisk-MAP)
- Policy-brief generation for model-developer and biosecurity-policy
  audiences
- Reproduction of the published 6-model evaluation against an organization's
  own held-out query bank

## Out of Scope

- Adversarial use of the published taxonomy or schema to engineer
  jailbreak prompts
- Operational threat assessment without the calibration set, query bank,
  and human review (the public artifact reports aggregate metrics; per-query
  scores are not published)
- Reframing AMBER / Action: Monitor classifications as deployment-ready
  decisions; the risk-color system is a *triage* heuristic for further review,
  not an automated gating rule
- Use of FORMAL_MODEL.md probabilities as direct gating thresholds in
  any production system without independent validation

## Withheld Content

Per `RESPONSIBLE_DISCLOSURE.md`:
- Full query bank (`query_bank.json`) is held off the public repository
  to prevent benchmark gaming and adversarial misuse
- Calibration set is held off
- Raw per-query model responses are held off
- Public-facing outputs use aggregate metrics only

## Reporting Concerns

- Open a GitHub issue with the `safety` label for: a query category that
  could enable adversarial prompt engineering, a risk-color mapping that
  is too aggressive or too lenient, an aggregate metric that could be
  misread as a deployment recommendation
- For sensitive disclosures, email jak4013@med.cornell.edu with subject
  "BIOTHREAT SAFETY"
- Query-bank access requests with stated justification: same email

## Limitations Recap

- 6-model evaluation is small-N; results do not transfer to model versions
  released after the evaluation date
- 93 queries per model is a sampled set; not exhaustive of biosecurity-relevant
  topics
- Risk model assumes specific attack-chain stages; alternative threat models
  may produce different colors
- Solo evaluator; expert circulation of brief content pending
