# BioThreat-Eval: Public Risk Summary

Date: 2026-03-30
Models evaluated: 6

## Executive Summary

Across 6 frontier and open-weight language models evaluated on dual-use biological knowledge queries:

- RED (restrict): 0 models
- AMBER (monitor): 3 models
- GREEN (accept): 3 models

## Key Findings

- AMBER: 3/6 models
- GREEN: 3/6 models

Open-weight models present elevated risk because safety mitigations can be removed through fine-tuning or prompt engineering. Weight-access restrictions merit consideration for models in AMBER or RED categories.

Mixed findings across models: some achieve acceptable risk levels while others require mitigation. This heterogeneity suggests that safety properties are design choices, not inherent to model capability.

## Methodology

Models were evaluated on safe proxy queries across 7 NSABB categories of dual-use research of concern at 5 threat levels. Behavioral responses were scored by cross-provider LLM judges on 4 dimensions. Risk was quantified via a 4-stage attack chain Monte Carlo model (10,000 samples). Classification uses median uplift ratio.

## Limitations

- Base attack probabilities are informed estimates, not empirical measurements
- Uplift coefficients are hyperparameters; full sensitivity analysis reported in detailed brief
- Safe proxy queries may not capture the full range of dual-use knowledge
- LLM-as-judge introduces scoring variability (sigma = 0.10)

---

*This assessment uses the BioThreat-Eval pipeline. Full methodology: FORMAL_MODEL.md*