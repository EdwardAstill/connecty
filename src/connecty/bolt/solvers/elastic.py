import numpy as np
from typing import Dict, List, Tuple

def solve_bolt_elastic(
    bolt_coords: np.ndarray,
    Fy: float,
    Fz: float,
    Mx: float,
    y_loc: float,
    z_loc: float
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Solves for bolt forces using the Elastic Method (Linear Distribution).
    Matches theory in bolt.md: y=vertical, z=horizontal.
    
    Parameters:
    bolt_coords : np.ndarray -> Nx2 array of [y, z] coordinates.
    Fy          : float      -> External vertical force.
    Fz          : float      -> External horizontal force.
    Mx          : float      -> Applied twisting moment about x-axis (CCW positive).
    y_loc       : float      -> y-coordinate where force is applied.
    z_loc       : float      -> z-coordinate where force is applied.
    
    Returns:
    Tuple[np.ndarray, np.ndarray]: Vertical and horizontal bolt forces.
    """
    bolt_coords = np.array(bolt_coords)  # Expected as [y, z]
    n = len(bolt_coords)
    
    # 1. Bolt-group centroid (Cy, Cz)
    centroid = np.mean(bolt_coords, axis=0)
    Cy, Cz = centroid[0], centroid[1]
    
    # 2. Polar Moment of Inertia (Ip)
    rel_coords = bolt_coords - centroid
    Ip = np.sum(rel_coords**2)
    
    # 3. Transfer loads to Centroid (Mx_total)
    # Matches: Mx - Fz*(y_loc - Cy) + Fy*(z_loc - Cz)
    Mx_total = Mx - Fz * (y_loc - Cy) + Fy * (z_loc - Cz)
    
    # 4. Direct Shear components
    Fy_p = Fy / n
    Fz_p = Fz / n
    
    # 5. Moment-induced Shear
    # Fy_m = -Mx*dz/Ip, Fz_m = -Mx*dy/Ip (Matches bolt.md equations)
    Fy_m = -(Mx_total * rel_coords[:, 1]) / Ip
    Fz_m = -(Mx_total * rel_coords[:, 0]) / Ip
    
    bolt_forces_y = Fy_p + Fy_m
    bolt_forces_z = Fz_p + Fz_m
    
    return bolt_forces_y, bolt_forces_z

# --- Example Usage ---
bolts = np.array([[0, 0], [3, 0], [0, 3], [3, 3]])
# Fy=-10 kip, Fz=0, Mx=50 kip-in, applied at y=1.5, z=6
results = solve_bolt_elastic(bolts, Fy=-10, Fz=0, Mx=50, y_loc=1.5, z_loc=6)
