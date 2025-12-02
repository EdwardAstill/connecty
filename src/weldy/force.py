"""
Force dataclass for applied loads.

Defines forces and moments that can be applied to a welded connection.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple

# Type alias
Point = Tuple[float, float]


@dataclass
class Force:
    """
    Applied force and moment at a specific location.
    
    The force is defined in the section's local coordinate system:
    - x-axis: Along the member (perpendicular to cross-section)
    - y-axis: Vertical in section plane
    - z-axis: Horizontal in section plane
    
    Attributes:
        Fx: Axial force along member axis (positive = tension)
        Fy: Shear force in y-direction (vertical)
        Fz: Shear force in z-direction (horizontal)
        Mx: Torsional moment about x-axis (twisting)
        My: Bending moment about y-axis (bends in x-z plane)
        Mz: Bending moment about z-axis (bends in x-y plane)
        location: (y, z) point of force application in section coordinates
    
    Units:
        Forces should be in consistent units (e.g., N, kN)
        Moments should be in consistent units (e.g., N·mm, kN·m)
        Location should match section geometry units (typically mm)
    """
    Fx: float = 0.0  # Axial force
    Fy: float = 0.0  # Vertical shear
    Fz: float = 0.0  # Horizontal shear
    Mx: float = 0.0  # Torsion
    My: float = 0.0  # Bending about y
    Mz: float = 0.0  # Bending about z
    location: Point = (0.0, 0.0)  # Point of application (y, z)
    
    @property
    def y_loc(self) -> float:
        """Y-coordinate of force application."""
        return self.location[0]
    
    @property
    def z_loc(self) -> float:
        """Z-coordinate of force application."""
        return self.location[1]
    
    @property
    def shear_magnitude(self) -> float:
        """Magnitude of resultant shear force."""
        import math
        return math.sqrt(self.Fy**2 + self.Fz**2)
    
    @property
    def total_force_magnitude(self) -> float:
        """Magnitude of total force vector."""
        import math
        return math.sqrt(self.Fx**2 + self.Fy**2 + self.Fz**2)
    
    def get_moments_about(self, y: float, z: float) -> Tuple[float, float, float]:
        """
        Calculate total moments about a point (y, z).
        
        This includes both the applied moments and the moments generated
        by the force components acting at a distance from the point.
        
        Args:
            y: Y-coordinate of point to take moments about
            z: Z-coordinate of point to take moments about
            
        Returns:
            Tuple of (Mx_total, My_total, Mz_total)
        """
        # Distance from point to force location
        dy = self.y_loc - y
        dz = self.z_loc - z
        
        # Moment from force eccentricity
        # Mx (torsion): Fz causes moment about x when offset in y
        #               Fy causes moment about x when offset in z
        Mx_eccentric = self.Fz * dy - self.Fy * dz
        
        # My (bending about y): Fx causes moment when offset in z
        My_eccentric = self.Fx * dz
        
        # Mz (bending about z): Fx causes moment when offset in y
        Mz_eccentric = -self.Fx * dy
        
        # Total moments = applied + eccentric
        Mx_total = self.Mx + Mx_eccentric
        My_total = self.My + My_eccentric
        Mz_total = self.Mz + Mz_eccentric
        
        return (Mx_total, My_total, Mz_total)
    
    @classmethod
    def from_components(
        cls,
        axial: float = 0.0,
        shear_y: float = 0.0,
        shear_z: float = 0.0,
        torsion: float = 0.0,
        moment_y: float = 0.0,
        moment_z: float = 0.0,
        at: Point = (0.0, 0.0)
    ) -> Force:
        """
        Alternative constructor with more descriptive parameter names.
        
        Args:
            axial: Axial force (tension positive)
            shear_y: Vertical shear force
            shear_z: Horizontal shear force
            torsion: Torsional moment
            moment_y: Bending moment about y-axis
            moment_z: Bending moment about z-axis
            at: Location of force application (y, z)
            
        Returns:
            Force instance
        """
        return cls(
            Fx=axial,
            Fy=shear_y,
            Fz=shear_z,
            Mx=torsion,
            My=moment_y,
            Mz=moment_z,
            location=at
        )

