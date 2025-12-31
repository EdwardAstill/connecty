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


def test_elastic_accepts_3d_loading_and_icr_rejects() -> None:
    """
    Elastic method supports full 3D demand (Fx/Fy/Fz with transferred My/Mz via x-eccentricity).
    ICR method is strictly in-plane (Fy/Fz/Mx) and must raise on any Fx/My/Mz.
    """
    connection = _make_weld_line(start_y=-50.0, start_z=0.0, end_y=50.0, end_z=0.0)
    load = Load(Fx=10_000.0, Fy=5_000.0, Fz=-2_500.0, location=(100.0, 0.0, 0.0))

    elastic = connection.analyze(load, method="elastic", discretization=80).analysis
    assert elastic.point_stresses

    # Sanity check: all three resultant components should be present somewhere for this case.
    assert any(abs(ps.components.total_axial) > 0.0 for ps in elastic.point_stresses)
    assert any(abs(ps.components.total_y) > 0.0 for ps in elastic.point_stresses)
    assert any(abs(ps.components.total_z) > 0.0 for ps in elastic.point_stresses)

    with pytest.raises(ValueError, match=r"ICR method only supports in-plane loading"):
        connection.analyze(load, method="icr", discretization=80)


