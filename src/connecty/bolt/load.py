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
    - x-axis: Horizontal (right positive)
    - y-axis: Vertical (up positive)
    - z-axis: Along the member (out of page positive)
    
    Attributes:
        Fx: Shear force in x-direction (horizontal)
        Fy: Shear force in y-direction (vertical)
        Fz: Axial force (out-of-plane, positive = tension)
        Mx: Bending moment about x-axis
        My: Bending moment about y-axis
        Mz: Torsional moment about z-axis
        location: (x, y, z) point of load application
        
    Sign Conventions:
        Fx: + = right
        Fy: + = up
        Fz: + = tension (out of page)
        Mx: + = CCW when viewed from +x (Right Hand Rule)
        My: + = CCW when viewed from +y (Right Hand Rule)
        Mz: + = CCW when viewed from +z (Right Hand Rule)
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
        return math.sqrt(self.Fx**2 + self.Fy**2)
    
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
        # Distance vector r from point (new origin) to load location
        dx = self.x_loc - x
        dy = self.y_loc - y
        dz = self.z_loc - z
        
        # Moment from force eccentricity (M = r x F):
        # Mx: dy*Fz - dz*Fy
        Mx_eccentric = dy * self.Fz - dz * self.Fy
        
        # My: dz*Fx - dx*Fz
        My_eccentric = dz * self.Fx - dx * self.Fz
        
        # Mz: dx*Fy - dy*Fx
        Mz_eccentric = dx * self.Fy - dy * self.Fx
        
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
        shear_x: float = 0.0,
        shear_y: float = 0.0,
        torsion: float = 0.0,
        moment_x: float = 0.0,
        moment_y: float = 0.0,
        at: Point = (0.0, 0.0, 0.0)
    ) -> Load:
        """
        Alternative constructor with descriptive parameter names.
        
        Args:
            axial: Axial force (tension positive) - Fz
            shear_x: Horizontal shear force - Fx
            shear_y: Vertical shear force - Fy
            torsion: Torsional moment - Mz
            moment_x: Bending moment about x-axis - Mx
            moment_y: Bending moment about y-axis - My
            at: Location of load application (x, y, z)
            
        Returns:
            Load instance
        """
        return cls(
            Fx=shear_x,
            Fy=shear_y,
            Fz=axial,
            Mx=moment_x,
            My=moment_y,
            Mz=torsion,
            location=at
        )
