import numpy as np
from typing import Tuple

def solve_bolt_elastic(
    bolt_coords: np.ndarray,
    Fx: float,
    Fy: float,
    Mz: float,
    x_loc: float,
    y_loc: float
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Solves for bolt forces using the Elastic Method (Linear Distribution).

    Works in a generic 2D (coord1, coord2) space. The caller maps global
    coordinates: for the y-z bolt plane, pass (y, z) as (coord1, coord2).

    Parameters:
    bolt_coords : np.ndarray -> Nx2 array of [coord1, coord2] coordinates.
    Fx          : float      -> External shear force in coord1 direction.
    Fy          : float      -> External shear force in coord2 direction.
    Mz          : float      -> Applied in-plane torsion (CCW positive).
    x_loc       : float      -> coord1 of load application point.
    y_loc       : float      -> coord2 of load application point.

    Returns:
    Tuple[np.ndarray, np.ndarray]: Bolt forces in (coord1, coord2) directions.
    """
    bolt_coords = np.array(bolt_coords)  # Expected as [x, y]
    n = len(bolt_coords)
    
    # 1. Bolt-group centroid (Cx, Cy)
    centroid = np.mean(bolt_coords, axis=0)
    Cx, Cy = centroid[0], centroid[1]
    
    # 2. Polar Moment of Inertia (Ip)
    rel_coords = bolt_coords - centroid
    Ip = np.sum(rel_coords**2)
    
    # 3. Transfer loads to Centroid (Mz_total)
    # Moment Mz = (r x F)_z = dx*Fy - dy*Fx
    # dx = x_loc - Cx, dy = y_loc - Cy
    dx = x_loc - Cx
    dy = y_loc - Cy
    Mz_total = Mz + dx * Fy - dy * Fx
    
    # 4. Direct Shear components
    Fx_p = Fx / n
    Fy_p = Fy / n
    
    # 5. Moment-induced Shear
    # Torsion Mz causes rotation.
    # Force perpendicular to radius vector r=(dx, dy).
    # F_m = Mz / Ip * (-dy, dx)
    # Fx_m = -Mz * dy / Ip
    # Fy_m = Mz * dx / Ip
    
    # rel_coords[:, 0] is dx (x - Cx)
    # rel_coords[:, 1] is dy (y - Cy)
    
    if Ip > 1e-12:
        Fx_m = -(Mz_total * rel_coords[:, 1]) / Ip
        Fy_m = (Mz_total * rel_coords[:, 0]) / Ip
    else:
        Fx_m = np.zeros(n)
        Fy_m = np.zeros(n)
    
    bolt_forces_x = Fx_p + Fx_m
    bolt_forces_y = Fy_p + Fy_m
    
    return bolt_forces_x, bolt_forces_y

# --- Example Usage ---
# bolts = np.array([[0, 0], [3, 0], [0, 3], [3, 3]])
# Fx=10 kip, Fy=0, Mz=50 kip-in, applied at x=6, y=1.5
# results = solve_bolt_elastic(bolts, Fx=10, Fy=0, Mz=50, x_loc=6, y_loc=1.5)
