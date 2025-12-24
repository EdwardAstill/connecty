"""Plate geometry helpers for bolt connections."""

from __future__ import annotations

from dataclasses import dataclass

Point = tuple[float, float]


@dataclass(frozen=True)
class Plate:
    """Axis-aligned plate rectangle in the bolt-group y-z plane.

    Plate geometry is specified by two opposing corners.

    Coordinates are (y, z) in the same length units used by the bolt group.
    
    Attributes:
        corner_a: First corner (y, z)
        corner_b: Opposite corner (y, z)
        thickness: Plate thickness (mm)
        fu: Ultimate tensile strength (MPa)
        fy: Yield strength (MPa) - optional, required for AS 4100
    """

    corner_a: Point
    corner_b: Point
    thickness: float
    fu: float
    fy: float | None = None

    def __post_init__(self) -> None:
        if self.thickness <= 0:
            raise ValueError("Plate thickness must be positive")
        if self.fu <= 0:
            raise ValueError("Plate fu (ultimate strength) must be positive")

    @property
    def y_min(self) -> float:
        return float(min(self.corner_a[0], self.corner_b[0]))

    @property
    def y_max(self) -> float:
        return float(max(self.corner_a[0], self.corner_b[0]))

    @property
    def z_min(self) -> float:
        return float(min(self.corner_a[1], self.corner_b[1]))

    @property
    def z_max(self) -> float:
        return float(max(self.corner_a[1], self.corner_b[1]))

    @property
    def depth_y(self) -> float:
        return self.y_max - self.y_min

    @property
    def depth_z(self) -> float:
        return self.z_max - self.z_min
