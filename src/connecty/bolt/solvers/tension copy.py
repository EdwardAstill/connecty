import numpy as np

def solve_bolt_tension(
    bolt_coords: np.ndarray,
    plate: any,
    Fz: float,
    Mx: float,
    My: float,
    tension_method: str = "accurate"
) -> np.ndarray:
    bolt_coords = np.array(bolt_coords)
    n = len(bolt_coords)
    
    # Initialize tensions with direct axial load component
    final_tensions = np.full(n, max(0.0, Fz / n))

    # Solve bending components independently (Superposition)
    # Note: For biaxial bending, this logic applies Mx and My separately.
    if Mx != 0:
        final_tensions += _calculate_bending_tensions(bolt_coords, plate, Mx, axis='x', method=tension_method)
    
    if My != 0:
        final_tensions += _calculate_bending_tensions(bolt_coords, plate, My, axis='y', method=tension_method)

    return np.maximum(0.0, final_tensions)

def _calculate_bending_tensions(bolt_coords, plate, M, axis='x', method='accurate'):
    """Calculates additional bolt tension due to a moment about the X or Y axis."""
    n = len(bolt_coords)
    idx = 1 if axis == 'x' else 0  # Bending about X uses Y coords; Bending about Y uses X coords
    coords = bolt_coords[:, idx]
    
    plate_min = plate.y_min if axis == 'x' else plate.x_min
    plate_max = plate.y_max if axis == 'x' else plate.x_max
    depth = plate.height if axis == 'x' else plate.width
    width = plate.width if axis == 'x' else plate.height

    # 1. Determine Neutral Axis (NA) and Compression Edge
    # If M > 0, compression is at min edge. NA is d/6 from that edge.
    comp_edge = plate_min if M > 0 else plate_max
    na_offset = depth / 6.0
    u_na = comp_edge + na_offset if M > 0 else comp_edge - na_offset

    # 2. Calculate Bolt "Unit" Forces and Unit Moment
    # Assumption: Tension is proportional to distance from NA.
    dist_from_na = np.abs(coords - u_na)
    # Bolts on the compression side of the NA have 0 tension contribution
    is_tension_side = (coords > u_na) if M > 0 else (coords < u_na)
    unit_bolt_forces = np.where(is_tension_side, dist_from_na, 0.0)
    
    # Moment of bolts about the Centroid (0,0)
    unit_bolt_moment = np.sum(unit_bolt_forces * coords)

    # 3. Calculate Plate "Unit" Compression Moment
    # Stress blocks: triangular distribution from NA (stress=0) to comp_edge (stress=max)
    n_strips = 100
    strip_h = na_offset / n_strips
    strip_area = strip_h * width
    
    unit_plate_moment = 0.0
    for i in range(n_strips):
        # Distance from NA to center of strip
        d_na = (i + 0.5) * strip_h
        # Local stress is proportional to distance from NA
        # Normalized so that stress at dist_from_na=1.0 is 1.0
        strip_force = d_na * strip_area
        # Coordinate of strip
        y_strip = u_na - d_na if M > 0 else u_na + d_na
        unit_plate_moment -= strip_force * y_strip # Compression moment subtracts

    # 4. Total Unit Moment Resistance
    # M_total_unit = M_bolts_unit - M_plate_unit
    total_unit_moment = unit_bolt_moment - unit_plate_moment
    
    # 5. Scale and Return
    scale_factor = abs(M) / abs(total_unit_moment)
    return unit_bolt_forces * scale_factor

    
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
    pass
