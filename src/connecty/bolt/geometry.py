"""
Bolt connection geometry models.

This module contains *input* data structures only (geometry + material/bolt specs).
Analysis is performed by `BoltResult` in `connecty.bolt.analysis`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Literal

import numpy as np

from ..common.load import Load

Point2D = tuple[float, float]  # (y, z)


_BOLT_GRADE_PROPERTIES: dict[str, dict[str, float]] = {
    # Typical values used for general connection design.
    # Units are user-defined; connecty is unit-agnostic.
    "A325": {"fy": 660.0, "fu": 830.0},
    "A490": {"fy": 940.0, "fu": 1040.0},
    "8.8": {"fy": 640.0, "fu": 800.0},
    "10.9": {"fy": 900.0, "fu": 1000.0},
}


@dataclass(frozen=True)
class BoltParams:
    """Bolt properties + size (unit-agnostic)."""

    diameter: float
    grade: str | None = None
    fy: float | None = None
    fu: float | None = None

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

        if self.fy is not None and self.fy <= 0.0:
            raise ValueError("Bolt fy must be positive")
        if self.fu is not None and self.fu <= 0.0:
            raise ValueError("Bolt fu must be positive")


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
class BoltLayout:
    """A 2D bolt layout (y-z plane). Geometry only."""

    points: list[Point2D]

    _properties: BoltProperties | None = field(default=None, repr=False, init=False)

    def __post_init__(self) -> None:
        if len(self.points) < 1:
            raise ValueError("Bolt layout must have at least one bolt")

    @classmethod
    def from_pattern(
        cls,
        rows: int,
        cols: int,
        spacing_y: float,
        spacing_z: float,
        origin: Point2D = (0.0, 0.0),
        offset_y: float = 0.0,
        offset_z: float = 0.0,
    ) -> "BoltLayout":
        """Create a rectangular bolt pattern centered at `origin`.

        You can also apply an explicit offset using `offset_y` / `offset_z` (in the y/z axes).
        If `offset_y` or `offset_z` is non-zero, `origin` must be left at its default (0, 0).
        """
        if rows < 1 or cols < 1:
            raise ValueError("rows and cols must be at least 1")

        if (offset_y != 0.0 or offset_z != 0.0) and origin != (0.0, 0.0):
            raise ValueError("Specify either origin or offset_y/offset_z, not both")
        if offset_y != 0.0 or offset_z != 0.0:
            origin = (float(offset_y), float(offset_z))

        y0, z0 = origin
        y_start = y0 - (rows - 1) * spacing_y / 2.0
        z_start = z0 - (cols - 1) * spacing_z / 2.0

        points: list[Point2D] = []
        for i in range(rows):
            for j in range(cols):
                y = y_start + i * spacing_y
                z = z_start + j * spacing_z
                points.append((y, z))

        return cls(points=points)

    @classmethod
    def from_circle(
        cls,
        n: int,
        radius: float,
        center: Point2D = (0.0, 0.0),
        start_angle: float = 0.0,
        offset_y: float = 0.0,
        offset_z: float = 0.0,
    ) -> "BoltLayout":
        """Create `n` bolts on a circle in the y-z plane."""
        if n < 1:
            raise ValueError("n must be at least 1")
        if radius <= 0.0:
            raise ValueError("radius must be positive")

        if (offset_y != 0.0 or offset_z != 0.0) and center != (0.0, 0.0):
            raise ValueError("Specify either center or offset_y/offset_z, not both")
        if offset_y != 0.0 or offset_z != 0.0:
            center = (float(offset_y), float(offset_z))

        cy, cz = center
        points: list[Point2D] = []
        for i in range(n):
            angle = math.radians(start_angle + i * 360.0 / n)
            y = cy + radius * math.sin(angle)
            z = cz + radius * math.cos(angle)
            points.append((y, z))

        return cls(points=points)

    def _calculate_properties(self) -> BoltProperties:
        if self._properties is not None:
            return self._properties

        y_arr = np.array([p[0] for p in self.points], dtype=float)
        z_arr = np.array([p[1] for p in self.points], dtype=float)

        Cy = float(np.mean(y_arr))
        Cz = float(np.mean(z_arr))

        dy_arr = y_arr - Cy
        dz_arr = z_arr - Cz

        Iz = float(np.sum(dy_arr**2))
        Iy = float(np.sum(dz_arr**2))
        Ip = Iy + Iz

        self._properties = BoltProperties(Cy=Cy, Cz=Cz, n=len(self.points), Iy=Iy, Iz=Iz, Ip=Ip)
        return self._properties

    @property
    def n(self) -> int:
        return len(self.points)

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

    @classmethod
    def from_dimensions(
        cls,
        *,
        width: float,
        height: float,
        thickness: float,
        fu: float,
        fy: float | None = None,
        center: Point2D = (0.0, 0.0),
    ) -> "Plate":
        """Create a rectangular plate from width/height (y/z) and an optional center point.

        Notes:
        - `width` is the plate size in the **y** direction.
        - `height` is the plate size in the **z** direction.
        """
        if width <= 0.0:
            raise ValueError("Plate width must be positive")
        if height <= 0.0:
            raise ValueError("Plate height must be positive")

        cy, cz = center
        half_w = width / 2.0
        half_h = height / 2.0

        return cls(
            corner_a=(cy - half_w, cz - half_h),
            corner_b=(cy + half_w, cz + half_h),
            thickness=thickness,
            fu=fu,
            fy=fy,
        )

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

    @property
    def width(self) -> float:
        """Alias for plate size in y-direction."""
        return self.depth_y

    @property
    def height(self) -> float:
        """Alias for plate size in z-direction."""
        return self.depth_z

    @property
    def center(self) -> Point2D:
        """Plate center (y, z)."""
        return ((self.y_min + self.y_max) / 2.0, (self.z_min + self.z_max) / 2.0)


TensionMethod = Literal["conservative", "accurate"]
ShearMethod = Literal["elastic", "icr"]


@dataclass(frozen=True)
class BoltConnection:
    """Bolt group + plate definition for connection geometry."""

    layout: BoltLayout
    bolt: BoltParams
    plate: Plate | None = None
    n_shear_planes: int = 1

    def __post_init__(self) -> None:
        if self.n_shear_planes < 1:
            raise ValueError("n_shear_planes must be at least 1")

        if self.plate is None:
            return

        radius = float(self.bolt.diameter) / 2.0
        for y, z in self.layout.points:
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
    ) -> "BoltResult":
        """Analyze this connection and return a `BoltResult`."""
        from .analysis import BoltResult

        return BoltResult(
            connection=self,
            load=load,
            shear_method=shear_method,
            tension_method=tension_method,
        )
__all__ = [
    "BoltParams",
    "BoltProperties",
    "BoltLayout",
    "Plate",
    "BoltConnection",
    "TensionMethod",
    "ShearMethod",
]


