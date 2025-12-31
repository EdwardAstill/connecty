"""
Weld class and WeldParams for weld stress analysis.

Supports fillet, PJP, CJP, and plug/slot welds per AISC 360.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal, List, Tuple, TYPE_CHECKING, Union, Sequence
import math
import numpy as np

if TYPE_CHECKING:
    from sectiony import Section, Geometry
    from .stress import StressResult

# Type aliases
Point = Tuple[float, float]
WeldType = Literal["fillet", "pjp", "cjp", "plug", "slot"]

@dataclass
class WeldParams:
    """
    Parameters defining weld configuration.
    
    Attributes:
        type: Type of weld - "fillet", "pjp", "cjp", "plug", or "slot"
        leg: Fillet weld leg size (w) in length units
        throat: Effective throat thickness (a or E) in length units
        area: Plug/slot weld area in length² units
    """
    type: WeldType
    
    # Geometry
    leg: float | None = None
    throat: float | None = None
    area: float | None = None

    # Strength (optional; unit-agnostic)
    electrode: str | None = None
    F_EXX: float | None = None
    
    def __post_init__(self) -> None:
        # Auto-calculate throat from leg for fillet welds
        if self.type == "fillet":
            if self.throat is None and self.leg is not None:
                # Equal leg 45° fillet: a = w × 0.707
                self.throat = self.leg * 0.707
            elif self.throat is not None and self.leg is None:
                # Back-calculate leg from throat
                self.leg = self.throat / 0.707

        # Optional: derive F_EXX from electrode label (e.g. "E70" -> 70.0).
        # No unit conversion is performed; connecty is unit-agnostic.
        if self.F_EXX is None and self.electrode is not None:
            import re

            match = re.search(r"(\d+(\.\d+)?)", str(self.electrode))
            if match is not None:
                self.F_EXX = float(match.group(1))


@dataclass
class WeldProperties:
    """
    Calculated geometric properties of a weld group.
    
    All properties are calculated about the weld group centroid.
    """
    Cx: float  # Centroid x-coordinate (along member, default 0.0)
    Cy: float  # Centroid y-coordinate
    Cz: float  # Centroid z-coordinate
    A: float   # Total weld area (throat × length)
    L: float   # Total weld length
    Iy: float  # Second moment about y-axis (Σz²·dA)
    Iz: float  # Second moment about z-axis (Σy²·dA)
    Ip: float  # Polar moment (Iy + Iz)


@dataclass
class Weld:
    """
    A weld group defined by geometry and weld parameters.
    
    Can be created directly from geometry or from a section's contour.
    
    Attributes:
        geometry: Weld path as sectiony Geometry
        parameters: WeldParams configuration
        section: Optional Section reference for plotting
    """
    geometry: Geometry
    parameters: WeldParams
    section: Section | None = None
    
    # Cached properties
    _properties: WeldProperties | None = field(default=None, repr=False, init=False)
    _discretized_points: List[Tuple[Point, float, Point, object]] | None = field(default=None, repr=False, init=False)
    
    def __post_init__(self) -> None:
        # Validate geometry
        if self.geometry is None:
            raise ValueError("geometry is required")
        if not self.geometry.contours:
            raise ValueError("geometry must have at least one contour")
    
    @classmethod
    def from_section(
        cls,
        section: Section,
        parameters: WeldParams,
        contour_index: int = 0
    ) -> Weld:
        """
        Create a Weld from a section's contour.
        
        Args:
            section: sectiony Section object
            parameters: WeldParams for the weld
            contour_index: Which contour to use (0 = outer)
            
        Returns:
            Weld with geometry extracted from section
        """
        if section.geometry is None:
            raise ValueError("Section has no geometry")
        if not section.geometry.contours:
            raise ValueError("Section has no contours")
        if contour_index >= len(section.geometry.contours):
            raise ValueError(f"Contour index {contour_index} out of range")
        
        from sectiony import Geometry
        
        # Extract the specified contour
        contour = section.geometry.contours[contour_index]
        geometry = Geometry(contours=[contour])
        
        return cls(
            geometry=geometry,
            parameters=parameters,
            section=section
        )
    
    def _discretize(self, discretization: int = 200) -> List[Tuple[Point, float, Point, object]]:
        """
        Discretize weld geometry into uniformly-spaced points with segment lengths.
        
        Uses sectiony's discretize_uniform for equal arc-length spacing across the
        entire weld path, which ensures stress continuity at segment boundaries.
        
        Args:
            discretization: Total number of points along the weld path
            
        Returns:
            List of ((y, z), ds, (t_y, t_z), contour) tuples containing the midpoint,
            its arc length, the local unit tangent direction, and the source contour.
        """
        if self._discretized_points is not None and len(self._discretized_points) >= discretization:
            return self._discretized_points
        
        points_with_ds: List[Tuple[Point, float, Point, object]] = []
        
        for contour in self.geometry.contours:
            # Use uniform discretization for equal arc-length spacing
            # This ensures smooth stress distribution without jumps at segment boundaries
            uniform_points = contour.discretize_uniform(count=discretization)
            
            if len(uniform_points) < 2:
                continue
            
            # Calculate arc length and tangent for each midpoint
            for i in range(len(uniform_points) - 1):
                p1 = uniform_points[i]
                p2 = uniform_points[i + 1]
                
                mid_y = (p1[0] + p2[0]) / 2
                mid_z = (p1[1] + p2[1]) / 2
                ds = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
                
                if ds > 1e-12:
                    t_y = (p2[0] - p1[0]) / ds
                    t_z = (p2[1] - p1[1]) / ds
                    points_with_ds.append(((mid_y, mid_z), ds, (t_y, t_z), contour))
            
            # Handle closed contour: add segment from last point back to first
            if contour.is_closed and len(uniform_points) >= 2:
                p1 = uniform_points[-1]
                p2 = uniform_points[0]
                mid_y = (p1[0] + p2[0]) / 2
                mid_z = (p1[1] + p2[1]) / 2
                ds = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
                
                if ds > 1e-12:
                    t_y = (p2[0] - p1[0]) / ds
                    t_z = (p2[1] - p1[1]) / ds
                    points_with_ds.append(((mid_y, mid_z), ds, (t_y, t_z), contour))
        
        self._discretized_points = points_with_ds
        return points_with_ds
    
    def _calculate_properties(self, discretization: int = 200) -> WeldProperties:
        """Calculate weld group geometric properties."""
        if self._properties is not None:
            return self._properties
        
        points_ds = self._discretize(discretization)
        
        if not points_ds:
            raise ValueError("Weld has no discretized points")
        
        # Get throat thickness
        throat = self.parameters.throat
        if throat is None:
            if self.parameters.type in ("plug", "slot") and self.parameters.area is not None:
                # For plug/slot, use area directly
                throat = 1.0  # Placeholder, area is used directly
            else:
                raise ValueError("Throat thickness not defined")
        
        # Calculate centroid
        y_arr = np.array([p[0][0] for p in points_ds])
        z_arr = np.array([p[0][1] for p in points_ds])
        ds_arr = np.array([p[1] for p in points_ds])
        
        if self.parameters.type in ("plug", "slot"):
            # For plug/slot, use provided area
            dA_arr = ds_arr  # Weight by length for centroid
            total_area = self.parameters.area if self.parameters.area else 0.0
        else:
            dA_arr = throat * ds_arr
            total_area = float(np.sum(dA_arr))
        
        total_length = float(np.sum(ds_arr))
        
        if total_area < 1e-12:
            raise ValueError("Weld has zero area")
        
        # Centroid (weighted by dA for proper calculation)
        Cy = float(np.sum(y_arr * dA_arr) / np.sum(dA_arr))
        Cz = float(np.sum(z_arr * dA_arr) / np.sum(dA_arr))
        
        # Second moments about centroid
        dy_arr = y_arr - Cy
        dz_arr = z_arr - Cz
        
        Iz = float(np.sum(dy_arr**2 * dA_arr))  # Σy²·dA
        Iy = float(np.sum(dz_arr**2 * dA_arr))  # Σz²·dA
        Ip = Iy + Iz
        
        self._properties = WeldProperties(
            Cx=0.0,  # Weld is always on the cross-section (x=0)
            Cy=Cy,
            Cz=Cz,
            A=total_area,
            L=total_length,
            Iy=Iy,
            Iz=Iz,
            Ip=Ip
        )
        
        return self._properties
    
    # Property accessors
    @property
    def A(self) -> float:
        """Total weld area (throat × length)."""
        return self._calculate_properties().A
    
    @property
    def L(self) -> float:
        """Total weld length."""
        return self._calculate_properties().L
    
    @property
    def Cx(self) -> float:
        """Centroid x-coordinate."""
        return self._calculate_properties().Cx
    
    @property
    def Cy(self) -> float:
        """Centroid y-coordinate."""
        return self._calculate_properties().Cy
    
    @property
    def Cz(self) -> float:
        """Centroid z-coordinate."""
        return self._calculate_properties().Cz
    
    @property
    def Iy(self) -> float:
        """Second moment about y-axis."""
        return self._calculate_properties().Iy
    
    @property
    def Iz(self) -> float:
        """Second moment about z-axis."""
        return self._calculate_properties().Iz
    
    @property
    def Ip(self) -> float:
        """Polar moment of inertia."""
        return self._calculate_properties().Ip

# Import Load here to avoid circular import at module level
from ..common.load import Load

# Legacy aliases removed (breaking changes allowed)
