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


def test_elastic_fx_only_is_uniform_axial() -> None:
    connection = _make_weld_line(start_y=-50.0, start_z=0.0, end_y=50.0, end_z=0.0)
    load = Load(Fx=12_000.0, location=(0.0, 0.0, 0.0))

    result = connection.analyze(load, method="elastic", discretization=60)
    loaded = result.analysis
    props = result.weld._calculate_properties(loaded.discretization)
    expected_axial = load.Fx / props.A

    assert loaded.point_stresses
    for ps in loaded.point_stresses:
        assert ps.components.total_y == pytest.approx(0.0, abs=1e-12)
        assert ps.components.total_z == pytest.approx(0.0, abs=1e-12)
        assert ps.components.total_axial == pytest.approx(expected_axial, rel=1e-12)
        assert ps.stress == pytest.approx(abs(expected_axial), rel=1e-12)


def test_elastic_my_produces_axial_gradient_over_z() -> None:
    connection = _make_weld_line(start_y=0.0, start_z=-50.0, end_y=0.0, end_z=50.0)
    load = Load(My=2_500_000.0, location=(0.0, 0.0, 0.0))

    result = connection.analyze(load, method="elastic", discretization=80)
    loaded = result.analysis
    props = result.weld._calculate_properties(loaded.discretization)
    Cy = props.Cy
    Cz = props.Cz
    Iy = props.Iy

    assert Iy > 0.0
    assert loaded.point_stresses

    # Check linear relationship: total_axial ~= (My/Iy) * (z - Cz)
    for ps in loaded.point_stresses:
        dz = ps.z - Cz
        expected = load.My * dz / Iy
        assert ps.components.total_y == pytest.approx(0.0, abs=1e-12)
        assert ps.components.total_z == pytest.approx(0.0, abs=1e-12)
        assert ps.components.total_axial == pytest.approx(expected, rel=1e-10, abs=1e-10)

    # Max |axial| should occur at max |dz|
    abs_dz = [abs(ps.z - Cz) for ps in loaded.point_stresses]
    abs_ax = [abs(ps.components.total_axial) for ps in loaded.point_stresses]
    assert abs_ax.index(max(abs_ax)) == abs_dz.index(max(abs_dz))
    assert props.Cy == pytest.approx(Cy, abs=1e-12)


def test_elastic_mz_produces_axial_gradient_over_y() -> None:
    connection = _make_weld_line(start_y=-50.0, start_z=0.0, end_y=50.0, end_z=0.0)
    load = Load(Mz=2_500_000.0, location=(0.0, 0.0, 0.0))

    result = connection.analyze(load, method="elastic", discretization=80)
    loaded = result.analysis
    props = result.weld._calculate_properties(loaded.discretization)
    Cy = props.Cy
    Iz = props.Iz

    assert Iz > 0.0
    assert loaded.point_stresses

    # Check linear relationship: total_axial ~= (Mz/Iz) * (y - Cy)
    for ps in loaded.point_stresses:
        dy = ps.y - Cy
        expected = load.Mz * dy / Iz
        assert ps.components.total_y == pytest.approx(0.0, abs=1e-12)
        assert ps.components.total_z == pytest.approx(0.0, abs=1e-12)
        assert ps.components.total_axial == pytest.approx(expected, rel=1e-10, abs=1e-10)

    # Max |axial| should occur at max |dy|
    abs_dy = [abs(ps.y - Cy) for ps in loaded.point_stresses]
    abs_ax = [abs(ps.components.total_axial) for ps in loaded.point_stresses]
    assert abs_ax.index(max(abs_ax)) == abs_dy.index(max(abs_dy))


def test_elastic_fy_with_x_eccentricity_creates_out_of_plane_bending_mz() -> None:
    """
    If Fy is applied at an x-offset, r x F transfers an out-of-plane moment Mz:
        Mz = -Fy * dx

    Elastic method should accept this 3D loading and produce a linear bending (axial)
    stress distribution over y.
    """
    connection = _make_weld_line(start_y=-50.0, start_z=0.0, end_y=50.0, end_z=0.0)
    load = Load(Fy=5_000.0, location=(100.0, 0.0, 0.0))

    result = connection.analyze(load, method="elastic", discretization=80)
    loaded = result.analysis
    props = result.weld._calculate_properties(loaded.discretization)
    Cy = props.Cy
    Iz = props.Iz

    assert Iz > 0.0
    assert loaded.point_stresses

    # Total moments about centroid include eccentricity contribution.
    # For this load, My_total is ~0 and Mz_total = -Fy * dx.
    _, _, Mz_total = load.get_moments_about(0.0, Cy, props.Cz)
    assert Mz_total == pytest.approx(-load.Fy * load.x_loc, rel=0.0, abs=1e-12)

    for ps in loaded.point_stresses:
        dy = ps.y - Cy
        expected_bending = Mz_total * dy / Iz
        assert ps.components.total_y == pytest.approx(load.Fy / props.A, rel=1e-12)
        assert ps.components.total_z == pytest.approx(0.0, abs=1e-12)
        assert ps.components.total_axial == pytest.approx(expected_bending, rel=1e-10, abs=1e-10)

    # Bending (axial) should be antisymmetric about the centroid for a symmetric weld line.
    top = max(loaded.point_stresses, key=lambda ps: ps.y)
    bot = min(loaded.point_stresses, key=lambda ps: ps.y)
    assert top.components.total_axial == pytest.approx(-bot.components.total_axial, rel=1e-10, abs=1e-10)


