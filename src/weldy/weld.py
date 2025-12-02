"""
Weld dataclasses: WeldParameters, WeldSegment, WeldGroup

These classes define the weld configuration and calculate weld group properties
for elastic stress analysis.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal, List, Tuple, TYPE_CHECKING
import math
import numpy as np

if TYPE_CHECKING:
    from sectiony import Section
    from sectiony.geometry import Segment

# Type aliases
Point = Tuple[float, float]
WeldType = Literal["fillet", "butt"]


@dataclass
class WeldParameters:
    """
    Parameters defining weld configuration.
    
    Attributes:
        weld_type: Type of weld - "fillet" or "butt"
        throat_thickness: Effective throat thickness (a) in mm
        leg_size: Leg size for fillet welds (z) in mm. If not provided,
                  calculated as throat_thickness / 0.707 for 45° fillet
        strength: Allowable or yield stress in MPa (optional, for utilization calc)
    """
    weld_type: WeldType
    throat_thickness: float
    leg_size: float | None = None
    strength: float | None = None
    
    def __post_init__(self) -> None:
        if self.leg_size is None and self.weld_type == "fillet":
            # For 45° fillet weld: a = z * cos(45°) = z * 0.707
            self.leg_size = self.throat_thickness / 0.707


@dataclass
class WeldSegment:
    """
    A single welded edge segment.
    
    Attributes:
        segment_index: Index of the segment in the section's contour
        parameters: WeldParameters for this segment
        contour_index: Index of the contour (default 0 for outer contour)
    """
    segment_index: int
    parameters: WeldParameters
    contour_index: int = 0
    
    # These are populated when attached to a section
    _start: Point | None = field(default=None, repr=False)
    _end: Point | None = field(default=None, repr=False)
    _length: float | None = field(default=None, repr=False)
    _segment_ref: Segment | None = field(default=None, repr=False)
    
    @property
    def start(self) -> Point:
        if self._start is None:
            raise ValueError("WeldSegment not initialized - call bind_to_section first")
        return self._start
    
    @property
    def end(self) -> Point:
        if self._end is None:
            raise ValueError("WeldSegment not initialized - call bind_to_section first")
        return self._end
    
    @property
    def length(self) -> float:
        if self._length is None:
            raise ValueError("WeldSegment not initialized - call bind_to_section first")
        return self._length
    
    @property
    def throat(self) -> float:
        """Effective throat thickness."""
        return self.parameters.throat_thickness
    
    @property
    def area(self) -> float:
        """Weld area = throat * length."""
        return self.throat * self.length
    
    def bind_to_section(self, section: Section) -> None:
        """
        Bind this weld segment to a section's geometry.
        Extracts start/end points and calculates length.
        """
        if section.geometry is None:
            raise ValueError("Section has no geometry")
        
        if not section.geometry.contours:
            raise ValueError("Section geometry has no contours")
        
        if self.contour_index >= len(section.geometry.contours):
            raise ValueError(f"Contour index {self.contour_index} out of range")
        
        contour = section.geometry.contours[self.contour_index]
        
        if self.segment_index >= len(contour.segments):
            raise ValueError(f"Segment index {self.segment_index} out of range")
        
        segment = contour.segments[self.segment_index]
        self._segment_ref = segment
        
        # Get start point from segment
        from sectiony.geometry import Line, Arc, CubicBezier
        
        if isinstance(segment, Line):
            self._start = segment.start
            self._end = segment.end
            self._length = math.sqrt(
                (self._end[0] - self._start[0])**2 + 
                (self._end[1] - self._start[1])**2
            )
        elif isinstance(segment, Arc):
            # Arc start point
            cy, cz = segment.center
            self._start = (
                cy + segment.radius * math.sin(segment.start_angle),
                cz + segment.radius * math.cos(segment.start_angle)
            )
            self._end = segment.end_point()
            # Arc length = r * theta
            angle_span = abs(segment.end_angle - segment.start_angle)
            self._length = segment.radius * angle_span
        elif isinstance(segment, CubicBezier):
            self._start = segment.p0
            self._end = segment.p3
            # Approximate bezier length by discretization
            points = segment.discretize(resolution=100)
            self._length = 0.0
            for i in range(len(points) - 1):
                dy = points[i+1][0] - points[i][0]
                dz = points[i+1][1] - points[i][1]
                self._length += math.sqrt(dy**2 + dz**2)
    
    def discretize(self, num_points: int = 50) -> List[Point]:
        """
        Discretize the weld segment into points for stress calculation.
        
        Args:
            num_points: Number of points to generate along the weld
            
        Returns:
            List of (y, z) points along the weld
        """
        if self._segment_ref is None:
            raise ValueError("WeldSegment not initialized - call bind_to_section first")
        
        return self._segment_ref.discretize(resolution=num_points)


@dataclass
class WeldGroupProperties:
    """
    Calculated properties of a weld group.
    
    All properties are calculated about the weld group centroid.
    """
    # Centroid location
    Cy: float  # y-coordinate of centroid
    Cz: float  # z-coordinate of centroid
    
    # Total weld area (throat * length summed)
    A: float
    
    # Total weld length
    L: float
    
    # Second moments of area about centroid
    Iz: float  # About horizontal axis (z) - sum(y^2 * dA)
    Iy: float  # About vertical axis (y) - sum(z^2 * dA)
    
    # Polar moment of area about centroid
    Ip: float  # Iz + Iy


@dataclass
class WeldGroup:
    """
    A group of weld segments for combined analysis.
    
    Calculates weld group properties (centroid, moments of inertia)
    for elastic stress analysis.
    """
    weld_segments: List[WeldSegment] = field(default_factory=list)
    _properties: WeldGroupProperties | None = field(default=None, repr=False)
    _section: Section | None = field(default=None, repr=False)
    
    @property
    def properties(self) -> WeldGroupProperties:
        if self._properties is None:
            raise ValueError("Properties not calculated - call calculate_properties first")
        return self._properties
    
    @property
    def total_length(self) -> float:
        """Total weld length."""
        return sum(seg.length for seg in self.weld_segments)
    
    @property
    def total_area(self) -> float:
        """Total weld area (throat * length)."""
        return sum(seg.area for seg in self.weld_segments)
    
    def add_segment(self, segment: WeldSegment) -> None:
        """Add a weld segment to the group."""
        self.weld_segments.append(segment)
        self._properties = None  # Invalidate cached properties
    
    def bind_to_section(self, section: Section) -> None:
        """Bind all weld segments to a section."""
        self._section = section
        for segment in self.weld_segments:
            segment.bind_to_section(section)
    
    def calculate_properties(self, discretization: int = 100) -> WeldGroupProperties:
        """
        Calculate weld group properties using discretized points.
        
        The weld is treated as a line with thickness = throat.
        Properties are calculated by discretizing each segment and
        treating each small piece as a point mass.
        
        Args:
            discretization: Points per segment for numerical integration
            
        Returns:
            WeldGroupProperties with centroid and moments of inertia
        """
        if not self.weld_segments:
            raise ValueError("No weld segments in group")
        
        # Collect all discretized points with their segment lengths
        y_list: List[float] = []
        z_list: List[float] = []
        ds_list: List[float] = []
        throat_list: List[float] = []
        total_length = 0.0

        for seg in self.weld_segments:
            points = seg.discretize(discretization)
            throat = seg.throat

            for i in range(len(points) - 1):
                p1 = points[i]
                p2 = points[i + 1]

                mid_y = (p1[0] + p2[0]) / 2
                mid_z = (p1[1] + p2[1]) / 2

                ds = math.hypot(p2[0] - p1[0], p2[1] - p1[1])

                y_list.append(mid_y)
                z_list.append(mid_z)
                ds_list.append(ds)
                throat_list.append(throat)

                total_length += ds

        if not y_list:
            raise ValueError("Weld group has no discretized points")

        y_arr = np.array(y_list, dtype=float)
        z_arr = np.array(z_list, dtype=float)
        ds_arr = np.array(ds_list, dtype=float)
        throat_arr = np.array(throat_list, dtype=float)

        dA_arr = throat_arr * ds_arr
        total_area = float(np.sum(dA_arr))

        if total_area < 1e-12:
            raise ValueError("Weld group has zero area")

        Cy = float(np.sum(y_arr * dA_arr) / total_area)
        Cz = float(np.sum(z_arr * dA_arr) / total_area)

        # Calculate moments of inertia about centroid using numpy
        dy_arr = y_arr - Cy
        dz_arr = z_arr - Cz

        Iz = float(np.sum(dy_arr**2 * dA_arr))
        Iy = float(np.sum(dz_arr**2 * dA_arr))
        
        Ip = Iz + Iy
        
        self._properties = WeldGroupProperties(
            Cy=Cy,
            Cz=Cz,
            A=total_area,
            L=total_length,
            Iz=Iz,
            Iy=Iy,
            Ip=Ip
        )
        
        return self._properties
    
    def get_all_points(self, discretization: int = 50) -> List[Tuple[Point, WeldSegment]]:
        """
        Get all discretized points from all segments.
        
        Returns:
            List of (point, segment) tuples
        """
        result: List[Tuple[Point, WeldSegment]] = []
        for seg in self.weld_segments:
            points = seg.discretize(discretization)
            for pt in points:
                result.append((pt, seg))
        return result

