from __future__ import annotations

import pytest
from sectiony.geometry import Contour, Geometry, Line

from connecty import Load, WeldBaseMetal, WeldConnection, WeldParams


def _make_weld_line(*, start_y: float, start_z: float, end_y: float, end_z: float) -> WeldConnection:
    geom = Geometry(
        contours=[
            Contour(
                segments=[Line(start=(float(start_y), float(start_z)), end=(float(end_y), float(end_z)))],
                hollow=False,
            )
        ]
    )
    params = WeldParams(type="fillet", leg=6.0)
    base_metal = WeldBaseMetal(t=10.0, fy=350.0, fu=450.0)
    return WeldConnection.from_geometry(geometry=geom, parameters=params, base_metal=base_metal)


def test_icr_rejects_fx() -> None:
    connection = _make_weld_line(start_y=-50.0, start_z=0.0, end_y=50.0, end_z=0.0)
    load = Load(Fx=10_000.0, Fy=5_000.0, location=(0.0, 0.0, 0.0))

    with pytest.raises(ValueError, match=r"ICR method only supports in-plane loading"):
        connection.analyze(load, method="icr", discretization=60)


def test_icr_rejects_my_mz_direct() -> None:
    connection = _make_weld_line(start_y=-50.0, start_z=0.0, end_y=50.0, end_z=0.0)
    load = Load(Fy=5_000.0, My=1_000_000.0, Mz=500_000.0, location=(0.0, 0.0, 0.0))

    with pytest.raises(ValueError, match=r"Out-of-plane loading detected"):
        connection.analyze(load, method="icr", discretization=60)


def test_icr_rejects_out_of_plane_from_x_eccentricity() -> None:
    # Even if Fx/My/Mz are not specified directly, x eccentricity can transfer
    # an out-of-plane moment (Mz) from Fy via r x F.
    connection = _make_weld_line(start_y=-50.0, start_z=0.0, end_y=50.0, end_z=0.0)
    load = Load(Fy=5_000.0, location=(100.0, 0.0, 0.0))

    with pytest.raises(ValueError, match=r"Out-of-plane loading detected"):
        connection.analyze(load, method="icr", discretization=60)


