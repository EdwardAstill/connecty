"""
Bolt connection geometry models.

This module contains *input* data structures only (geometry + material/bolt specs).
Analysis is performed by `LoadedBoltConnection` in `connecty.bolt.analysis`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Literal

import numpy as np

from ..common.load import Load

Point2D = tuple[float, float]  # (y, z)


@dataclass
class BoltParameters:
    """Bolt configuration parameters."""

    diameter: float
    grade: str = "A325"

    def __post_init__(self) -> None:
        if self.diameter <= 0.0:
            raise ValueError("Bolt diameter must be positive")
        if self.grade not in ("A325", "A490", "8.8", "10.9"):
            raise ValueError(f"Bolt grade must be A325, A490, 8.8, or 10.9, got {self.grade}")


@dataclass(frozen=True)
class BoltProperties:
    """Geometric properties of a bolt group about its centroid."""

    Cy: float
    Cz: float
    n: int
    Iy: float
    Iz: float
    Ip: float


@dataclass
class BoltGroup:
    """A group of bolts defined by (y, z) positions and bolt parameters."""

    positions: list[Point2D]
    diameter: float
    grade: str = "A325"

    _properties: BoltProperties | None = field(default=None, repr=False, init=False)

    def __post_init__(self) -> None:
        if len(self.positions) < 1:
            raise ValueError("Bolt group must have at least one bolt")
        if self.diameter <= 0.0:
            raise ValueError("Bolt diameter must be positive")
        if self.grade not in ("A325", "A490", "8.8", "10.9"):
            raise ValueError(f"Bolt grade must be A325, A490, 8.8, or 10.9, got {self.grade}")

    @property
    def parameters(self) -> BoltParameters:
        return BoltParameters(diameter=self.diameter, grade=self.grade)

    @classmethod
    def from_pattern(
        cls,
        rows: int,
        cols: int,
        spacing_y: float,
        spacing_z: float,
        diameter: float,
        grade: str = "A325",
        origin: Point2D = (0.0, 0.0),
    ) -> "BoltGroup":
        """Create a rectangular bolt pattern centered at `origin`."""
        if rows < 1 or cols < 1:
            raise ValueError("rows and cols must be at least 1")

        y0, z0 = origin
        y_start = y0 - (rows - 1) * spacing_y / 2.0
        z_start = z0 - (cols - 1) * spacing_z / 2.0

        positions: list[Point2D] = []
        for i in range(rows):
            for j in range(cols):
                y = y_start + i * spacing_y
                z = z_start + j * spacing_z
                positions.append((y, z))

        return cls(positions=positions, diameter=diameter, grade=grade)

    @classmethod
    def from_circle(
        cls,
        n: int,
        radius: float,
        diameter: float,
        grade: str = "A325",
        center: Point2D = (0.0, 0.0),
        start_angle: float = 0.0,
    ) -> "BoltGroup":
        """Create `n` bolts on a circle in the y-z plane."""
        if n < 1:
            raise ValueError("n must be at least 1")
        if radius <= 0.0:
            raise ValueError("radius must be positive")

        cy, cz = center
        positions: list[Point2D] = []
        for i in range(n):
            angle = math.radians(start_angle + i * 360.0 / n)
            y = cy + radius * math.sin(angle)
            z = cz + radius * math.cos(angle)
            positions.append((y, z))

        return cls(positions=positions, diameter=diameter, grade=grade)

    def _calculate_properties(self) -> BoltProperties:
        if self._properties is not None:
            return self._properties

        y_arr = np.array([p[0] for p in self.positions], dtype=float)
        z_arr = np.array([p[1] for p in self.positions], dtype=float)

        Cy = float(np.mean(y_arr))
        Cz = float(np.mean(z_arr))

        dy_arr = y_arr - Cy
        dz_arr = z_arr - Cz

        Iz = float(np.sum(dy_arr**2))
        Iy = float(np.sum(dz_arr**2))
        Ip = Iy + Iz

        self._properties = BoltProperties(Cy=Cy, Cz=Cz, n=len(self.positions), Iy=Iy, Iz=Iz, Ip=Ip)
        return self._properties

    @property
    def n(self) -> int:
        return len(self.positions)

    @property
    def Cy(self) -> float:
        return self._calculate_properties().Cy

    @property
    def Cz(self) -> float:
        return self._calculate_properties().Cz

    @property
    def Iy(self) -> float:
        return self._calculate_properties().Iy

    @property
    def Iz(self) -> float:
        return self._calculate_properties().Iz

    @property
    def Ip(self) -> float:
        return self._calculate_properties().Ip


@dataclass(frozen=True)
class Plate:
    """Axis-aligned rectangular plate in the bolt-group y-z plane."""

    corner_a: Point2D
    corner_b: Point2D
    thickness: float
    fu: float
    fy: float | None = None

    def __post_init__(self) -> None:
        if self.thickness <= 0.0:
            raise ValueError("Plate thickness must be positive")
        if self.fu <= 0.0:
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


TensionMethod = Literal["conservative", "accurate"]
ShearMethod = Literal["elastic", "icr"]


@dataclass(frozen=True)
class BoltConnection:
    """Bolt group + plate definition for connection geometry."""

    bolt_group: BoltGroup
    plate: Plate
    n_shear_planes: int = 1

    def __post_init__(self) -> None:
        if self.n_shear_planes < 1:
            raise ValueError("n_shear_planes must be at least 1")

        radius = self.bolt_group.diameter / 2.0
        for y, z in self.bolt_group.positions:
            dist_to_y_min = y - self.plate.y_min
            dist_to_y_max = self.plate.y_max - y
            dist_to_z_min = z - self.plate.z_min
            dist_to_z_max = self.plate.z_max - z

            if (
                dist_to_y_min < radius
                or dist_to_y_max < radius
                or dist_to_z_min < radius
                or dist_to_z_max < radius
            ):
                raise ValueError(
                    f"Bolt at ({y}, {z}) is within diameter/2 ({radius}) of plate boundary"
                )

    def analyze(
        self,
        load: Load,
        *,
        shear_method: ShearMethod = "elastic",
        tension_method: TensionMethod = "conservative",
    ) -> "LoadedBoltConnection":
        """Analyze this connection and return a `LoadedBoltConnection`."""
        from .analysis import LoadedBoltConnection

        return LoadedBoltConnection(
            connection=self,
            load=load,
            shear_method=shear_method,
            tension_method=tension_method,
        )


