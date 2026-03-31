from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Point2D = tuple[float, float]
HoleType = Literal["standard", "oversize", "short_slotted", "long_slotted"]
SurfaceClass = Literal["A", "B"]

@dataclass(frozen=True)
class Plate:
    """Axis-aligned rectangular plate in the y-z cross-section plane."""

    corner_a: Point2D  # (y, z)
    corner_b: Point2D  # (y, z)
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
        """Create a rectangular plate from width/height and an optional center point.

        Notes:
        - `width` is the plate size in the **z** direction (horizontal).
        - `height` is the plate size in the **y** direction (vertical).
        - `center` is (y, z).
        """
        if width <= 0.0:
            raise ValueError("Plate width must be positive")
        if height <= 0.0:
            raise ValueError("Plate height must be positive")

        cy, cz = center
        half_h = height / 2.0  # y direction (vertical)
        half_w = width / 2.0   # z direction (horizontal)

        return cls(
            corner_a=(cy - half_h, cz - half_w),
            corner_b=(cy + half_h, cz + half_w),
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
        """Plate size in z-direction (horizontal)."""
        return self.depth_z

    @property
    def height(self) -> float:
        """Plate size in y-direction (vertical)."""
        return self.depth_y

    @property
    def center(self) -> Point2D:
        """Plate center (y, z)."""
        return ((self.y_min + self.y_max) / 2.0, (self.z_min + self.z_max) / 2.0)
