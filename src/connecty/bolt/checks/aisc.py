"""
AISC 360-22 bolt checks for A325/A490 bolts.

Implements bearing-type and slip-critical checks using per-bolt demands from
analysis results. Returned results follow a small dataclass API with an
``info`` dict for easy serialization or tabulation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Literal, Tuple


# === Reference data (AISC 360-22) ===

Grade = Literal["A325", "A490"]
HoleType = Literal["standard", "oversize", "short_slotted", "long_slotted"]
SlotOrientation = Literal["perpendicular", "parallel"]
SlipClass = Literal["A", "B"]
ConnectionType = Literal["bearing", "slip-critical"]

GRADE_STRESS = {
	"A325": {"Fnt": 620.0, "Fnv_N": 370.0, "Fnv_X": 470.0},  # MPa
	"A490": {"Fnt": 780.0, "Fnv_N": 470.0, "Fnv_X": 580.0},
}

PRETENSION_KN = {
	12: {"A325": 49.0, "A490": 72.0},
	16: {"A325": 91.0, "A490": 114.0},
	20: {"A325": 142.0, "A490": 179.0},
	22: {"A325": 176.0, "A490": 221.0},
	24: {"A325": 205.0, "A490": 257.0},
	27: {"A325": 267.0, "A490": 334.0},
	30: {"A325": 326.0, "A490": 408.0},
	36: {"A325": 475.0, "A490": 595.0},
}

HOLE_DIAMETERS = {
	12: {"standard": 14.0, "oversize": 16.0, "short_slotted": 14.0, "long_slotted": 14.0},
	16: {"standard": 18.0, "oversize": 20.0, "short_slotted": 18.0, "long_slotted": 18.0},
	20: {"standard": 22.0, "oversize": 24.0, "short_slotted": 22.0, "long_slotted": 22.0},
	22: {"standard": 24.0, "oversize": 28.0, "short_slotted": 24.0, "long_slotted": 24.0},
	24: {"standard": 27.0, "oversize": 30.0, "short_slotted": 27.0, "long_slotted": 27.0},
	27: {"standard": 30.0, "oversize": 35.0, "short_slotted": 30.0, "long_slotted": 30.0},
	30: {"standard": 33.0, "oversize": 38.0, "short_slotted": 33.0, "long_slotted": 33.0},
}

SLIP_COEFFICIENT = {"A": 0.30, "B": 0.50}
PHI_BEARING = 0.75
PHI_SHEAR = 0.75
PHI_TENSION = 0.75
DU = 1.13  # Mean installed pretension multiplier


# === Data classes ===


@dataclass
class BoltDesignParams:
	"""Design-only inputs required for checks."""

	grade: Grade
	hole_type: HoleType = "standard"
	slot_orientation: SlotOrientation = "perpendicular"
	threads_in_shear_plane: bool = True
	slip_class: SlipClass = "A"
	n_s: int = 1  # number of slip planes
	fillers: int = 0  # count of fillers (>=2 -> h_f = 0.85)
	plate_fu: float | None = None  # MPa
	plate_thickness: float | None = None  # mm
	edge_distance_y: float | None = None  # mm to plate edge in y
	edge_distance_z: float | None = None  # mm to plate edge in z
	tension_per_bolt: float | None = None  # kN (factored), overrides uniform Fx/n
	n_b_tension: int | None = None  # bolts carrying tension for k_sc
	pretension_override: float | None = None  # kN

	def hole_diameter(self, bolt_diameter: float) -> float:
		size_key = int(round(bolt_diameter))
		if size_key in HOLE_DIAMETERS:
			return HOLE_DIAMETERS[size_key][self.hole_type]
		# Fallback: standard hole = d + 2 mm typical
		return bolt_diameter + 2.0

	def pretension(self, bolt_diameter: float) -> float:
		if self.pretension_override is not None:
			return self.pretension_override
		size_key = int(round(bolt_diameter))
		if size_key not in PRETENSION_KN:
			raise ValueError(f"No pretension table entry for bolt size {bolt_diameter} mm")
		return PRETENSION_KN[size_key][self.grade]

	@property
	def slip_mu(self) -> float:
		return SLIP_COEFFICIENT[self.slip_class]

	@property
	def h_f(self) -> float:
		return 0.85 if self.fillers >= 2 else 1.0


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

	@property
	def info(self) -> Dict[str, Any]:
		return {
			"bolt_index": self.bolt_index,
			"point": self.point,
			"shear_demand_kN": self.shear_demand,
			"tension_demand_kN": self.tension_demand,
			"shear_capacity_kN": self.shear_capacity,
			"tension_capacity_kN": self.tension_capacity,
			"bearing_capacity_kN": self.bearing_capacity,
			"slip_capacity_kN": self.slip_capacity,
			"shear_util": self.shear_util,
			"tension_util": self.tension_util,
			"bearing_util": self.bearing_util,
			"slip_util": self.slip_util,
			"governing_util": self.governing_util,
			"governing_limit_state": self.governing_limit_state,
		}


@dataclass
class BoltCheckResult:
	connection_type: ConnectionType
	method: str
	details: List[BoltCheckDetail] = field(default_factory=list)
	governing_bolt_index: int | None = None
	governing_limit_state: str | None = None
	governing_utilization: float = 0.0

	@property
	def info(self) -> Dict[str, Any]:
		return {
			"connection_type": self.connection_type,
			"method": self.method,
			"governing_bolt_index": self.governing_bolt_index,
			"governing_limit_state": self.governing_limit_state,
			"governing_utilization": self.governing_utilization,
			"details": [d.info for d in self.details],
		}


# === Core check ===


def check_bolt_group_aisc(
	result,
	design: BoltDesignParams,
	connection_type: ConnectionType = "bearing",
) -> BoltCheckResult:
	"""
	Evaluate AISC 360-22 checks for a BoltResult.
	"""

	from ..bolt import BoltForce, BoltResult  # Local import to avoid circularity

	if connection_type not in ("bearing", "slip-critical"):
		raise ValueError("connection_type must be 'bearing' or 'slip-critical'")
	if not isinstance(result, BoltResult):
		raise TypeError("result must be a BoltResult from BoltGroup.analyze")

	bolt_diameter = result.bolt_group.parameters.diameter
	area_b = _bolt_area(bolt_diameter)
	stresses = GRADE_STRESS[design.grade]
	Fnv = stresses["Fnv_N" if design.threads_in_shear_plane else "Fnv_X"]
	Fnt = stresses["Fnt"]
	hole_dia = design.hole_diameter(bolt_diameter)

	phi_slip = _phi_slip(design.hole_type, design.slot_orientation)
	pretension = design.pretension(bolt_diameter)
	n_b = design.n_b_tension or len(result.bolt_forces)

	# Tension demand: uniform Fx/n unless explicitly provided
	if design.tension_per_bolt is not None:
		tension_per_bolt = design.tension_per_bolt
	else:
		tension_per_bolt = result.force.Fx / 1000.0 / max(len(result.bolt_forces), 1)
		tension_per_bolt = max(0.0, tension_per_bolt)

	details: List[BoltCheckDetail] = []

	for idx, bf in enumerate(result.bolt_forces):
		Vu = math.hypot(bf.Fy, bf.Fz)  # kN resultant shear per bolt
		Tu = tension_per_bolt  # kN per bolt

		shear_cap = PHI_SHEAR * Fnv * area_b / 1000.0  # kN

		f_rv = Vu * 1000.0 / area_b  # MPa
		Fnt_prime = min(Fnt, 1.3 * Fnt - (Fnt / (PHI_TENSION * Fnv)) * f_rv)
		Fnt_prime = max(0.0, Fnt_prime)
		tension_cap = PHI_TENSION * Fnt_prime * area_b / 1000.0  # kN

		bearing_cap = _bearing_capacity(
			design=design,
			hole_dia=hole_dia,
			bolt_dia=bolt_diameter,
			Vu=Vu,
		)

		slip_cap = None
		slip_util = None
		if connection_type == "slip-critical":
			k_sc = max(0.0, 1.0 - Tu / (DU * pretension * n_b))
			slip_cap = phi_slip * design.slip_mu * DU * design.h_f * pretension * design.n_s * k_sc
			slip_util = Vu / slip_cap if slip_cap and slip_cap > 0 else math.inf

		shear_util = Vu / shear_cap if shear_cap > 0 else math.inf
		tension_util = Tu / tension_cap if tension_cap > 0 else math.inf
		bearing_util = Vu / bearing_cap if bearing_cap > 0 else math.inf

		util_candidates = [
			(shear_util, "shear"),
			(tension_util, "tension"),
			(bearing_util, "bearing"),
		]
		if slip_util is not None:
			util_candidates.append((slip_util, "slip"))

		governing_util, governing_state = max(util_candidates, key=lambda x: x[0])

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
			)
		)

	governing_idx, governing_state, governing_util = _governing(details)

	return BoltCheckResult(
		connection_type=connection_type,
		method=result.method,
		details=details,
		governing_bolt_index=governing_idx,
		governing_limit_state=governing_state,
		governing_utilization=governing_util,
	)


# === Helpers ===


def _bolt_area(diameter_mm: float) -> float:
	return math.pi * (diameter_mm ** 2) / 4.0


def _phi_slip(hole_type: HoleType, slot_orientation: SlotOrientation) -> float:
	if hole_type == "long_slotted":
		return 0.70
	if hole_type == "oversize":
		return 0.85
	if hole_type == "short_slotted":
		return 1.0 if slot_orientation == "perpendicular" else 0.85
	return 1.0


def _bearing_capacity(
	design: BoltDesignParams,
	hole_dia: float,
	bolt_dia: float,
	Vu: float,
) -> float:
	if design.plate_fu is None or design.plate_thickness is None:
		raise ValueError("plate_fu and plate_thickness are required for bearing checks")
	if design.edge_distance_y is None and design.edge_distance_z is None:
		raise ValueError("Provide at least one edge distance (y or z) for bearing checks")

	clear_y = None if design.edge_distance_y is None else design.edge_distance_y - hole_dia / 2.0
	clear_z = None if design.edge_distance_z is None else design.edge_distance_z - hole_dia / 2.0

	# Use the smallest available clear distance as governing for tear-out
	candidates = [c for c in (clear_y, clear_z) if c is not None]
	lc = max(min(candidates), 0.0) if candidates else 0.0

	bearing_nom = 2.4 * bolt_dia * design.plate_thickness * design.plate_fu  # N
	tear_nom = 1.2 * lc * design.plate_thickness * design.plate_fu  # N

	Rn = min(bearing_nom, tear_nom)
	return PHI_BEARING * Rn / 1000.0


def _governing(details: List[BoltCheckDetail]) -> Tuple[int | None, str | None, float]:
	if not details:
		return None, None, 0.0
	idx, detail = max(enumerate(details), key=lambda item: item[1].governing_util)
	return idx, detail.governing_limit_state, detail.governing_util
