"""Shared bolt demo case for examples.

All bolt examples (analysis, check, plotting) should use the same geometry and load
so results are directly comparable.

Conventions
-----------
- Lengths: mm
- Forces: N
- Moments: N*mm

This keeps stresses from analysis in MPa (N/mm^2).
"""

from __future__ import annotations

from dataclasses import dataclass

from connecty import BoltConnection, BoltGroup, ConnectionLoad, Plate


@dataclass(frozen=True)
class DemoBoltCase:
    bolt_group: BoltGroup
    plate: Plate
    connection: BoltConnection
    load: ConnectionLoad


def make_demo_case(*, grade: str = "A325") -> DemoBoltCase:
    """Create the shared 3x2 rectangular bolt connection used by examples."""

    bolt_group = BoltGroup.from_pattern(
        rows=3,
        cols=2,
        spacing_y=75.0,
        spacing_z=60.0,
        diameter=20.0,
        grade=grade,
        origin=(0.0, 0.0),
    )

    # With the pattern centered at (0, 0):
    # y = [-75, 0, +75], z = [-30, +30]
    plate = Plate(
        corner_a=(-125.0, -80.0),
        corner_b=(125.0, 80.0),
        thickness=12.0,
        fu=450.0,
        fy=350.0,
    )

    connection = BoltConnection(bolt_group=bolt_group, plate=plate)

    # Load chosen to exercise:
    # - in-plane shear + torsion (via eccentricity)
    # - out-of-plane tension + bending (My/Mz)
    load = ConnectionLoad(
        Fx=30_000.0,   # N
        Fy=-120_000.0, # N
        Fz=45_000.0,   # N
        My=6_000_000.0,  # N*mm
        Mz=-4_000_000.0, # N*mm
        location=(0.0, 0.0, 150.0),
    )

    return DemoBoltCase(
        bolt_group=bolt_group,
        plate=plate,
        connection=connection,
        load=load,
    )


def demo_edge_distances_mm(case: DemoBoltCase) -> tuple[float, float, float]:
    """Return (edge_y, edge_z, edge_clear) for check examples.

    - edge_y/edge_z are *center-to-edge* distances (mm), suitable for AISC inputs.
    - edge_clear is an approximate *clear* distance (mm) for AS 4100 tear-out.

    These are computed as the minimum distance from any bolt center to the plate edge.
    """

    y_min = case.plate.y_min
    y_max = case.plate.y_max
    z_min = case.plate.z_min
    z_max = case.plate.z_max

    min_y = min(min(y - y_min, y_max - y) for (y, _z) in case.bolt_group.positions)
    min_z = min(min(z - z_min, z_max - z) for (_y, z) in case.bolt_group.positions)

    # Conservative clear distance approximation.
    edge_clear = max(min(min_y, min_z) - case.bolt_group.diameter / 2.0, 0.0)

    return float(min_y), float(min_z), float(edge_clear)
