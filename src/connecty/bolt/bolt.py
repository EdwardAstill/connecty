from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..common.load import Load
    from .analysis import LoadedBoltConnection

from .plate import Plate
from .layout import BoltLayout
import numpy as np



_BOLT_GRADE_PROPERTIES: dict[str, dict[str, float]] = {
    # Typical values used for general connection design.
    # Units are user-defined; connecty is unit-agnostic.
    "A325": {"fy": 660.0, "fu": 830.0},
    "A490": {"fy": 940.0, "fu": 1040.0},
    "8.8": {"fy": 640.0, "fu": 800.0},
    "10.9": {"fy": 900.0, "fu": 1000.0},
}

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




@dataclass(slots=True)
class BoltParams:
    diameter: float
    grade: str | None = None
    threaded_in_shear_plane: bool = True
    E: float = 210000.0  # Modulus of elasticity (default steel) [N/mm^2] if using mm

    fy: float = field(init=False)
    fu: float = field(init=False)
    Fnt: float = field(init=False)
    Fnv: float = field(init=False)
    Fnv_N: float = field(init=False)
    Fnv_X: float = field(init=False)
    T_b: float = field(init=False) # pretension force
    area: float = field(init=False)
    stiffness: float = field(init=False)

    def __post_init__(self) -> None:
        self.recalculate()

    def recalculate(self) -> None:
        if self.grade is None:
             raise ValueError("Bolt grade is required")
        if self.grade not in _BOLT_GRADE_PROPERTIES:
             raise ValueError(f"Unknown bolt grade: {self.grade}")

        props = _BOLT_GRADE_PROPERTIES[self.grade]
        self.fy = float(props["fy"])
        self.fu = float(props["fu"])

        self.area = float(np.pi * (self.diameter**2) / 4.0)

        stresses = AISC_GRADE_STRESS[self.grade]
        self.Fnt = float(stresses["Fnt"])
        self.Fnv_N = float(stresses["Fnv_N"])
        self.Fnv_X = float(stresses["Fnv_X"])

        self.Fnv = float(self.Fnv_N if self.threaded_in_shear_plane else self.Fnv_X)
        self.T_b = float(AISC_PRETENSION_KN[self.diameter][self.grade])
        # Stiffness depends on grip length, so it is assigned by BoltConnection.
        self.stiffness = float("nan")

    def update_shear_plane_threads(self, included: bool) -> None:
        self.threaded_in_shear_plane = included
        self.recalculate()


@dataclass(slots=True)
class Bolt:
    """A single bolt in the y-z plane.

    Forces convention:
    - forces[0] = Fx (tension, out-of-plane)
    - forces[1] = Fy (shear, vertical in section plane)
    - forces[2] = Fz (shear, horizontal in section plane)
    """

    params: BoltParams
    position: tuple[float, float]  # (y, z)
    index: Optional[int] = field(default=None)
    k: float = field(init=False)

    def __post_init__(self) -> None:
        # Assigned by BoltConnection based on grip length.
        self.k = float("nan")

    @property
    def y(self) -> float:
        return self.position[0]

    @property
    def z(self) -> float:
        return self.position[1]


@dataclass(slots=True)
class BoltGroup:
    """Internal grouping of Bolt objects in the y-z plane."""

    bolts: list[Bolt]
    centroid: tuple[float, float] = field(init=False)

    def __post_init__(self) -> None:
        if not self.bolts:
            raise ValueError("BoltGroup must contain at least one bolt")

        cy = sum(b.position[0] for b in self.bolts) / len(self.bolts)
        cz = sum(b.position[1] for b in self.bolts) / len(self.bolts)
        self.centroid = (cy, cz)

    @property
    def n(self) -> int:
        return len(self.bolts)

    @property
    def points(self) -> list[tuple[float, float]]:
        return [b.position for b in self.bolts]

    @property
    def Cy(self) -> float:
        return self.centroid[0]

    @property
    def Cz(self) -> float:
        return self.centroid[1]

    @property
    def Ip(self) -> float:
        y_arr = np.array([b.position[0] for b in self.bolts], dtype=float)
        z_arr = np.array([b.position[1] for b in self.bolts], dtype=float)

        dy_arr = y_arr - self.Cy
        dz_arr = z_arr - self.Cz

        Iy = np.sum(dz_arr**2)
        Iz = np.sum(dy_arr**2)
        return float(Iy + Iz)

    @classmethod
    def create(
        cls,
        layout: BoltLayout,
        params: BoltParams,
    ) -> "BoltGroup":
        bolts = [
            Bolt(params=copy.copy(params), position=pos)
            for pos in layout.points
        ]
        return cls(bolts)


@dataclass(slots=True)
class BoltConnection:
    """A bolt connection in the y-z cross-section plane.

    Args:
        layout: Bolt positions (y, z).
        bolt: Bolt parameters (diameter, grade, etc.).
        plate: Plate geometry and material.
        n_shear_planes: Number of shear planes.
        threaded_in_shear_plane: Override bolt params thread setting.
    """

    layout: BoltLayout
    bolt: BoltParams
    plate: Plate
    n_shear_planes: int
    threaded_in_shear_plane: Optional[bool] = None

    bolt_group: BoltGroup = field(init=False)

    def __post_init__(self) -> None:
        self.bolt_group = BoltGroup.create(self.layout, self.bolt)

        if self.threaded_in_shear_plane is not None:
            for b in self.bolt_group.bolts:
                b.params.update_shear_plane_threads(self.threaded_in_shear_plane)

        total_thickness = self.plate.thickness
        if total_thickness <= 0.0:
            raise ValueError("plate thickness must be > 0 to compute bolt stiffness")

        for b in self.bolt_group.bolts:
            k = float(b.params.E * b.params.area / total_thickness)
            b.params.stiffness = k
            b.k = k

    def analyze(
        self,
        load: "Load",
        shear_method: str = "elastic",
        tension_method: str = "conservative",
    ) -> "LoadedBoltConnection":
        from .analysis import LoadedBoltConnection
        return LoadedBoltConnection(
            bolt_connection=self,
            load=load,
            shear_method=shear_method,
            tension_method=tension_method,
        )
