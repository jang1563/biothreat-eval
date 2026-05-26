"""Release-readiness checks for public repository artifacts."""

from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib

from scripts import convert_to_hf


ROOT = Path(__file__).resolve().parents[1]


def test_pyproject_includes_root_modules_in_wheel() -> None:
    """All root pipeline modules should be listed for wheel/sdist builds."""
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    configured = set(pyproject["tool"]["setuptools"]["py-modules"])

    expected = {
        path.stem
        for path in ROOT.glob("*.py")
        if path.name != "__init__.py"
    }

    assert expected <= configured


def test_hf_dataset_card_has_viewer_configs_and_safety_scope(
    tmp_path: Path, monkeypatch
) -> None:
    """The generated Hugging Face card should expose aggregate tables only."""
    monkeypatch.setattr(convert_to_hf, "HF_DIR", tmp_path)

    convert_to_hf.write_dataset_card()
    card = (tmp_path / "README.md").read_text()

    for config_name in [
        "behavioral_profiles",
        "risk_assessment",
        "uplift_results",
        "policy_recommendations",
    ]:
        assert f"config_name: {config_name}" in card

    assert "aggregate metrics only" in card
    assert "raw_response" not in card
    assert "GEMINI_API_KEY" not in card


def test_manifest_excludes_private_artifacts() -> None:
    """Source distributions must not include private evaluation artifacts."""
    manifest = (ROOT / "MANIFEST.in").read_text()

    required_public_includes = [
        "include SECURITY.md",
        "recursive-include docs *.md",
        "recursive-include scripts *.py",
        "include data/raw/query_bank_schema.json",
    ]
    forbidden_private_patterns = [
        ".env\n",
        "data/raw/query_bank.json",
        "data/raw/query_bank_draft.json",
        "data/raw/calibration_set.json",
        "data/processed/evaluation_results_*.json",
        "data/processed/eval_*_partial.json",
        "results/policy_briefs/detailed_brief.md",
        "recursive-include data ",
        "recursive-include hf_data ",
    ]
    required_prunes = [
        "prune hf_data",
    ]

    for pattern in required_public_includes + required_prunes:
        assert pattern in manifest

    for pattern in forbidden_private_patterns:
        assert pattern not in manifest
