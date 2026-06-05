"""Policy mapper: risk assessments -> actionable policy recommendations.

Maps risk colors to specific policy actions per RAND ACE framework.
Handles cross-model logic for mixed-risk scenarios.
"""

import json
from collections import Counter, defaultdict

from config import RESULTS_DIR
from models import PolicyRecommendation, RiskAssessment, RiskColor

# ─── Action Mapping ──────────────────────────────────────────────────────────

_ACTIONS = {
    RiskColor.RED: {
        "level": "restrict",
        "actions": [
            "Deploy constitutional classifiers for dual-use biology queries",
            "Implement API access controls with enhanced monitoring",
            "Mandatory pre-deployment red-team testing before capability updates",
            "Report findings to OSTP and NSABB for policy consideration",
            "Consider model weight access restrictions for open-weight variants",
        ],
    },
    RiskColor.AMBER: {
        "level": "monitor",
        "actions": [
            "Enhanced behavioral monitoring for dual-use query patterns",
            "6-month re-evaluation cycle with updated query bank",
            "Voluntary safeguard implementation with developer engagement",
            "Red-team testing required before major capability updates",
            "Cross-provider information sharing on identified patterns",
        ],
    },
    RiskColor.GREEN: {
        "level": "accept",
        "actions": [
            "Standard safety practices sufficient",
            "Annual review with updated evaluation methodology",
            "Transparency reports on dual-use query handling",
            "Continued participation in voluntary safety commitments",
        ],
    },
}


def map_risk_to_policy(
    model_name: str,
    assessments: list[RiskAssessment],
) -> PolicyRecommendation:
    """Generate policy recommendation for one model across all scenarios."""
    scenario_risks = {a.scenario_id: a.risk_color for a in assessments}

    # Overall risk = worst-case across scenarios
    colors = list(scenario_risks.values())
    if RiskColor.RED in colors:
        overall = RiskColor.RED
    elif RiskColor.AMBER in colors:
        overall = RiskColor.AMBER
    else:
        overall = RiskColor.GREEN

    action_info = _ACTIONS[overall]

    return PolicyRecommendation(
        model_name=model_name,
        overall_risk=overall,
        action_level=action_info["level"],
        specific_actions=action_info["actions"],
        scenario_risks=scenario_risks,
    )


def cross_model_analysis(recommendations: list[PolicyRecommendation]) -> str:
    """Generate cross-model findings text."""
    color_counts = Counter(r.overall_risk for r in recommendations)
    n_models = len(recommendations)

    lines = []

    # Summary
    for color in [RiskColor.RED, RiskColor.AMBER, RiskColor.GREEN]:
        count = color_counts.get(color, 0)
        if count > 0:
            lines.append(f"- {color.value}: {count}/{n_models} models")

    # Open-source weight risk
    open_weight_models = [r for r in recommendations
                          if any(kw in r.model_name.lower()
                                 for kw in ("llama", "qwen", "deepseek"))]
    if open_weight_models:
        open_risks = [r.overall_risk for r in open_weight_models]
        if any(r != RiskColor.GREEN for r in open_risks):
            lines.append(
                "\nOpen-weight models present elevated risk because safety "
                "mitigations can be removed through fine-tuning or prompt "
                "engineering. Weight-access restrictions merit consideration "
                "for models in AMBER or RED categories."
            )

    # Mixed findings
    if color_counts.get(RiskColor.GREEN, 0) > 0 and (
        color_counts.get(RiskColor.AMBER, 0) + color_counts.get(RiskColor.RED, 0) > 0
    ):
        lines.append(
            "\nMixed findings across models: some achieve acceptable risk "
            "levels while others require mitigation. This heterogeneity "
            "suggests that safety properties are design choices, not "
            "inherent to model capability."
        )

    return "\n".join(lines) if lines else "Insufficient data for cross-model analysis."


# ─── Pipeline Entry Point ───────────────────────────────────────────────────

def run_policy_mapping() -> list[PolicyRecommendation]:
    """Generate policy recommendations from saved risk assessments."""
    risk_path = RESULTS_DIR / "risk_assessment.json"
    if not risk_path.exists():
        raise FileNotFoundError(
            f"Risk assessment not found at {risk_path}. Run --step risk first."
        )

    raw = json.loads(risk_path.read_text())
    assessments = [RiskAssessment.model_validate(a) for a in raw]

    # Group by model
    by_model: dict[str, list[RiskAssessment]] = defaultdict(list)
    for a in assessments:
        by_model[a.model_name].append(a)

    recommendations = []
    for model_name, model_assessments in by_model.items():
        rec = map_risk_to_policy(model_name, model_assessments)
        recommendations.append(rec)
        print(f"  {model_name}: {rec.overall_risk.value} ({rec.action_level})")

    return recommendations
