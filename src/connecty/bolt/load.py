"""Connection load definition for bolt connections."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class ConnectionLoad:
    """Applied forces and moments for a bolt connection.
    
    Defines the external loads acting on a connection at a specific location.
    
    Attributes:
        Fx: Force in x-direction (out-of-plane/axial) in force units
        Fy: Force in y-direction (vertical) in force units
        Fz: Force in z-direction (horizontal) in force units
        Mx: Moment about x-axis (torsion) in force·length units
        My: Moment about y-axis (bending, produces z-gradient) in force·length units
        Mz: Moment about z-axis (bending, produces y-gradient) in force·length units
        location: Tuple[float, float, float] — Point (x, y, z) where load acts in length units
    
    Notes:
        - Use consistent units throughout (e.g., N and mm → moments in N·mm)
        - Moments are defined at the location point
    """
    
    Fx: float = 0.0
    Fy: float = 0.0
    Fz: float = 0.0
    Mx: float = 0.0
    My: float = 0.0
    Mz: float = 0.0
    location: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    
    def equivalent_load(self, position: Tuple[float, float, float]) -> ConnectionLoad:
        """Compute equivalent forces and moments at a different position.
        
        Transfers the load from the current location to a new position,
        adjusting moments to account for the force offset.
        
        Args:
            position: Target position (x, y, z) in length units
            
        Returns:
            New ConnectionLoad with equivalent forces and moments at the target position
        """
        # Forces remain the same
        Fx_eq = self.Fx
        Fy_eq = self.Fy
        Fz_eq = self.Fz
        
        # Compute position difference
        dx = position[0] - self.location[0]
        dy = position[1] - self.location[1]
        dz = position[2] - self.location[2]
        
        # Transfer moments: M_new = M_old + r × F
        # Mx_new = Mx + (Fy * dz - Fz * dy)
        # My_new = My + (Fz * dx - Fx * dz)
        # Mz_new = Mz + (Fx * dy - Fy * dx)
        Mx_eq = self.Mx + (self.Fy * dz - self.Fz * dy)
        My_eq = self.My + (self.Fz * dx - self.Fx * dz)
        Mz_eq = self.Mz + (self.Fx * dy - self.Fy * dx)
        
        return ConnectionLoad(
            Fx=Fx_eq,
            Fy=Fy_eq,
            Fz=Fz_eq,
            Mx=Mx_eq,
            My=My_eq,
            Mz=Mz_eq,
            location=position
        )
