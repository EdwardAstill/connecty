"""Elastic (linear) in-plane shear distribution for bolt groups."""

from __future__ import annotations

from ..geometry import BoltGroup
from ..results import BoltResult
from ...common.icr_solver import ZERO_TOLERANCE
from ...common.load import Load


def solve_elastic_shear(*, bolt_group: BoltGroup, load: Load) -> list[BoltResult]:
    """Return per-bolt in-plane shear forces using the elastic method."""
    props = bolt_group._calculate_properties()
    n = props.n
    Cy = props.Cy
    Cz = props.Cz
    Ip = props.Ip

    Mx_total, _, _ = load.get_moments_about(0.0, Cy, Cz)

    Fy = load.Fy
    Fz = load.Fz
    Mx = float(Mx_total)

    bolt_results: list[BoltResult] = []
    for (y, z) in bolt_group.positions:
        dy = y - Cy
        dz = z - Cz

        R_direct_y = Fy / n if n > 0 else 0.0
        R_direct_z = Fz / n if n > 0 else 0.0

        R_moment_y = 0.0
        R_moment_z = 0.0
        if Ip > ZERO_TOLERANCE:
            R_moment_y = -Mx * dz / Ip
            R_moment_z = Mx * dy / Ip

        bolt_results.append(
            BoltResult(
                point=(y, z),
                Fy=R_direct_y + R_moment_y,
                Fz=R_direct_z + R_moment_z,
                Fx=0.0,
                diameter=bolt_group.diameter,
            )
        )

    return bolt_results


