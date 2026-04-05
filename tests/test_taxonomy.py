"""Tests for taxonomy and query bank."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import NSABBCategory, ThreatLevel
from taxonomy import build_taxonomy, get_evaluable_cells, taxonomy_summary


def test_taxonomy_has_35_cells():
    cells = build_taxonomy()
    assert len(cells) == 35, f"Expected 35 cells, got {len(cells)}"


def test_taxonomy_7_categories():
    cells = build_taxonomy()
    cats = {c.category for c in cells}
    assert len(cats) == 7
    for cat in NSABBCategory:
        assert cat in cats


def test_taxonomy_5_levels():
    cells = build_taxonomy()
    levels = {c.level for c in cells}
    assert len(levels) == 5
    for level in ThreatLevel:
        assert level in levels


def test_evaluable_count():
    evaluable = get_evaluable_cells()
    assert len(evaluable) == 31, f"Expected 31 evaluable cells, got {len(evaluable)}"


def test_non_evaluable_are_l5_cats_4_7():
    cells = build_taxonomy()
    non_eval = [c for c in cells if not c.evaluable]
    assert len(non_eval) == 4

    expected_cats = {
        NSABBCategory.INCREASE_STABILITY,
        NSABBCategory.ALTER_HOST_RANGE,
        NSABBCategory.ENHANCE_SUSCEPTIBILITY,
        NSABBCategory.GENERATE_RECONSTRUCT,
    }
    for cell in non_eval:
        assert cell.level == ThreatLevel.L5
        assert cell.category in expected_cats


def test_safety_tiers():
    cells = build_taxonomy()
    for cell in cells:
        if cell.level.value <= 2:
            assert cell.safety_tier == 1
        elif cell.level.value == 3:
            assert cell.safety_tier == 2
        else:
            assert cell.safety_tier == 3


def test_taxonomy_summary_is_string():
    summary = taxonomy_summary()
    assert isinstance(summary, str)
    assert "BioThreat-Eval Taxonomy" in summary
    assert "31" in summary  # evaluable count


def test_all_cells_have_descriptions():
    cells = build_taxonomy()
    for cell in cells:
        assert cell.description, f"Cell {cell.category}xL{cell.level.value} has no description"
        assert len(cell.description) > 20


def test_categories_exhaustive():
    """Verify all 7 NSABB categories are covered."""
    assert len(NSABBCategory) == 7
    expected = [
        "enhance_harm", "disrupt_immunity", "confer_resistance",
        "increase_stability", "alter_host_range", "enhance_susceptibility",
        "generate_reconstruct",
    ]
    for name in expected:
        assert NSABBCategory(name)
