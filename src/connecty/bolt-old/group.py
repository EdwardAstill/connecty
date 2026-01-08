"""
Bolt connection geometry models.

This module contains *input* data structures only (geometry + material/bolt specs).
Analysis is performed by `BoltResult` in `connecty.bolt.analysis`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import TYPE_CHECKING

import numpy as np

from ..common.load import Load
from .types import Point2D, TensionMethod, ShearMethod, HoleType, SurfaceClass

if TYPE_CHECKING:
    from .analysis import BoltResult
    from .plate import Plate
    from .bolt import BoltParams


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
        tension_method: TensionMethod = "accurate",
    ) -> BoltResult:
        """Analyze this connection and return a `BoltResult`."""
        from .analysis import BoltResult

        return BoltResult(
            connection=self,
            load=load,
            shear_method=shear_method,
            tension_method=tension_method,
        )
