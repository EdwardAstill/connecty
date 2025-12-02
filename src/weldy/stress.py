"""
Weld stress calculation using the elastic method.

This module calculates stress distribution along welds based on:
- Direct stress from forces
- Torsional stress from moment about weld centroid
- Bending stress from moments about principal axes
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, TYPE_CHECKING
import math

if TYPE_CHECKING:
    from .weld import WeldGroup, WeldSegment
    from .force import Force

# Type alias
Point = Tuple[float, float]


@dataclass
class StressComponents:
    """
    Stress components at a single point on the weld.
    
    All stresses are in force per unit area (e.g., MPa if using N and mm).
    """
    # Direct stress components (from forces)
    f_axial: float = 0.0      # From Fx (axial load)
    f_shear_y: float = 0.0    # From Fy (vertical shear)
    f_shear_z: float = 0.0    # From Fz (horizontal shear)
    
    # Torsional stress components (from Mx about weld centroid)
    f_torsion_y: float = 0.0  # Y-component of torsion stress
    f_torsion_z: float = 0.0  # Z-component of torsion stress
    
    # Bending stress components
    f_bending_y: float = 0.0  # From My (bending about y-axis)
    f_bending_z: float = 0.0  # From Mz (bending about z-axis)
    
    @property
    def total_y(self) -> float:
        """Total stress in y-direction."""
        return self.f_shear_y + self.f_torsion_y
    
    @property
    def total_z(self) -> float:
        """Total stress in z-direction."""
        return self.f_shear_z + self.f_torsion_z
    
    @property
    def total_axial(self) -> float:
        """Total axial (x-direction) stress."""
        return self.f_axial + self.f_bending_y + self.f_bending_z
    
    @property
    def resultant(self) -> float:
        """Resultant stress magnitude (vector sum of all components)."""
        return math.sqrt(
            self.total_axial**2 + 
            self.total_y**2 + 
            self.total_z**2
        )
    
    @property
    def shear_resultant(self) -> float:
        """Resultant in-plane shear stress (y-z plane)."""
        return math.sqrt(self.total_y**2 + self.total_z**2)


@dataclass
class PointStress:
    """
    Stress result at a specific point on the weld.
    """
    point: Point
    segment: WeldSegment
    components: StressComponents
    
    @property
    def y(self) -> float:
        return self.point[0]
    
    @property
    def z(self) -> float:
        return self.point[1]
    
    @property
    def stress(self) -> float:
        """Resultant stress magnitude."""
        return self.components.resultant


@dataclass
class WeldStressResult:
    """
    Complete stress analysis result for a weld group.
    """
    weld_group: WeldGroup
    force: Force
    point_stresses: List[PointStress] = field(default_factory=list)
    
    @property
    def max_stress(self) -> float:
        """Maximum resultant stress in the weld group."""
        if not self.point_stresses:
            return 0.0
        return max(ps.stress for ps in self.point_stresses)
    
    @property
    def min_stress(self) -> float:
        """Minimum resultant stress in the weld group."""
        if not self.point_stresses:
            return 0.0
        return min(ps.stress for ps in self.point_stresses)
    
    @property
    def max_stress_point(self) -> PointStress | None:
        """Point with maximum stress."""
        if not self.point_stresses:
            return None
        return max(self.point_stresses, key=lambda ps: ps.stress)
    
    def get_stress_range(self) -> Tuple[float, float]:
        """Get (min, max) stress values."""
        return (self.min_stress, self.max_stress)
    
    def get_stresses_for_segment(self, segment_index: int) -> List[PointStress]:
        """Get all point stresses for a specific segment."""
        return [
            ps for ps in self.point_stresses 
            if ps.segment.segment_index == segment_index
        ]
    
    def utilization(self, allowable_stress: float) -> float:
        """
        Calculate utilization ratio (max_stress / allowable).
        
        Args:
            allowable_stress: Allowable weld stress
            
        Returns:
            Utilization ratio (< 1.0 means acceptable)
        """
        if allowable_stress <= 0:
            raise ValueError("Allowable stress must be positive")
        return self.max_stress / allowable_stress


class WeldStressCalculator:
    """
    Calculator for elastic weld stress analysis.
    
    Uses the elastic method where:
    - Direct stresses are uniformly distributed (F/A)
    - Torsional stresses vary with distance from centroid (M*r/Ip)
    - Bending stresses vary linearly (M*d/I)
    """
    
    def __init__(self, weld_group: WeldGroup):
        """
        Initialize calculator with a weld group.
        
        Args:
            weld_group: WeldGroup with calculated properties
        """
        self.weld_group = weld_group
        
        # Ensure properties are calculated
        if weld_group._properties is None:
            raise ValueError("WeldGroup properties not calculated - call calculate_properties first")
    
    @property
    def props(self):
        """Shorthand for weld group properties."""
        return self.weld_group.properties
    
    def calculate_stress_at_point(
        self, 
        y: float, 
        z: float, 
        force: Force
    ) -> StressComponents:
        """
        Calculate stress components at a single point.
        
        Args:
            y: Y-coordinate of point
            z: Z-coordinate of point
            force: Applied force
            
        Returns:
            StressComponents at the point
        """
        props = self.props
        
        # Get moments about weld centroid
        Mx_total, My_total, Mz_total = force.get_moments_about(props.Cy, props.Cz)
        
        # Direct stress from forces
        A = props.A
        f_axial = force.Fx / A if A > 0 else 0.0
        f_shear_y = force.Fy / A if A > 0 else 0.0
        f_shear_z = force.Fz / A if A > 0 else 0.0
        
        # Distance from centroid
        dy = y - props.Cy
        dz = z - props.Cz
        r = math.sqrt(dy**2 + dz**2)
        
        # Torsional stress (perpendicular to radius)
        # τ = M*r/Ip, direction is perpendicular to radius vector
        f_torsion_y = 0.0
        f_torsion_z = 0.0
        
        if props.Ip > 0 and r > 1e-9:
            torsion_magnitude = Mx_total * r / props.Ip
            # Direction perpendicular to radius: rotate (dy, dz) by 90°
            # For CCW rotation of force about centroid: (-dz, dy) normalized
            f_torsion_y = -torsion_magnitude * dz / r
            f_torsion_z = torsion_magnitude * dy / r
        
        # Bending stress
        # My causes normal stress variation with z
        # Mz causes normal stress variation with y
        f_bending_y = 0.0
        f_bending_z = 0.0
        
        if props.Iy > 0:
            # My bending: axial stress varies with z
            f_bending_y = My_total * dz / props.Iy
        
        if props.Iz > 0:
            # Mz bending: axial stress varies with y
            # Standard beam convention: sigma = -Mz * y / Iz.
            # Mz vector along +z. y is up.
            # +Mz compresses top (y>0). So -Mz*y/Iz.
            f_bending_z = -Mz_total * dy / props.Iz
        
        return StressComponents(
            f_axial=f_axial,
            f_shear_y=f_shear_y,
            f_shear_z=f_shear_z,
            f_torsion_y=f_torsion_y,
            f_torsion_z=f_torsion_z,
            f_bending_y=f_bending_y,
            f_bending_z=f_bending_z
        )
    
    def calculate(
        self, 
        force: Force, 
        discretization: int = 50
    ) -> WeldStressResult:
        """
        Calculate stress distribution for the entire weld group.
        
        Args:
            force: Applied force
            discretization: Points per segment for stress evaluation
            
        Returns:
            WeldStressResult with stress at all points
        """
        point_stresses: List[PointStress] = []
        
        for segment in self.weld_group.weld_segments:
            points = segment.discretize(discretization)
            
            for point in points:
                y, z = point
                components = self.calculate_stress_at_point(y, z, force)
                
                point_stresses.append(PointStress(
                    point=point,
                    segment=segment,
                    components=components
                ))
        
        return WeldStressResult(
            weld_group=self.weld_group,
            force=force,
            point_stresses=point_stresses
        )


def calculate_weld_stress(
    weld_group: WeldGroup, 
    force: Force,
    discretization: int = 50
) -> WeldStressResult:
    """
    Convenience function to calculate weld stress.
    
    Args:
        weld_group: WeldGroup with calculated properties
        force: Applied force
        discretization: Points per segment
        
    Returns:
        WeldStressResult
    """
    calculator = WeldStressCalculator(weld_group)
    return calculator.calculate(force, discretization)

