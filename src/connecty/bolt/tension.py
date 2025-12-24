"""Plate-based bolt tension distribution.

Implements the handbook-style neutral-axis method described in documentation/bolt/theory.md.

Computes bolt tension from moments about BOTH the y and z axes:
- My produces a tension gradient across the plate z-depth
- Mz produces a tension gradient across the plate y-depth

Tension contributions are summed per bolt and compression is set to zero.
"""

from __future__ import annotations

from typing import Dict, Literal

from ..common.force import Force
from .bolt import BoltGroup
from .plate import Plate


TensionMethod = Literal["conservative", "accurate"]


def calculate_plate_bolt_tensions(
    *,
    bolt_group: BoltGroup,
    plate: Plate,
    force: Force,
    tension_method: TensionMethod,
) -> list[float]:
    """Return per-bolt tension (Fx) from plate method.

    The result is a list aligned with bolt_group.positions.

    Notes:
    - Direct axial tension Fx (if positive) is distributed uniformly.
    - Moment-induced tension from My and Mz is computed separately and summed.
    - Compression (negative) is not carried by bolts, so final values are clamped >= 0.
    """

    n = bolt_group.n
    if n < 1:
        return []

    # Moments about the bolt-group centroid for consistency with shear analysis.
    Cy = bolt_group.Cy
    Cz = bolt_group.Cz
    Mx_total, My_total, Mz_total = force.get_moments_about(0.0, Cy, Cz)
    My = float(My_total)
    Mz = float(Mz_total)

    # Start with direct axial (tension only).
    Fx_direct = max(0.0, float(force.Fx))
    per_bolt = [Fx_direct / n for _ in range(n)]

    # Add moment-induced contributions from both axes.
    add_my = _tension_from_moment_about_axis(
        bolt_group=bolt_group,
        plate=plate,
        moment=My,
        axis="y",
        tension_method=tension_method,
    )
    add_mz = _tension_from_moment_about_axis(
        bolt_group=bolt_group,
        plate=plate,
        moment=Mz,
        axis="z",
        tension_method=tension_method,
    )

    for i in range(n):
        per_bolt[i] += add_my[i] + add_mz[i]
        if per_bolt[i] < 0:
            per_bolt[i] = 0.0

    return per_bolt


def _tension_from_moment_about_axis(
    *,
    bolt_group: BoltGroup,
    plate: Plate,
    moment: float,
    axis: Literal["y", "z"],
    tension_method: TensionMethod,
) -> list[float]:
    """Return per-bolt tension from a single bending moment component.

    axis:
    - "y": uses plate z-depth; groups bolts into columns by exact z coordinate
    - "z": uses plate y-depth; groups bolts into rows by exact y coordinate

    moment sign selects compression edge; tension side is opposite.
    """

    n = bolt_group.n
    out = [0.0 for _ in range(n)]

    if abs(moment) < 1e-12:
        return out

    if axis == "y":
        u_vals = [p[1] for p in bolt_group.positions]  # z
        u_min = plate.z_min
        u_max = plate.z_max
    elif axis == "z":
        u_vals = [p[0] for p in bolt_group.positions]  # y
        u_min = plate.y_min
        u_max = plate.y_max
    else:
        raise ValueError("axis must be 'y' or 'z'")

    d = float(u_max - u_min)
    if d <= 0:
        raise ValueError("Plate depth must be positive (check corner coordinates)")

    # Determine compression edge from moment sign.
    # Convention aligned with bolt elastic axial term:
    #   Fx += My * dz / Iy  (tension increases with +z when My>0)
    #   Fx += Mz * dy / Iz  (tension increases with +y when Mz>0)
    # So for moment>0, compression is at the negative edge (min).
    if moment > 0:
        comp_edge = float(u_min)
    else:
        comp_edge = float(u_max)

    # Neutral axis location
    if tension_method == "conservative":
        na = 0.5 * (u_min + u_max)
    elif tension_method == "accurate":
        # d/6 from compression edge
        if comp_edge == u_min:
            na = u_min + d / 6.0
        else:
            na = u_max - d / 6.0
    else:
        raise ValueError("tension_method must be 'conservative' or 'accurate'")

    # y_c: lever arm from NA to resultant compression C.
    # Compression resultant is at the compression edge (plate boundary).
    # Since tension bolts are on one side of NA, compression is on the opposite side, so y_c is negative.
    y_c = -abs(comp_edge - na)

    # Build bolt rows/columns by exact coordinate.
    rows: Dict[float, list[int]] = {}
    for idx, u in enumerate(u_vals):
        rows.setdefault(float(u), []).append(idx)

    # Identify tension-side rows: those on the opposite side of NA from the compression edge.
    # Use the sign of (u - na) to decide which side is tension.
    tension_sign = 1.0 if moment > 0 else -1.0

    row_data: list[tuple[float, int, list[int]]] = []  # (y_i, n_i, indices)
    for u_key, indices in rows.items():
        rel = float(u_key) - na
        if tension_sign * rel <= 0:
            continue
        y_i = abs(rel)
        row_data.append((y_i, len(indices), indices))

    if not row_data:
        return out

    y_1 = max(y_i for (y_i, _, _) in row_data)
    if y_1 <= 0:
        return out

    # Solve for the total force in the critical (farthest) tension row, T1.
    # From theory.md:
    #   T1 = M / Σ[ y_i ( y_i/y1 - y_c/y1 ) ]  over tension-side rows
    denom = 0.0
    for (y_i, _, _) in row_data:
        denom += y_i * ((y_i / y_1) - (y_c / y_1))

    if abs(denom) < 1e-12:
        raise ValueError("Cannot solve tension distribution (denominator ~ 0); check NA and plate geometry")

    T1 = abs(float(moment)) / denom

    # Distribute row totals linearly with distance, then split equally across bolts in the row.
    for (y_i, n_i, indices) in row_data:
        T_row = T1 * (y_i / y_1)
        T_per_bolt = T_row / n_i
        for idx in indices:
            out[idx] += T_per_bolt

    return out
