import pytest

from sectiony.library import rhs
from connecty import Load, WeldParams, WeldedSection


@pytest.fixture
def welded_section() -> WeldedSection:
    """Default welded RHS section for continuity tests."""
    section = rhs(b=100, h=200, t=10, r=15)
    welded = WeldedSection(section=section)
    params = WeldParams(
        type="fillet",
        throat_thickness=4.2,
        leg_size=6.0,
    )
    welded.weld_all_segments(params)
    welded.calculate_properties()
    return welded


@pytest.fixture
def force() -> Load:
    """Default load for baseline continuity test."""
    return Load(Fy=-100000, location=(0, 0, 0))

