from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Point2D = tuple[float, float]
HoleType = Literal["standard", "oversize", "short_slotted", "long_slotted"]
SurfaceClass = Literal["A", "B"]

@dataclass(frozen=True)
class Plate:
    """Axis-aligned rectangular plate in the bolt-group x-y plane."""

    corner_a: Point2D
    corner_b: Point2D
    thickness: float
    fu: float
    fy: float | None = None
    hole_type: HoleType = "standard"
    hole_orientation: float | None = None
    surface_class: SurfaceClass | None = None
    slip_coefficient: float | None = None

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
        hole_type: HoleType = "standard",
        hole_orientation: float | None = None,
        surface_class: SurfaceClass | None = None,
        slip_coefficient: float | None = None,
    ) -> "Plate":
        """Create a rectangular plate from width/height (x/y) and an optional center point.

        Notes:
        - `width` is the plate size in the **x** direction.
        - `height` is the plate size in the **y** direction.
        - `center` is (x, y).
        """
        if width <= 0.0:
            raise ValueError("Plate width must be positive")
        if height <= 0.0:
            raise ValueError("Plate height must be positive")

        cx, cy = center
        half_w = width / 2.0
        half_h = height / 2.0

        return cls(
            corner_a=(cx - half_w, cy - half_h),
            corner_b=(cx + half_w, cy + half_h),
            thickness=thickness,
            fu=fu,
            fy=fy,
            hole_type=hole_type,
            hole_orientation=hole_orientation,
            surface_class=surface_class,
            slip_coefficient=slip_coefficient,
        )

    def __post_init__(self) -> None:
        if self.thickness <= 0.0:
            raise ValueError("Plate thickness must be positive")
        if self.fu <= 0.0:
            raise ValueError("Plate fu (ultimate strength) must be positive")
        
        if self.slip_coefficient is None:
            if self.surface_class == "A":
                object.__setattr__(self, "slip_coefficient", 0.30)
            elif self.surface_class == "B":
                object.__setattr__(self, "slip_coefficient", 0.50)

    @property
    def x_min(self) -> float:
        return float(min(self.corner_a[0], self.corner_b[0]))

    @property
    def x_max(self) -> float:
        return float(max(self.corner_a[0], self.corner_b[0]))

    @property
    def y_min(self) -> float:
        return float(min(self.corner_a[1], self.corner_b[1]))

    @property
    def y_max(self) -> float:
        return float(max(self.corner_a[1], self.corner_b[1]))

    @property
    def depth_x(self) -> float:
        return self.x_max - self.x_min

    @property
    def depth_y(self) -> float:
        return self.y_max - self.y_min

    @property
    def width(self) -> float:
        """Alias for plate size in x-direction."""
        return self.depth_x

    @property
    def height(self) -> float:
        """Alias for plate size in y-direction."""
        return self.depth_y

    @property
    def center(self) -> Point2D:
        """Plate center (x, y)."""
        return ((self.x_min + self.x_max) / 2.0, (self.y_min + self.y_max) / 2.0)
