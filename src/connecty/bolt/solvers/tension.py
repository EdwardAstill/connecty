"""Plate-based bolt tension distribution (neutral-axis method)."""

from __future__ import annotations

from typing import Dict, Literal

from ...common.load import Load
from ..geometry import BoltLayout, Plate

TensionMethod = Literal["conservative", "accurate"]


def calculate_plate_bolt_tensions(
    *,
    layout: BoltLayout,
    plate: Plate,
    load: Load,
    tension_method: TensionMethod,
) -> list[float]:
    """Return per-bolt tension (Fx) from the plate neutral-axis method."""
    n = layout.n
    if n < 1:
        return []

    Cy = layout.Cy
    Cz = layout.Cz
    _, My_total, Mz_total = load.get_moments_about(0.0, Cy, Cz)
    My = float(My_total)
    Mz = float(Mz_total)

    Fx_direct = max(0.0, float(load.Fx))
    per_bolt = [Fx_direct / n for _ in range(n)]

    add_my = _tension_from_moment_about_axis(
        layout=layout,
        plate=plate,
        moment=My,
        axis="y",
        tension_method=tension_method,
    )
    add_mz = _tension_from_moment_about_axis(
        layout=layout,
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
    layout: BoltLayout,
    plate: Plate,
    moment: float,
    axis: Literal["y", "z"],
    tension_method: TensionMethod,
) -> list[float]:
    """Calculate bolt tension from moment about an axis.
    
    Returns tension values for all bolts, including negative values for bolts
    in the compression zone. The calling function should sum all components
    before applying the compression rule (negative total → 0).
    """
    n = layout.n
    out = [0.0 for _ in range(n)]
    if abs(moment) < 1e-12:
        return out

    if axis == "y":
        u_vals = [p[1] for p in layout.points]  # z
        u_min = plate.z_min
        u_max = plate.z_max
        u_centroid = float(layout.Cz)
    elif axis == "z":
        u_vals = [p[0] for p in layout.points]  # y
        u_min = plate.y_min
        u_max = plate.y_max
        u_centroid = float(layout.Cy)
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

    # Group bolts by position coordinate (rows)
    rows: Dict[float, list[int]] = {}
    for idx, u in enumerate(u_vals):
        rows.setdefault(float(u), []).append(idx)

    tension_sign = 1.0 if moment > 0.0 else -1.0

    # Separate tension and compression side rows
    tension_rows: list[tuple[float, int, list[int]]] = []
    compression_rows: list[tuple[float, int, list[int]]] = []
    
    for u_key, indices in rows.items():
        rel = float(u_key) - na
        y_i = abs(rel)
        
        if tension_sign * rel > 0.0:
            # Tension side
            tension_rows.append((y_i, len(indices), indices))
        else:
            # Compression side (will get negative values)
            compression_rows.append((y_i, len(indices), indices))

    # If no bolts on tension side, no moment to distribute
    if not tension_rows:
        return out

    y_1 = max(y_i for (y_i, _, _) in tension_rows)
    if y_1 <= 0.0:
        return out

    # Solve for T1 using only tension-side bolts (per handbook method)
    denom = 0.0
    for (y_i, _, _) in tension_rows:
        denom += y_i * ((y_i / y_1) - (y_c / y_1))

    if abs(denom) < 1e-12:
        raise ValueError("Cannot solve tension distribution (denominator ~ 0); check NA and plate geometry")

    T1 = abs(float(moment)) / denom

    # Distribute tension to tension-side bolts (positive values)
    for (y_i, n_i, indices) in tension_rows:
        T_row = T1 * (y_i / y_1)
        T_per_bolt = T_row / n_i
        for idx in indices:
            out[idx] = T_per_bolt

    # Distribute compression to compression-side bolts (negative values)
    # Use linear distribution from NA, maintaining the same slope as tension side
    for (y_i, n_i, indices) in compression_rows:
        T_row = -T1 * (y_i / y_1)  # Negative for compression
        T_per_bolt = T_row / n_i
        for idx in indices:
            out[idx] = T_per_bolt

    return out


