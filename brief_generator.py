"""Policy brief generator: RAND-style 2-page briefs.

Two versions:
  - Public summary: aggregate risk only
  - Detailed brief: full per-model per-stage tables
"""

import json
from datetime import datetime, timezone
from collections import defaultdict

from config import RESULTS_DIR, POLICY_BRIEFS_DIR
from models import (
    RiskAssessment, UpliftResult, PolicyRecommendation, PolicyBrief, RiskColor,
)
from policy_mapper import cross_model_analysis


def _format_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def generate_public_brief(
    recommendations: list[PolicyRecommendation],
    assessments: list[RiskAssessment],
) -> str:
    """Generate public summary brief (aggregate metrics only)."""
    date = _format_date()
    n_models = len(recommendations)

    # Count risk colors
    reds = sum(1 for r in recommendations if r.overall_risk == RiskColor.RED)
    ambers = sum(1 for r in recommendations if r.overall_risk == RiskColor.AMBER)
    greens = sum(1 for r in recommendations if r.overall_risk == RiskColor.GREEN)

    lines = [
        "# BioThreat-Eval: Public Risk Summary",
        "",
        f"Date: {date}",
        f"Models evaluated: {n_models}",
        "",
        "## Executive Summary",
        "",
        f"Across {n_models} frontier and open-weight language models evaluated "
        f"on dual-use biological knowledge queries:",
        "",
        f"- RED (restrict): {reds} models",
        f"- AMBER (monitor): {ambers} models",
        f"- GREEN (accept): {greens} models",
        "",
    ]

    # Cross-model findings
    cross = cross_model_analysis(recommendations)
    lines.extend(["## Key Findings", "", cross, ""])

    # Methodology note
    lines.extend([
        "## Methodology",
        "",
        "Models were evaluated on safe proxy queries across 7 NSABB categories "
        "of dual-use research of concern at 5 threat levels. Behavioral responses "
        "were scored by cross-provider LLM judges on 4 dimensions. Risk was "
        "quantified via a 4-stage attack chain Monte Carlo model (10,000 samples). "
        "Classification uses median uplift ratio.",
        "",
        "## Limitations",
        "",
        "- Base attack probabilities are informed estimates, not empirical measurements",
        "- Uplift coefficients are hyperparameters; full sensitivity analysis reported in detailed brief",
        "- Safe proxy queries may not capture the full range of dual-use knowledge",
        "- LLM-as-judge introduces scoring variability (sigma = 0.10)",
        "",
        "---",
        "",
        "*This assessment uses the BioThreat-Eval pipeline. "
        "Full methodology: FORMAL_MODEL.md*",
    ])

    return "\n".join(lines)


def generate_detailed_brief(
    recommendations: list[PolicyRecommendation],
    assessments: list[RiskAssessment],
    uplift_results: list[UpliftResult] | None = None,
) -> str:
    """Generate detailed brief with per-model per-stage tables.

    Marked: 'For policymakers and model developers only'
    """
    date = _format_date()

    lines = [
        "# BioThreat-Eval: Detailed Risk Assessment",
        "",
        f"Date: {date}",
        "Classification: For policymakers and model developers only",
        "",
        "## Executive Summary",
        "",
    ]

    # Summary table
    lines.extend([
        "### Risk Overview",
        "",
        "| Model | Overall Risk | Action | Scenarios (RED/AMBER/GREEN) |",
        "|-------|-------------|--------|---------------------------|",
    ])

    for rec in recommendations:
        s_colors = rec.scenario_risks
        reds = sum(1 for v in s_colors.values() if v == "RED")
        ambers = sum(1 for v in s_colors.values() if v == "AMBER")
        greens = sum(1 for v in s_colors.values() if v == "GREEN")
        lines.append(
            f"| {rec.model_name} | {rec.overall_risk.value} | "
            f"{rec.action_level} | {reds}/{ambers}/{greens} |"
        )

    lines.append("")

    # Per-model detail
    lines.append("## Per-Model Assessment")
    lines.append("")

    # Group assessments by model
    by_model: dict[str, list[RiskAssessment]] = defaultdict(list)
    for a in assessments:
        by_model[a.model_name].append(a)

    for model_name, model_assessments in by_model.items():
        lines.append(f"### {model_name}")
        lines.append("")
        lines.append("| Scenario | Risk | Median R | 95% CI | Chain Base | Chain LLM |")
        lines.append("|----------|------|----------|--------|-----------|----------|")

        for a in model_assessments:
            lines.append(
                f"| {a.scenario_id} | {a.risk_color.value} | "
                f"{a.uplift_ratio:.2f} | [{a.ci_95_low:.2f}, {a.ci_95_high:.2f}] | "
                f"{a.chain_base:.6f} | {a.chain_llm:.6f} |"
            )

        lines.append("")

        # Stage breakdown for first scenario
        if model_assessments:
            a = model_assessments[0]
            lines.append(f"Stage breakdown ({a.scenario_id}):")
            lines.append("")
            lines.append("| Stage | P_base | P_llm | Uplift | 95% CI |")
            lines.append("|-------|--------|-------|--------|--------|")
            for sr in a.stage_risks:
                lines.append(
                    f"| {sr.stage} | {sr.p_base:.4f} | {sr.p_llm:.4f} | "
                    f"+{sr.uplift:.4f} | [{sr.ci_low:.4f}, {sr.ci_high:.4f}] |"
                )
            lines.append("")

    # Policy recommendations
    lines.extend(["## Policy Recommendations", ""])
    for rec in recommendations:
        lines.append(f"### {rec.model_name} ({rec.overall_risk.value}: {rec.action_level})")
        lines.append("")
        for action in rec.specific_actions:
            lines.append(f"- {action}")
        lines.append("")

    # Cross-model findings
    cross = cross_model_analysis(recommendations)
    lines.extend(["## Cross-Model Findings", "", cross, ""])

    # Methodology
    lines.extend([
        "## Methodology",
        "",
        "See FORMAL_MODEL.md for complete specification.",
        "",
        "## Limitations",
        "",
        "- Base probabilities and uplift coefficients are informed estimates",
        "- Full sensitivity analysis available in results/reports/",
        "- Query bank uses safe proxies (WMDP methodology)",
        "- Judge scoring noise modeled as N(0, 0.10)",
        "",
        "---",
        "",
        "*Generated by BioThreat-Eval pipeline*",
    ])

    return "\n".join(lines)


# ─── Pipeline Entry Point ───────────────────────────────────────────────────

def run_brief_generation() -> dict[str, str]:
    """Generate both brief versions from saved results."""
    # Load recommendations
    rec_path = RESULTS_DIR / "policy_recommendations.json"
    if not rec_path.exists():
        raise FileNotFoundError(f"Not found: {rec_path}. Run --step policy first.")
    recs = [PolicyRecommendation.model_validate(r)
            for r in json.loads(rec_path.read_text())]

    # Load assessments
    risk_path = RESULTS_DIR / "risk_assessment.json"
    assessments = [RiskAssessment.model_validate(a)
                   for a in json.loads(risk_path.read_text())]

    # Load uplift (optional)
    uplift_results = None
    uplift_path = RESULTS_DIR / "uplift_results.json"
    if uplift_path.exists():
        uplift_results = [UpliftResult.model_validate(u)
                          for u in json.loads(uplift_path.read_text())]

    public = generate_public_brief(recs, assessments)
    detailed = generate_detailed_brief(recs, assessments, uplift_results)

    return {
        "public_summary": public,
        "detailed_brief": detailed,
    }
