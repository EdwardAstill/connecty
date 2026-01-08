"""AS 4100 / SDHB bolt group checks."""

from __future__ import annotations

import math
from typing import Any

from ..plate import Plate


AS4100_GRADE_PROPERTIES: dict[str, dict] = {
    "8.8": {
        "fuf": 800.0,
        "fy": 640.0,
        "As": {12: 84.3, 16: 157.0, 20: 245.0, 22: 303.0, 24: 353.0, 27: 459.0, 30: 561.0, 36: 817.0},
        "Ac": {12: 76.3, 16: 140.7, 20: 217.5, 22: 268.8, 24: 312.1, 27: 405.7, 30: 491.4, 36: 713.0},
        "Ao": {12: 113.1, 16: 201.1, 20: 314.2, 22: 380.1, 24: 452.4, 27: 572.6, 30: 706.9, 36: 1017.9},
    },
    "10.9": {
        "fuf": 1000.0,
        "fy": 900.0,
        "As": {12: 84.3, 16: 157.0, 20: 245.0, 22: 303.0, 24: 353.0, 27: 459.0, 30: 561.0, 36: 817.0},
        "Ac": {12: 76.3, 16: 140.7, 20: 217.5, 22: 268.8, 24: 312.1, 27: 405.7, 30: 491.4, 36: 713.0},
        "Ao": {12: 113.1, 16: 201.1, 20: 314.2, 22: 380.1, 24: 452.4, 27: 572.6, 30: 706.9, 36: 1017.9},
    },
}

AS4100_PRETENSION_KN: dict[int, dict[str, float]] = {
    12: {"8.8": 50.0, "10.9": 65.0},
    16: {"8.8": 95.0, "10.9": 125.0},
    20: {"8.8": 155.0, "10.9": 205.0},
    22: {"8.8": 190.0, "10.9": 250.0},
    24: {"8.8": 225.0, "10.9": 295.0},
    27: {"8.8": 295.0, "10.9": 385.0},
    30: {"8.8": 360.0, "10.9": 475.0},
    36: {"8.8": 530.0, "10.9": 700.0},
}


def check_as4100(
    *,
    result,
    grade: str,
    bolt_diameter: float,
    plate: Plate,
    connection_type: str,
    hole_type: str,
    hole_type_factor: float,
    slip_coefficient: float,
    n_e: int,
    nn_shear_planes: int,
    nx_shear_planes: int,
    prying_allowance: float,
    reduction_factor_kr: float,
    tension_per_bolt: float | None,
    pretension_override: float | None,
    require_explicit_tension: bool,
    assume_uniform_tension_if_missing: bool,
) -> dict[str, Any]:
    if connection_type not in ("bearing", "friction"):
        raise ValueError("AS 4100 connection_type must be 'bearing' or 'friction'")

    props = AS4100_GRADE_PROPERTIES[grade]
    fuf = float(props["fuf"])

    size_key = int(round(bolt_diameter))

    As_table = props["As"]
    Ac_table = props["Ac"]
    Ao_table = props["Ao"]

    if size_key in As_table:
        As = float(As_table[size_key])
    else:
        As = float(math.pi * (bolt_diameter**2) / 4.0 * 0.75)

    if size_key in Ac_table:
        Ac = float(Ac_table[size_key])
    else:
        Ac = As * 0.9

    if size_key in Ao_table:
        Ao = float(Ao_table[size_key])
    else:
        Ao = float(math.pi * (bolt_diameter**2) / 4.0)

    Vf = 0.62 * reduction_factor_kr * fuf * (nn_shear_planes * Ac + nx_shear_planes * Ao) / 1000.0
    shear_capacity = 0.8 * Vf

    Ntf = As * fuf / 1000.0
    tension_capacity = 0.8 * Ntf

    Vb = 3.2 * plate.thickness * bolt_diameter * plate.fu
    
    # Standard hole diameter for AS 4100 (typically bolt_diameter + 2mm)
    hole_dia = bolt_diameter + 2.0

    slip_capacity: float | None = None
    pretension: float | None = None
    if connection_type == "friction":
        if pretension_override is not None:
            pretension = pretension_override
        else:
            pretension = AS4100_PRETENSION_KN[size_key][grade]
        slip_capacity = 0.7 * slip_coefficient * n_e * pretension * hole_type_factor

    bolt_results = result.to_bolt_forces()

    if tension_per_bolt is not None:
        tension_mode = "override"
        tension_value = max(0.0, float(tension_per_bolt)) / 1000.0
    else:
        tension_mode = "per_bolt"
        tension_value = None

    if tension_mode != "per_bolt":
        if require_explicit_tension:
            pass
    else:
        if not bolt_results and (require_explicit_tension or not assume_uniform_tension_if_missing):
            raise ValueError("No bolt tension provided for AS 4100")

    meta: dict[str, object] = {
        "standard": "as4100",
        "grade": grade,
        "bolt_diameter": float(bolt_diameter),
        "hole_dia": float(hole_dia),
        "fuf": float(fuf),
        "As": float(As),
        "Ac": float(Ac),
        "Ao": float(Ao),
        "nn_shear_planes": int(nn_shear_planes),
        "nx_shear_planes": int(nx_shear_planes),
        "reduction_factor_kr": float(reduction_factor_kr),
        "Vf_kN": float(Vf),
        "shear_capacity_kN": float(shear_capacity),
        "Ntf_kN": float(Ntf),
        "tension_capacity_kN": float(tension_capacity),
        "plate_fu": float(plate.fu),
        "plate_thickness": float(plate.thickness),
        "Vb_N": float(Vb),
        "connection_type": connection_type,
        "hole_type": hole_type,
        "hole_type_factor": float(hole_type_factor),
        "slip_coefficient": float(slip_coefficient),
        "n_e": int(n_e),
        "pretension_kN": None if pretension is None else float(pretension),
        "slip_capacity_kN": None if slip_capacity is None else float(slip_capacity),
        "prying_allowance": float(prying_allowance),
        "tension_mode": tension_mode,
    }

    details: list[dict[str, Any]] = []
    for idx, bf in enumerate(bolt_results):
        Vu = math.hypot(bf.Fy, bf.Fz) / 1000.0

        if tension_mode == "override":
            Tu = float(tension_value)
        else:
            Tu = max(0.0, float(bf.Fx)) / 1000.0

        Tu_prying = Tu * (1.0 + prying_allowance) if Tu > 0.0 else Tu

        # AS 4100 Clause 9.3.2.4: a_e is clear distance from hole edge to plate edge
        # Standard hole diameter is typically bolt_diameter + 2mm
        hole_dia = bolt_diameter + 2.0
        
        bolt_y, bolt_z = bf.point
        edge_clear_y_min = abs(bolt_y - plate.y_min)
        edge_clear_y_max = abs(plate.y_max - bolt_y)
        edge_clear_z_min = abs(bolt_z - plate.z_min)
        edge_clear_z_max = abs(plate.z_max - bolt_z)
        
        # Minimum distance from bolt center to plate edge
        edge_clear_center = min(edge_clear_y_min, edge_clear_y_max, edge_clear_z_min, edge_clear_z_max)
        
        # a_e: clear distance from hole edge to plate edge (per AS 4100:2020 Cl. 9.3.2.4)
        a_e = edge_clear_center - hole_dia / 2.0

        Vp = a_e * plate.thickness * plate.fu
        bearing_capacity = 0.9 * min(Vb, Vp) / 1000.0

        shear_util = Vu / shear_capacity if shear_capacity > 0.0 else math.inf
        tension_util = Tu_prying / tension_capacity if tension_capacity > 0.0 else math.inf
        bearing_util = Vu / bearing_capacity if bearing_capacity > 0.0 else math.inf

        term_v = (Vu / shear_capacity) ** 2 if shear_capacity > 0.0 else math.inf
        term_t = (Tu_prying / tension_capacity) ** 2 if tension_capacity > 0.0 else math.inf
        interaction_util = term_v + term_t if (term_v + term_t) < math.inf else math.inf

        slip_util: float | None = None
        if slip_capacity is not None:
            slip_util = Vu / slip_capacity if slip_capacity > 0.0 else math.inf

        utils: list[tuple[float, str]] = [
            (shear_util, "shear"),
            (tension_util, "tension"),
            (interaction_util, "interaction"),
            (bearing_util, "bearing"),
        ]
        if slip_util is not None:
            utils.append((slip_util, "slip"))

        governing_util, governing_state = max(utils, key=lambda x: x[0])

        calc: dict[str, object] = {
            "Vu_kN": float(Vu),
            "Tu_kN": float(Tu),
            "Tu_prying_kN": float(Tu_prying),
            "prying_allowance": float(prying_allowance),
            "Vb_N": float(Vb),
            "hole_dia": float(hole_dia),
            "edge_clear_center": float(edge_clear_center),
            "a_e": float(a_e),
            "Vp_N": float(Vp),
            "bearing_capacity_kN": float(bearing_capacity),
            "shear_capacity_kN": float(shear_capacity),
            "tension_capacity_kN": float(tension_capacity),
            "term_v": float(term_v) if term_v < math.inf else math.inf,
            "term_t": float(term_t) if term_t < math.inf else math.inf,
        }

        details.append({
            "bolt_index": idx,
            "point": bf.point,
            "shear_demand_kN": Vu,
            "tension_demand_kN": Tu,
            "shear_capacity_kN": shear_capacity,
            "tension_capacity_kN": tension_capacity,
            "bearing_capacity_kN": bearing_capacity,
            "slip_capacity_kN": slip_capacity,
            "shear_util": shear_util,
            "tension_util": tension_util,
            "bearing_util": bearing_util,
            "slip_util": slip_util,
            "governing_util": governing_util,
            "governing_limit_state": governing_state,
            "interaction_util": interaction_util,
            "calc": calc,
        })

    if not details:
        gov_idx, gov_state, gov_util = None, None, 0.0
    else:
        idx_in_list, detail = max(enumerate(details), key=lambda item: item[1]["governing_util"])
        gov_idx = detail["bolt_index"]
        gov_state = detail["governing_limit_state"]
        gov_util = detail["governing_util"]

    return {
        "connection_type": connection_type,
        "method": result.method,
        "governing_bolt_index": gov_idx,
        "governing_limit_state": gov_state,
        "governing_utilization": gov_util,
        "meta": meta,
        "details": details,
    }


__all__ = ["AS4100_GRADE_PROPERTIES", "AS4100_PRETENSION_KN", "check_as4100"]
