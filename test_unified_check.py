"""Regression tests for bolt check entrypoints.

This file used to be a print-only script and was accidentally collected by
pytest. It now contains real tests aligned with the current API:

- Bolt grade lives on BoltGroup
- Plate strengths live on Plate
"""

from __future__ import annotations

from connecty import BoltConnection, BoltGroup, ConnectionLoad, ConnectionResult, Plate
from connecty.bolt.checks import aisc, as4100


def _base_geometry(*, grade: str):
    bolts = BoltGroup.from_pattern(
        rows=3,
        cols=2,
        spacing_y=75.0,
        spacing_z=60.0,
        diameter=20.0,
        grade=grade,
        origin=(0.0, 0.0),
    )
    plate = Plate(
        corner_a=(-125.0, -80.0),
        corner_b=(125.0, 80.0),
        thickness=12.0,
        fu=450.0,
        fy=350.0,
    )
    return bolts, plate


def test_aisc_check_runs() -> None:
    bolts, plate = _base_geometry(grade="A325")
    conn = BoltConnection(bolt_group=bolts, plate=plate)
    load = ConnectionLoad(Fx=30_000.0, Fy=-120_000.0, Fz=45_000.0, location=(0.0, 0.0, 150.0))
    result = ConnectionResult(connection=conn, load=load, shear_method="elastic", tension_method="accurate")

    design = aisc.BoltDesignParams(
        hole_type="standard",
        threads_in_shear_plane=True,
        edge_distance_y=50.0,
        edge_distance_z=50.0,
        use_analysis_bolt_tension_if_present=True,
    )
    check = aisc.check_bolt_group_aisc(result, design, connection_type="bearing")
    assert check.governing_utilization >= 0.0
    assert check.governing_limit_state is not None


def test_as4100_check_runs() -> None:
    bolts, plate = _base_geometry(grade="8.8")
    conn = BoltConnection(bolt_group=bolts, plate=plate)
    load = ConnectionLoad(Fx=30_000.0, Fy=-120_000.0, Fz=45_000.0, location=(0.0, 0.0, 150.0))
    result = ConnectionResult(connection=conn, load=load, shear_method="elastic", tension_method="accurate")

    design = as4100.BoltDesignParams(
        hole_type="standard",
        hole_type_factor=1.0,
        edge_distance=40.0,
        nn_shear_planes=1,
        nx_shear_planes=0,
        prying_allowance=0.25,
        use_analysis_bolt_tension_if_present=True,
    )
    check = as4100.check_bolt_group_sd_handbook(result, design, connection_type="bearing")
    assert check.governing_utilization >= 0.0
    assert check.governing_limit_state is not None
