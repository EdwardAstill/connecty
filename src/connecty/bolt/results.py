"""Result models for bolt analysis."""

from __future__ import annotations

from dataclasses import dataclass
import math

Point2D = tuple[float, float]  # (y, z)


@dataclass
class BoltResult:
    """Forces and derived stresses at a single bolt location."""

    point: Point2D
    Fy: float
    Fz: float
    Fx: float = 0.0
    diameter: float = 0.0
    n_shear_planes: int = 1

    @property
    def y(self) -> float:
        return self.point[0]

    @property
    def z(self) -> float:
        return self.point[1]

    @property
    def shear(self) -> float:
        return math.hypot(self.Fy, self.Fz)

    @property
    def axial(self) -> float:
        return self.Fx

    @property
    def resultant(self) -> float:
        return math.sqrt(self.Fy**2 + self.Fz**2 + self.Fx**2)

    @property
    def angle(self) -> float:
        return math.degrees(math.atan2(self.Fy, self.Fz))

    @property
    def area(self) -> float:
        if self.diameter <= 0.0:
            return 0.0
        return math.pi * (self.diameter / 2.0) ** 2

    @property
    def shear_stress(self) -> float:
        if self.area <= 0.0:
            return 0.0
        planes = max(1, int(self.n_shear_planes))
        return self.shear / (self.area * planes)

    @property
    def shear_stress_y(self) -> float:
        if self.area <= 0.0:
            return 0.0
        planes = max(1, int(self.n_shear_planes))
        return abs(self.Fy) / (self.area * planes)

    @property
    def shear_stress_z(self) -> float:
        if self.area <= 0.0:
            return 0.0
        planes = max(1, int(self.n_shear_planes))
        return abs(self.Fz) / (self.area * planes)

    @property
    def axial_stress(self) -> float:
        if self.area <= 0.0:
            return 0.0
        stress = self.Fx / self.area
        return max(0.0, stress)

    @property
    def combined_stress(self) -> float:
        if self.area <= 0.0:
            return 0.0
        return math.sqrt(self.shear_stress**2 + abs(self.axial_stress) ** 2)


