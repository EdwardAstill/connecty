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


def test_icr_rejects_fx() -> None:
    weld = _make_weld_line(start_y=-50.0, start_z=0.0, end_y=50.0, end_z=0.0)
    load = Load(Fx=10_000.0, Fy=5_000.0, location=(0.0, 0.0, 0.0))

    with pytest.raises(ValueError, match=r"ICR method only supports in-plane loading"):
        LoadedWeld(weld=weld, load=load, method="icr", discretization=60)


def test_icr_rejects_my_mz_direct() -> None:
    weld = _make_weld_line(start_y=-50.0, start_z=0.0, end_y=50.0, end_z=0.0)
    load = Load(Fy=5_000.0, My=1_000_000.0, Mz=500_000.0, location=(0.0, 0.0, 0.0))

    with pytest.raises(ValueError, match=r"Out-of-plane loading detected"):
        LoadedWeld(weld=weld, load=load, method="icr", discretization=60)


def test_icr_rejects_out_of_plane_from_x_eccentricity() -> None:
    # Even if Fx/My/Mz are not specified directly, x eccentricity can transfer
    # an out-of-plane moment (Mz) from Fy via r x F.
    weld = _make_weld_line(start_y=-50.0, start_z=0.0, end_y=50.0, end_z=0.0)
    load = Load(Fy=5_000.0, location=(100.0, 0.0, 0.0))

    with pytest.raises(ValueError, match=r"Out-of-plane loading detected"):
        LoadedWeld(weld=weld, load=load, method="icr", discretization=60)


