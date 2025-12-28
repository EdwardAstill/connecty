"""Plate-based bolt tension distribution (neutral-axis method)."""

from __future__ import annotations

from typing import Dict, Literal

from ...common.load import Load
from ..geometry import BoltGroup, Plate

TensionMethod = Literal["conservative", "accurate"]


def calculate_plate_bolt_tensions(
    *,
    bolt_group: BoltGroup,
    plate: Plate,
    load: Load,
    tension_method: TensionMethod,
) -> list[float]:
    """Return per-bolt tension (Fx) from the plate neutral-axis method."""
    n = bolt_group.n
    if n < 1:
        return []

    Cy = bolt_group.Cy
    Cz = bolt_group.Cz
    _, My_total, Mz_total = load.get_moments_about(0.0, Cy, Cz)
    My = float(My_total)
    Mz = float(Mz_total)

    Fx_direct = max(0.0, float(load.Fx))
    per_bolt = [Fx_direct / n for _ in range(n)]

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
        if per_bolt[i] < 0.0:
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
    n = bolt_group.n
    out = [0.0 for _ in range(n)]
    if abs(moment) < 1e-12:
        return out

    if axis == "y":
        u_vals = [p[1] for p in bolt_group.positions]  # z
        u_min = plate.z_min
        u_max = plate.z_max
        u_centroid = float(bolt_group.Cz)
    elif axis == "z":
        u_vals = [p[0] for p in bolt_group.positions]  # y
        u_min = plate.y_min
        u_max = plate.y_max
        u_centroid = float(bolt_group.Cy)
    else:
        raise ValueError("axis must be 'y' or 'z'")

    d = float(u_max - u_min)
    if d <= 0.0:
        raise ValueError("Plate depth must be positive (check corner coordinates)")

    comp_edge = float(u_min) if moment > 0.0 else float(u_max)

    if tension_method == "conservative":
        # Per documentation/theory/bolt.md: conservative NA at the bolt-group centroid line.
        na = u_centroid
    elif tension_method == "accurate":
        if comp_edge == u_min:
            na = u_min + d / 6.0
        else:
            na = u_max - d / 6.0
    else:
        raise ValueError("tension_method must be 'conservative' or 'accurate'")

    # Guard against degenerate/invalid NA locations.
    if not (u_min <= na <= u_max):
        raise ValueError("Neutral axis (NA) lies outside the plate; check bolt group vs plate geometry")

    y_c = -abs(comp_edge - na)

    rows: Dict[float, list[int]] = {}
    for idx, u in enumerate(u_vals):
        rows.setdefault(float(u), []).append(idx)

    tension_sign = 1.0 if moment > 0.0 else -1.0

    row_data: list[tuple[float, int, list[int]]] = []
    for u_key, indices in rows.items():
        rel = float(u_key) - na
        if tension_sign * rel <= 0.0:
            continue
        y_i = abs(rel)
        row_data.append((y_i, len(indices), indices))

    if not row_data:
        return out

    y_1 = max(y_i for (y_i, _, _) in row_data)
    if y_1 <= 0.0:
        return out

    denom = 0.0
    for (y_i, _, _) in row_data:
        denom += y_i * ((y_i / y_1) - (y_c / y_1))

    if abs(denom) < 1e-12:
        raise ValueError("Cannot solve tension distribution (denominator ~ 0); check NA and plate geometry")

    T1 = abs(float(moment)) / denom

    for (y_i, n_i, indices) in row_data:
        T_row = T1 * (y_i / y_1)
        T_per_bolt = T_row / n_i
        for idx in indices:
            out[idx] += T_per_bolt

    return out


