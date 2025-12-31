import pytest

from sectiony.library import rhs
from connecty import Load, WeldBaseMetal, WeldConnection, WeldParams


@pytest.fixture
def welded_section() -> WeldConnection:
    """Default RHS weld path for continuity tests (new API)."""
    section = rhs(b=100, h=200, t=10, r=15)

    params = WeldParams(type="fillet", throat=4.2, leg=6.0)
    base_metal = WeldBaseMetal(t=10.0, fy=350.0, fu=450.0)

    if section.geometry is None:
        raise ValueError("Test section has no geometry")

    return WeldConnection.from_geometry(geometry=section.geometry, parameters=params, base_metal=base_metal)


@pytest.fixture
def force() -> Load:
    """Default load for baseline continuity test."""
    return Load(Fy=-100000, location=(0, 0, 0))

