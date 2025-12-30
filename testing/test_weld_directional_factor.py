from __future__ import annotations

import pytest
from sectiony.geometry import Contour, Geometry, Line

from connecty import Load, LoadedWeld, Weld, WeldParams


def _make_weld_line(*, start_y: float, start_z: float, end_y: float, end_z: float) -> Weld:
    geom = Geometry(
        contours=[
            Contour(
                segments=[Line(start=(float(start_y), float(start_z)), end=(float(end_y), float(end_z)))],
                hollow=False,
            )
        ]
    )
    params = WeldParams(type="fillet", leg=6.0)
    return Weld(geometry=geom, parameters=params, section=None)


def test_kds_parallel_to_weld_is_one() -> None:
    # Weld line along y-axis (tangent is +/-y). Load Fy -> parallel => theta=0 => k_ds=1.0.
    weld = _make_weld_line(start_y=-50.0, start_z=0.0, end_y=50.0, end_z=0.0)
    load = Load(Fy=5_000.0, location=(0.0, 0.0, 0.0))

    loaded = LoadedWeld(weld=weld, load=load, method="elastic", discretization=60)
    kds = loaded.directional_factors()

    assert kds
    assert min(kds) == pytest.approx(1.0, abs=1e-12)
    assert max(kds) == pytest.approx(1.0, abs=1e-12)


def test_kds_perpendicular_to_weld_is_one_point_five() -> None:
    # Weld line along y-axis (tangent is +/-y). Load Fz -> perpendicular => theta=90 => k_ds=1.5.
    weld = _make_weld_line(start_y=-50.0, start_z=0.0, end_y=50.0, end_z=0.0)
    load = Load(Fz=5_000.0, location=(0.0, 0.0, 0.0))

    loaded = LoadedWeld(weld=weld, load=load, method="elastic", discretization=60)
    kds = loaded.directional_factors()

    assert kds
    assert min(kds) == pytest.approx(1.5, abs=1e-10)
    assert max(kds) == pytest.approx(1.5, abs=1e-10)


