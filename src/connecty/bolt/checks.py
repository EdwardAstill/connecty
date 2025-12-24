"""
Unified bolt checks for AISC 360-22 and AS 4100.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from .bolt import ConnectionResult

# === Reference data ===

# AISC 360-22
AISC_GRADE_STRESS = {
    "A325": {"Fnt": 620.0, "Fnv_N": 370.0, "Fnv_X": 470.0},
    "A490": {"Fnt": 780.0, "Fnv_N": 470.0, "Fnv_X": 580.0},
}

AISC_PRETENSION_KN = {
    12: {"A325": 49.0, "A490": 72.0}, 16: {"A325": 91.0, "A490": 114.0},
    20: {"A325": 142.0, "A490": 179.0}, 22: {"A325": 176.0, "A490": 221.0},
    24: {"A325": 205.0, "A490": 257.0}, 27: {"A325": 267.0, "A490": 334.0},
    30: {"A325": 326.0, "A490": 408.0}, 36: {"A325": 475.0, "A490": 595.0},
}

AISC_HOLE_DIAMETERS = {
    12: {"standard": 14.0, "oversize": 16.0, "short_slotted": 14.0, "long_slotted": 14.0},
    16: {"standard": 18.0, "oversize": 20.0, "short_slotted": 18.0, "long_slotted": 18.0},
    20: {"standard": 22.0, "oversize": 24.0, "short_slotted": 22.0, "long_slotted": 22.0},
    22: {"standard": 24.0, "oversize": 28.0, "short_slotted": 24.0, "long_slotted": 24.0},
    24: {"standard": 27.0, "oversize": 30.0, "short_slotted": 27.0, "long_slotted": 27.0},
    27: {"standard": 30.0, "oversize": 35.0, "short_slotted": 30.0, "long_slotted": 30.0},
    30: {"standard": 33.0, "oversize": 38.0, "short_slotted": 33.0, "long_slotted": 33.0},
}

AISC_SLIP_COEFFICIENT = {"A": 0.30, "B": 0.50}

# AS 4100
AS4100_GRADE_PROPERTIES = {
    "8.8": {
        "fuf": 800.0, "fy": 640.0,
        "As": {12: 84.3, 16: 157.0, 20: 245.0, 22: 303.0, 24: 353.0, 27: 459.0, 30: 561.0, 36: 817.0},
        "Ac": {12: 76.3, 16: 140.7, 20: 217.5, 22: 268.8, 24: 312.1, 27: 405.7, 30: 491.4, 36: 713.0},
        "Ao": {12: 113.1, 16: 201.1, 20: 314.2, 22: 380.1, 24: 452.4, 27: 572.6, 30: 706.9, 36: 1017.9},
    },
    "10.9": {
        "fuf": 1000.0, "fy": 900.0,
        "As": {12: 84.3, 16: 157.0, 20: 245.0, 22: 303.0, 24: 353.0, 27: 459.0, 30: 561.0, 36: 817.0},
        "Ac": {12: 76.3, 16: 140.7, 20: 217.5, 22: 268.8, 24: 312.1, 27: 405.7, 30: 491.4, 36: 713.0},
        "Ao": {12: 113.1, 16: 201.1, 20: 314.2, 22: 380.1, 24: 452.4, 27: 572.6, 30: 706.9, 36: 1017.9},
    },
}

AS4100_PRETENSION_KN = {
    12: {"8.8": 50.0, "10.9": 65.0}, 16: {"8.8": 95.0, "10.9": 125.0},
    20: {"8.8": 155.0, "10.9": 205.0}, 22: {"8.8": 190.0, "10.9": 250.0},
    24: {"8.8": 225.0, "10.9": 295.0}, 27: {"8.8": 295.0, "10.9": 385.0},
    30: {"8.8": 360.0, "10.9": 475.0}, 36: {"8.8": 530.0, "10.9": 700.0},
}


# === Result classes ===

@dataclass
class BoltCheckDetail:
    bolt_index: int
    point: Tuple[float, float]
    shear_demand: float
    tension_demand: float
    shear_capacity: float
    tension_capacity: float
    bearing_capacity: float
    slip_capacity: float | None
    shear_util: float
    tension_util: float
    bearing_util: float
    slip_util: float | None
    governing_util: float
    governing_limit_state: str
    interaction_util: float = 0.0

    @property
    def info(self) -> Dict[str, Any]:
        return {
            "bolt_index": self.bolt_index, "point": self.point,
            "shear_demand_kN": self.shear_demand, "tension_demand_kN": self.tension_demand,
            "shear_capacity_kN": self.shear_capacity, "tension_capacity_kN": self.tension_capacity,
            "bearing_capacity_kN": self.bearing_capacity, "slip_capacity_kN": self.slip_capacity,
            "shear_util": self.shear_util, "tension_util": self.tension_util,
            "bearing_util": self.bearing_util, "slip_util": self.slip_util,
            "interaction_util": self.interaction_util, "governing_util": self.governing_util,
            "governing_limit_state": self.governing_limit_state,
        }


@dataclass
class BoltCheckResult:
    connection_type: str
    method: str
    details: List[BoltCheckDetail] = field(default_factory=list)
    governing_bolt_index: int | None = None
    governing_limit_state: str | None = None
    governing_utilization: float = 0.0

    @property
    def info(self) -> Dict[str, Any]:
        return {
            "connection_type": self.connection_type, "method": self.method,
            "governing_bolt_index": self.governing_bolt_index,
            "governing_limit_state": self.governing_limit_state,
            "governing_utilization": self.governing_utilization,
            "details": [d.info for d in self.details],
        }


# === Main check function ===

def check_bolt_group(
    result: "ConnectionResult",
    standard: str | None = None,
    connection_type: str | None = None,
    hole_type: str = "standard",
    slot_orientation: str = "perpendicular",
    threads_in_shear_plane: bool = True,
    slip_class: str = "A",
    n_s: int = 1,
    fillers: int = 0,
    n_b_tension: int | None = None,
    hole_type_factor: float = 1.0,
    slip_coefficient: float = 0.35,
    n_e: int = 1,
    nn_shear_planes: int = 1,
    nx_shear_planes: int = 0,
    prying_allowance: float = 0.25,
    reduction_factor_kr: float = 1.0,
    tension_per_bolt: float | None = None,
    pretension_override: float | None = None,
    require_explicit_tension: bool = False,
    assume_uniform_tension_if_missing: bool = True,
) -> BoltCheckResult:
    """Check bolt group per AISC 360-22 or AS 4100."""
    
    grade = result.connection.bolt_group.grade
    bolt_diameter = result.connection.bolt_group.parameters.diameter
    plate = result.connection.plate
    
    # Auto-detect standard
    if standard is None:
        standard = "aisc" if grade in ("A325", "A490") else "as4100"
    
    standard = standard.lower()
    connection_type = connection_type or "bearing"
    
    if standard == "aisc":
        return _check_aisc(
            result, grade, bolt_diameter, plate, connection_type, hole_type, slot_orientation,
            threads_in_shear_plane, slip_class, n_s, fillers, n_b_tension,
            tension_per_bolt, pretension_override
        )
    else:
        return _check_as4100(
            result, grade, bolt_diameter, plate, connection_type, hole_type, hole_type_factor,
            slip_coefficient, n_e, nn_shear_planes, nx_shear_planes, prying_allowance,
            reduction_factor_kr, tension_per_bolt, pretension_override,
            require_explicit_tension, assume_uniform_tension_if_missing
        )


# === AISC Implementation ===

def _check_aisc(result, grade, bolt_diameter, plate, connection_type, hole_type, slot_orientation,
                threads_in_shear_plane, slip_class, n_s, fillers, n_b_tension,
                tension_per_bolt, pretension_override):
    """AISC 360-22 check."""
    
    if connection_type not in ("bearing", "slip-critical"):
        raise ValueError("AISC connection_type must be 'bearing' or 'slip-critical'")
    
    # Get material properties
    area_b = math.pi * (bolt_diameter ** 2) / 4.0
    stresses = AISC_GRADE_STRESS[grade]
    Fnv = stresses["Fnv_N" if threads_in_shear_plane else "Fnv_X"]
    Fnt = stresses["Fnt"]
    
    # Hole diameter
    size_key = int(round(bolt_diameter))
    hole_dia = AISC_HOLE_DIAMETERS.get(size_key, {}).get(hole_type, bolt_diameter + 2.0)
    
    # Pretension
    pretension = pretension_override or AISC_PRETENSION_KN[size_key][grade]
    
    # Slip factor
    phi_slip = 1.0
    if hole_type == "long_slotted":
        phi_slip = 0.70
    elif hole_type == "oversize":
        phi_slip = 0.85
    elif hole_type == "short_slotted":
        phi_slip = 1.0 if slot_orientation == "perpendicular" else 0.85
    
    slip_mu = AISC_SLIP_COEFFICIENT[slip_class]
    h_f = 0.85 if fillers >= 2 else 1.0
    
    bolt_results = result.to_bolt_results()
    n_b = n_b_tension or len(bolt_results)
    
    # Tension demand mode - always use per-bolt tensions when available
    has_per_bolt_tension = bolt_results and hasattr(bolt_results[0], "Fx")
    if tension_per_bolt is not None:
        tension_mode = "override"
        tension_value = max(0.0, float(tension_per_bolt)) / 1000.0
    elif has_per_bolt_tension:
        tension_mode = "per_bolt"
        tension_value = None
    else:
        tension_mode = "uniform"
        tension_value = max(0.0, float(result.load.Fx)) / 1000.0 / max(len(bolt_results), 1)
    
    details = []
    for idx, bf in enumerate(bolt_results):
        # Demands (kN)
        Vu = math.hypot(bf.Fy, bf.Fz) / 1000.0
        Tu = max(0.0, float(getattr(bf, "Fx"))) / 1000.0 if tension_mode == "per_bolt" else tension_value
        
        # Shear capacity
        shear_cap = 0.75 * Fnv * area_b / 1000.0
        
        # Tension capacity (with shear interaction)
        f_rv = (Vu * 1000.0) / area_b
        Fnt_prime = max(0.0, min(Fnt, 1.3 * Fnt - (Fnt / (0.75 * Fnv)) * f_rv))
        tension_cap = 0.75 * Fnt_prime * area_b / 1000.0
        
        # Bearing capacity - calculate edge distances from plate boundaries
        bolt_y, bolt_z = bf.point
        edge_clear_y_min = abs(bolt_y - plate.y_min) - hole_dia / 2.0
        edge_clear_y_max = abs(plate.y_max - bolt_y) - hole_dia / 2.0
        edge_clear_z_min = abs(bolt_z - plate.z_min) - hole_dia / 2.0
        edge_clear_z_max = abs(plate.z_max - bolt_z) - hole_dia / 2.0
        lc = min(edge_clear_y_min, edge_clear_y_max, edge_clear_z_min, edge_clear_z_max)
        
        bearing_nom = 2.4 * bolt_diameter * plate.thickness * plate.fu
        tear_nom = 1.2 * lc * plate.thickness * plate.fu
        bearing_cap = 0.75 * min(bearing_nom, tear_nom) / 1000.0
        
        # Slip capacity
        slip_cap = None
        slip_util = None
        if connection_type == "slip-critical":
            k_sc = max(0.0, 1.0 - Tu / (1.13 * pretension * n_b))
            slip_cap = phi_slip * slip_mu * 1.13 * h_f * pretension * n_s * k_sc
            slip_util = Vu / slip_cap if slip_cap > 0 else math.inf
        
        # Utilizations
        shear_util = Vu / shear_cap if shear_cap > 0 else math.inf
        tension_util = Tu / tension_cap if tension_cap > 0 else math.inf
        bearing_util = Vu / bearing_cap if bearing_cap > 0 else math.inf
        
        utils = [(shear_util, "shear"), (tension_util, "tension"), (bearing_util, "bearing")]
        if slip_util is not None:
            utils.append((slip_util, "slip"))
        
        governing_util, governing_state = max(utils, key=lambda x: x[0])
        
        details.append(BoltCheckDetail(
            bolt_index=idx, point=bf.point, shear_demand=Vu, tension_demand=Tu,
            shear_capacity=shear_cap, tension_capacity=tension_cap, bearing_capacity=bearing_cap,
            slip_capacity=slip_cap, shear_util=shear_util, tension_util=tension_util,
            bearing_util=bearing_util, slip_util=slip_util, governing_util=governing_util,
            governing_limit_state=governing_state,
        ))
    
    gov_idx, gov_state, gov_util = _get_governing(details)
    return BoltCheckResult(connection_type, result.method, details, gov_idx, gov_state, gov_util)


# === AS 4100 Implementation ===

def _check_as4100(result, grade, bolt_diameter, plate, connection_type, hole_type, hole_type_factor,
                  slip_coefficient, n_e, nn_shear_planes, nx_shear_planes, prying_allowance,
                  reduction_factor_kr, tension_per_bolt, pretension_override,
                  require_explicit_tension, assume_uniform_tension_if_missing):
    """AS 4100 check."""
    
    if connection_type not in ("bearing", "friction"):
        raise ValueError("AS 4100 connection_type must be 'bearing' or 'friction'")
    
    # Material properties
    props = AS4100_GRADE_PROPERTIES[grade]
    fuf = props["fuf"]
    size_key = int(round(bolt_diameter))
    As = props["As"].get(size_key, math.pi * (bolt_diameter ** 2) / 4.0 * 0.75)
    Ac = props["Ac"].get(size_key, As * 0.9)
    Ao = props["Ao"].get(size_key, math.pi * (bolt_diameter ** 2) / 4.0)
    
    # Capacities (all bolts same)
    Vf = 0.62 * reduction_factor_kr * fuf * (nn_shear_planes * Ac + nx_shear_planes * Ao) / 1000.0
    shear_capacity = 0.8 * Vf
    
    Ntf = As * fuf / 1000.0
    tension_capacity = 0.8 * Ntf
    
    # Bearing capacity
    Vb = 3.2 * plate.thickness * bolt_diameter * plate.fu
    
    # Slip capacity
    slip_capacity = None
    if connection_type == "friction":
        pretension = pretension_override or AS4100_PRETENSION_KN[size_key][grade]
        slip_capacity = 0.7 * slip_coefficient * n_e * pretension * hole_type_factor
    
    # Tension demand mode - always use per-bolt tensions when available
    bolt_results = result.to_bolt_results()
    has_per_bolt_tension = bolt_results and hasattr(bolt_results[0], "Fx")
    
    if tension_per_bolt is not None:
        tension_mode = "override"
        tension_value = max(0.0, float(tension_per_bolt)) / 1000.0
    elif has_per_bolt_tension:
        tension_mode = "per_bolt"
        tension_value = None
    else:
        if require_explicit_tension or not assume_uniform_tension_if_missing:
            raise ValueError("No bolt tension provided for AS 4100")
        tension_mode = "uniform"
        tension_value = max(0.0, float(result.load.Fx)) / 1000.0 / max(len(bolt_results), 1)
    
    details = []
    for idx, bf in enumerate(bolt_results):
        # Demands (kN)
        Vu = math.hypot(bf.Fy, bf.Fz) / 1000.0
        Tu = max(0.0, float(getattr(bf, "Fx"))) / 1000.0 if tension_mode == "per_bolt" else tension_value
        Tu_prying = Tu * (1.0 + prying_allowance) if Tu > 0 else Tu
        
        # Bearing capacity - calculate clear edge distance for this bolt
        bolt_y, bolt_z = bf.point
        edge_clear_y_min = abs(bolt_y - plate.y_min)
        edge_clear_y_max = abs(plate.y_max - bolt_y)
        edge_clear_z_min = abs(bolt_z - plate.z_min)
        edge_clear_z_max = abs(plate.z_max - bolt_z)
        edge_clear = min(edge_clear_y_min, edge_clear_y_max, edge_clear_z_min, edge_clear_z_max)
        Vp = edge_clear * plate.thickness * plate.fu
        bearing_capacity = 0.9 * min(Vb, Vp) / 1000.0
        
        # Utilizations
        shear_util = Vu / shear_capacity if shear_capacity > 0 else math.inf
        tension_util = Tu_prying / tension_capacity if tension_capacity > 0 else math.inf
        bearing_util = Vu / bearing_capacity if bearing_capacity > 0 else math.inf
        
        # Interaction (quadratic)
        term_v = (Vu / shear_capacity) ** 2 if shear_capacity > 0 else math.inf
        term_t = (Tu_prying / tension_capacity) ** 2 if tension_capacity > 0 else math.inf
        interaction_util = term_v + term_t if (term_v + term_t) < math.inf else math.inf
        
        # Slip
        slip_util = None
        if slip_capacity:
            slip_util = Vu / slip_capacity if slip_capacity > 0 else math.inf
        
        utils = [(shear_util, "shear"), (tension_util, "tension"),
                 (interaction_util, "interaction"), (bearing_util, "bearing")]
        if slip_util is not None:
            utils.append((slip_util, "slip"))
        
        governing_util, governing_state = max(utils, key=lambda x: x[0])
        
        details.append(BoltCheckDetail(
            bolt_index=idx, point=bf.point, shear_demand=Vu, tension_demand=Tu,
            shear_capacity=shear_capacity, tension_capacity=tension_capacity,
            bearing_capacity=bearing_capacity, slip_capacity=slip_capacity,
            shear_util=shear_util, tension_util=tension_util, bearing_util=bearing_util,
            slip_util=slip_util, interaction_util=interaction_util,
            governing_util=governing_util, governing_limit_state=governing_state,
        ))
    
    gov_idx, gov_state, gov_util = _get_governing(details)
    return BoltCheckResult(connection_type, result.method, details, gov_idx, gov_state, gov_util)


# === Helper ===

def _get_governing(details: List[BoltCheckDetail]) -> Tuple[int | None, str | None, float]:
    """Find governing bolt."""
    if not details:
        return None, None, 0.0
    idx, detail = max(enumerate(details), key=lambda item: item[1].governing_util)
    return idx, detail.governing_limit_state, detail.governing_util
