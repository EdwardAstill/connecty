from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np


if TYPE_CHECKING:
    from .analysis import BoltResult


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


@dataclass
class BoltParams:
    """Bolt properties + size (unit-agnostic)."""

    diameter: float #mm
    grade: str | None = None # A325, A490
    fy: float | None = None # MPa
    fu: float | None = None # MPa
    Fnt: float | None = None # MPa
    Fnv_N: float | None = None # MPa
    Fnv_X: float | None = None # MPa

    def __post_init__(self) -> None:
        if self.diameter <= 0.0:
            raise ValueError("Bolt diameter must be positive")

        if self.grade is None and (self.fy is None or self.fu is None):
            raise ValueError("Provide either grade or both fy and fu")

        if self.grade is not None and self.grade not in _BOLT_GRADE_PROPERTIES:
            raise ValueError(f"Unsupported bolt grade: {self.grade}")

        if self.fy is None and self.grade is not None:
            object.__setattr__(self, "fy", float(_BOLT_GRADE_PROPERTIES[self.grade]["fy"]))
        if self.fu is None and self.grade is not None:
            object.__setattr__(self, "fu", float(_BOLT_GRADE_PROPERTIES[self.grade]["fu"]))

        if self.grade is not None:
            object.__setattr__(self, "Fnt", float(AISC_GRADE_STRESS[self.grade]["Fnt"]))
            object.__setattr__(self, "Fnv_N", float(AISC_GRADE_STRESS[self.grade]["Fnv_N"]))
            object.__setattr__(self, "Fnv_X", float(AISC_GRADE_STRESS[self.grade]["Fnv_X"]))

        if self.fy is not None and self.fy <= 0.0:
            raise ValueError("Bolt fy must be positive")
        if self.fu is not None and self.fu <= 0.0:
            raise ValueError("Bolt fu must be positive")
    
    @property
    def area(self) -> float:
        return np.pi * (self.diameter**2) / 4.0

    @property
    def get_Fnt(self) -> float | None:
        """Nominal tension stress (depends on standard)"""
        # TODO: Implement from AISC_GRADE_STRESS lookup
        raise NotImplementedError("Fnt property not yet implemented")

    @property
    def get_Fnv(self) -> float | None:
        """Nominal shear stress (depends on standard)"""
        # TODO: Implement from AISC_GRADE_STRESS lookup
        raise NotImplementedError("Fnv property not yet implemented")
