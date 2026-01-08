"""
Load dataclass for applied loads.

Defines forces and moments that can be applied to a welded connection.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple
import math

# Type alias
Point = Tuple[float, float, float]


@dataclass
class Load:
    """
    Applied force and moment at a specific location.
    
    The load is defined in the section's local coordinate system:
    - x-axis: Along the member (perpendicular to cross-section, out of page)
    - y-axis: Vertical in section plane (up positive)
    - z-axis: Horizontal in section plane (right positive)
    
    Attributes:
        Fx: Axial force (out-of-plane, positive = tension)
        Fy: Shear force in y-direction (vertical)
        Fz: Shear force in z-direction (horizontal)
        Mx: Torsional moment about x-axis
        My: Bending moment about y-axis
        Mz: Bending moment about z-axis
        location: (x, y, z) point of load application
        
    Sign Conventions:
        Fx: + = tension
        Fy: + = up
        Fz: + = right
        Mx: + = CCW when viewed from +x
        My: + = tension on +z side
        Mz: + = tension on +y side
    """
    Fx: float = 0.0
    Fy: float = 0.0
    Fz: float = 0.0
    Mx: float = 0.0
    My: float = 0.0
    Mz: float = 0.0
    location: Point = (0.0, 0.0, 0.0)
    
    @property
    def x_loc(self) -> float:
        """X-coordinate of load application."""
        return self.location[0]
    
    @property
    def y_loc(self) -> float:
        """Y-coordinate of load application."""
        return self.location[1]
    
    @property
    def z_loc(self) -> float:
        """Z-coordinate of load application."""
        return self.location[2]
    
    @property
    def shear_magnitude(self) -> float:
        """Magnitude of in-plane shear force."""
        return math.sqrt(self.Fy**2 + self.Fz**2)
    
    @property
    def total_force_magnitude(self) -> float:
        """Magnitude of total force vector."""
        return math.sqrt(self.Fx**2 + self.Fy**2 + self.Fz**2)
    
    def at(self, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> Tuple[float, float, float, float, float, float]:
        """
        Calculate equivalent load (forces and moments) at a point (x, y, z).
        
        Returns the forces (unchanged) and total moments at the specified point,
        including applied moments plus moments from force eccentricity.
        
        Args:
            x: X-coordinate of point (default 0.0)
            y: Y-coordinate of point (default 0.0)
            z: Z-coordinate of point (default 0.0)
            
        Returns:
            Tuple of (Fx, Fy, Fz, Mx_total, My_total, Mz_total)
        """
        # Distance from point to load location
        dx = self.x_loc - x
        dy = self.y_loc - y
        dz = self.z_loc - z
        
        # Moment from force eccentricity:
        # Mx (torsion): Fz × dy - Fy × dz (in-plane moment)
        Mx_eccentric = self.Fz * dy - self.Fy * dz
        
        # My (bending about y): Fz × dx - Fx × dz
        My_eccentric = self.Fz * dx - self.Fx * dz
        
        # Mz (bending about z): Fx × dy - Fy × dx
        Mz_eccentric = self.Fx * dy - self.Fy * dx
        
        return (
            self.Fx,
            self.Fy,
            self.Fz,
            self.Mx + Mx_eccentric,
            self.My + My_eccentric,
            self.Mz + Mz_eccentric
        )
    
    def get_moments_about(self, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> Tuple[float, float, float]:
        """
        Calculate total moments about a point (x, y, z).
        
        Includes applied moments plus moments from force eccentricity.
        
        Args:
            x: X-coordinate of point (default 0.0)
            y: Y-coordinate of point (default 0.0)
            z: Z-coordinate of point (default 0.0)
            
        Returns:
            Tuple of (Mx_total, My_total, Mz_total)
        """
        _, _, _, Mx, My, Mz = self.at(x=x, y=y, z=z)
        return (Mx, My, Mz)

    def equivalent_at(self, location: Point) -> "Load":
        """Return an equivalent Load at a new application point.

        Forces stay the same; moments are transferred to the new point via:
        M_new = M_old + r x F, where r is the offset from the new point to the
        original load application point.
        """
        Fx, Fy, Fz, Mx, My, Mz = self.at(x=location[0], y=location[1], z=location[2])
        return Load(
            Fx=float(Fx),
            Fy=float(Fy),
            Fz=float(Fz),
            Mx=float(Mx),
            My=float(My),
            Mz=float(Mz),
            location=tuple(location),
        )
    
    @classmethod
    def from_components(
        cls,
        axial: float = 0.0,
        shear_y: float = 0.0,
        shear_z: float = 0.0,
        torsion: float = 0.0,
        moment_y: float = 0.0,
        moment_z: float = 0.0,
        at: Point = (0.0, 0.0, 0.0)
    ) -> Load:
        """
        Alternative constructor with descriptive parameter names.
        
        Args:
            axial: Axial force (tension positive)
            shear_y: Vertical shear force
            shear_z: Horizontal shear force
            torsion: Torsional moment
            moment_y: Bending moment about y-axis
            moment_z: Bending moment about z-axis
            at: Location of load application (x, y, z)
            
        Returns:
            Load instance
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

