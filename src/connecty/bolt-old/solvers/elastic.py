"""Elastic (linear) in-plane shear distribution for bolt groups."""

from __future__ import annotations

from ..group import BoltLayout
from ..results import BoltForce
from ...common.icr_solver import ZERO_TOLERANCE
from ...common.load import Load


def solve_elastic_shear(*, layout: BoltLayout, bolt_diameter: float, load: Load) -> list[BoltForce]:
    """Return per-bolt in-plane shear forces using the elastic method."""
    props = layout._calculate_properties()
    n = props.n
    Cy = props.Cy
    Cz = props.Cz
    Ip = props.Ip

    # 3) Transfer loads to centroid
    # Note: Implementing formula from documentation/theory/bolt.md directly
    # M_total = Mx - Fz * (y_loc - Cy) + Fy * (z_loc - Cz)
    Mx_total = load.Mx - load.Fz * (load.y_loc - Cy) + load.Fy * (load.z_loc - Cz)

    Fy = load.Fy
    Fz = load.Fz
    Mx = float(Mx_total)

    Fys = []
    Fzs = []
    for (y, z) in layout.points:
        dy = y - Cy
        dz = z - Cz

        R_direct_y = Fy / n if n > 0 else 0.0
        R_direct_z = Fz / n if n > 0 else 0.0

        R_moment_y = 0.0
        R_moment_z = 0.0
        if Ip > ZERO_TOLERANCE:
            # Matches documentation formulas:
            # Fy_m = -Mx_total * dz / Ip
            # Fz_m = -Mx_total * dy / Ip
            R_moment_y = -Mx * dz / Ip
            R_moment_z = -Mx * dy / Ip

        Fys.append(R_direct_y + R_moment_y)
        Fzs.append(R_direct_z + R_moment_z)

    return Fys, Fzs


