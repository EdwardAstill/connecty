from __future__ import annotations

from dataclasses import dataclass

import pytest

from sectiony.geometry import Contour, Geometry, Line

from connecty import WeldBaseMetal, WeldConnection, WeldParams
from connecty.weld.checks import check_weld_group


@dataclass(frozen=True)
class _DummyResult:
    connection: WeldConnection
    method: str
    max_stress: float


def _make_simple_fillet_connection(*, w: float, t: float, fy: float, fu: float) -> WeldConnection:
    # 100 mm straight weld line in y-z plane
    geom = Geometry(
        contours=[
            Contour(
                segments=[Line(start=(0.0, 0.0), end=(100.0, 0.0))],
                hollow=False,
            )
        ]
    )
    params = WeldParams(type="fillet", leg=w)
    base = WeldBaseMetal(t=t, fy=fy, fu=fu)
    return WeldConnection.from_geometry(geometry=geom, parameters=params, base_metal=base)


def test_aisc_fillet_detailing_max_fillet_can_govern() -> None:
    conn = _make_simple_fillet_connection(w=6.0, t=10.0, fy=350.0, fu=450.0)
    dummy = _DummyResult(connection=conn, method="elastic", max_stress=50.0)

    check = check_weld_group(dummy, standard="aisc")

    assert check.details
    d = check.details[0]
    assert d.governing_limit_state == "detailing_max_fillet"
    assert d.governing_util == pytest.approx(6.0 / 8.0, rel=1e-12)


def test_aisc_fillet_weld_metal_governs_under_high_stress() -> None:
    conn = _make_simple_fillet_connection(w=6.0, t=10.0, fy=350.0, fu=450.0)
    dummy = _DummyResult(connection=conn, method="elastic", max_stress=500.0)

    check = check_weld_group(dummy, standard="aisc")

    assert check.details
    d = check.details[0]
    assert d.governing_limit_state == "weld_metal"
    # With matching-electrode default, F_EXX = Fu = 450 MPa -> φ*0.60*FEXX = 202.5 MPa.
    assert d.governing_util == pytest.approx(500.0 / 202.5, rel=1e-9)


