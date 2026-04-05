"""Threat scenarios for risk assessment.

5 scenarios covering all 7 NSABB categories.
Each scenario maps to specific categories for category-aware B_i computation.

Note: actor_profile and impact_factor are metadata for policy reporting and
future extensions (e.g., actor-capability-weighted risk). They are NOT used
in the current B_i or Monte Carlo computation (see risk_model.py).
"""

from models import NSABBCategory, ThreatScenario


def build_scenarios() -> list[ThreatScenario]:
    """Build the 5 threat scenarios."""
    return [
        ThreatScenario(
            scenario_id="toxin_acquisition",
            name="Toxin Acquisition",
            description=(
                "Novice actor attempts to synthesize a known toxin using "
                "publicly available AI tools for research guidance and "
                "protocol generation. Based on Aum Shinrikyo case analysis."
            ),
            relevant_categories=[
                NSABBCategory.ENHANCE_HARM,
                NSABBCategory.GENERATE_RECONSTRUCT,
            ],
            actor_profile="novice",
            impact_factor=1.0,
        ),
        ThreatScenario(
            scenario_id="pandemic_pathogen",
            name="Pandemic Pathogen Enhancement",
            description=(
                "Organized group seeks to enhance a pathogen's stability "
                "and transmissibility, altering host range for human "
                "infection. Informed by NASEM 2018 framework."
            ),
            relevant_categories=[
                NSABBCategory.INCREASE_STABILITY,
                NSABBCategory.ALTER_HOST_RANGE,
            ],
            actor_profile="organized_group",
            impact_factor=5.0,
        ),
        ThreatScenario(
            scenario_id="agricultural_bioweapon",
            name="Agricultural Bioweapon",
            description=(
                "State-level actor targets agricultural systems by "
                "engineering drug-resistant crop pathogens with enhanced "
                "virulence. Informed by Gryphon Scientific 2024 analysis."
            ),
            relevant_categories=[
                NSABBCategory.CONFER_RESISTANCE,
                NSABBCategory.ENHANCE_HARM,
            ],
            actor_profile="state_actor",
            impact_factor=2.0,
        ),
        ThreatScenario(
            scenario_id="drug_resistance",
            name="Drug Resistance Engineering",
            description=(
                "Group exploits collateral sensitivity knowledge to engineer "
                "multi-drug resistant pathogens. Connected to AMR game tree "
                "analysis showing evolutionary predictability."
            ),
            relevant_categories=[
                NSABBCategory.CONFER_RESISTANCE,
                NSABBCategory.DISRUPT_IMMUNITY,
            ],
            actor_profile="organized_group",
            impact_factor=1.5,
        ),
        ThreatScenario(
            scenario_id="de_novo_pathogen",
            name="De Novo Pathogen Design",
            description=(
                "Sophisticated actor with molecular biology training "
                "attempts de novo pathogen design using AI-assisted "
                "protein engineering. RAND PEA4710-1 scenario."
            ),
            relevant_categories=[
                NSABBCategory.GENERATE_RECONSTRUCT,
                NSABBCategory.ENHANCE_SUSCEPTIBILITY,
            ],
            actor_profile="sophisticated",
            impact_factor=4.0,
        ),
    ]


def get_scenario(scenario_id: str) -> ThreatScenario:
    """Get a scenario by ID."""
    for s in build_scenarios():
        if s.scenario_id == scenario_id:
            return s
    raise ValueError(f"Unknown scenario: {scenario_id}")


def verify_category_coverage() -> dict[str, list[str]]:
    """Verify all 7 NSABB categories appear in at least one scenario."""
    scenarios = build_scenarios()
    coverage: dict[str, list[str]] = {}

    for cat in NSABBCategory:
        covering = [s.scenario_id for s in scenarios if cat in s.relevant_categories]
        coverage[cat.value] = covering

    missing = [cat for cat, scens in coverage.items() if not scens]
    if missing:
        raise ValueError(f"Categories not covered by any scenario: {missing}")

    return coverage
