from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass(frozen=True)
class BoltLayout:
    """Bolt positions in the y-z cross-section plane.

    Coordinates follow the connecty convention:
    - y: vertical axis in the section plane
    - z: horizontal axis in the section plane
    - x: along the member (out-of-plane, tension direction)
    """

    points: list[tuple[float, float]]

    def __post_init__(self) -> None:
        if not self.points:
            raise ValueError("BoltLayout must contain at least one bolt position")

    @classmethod
    def from_pattern(
        cls,
        *,
        rows: int,
        cols: int,
        spacing_y: float,
        spacing_z: float,
        offset_y: float = 0.0,
        offset_z: float = 0.0,
    ) -> BoltLayout:
        """Create a rectangular grid of bolt positions centred at (offset_y, offset_z).

        Args:
            rows: Number of rows (y direction).
            cols: Number of columns (z direction).
            spacing_y: Centre-to-centre distance between rows.
            spacing_z: Centre-to-centre distance between columns.
            offset_y: Shift the grid centre in y.
            offset_z: Shift the grid centre in z.
        """
        if rows < 1 or cols < 1:
            raise ValueError("rows and cols must be >= 1")

        height = (rows - 1) * spacing_y if rows > 1 else 0.0
        width = (cols - 1) * spacing_z if cols > 1 else 0.0

        start_y = -height / 2.0 + offset_y
        start_z = -width / 2.0 + offset_z

        pts: list[tuple[float, float]] = []
        for r in range(rows):
            for c in range(cols):
                y = start_y + r * spacing_y
                z = start_z + c * spacing_z
                pts.append((y, z))

        return cls(points=pts)

    @classmethod
    def from_circular(
        cls,
        *,
        radius: float,
        n: int = 6,
        center: tuple[float, float] = (0.0, 0.0),
        start_angle: float = 0.0,
    ) -> BoltLayout:
        """Create a circular bolt pattern.

        Args:
            radius: Bolt circle radius.
            n: Number of bolts.
            center: Centre of the circle (y, z).
            start_angle: Starting angle in degrees (CCW from +z axis).
        """
        cy, cz = center
        start_rad = math.radians(start_angle)
        step = 2 * math.pi / n

        pts: list[tuple[float, float]] = []
        for i in range(n):
            angle = start_rad + i * step
            y = cy + radius * math.sin(angle)
            z = cz + radius * math.cos(angle)
            pts.append((y, z))

        return cls(points=pts)

    @property
    def n(self) -> int:
        return len(self.points)

    @property
    def Cy(self) -> float:
        return sum(p[0] for p in self.points) / self.n

    @property
    def Cz(self) -> float:
        return sum(p[1] for p in self.points) / self.n
