import numpy as np
from dataclasses import dataclass
from typing import Literal, Tuple
from ..plate import Plate

def solve_bolt_tension_simple(
    bolt_coords: np.ndarray,
    plate: Plate,
    Fx: float,
    My: float,
    Mz: float,
    tension_method: Literal["accurate", "conservative"] = "accurate"
) -> np.ndarray:
    """
    Calculates bolt tension per bolt.md.
    My distribution varies with z-coordinates; Mz distribution varies with y-coordinates.
    
    Parameters:
    bolt_coords : np.ndarray -> Nx2 array of [y, z] coordinates.
    plate       : Plate      -> Object with centroid and dimensions.
    Fx          : float      -> Applied axial tension.
    My, Mz      : float      -> Moments about the Y and Z axes.
    tension_method : str     -> "accurate" (d/6 from edge) or "conservative" (at mid-plane).
    
    Returns:
    np.ndarray: Tension in each bolt (compression bolts have negative values, clamped to 0).
    """
    bolt_coords = np.array(bolt_coords)  # [y, z]
    n = len(bolt_coords)
    f_direct = max(0.0, Fx / n)
    tensions = np.full(n, f_direct)

    # Bending around Y-axis (Affected by Z coordinates)
    if abs(My) > 1e-12:
        plate_cy, plate_cz = plate.center
        z_min = plate_cz - (plate.height / 2)
        z_max = plate_cz + (plate.height / 2)
        u_comp = z_min if My > 0 else z_max
        
        if tension_method == "accurate":
            # d/6 from compression edge
            u_na = u_comp + (plate.height / 6.0) if u_comp == z_min else u_comp - (plate.height / 6.0)
        else:  # conservative
            u_na = (z_min + z_max) / 2
            
        tensions += _distribute_moment(bolt_coords[:, 1], My, u_na, u_comp)

    # Bending around Z-axis (Affected by Y coordinates)
    if abs(Mz) > 1e-12:
        plate_cy, plate_cz = plate.center
        y_min = plate_cy - (plate.width / 2)
        y_max = plate_cy + (plate.width / 2)
        u_comp = y_min if Mz > 0 else y_max
        
        if tension_method == "accurate":
            u_na = u_comp + (plate.width / 6.0) if u_comp == y_min else u_comp - (plate.width / 6.0)
        else:
            u_na = (y_min + y_max) / 2
            
        tensions += _distribute_moment(bolt_coords[:, 0], Mz, u_na, u_comp)

    return np.maximum(0.0, tensions)

def _distribute_moment(
    u_coords: np.ndarray,
    M: float,
    u_na: float,
    u_comp: float
) -> np.ndarray:
    """
    Refined to match the T1 = |M| / sum(yi * (yi/y1 - yc/y1)) formula.
    
    Parameters:
    u_coords : np.ndarray -> Bolt coordinates along the axis of interest.
    M        : float      -> Applied moment.
    u_na     : float      -> Neutral axis position.
    u_comp   : float      -> Compression edge position.
    
    Returns:
    np.ndarray: Moment-induced tensions along the coordinate axis.
    """
    rel_dist = u_coords - u_na
    # Tension side is opposite to the compression edge relative to NA
    is_tension = (rel_dist > 0) if (u_na > u_comp) else (rel_dist < 0)
    
    y_i = np.abs(rel_dist)
    y_c = -np.abs(u_comp - u_na)
    
    if not np.any(is_tension):
        return np.zeros_like(u_coords)
    
    y_1 = np.max(y_i[is_tension])
    # Denominator from bolt.md: sum(yi * (yi/y1 - yc/y1))
    denom = np.sum(y_i[is_tension] * (y_i[is_tension] / y_1 - y_c / y_1))
    
    T1 = np.abs(M) / denom if denom > 1e-9 else 0.0
    
    # Linear distribution; compression side gets negative values
    final_forces = T1 * (y_i / y_1)
    final_forces[~is_tension] *= -1.0
    return final_forces

def apply_prying_forces(
    tensions: np.ndarray,
    t_plate: float,
    a: float,
    b: float,
    bolt_diameter: float,
    fy_plate: float
) -> np.ndarray:
    """
    Calculates design tension (T'u) including prying action.
    Following simplified AISC/industry logic.
    
    Parameters:
    tensions      : np.ndarray -> Static tension per bolt (Tu) from solve_bolt_tension_simple.
    t_plate       : float      -> Thickness of the plate.
    a             : float      -> Distance from bolt centerline to plate edge.
    b             : float      -> Distance from bolt centerline to face of support.
    bolt_diameter : float      -> Diameter of the bolt.
    fy_plate      : float      -> Yield strength of the plate material.
    
    Returns:
    np.ndarray: Total tension demand per bolt (Tu + Q).
    """
    # 1. Effective width per bolt (simplified)
    # Usually taken as the tributary width or prying strip width
    p: float = 2 * bolt_diameter 
    
    # 2. Parametric ratios
    rho: float = b / a if a > 0 else 1.0
    delta: float = 1.0 - (bolt_diameter / p)  # Ratio of net area at bolt line
    
    # 3. Calculate Tc (Bolt capacity required to eliminate prying)
    # This is a simplified check for plate stiffness
    t_req: np.ndarray = np.sqrt((4.44 * tensions * b) / (p * fy_plate * (1 + delta)))
    
    # 4. Prying force calculation (Q)
    # If the plate is thick enough (t_plate > t_req), prying is negligible.
    prying_ratio: np.ndarray = np.where(
        t_plate < t_req,
        (1 / delta) * ((t_req / t_plate)**2 - 1) * (rho / (1 + rho)),
        0.0
    )
    
    # Ensure prying ratio doesn't exceed 1.0 (theoretical limit)
    prying_ratio = np.clip(prying_ratio, 0.0, 1.0)
    
    return tensions * (1 + prying_ratio)

if __name__ == "__main__":
    # --- Example Usage ---
    # my_plate = Plate(Cy=0, Cz=0, height=12.0, width=8.0)
    # bolts = np.array([[-2, -4], [2, -4], [-2, 4], [2, 4]])  # 4 bolts in [y, z]
    # results = solve_bolt_tension_simple(bolts, my_plate, Fx=10, My=150, Mz=0)
    # print(f"Bolt Tensions: {results}")
    pass
