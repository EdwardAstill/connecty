"""AISC 360-22 bolt group checks."""

from __future__ import annotations

import math

from ..geometry import Plate
from .models import BoltCheckDetail, BoltCheckResult, get_governing


AISC_GRADE_STRESS: dict[str, dict[str, float]] = {
    "A325": {"Fnt": 620.0, "Fnv_N": 370.0, "Fnv_X": 470.0},
    "A490": {"Fnt": 780.0, "Fnv_N": 470.0, "Fnv_X": 580.0},
}

AISC_PRETENSION_KN: dict[int, dict[str, float]] = {
    12: {"A325": 49.0, "A490": 72.0},
    16: {"A325": 91.0, "A490": 114.0},
    20: {"A325": 142.0, "A490": 179.0},
    22: {"A325": 176.0, "A490": 221.0},
    24: {"A325": 205.0, "A490": 257.0},
    27: {"A325": 267.0, "A490": 334.0},
    30: {"A325": 326.0, "A490": 408.0},
    36: {"A325": 475.0, "A490": 595.0},
}

AISC_HOLE_DIAMETERS: dict[int, dict[str, float]] = {
    12: {"standard": 14.0, "oversize": 16.0, "short_slotted": 14.0, "long_slotted": 14.0},
    16: {"standard": 18.0, "oversize": 20.0, "short_slotted": 18.0, "long_slotted": 18.0},
    20: {"standard": 22.0, "oversize": 24.0, "short_slotted": 22.0, "long_slotted": 22.0},
    22: {"standard": 24.0, "oversize": 28.0, "short_slotted": 24.0, "long_slotted": 24.0},
    24: {"standard": 27.0, "oversize": 30.0, "short_slotted": 27.0, "long_slotted": 27.0},
    27: {"standard": 30.0, "oversize": 35.0, "short_slotted": 30.0, "long_slotted": 30.0},
    30: {"standard": 33.0, "oversize": 38.0, "short_slotted": 33.0, "long_slotted": 33.0},
}

AISC_SLIP_COEFFICIENT: dict[str, float] = {"A": 0.30, "B": 0.50}


def check_aisc(
    *,
    result,
    grade: str,
    bolt_diameter: float,
    plate: Plate,
    connection_type: str,
    hole_type: str,
    slot_orientation: str,
    threads_in_shear_plane: bool,
    slip_class: str,
    n_s: int,
    fillers: int,
    n_b_tension: int | None,
    tension_per_bolt: float | None,
    pretension_override: float | None,
) -> BoltCheckResult:
    if connection_type not in ("bearing", "slip-critical"):
        raise ValueError("AISC connection_type must be 'bearing' or 'slip-critical'")
    if n_s < 1:
        raise ValueError("AISC n_s (number of shear/slip planes) must be at least 1")

    area_b = math.pi * (bolt_diameter**2) / 4.0
    stresses = AISC_GRADE_STRESS[grade]
    Fnv = stresses["Fnv_N" if threads_in_shear_plane else "Fnv_X"]
    Fnt = stresses["Fnt"]

    size_key = int(round(bolt_diameter))
    if size_key in AISC_HOLE_DIAMETERS:
        hole_table = AISC_HOLE_DIAMETERS[size_key]
    else:
        hole_table = {}
    if hole_type in hole_table:
        hole_dia = hole_table[hole_type]
    else:
        hole_dia = bolt_diameter + 2.0

    if pretension_override is not None:
        pretension = pretension_override
    else:
        pretension = AISC_PRETENSION_KN[size_key][grade]

    phi_slip = 1.0
    if hole_type == "long_slotted":
        phi_slip = 0.70
    elif hole_type == "oversize":
        phi_slip = 0.85
    elif hole_type == "short_slotted":
        if slot_orientation == "perpendicular":
            phi_slip = 1.0
        else:
            phi_slip = 0.85

    slip_mu = AISC_SLIP_COEFFICIENT[slip_class]
    h_f = 0.85 if fillers >= 2 else 1.0

    bolt_results = result.to_bolt_forces()
    n_b = n_b_tension if n_b_tension is not None else len(bolt_results)

    if tension_per_bolt is not None:
        tension_mode = "override"
        tension_value = max(0.0, float(tension_per_bolt)) / 1000.0
    else:
        tension_mode = "per_bolt"
        tension_value = None

    phi = 0.75
    meta: dict[str, object] = {
        "standard": "aisc",
        "grade": grade,
        "bolt_diameter": float(bolt_diameter),
        "area_b": float(area_b),
        "phi": float(phi),
        "Fnv": float(Fnv),
        "Fnt": float(Fnt),
        "threads_in_shear_plane": bool(threads_in_shear_plane),
        "hole_type": hole_type,
        "hole_dia": float(hole_dia),
        "connection_type": connection_type,
        "pretension_kN": float(pretension),
        "slip_class": slip_class,
        "slip_mu": float(slip_mu),
        "phi_slip": float(phi_slip),
        "fillers": int(fillers),
        "h_f": float(h_f),
        "n_s": int(n_s),
        "n_b_tension": int(n_b),
        "tension_mode": tension_mode,
    }

    details: list[BoltCheckDetail] = []
    for idx, bf in enumerate(bolt_results):
        Vu = math.hypot(bf.Fy, bf.Fz) / 1000.0

        if tension_mode == "override":
            Tu = float(tension_value)
        else:
            Tu = max(0.0, float(bf.Fx)) / 1000.0

        # AISC J3.6: shear strength is per shear plane, so multiply by n_s.
        shear_cap = phi * Fnv * area_b * n_s / 1000.0

        # AISC J3.7 uses bolt shear stress; for multiple shear planes, distribute over n_s.
        f_rv = (Vu * 1000.0) / (area_b * n_s)
        Fnt_prime = max(0.0, min(Fnt, 1.3 * Fnt - (Fnt / (phi * Fnv)) * f_rv))
        tension_cap = phi * Fnt_prime * area_b / 1000.0

        bolt_y, bolt_z = bf.point
        edge_clear_y_min = abs(bolt_y - plate.y_min) - hole_dia / 2.0
        edge_clear_y_max = abs(plate.y_max - bolt_y) - hole_dia / 2.0
        edge_clear_z_min = abs(bolt_z - plate.z_min) - hole_dia / 2.0
        edge_clear_z_max = abs(plate.z_max - bolt_z) - hole_dia / 2.0
        lc = min(edge_clear_y_min, edge_clear_y_max, edge_clear_z_min, edge_clear_z_max)

        bearing_nom = 2.4 * bolt_diameter * plate.thickness * plate.fu
        tear_nom = 1.2 * lc * plate.thickness * plate.fu
        bearing_cap = phi * min(bearing_nom, tear_nom) / 1000.0

        slip_cap: float | None = None
        slip_util: float | None = None
        k_sc: float | None = None
        if connection_type == "slip-critical":
            k_sc = max(0.0, 1.0 - Tu / (1.13 * pretension))
            slip_cap = phi_slip * slip_mu * 1.13 * h_f * pretension * n_s * k_sc
            slip_util = Vu / slip_cap if slip_cap > 0.0 else math.inf

        shear_util = Vu / shear_cap if shear_cap > 0.0 else math.inf
        tension_util = Tu / tension_cap if tension_cap > 0.0 else math.inf
        bearing_util = Vu / bearing_cap if bearing_cap > 0.0 else math.inf

        utils: list[tuple[float, str]] = [(shear_util, "shear"), (tension_util, "tension"), (bearing_util, "bearing")]
        if slip_util is not None:
            utils.append((slip_util, "slip"))

        governing_util, governing_state = max(utils, key=lambda x: x[0])

        calc: dict[str, object] = {
            "Vu_kN": float(Vu),
            "Tu_kN": float(Tu),
            "area_b": float(area_b),
            "phi": float(phi),
            "Fnv": float(Fnv),
            "Fnt": float(Fnt),
            "f_rv": float(f_rv),
            "Fnt_prime": float(Fnt_prime),
            "hole_dia": float(hole_dia),
            "lc": float(lc),
            "bearing_nom_N": float(bearing_nom),
            "tear_nom_N": float(tear_nom),
            "bearing_nom_kN": float(bearing_nom / 1000.0),
            "tear_nom_kN": float(tear_nom / 1000.0),
            "k_sc": None if k_sc is None else float(k_sc),
            "pretension_kN": float(pretension),
            "phi_slip": float(phi_slip),
            "slip_mu": float(slip_mu),
            "h_f": float(h_f),
            "n_s": int(n_s),
            "n_b_tension": int(n_b),
        }

        details.append(
            BoltCheckDetail(
                bolt_index=idx,
                point=bf.point,
                shear_demand=Vu,
                tension_demand=Tu,
                shear_capacity=shear_cap,
                tension_capacity=tension_cap,
                bearing_capacity=bearing_cap,
                slip_capacity=slip_cap,
                shear_util=shear_util,
                tension_util=tension_util,
                bearing_util=bearing_util,
                slip_util=slip_util,
                governing_util=governing_util,
                governing_limit_state=governing_state,
                calc=calc,
            )
        )

    gov_idx, gov_state, gov_util = get_governing(details)
    return BoltCheckResult(connection_type, result.method, details, gov_idx, gov_state, gov_util, meta=meta)


__all__ = [
    "AISC_GRADE_STRESS",
    "AISC_PRETENSION_KN",
    "AISC_HOLE_DIAMETERS",
    "AISC_SLIP_COEFFICIENT",
    "check_aisc",
]


