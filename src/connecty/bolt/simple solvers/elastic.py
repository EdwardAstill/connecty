import numpy as np

def solve_bolt_elastic(bolt_coords, Fx, Fy, P_pos, M_ext):
    """
    Solves for bolt forces using the Elastic Method (Linear Distribution).
    
    Parameters:
    bolt_coords : np.array -> Nx2 array of [x, y] coordinates.
    Fx, Fy      : float    -> External force components.
    P_pos       : list/vec -> [x, y] where the force is applied.
    M_ext       : float    -> Applied twisting moment (CCW positive).
    
    Returns:
    dict: Contains centroid, polar moment J, and individual bolt force vectors.
    """
    bolt_coords = np.array(bolt_coords)
    n = len(bolt_coords)
    
    # 1. Find the Centroid (x_bar, y_bar)
    centroid = np.mean(bolt_coords, axis=0)
    
    # 2. Calculate Polar Moment of Inertia (J) about the centroid
    # J = sum(dx^2 + dy^2)
    relative_coords = bolt_coords - centroid
    J = np.sum(relative_coords**2)
    
    # 3. Calculate Total Moment about the Centroid
    # M_centroid = M_ext + (Force Moment arm)
    arm_x = P_pos[0] - centroid[0]
    arm_y = P_pos[1] - centroid[1]
    M_c = M_ext + (arm_x * Fy - arm_y * Fx)
    
    # 4. Direct Shear components (equal for all bolts)
    f_direct_x = Fx / n
    f_direct_y = Fy / n
    
    # 5. Torsional Shear components
    # f_mx = -M*dy / J, f_my = M*dx / J (Perpendicular to radius)
    f_torsion_x = -(M_c * relative_coords[:, 1]) / J
    f_torsion_y =  (M_c * relative_coords[:, 0]) / J
    
    # 6. Resultant Forces for each bolt
    bolt_forces_x = f_direct_x + f_torsion_x
    bolt_forces_y = f_direct_y + f_torsion_y
    resultant_magnitudes = np.sqrt(bolt_forces_x**2 + bolt_forces_y**2)
    
    return {
        "centroid": centroid,
        "J": J,
        "total_moment_at_centroid": M_c,
        "bolt_forces": np.column_stack((bolt_forces_x, bolt_forces_y)),
        "max_force": np.max(resultant_magnitudes)
    }

# --- Example Usage ---
bolts = np.array([[0,0], [3,0], [0,3], [3,3]])
# 10k force in Y at x=6, plus 50k-in moment
results = solve_bolt_elastic(bolts, 0, -10, [6, 1.5], 50)

print(f"Centroid: {results['centroid']}")
print(f"Max Bolt Force: {results['max_force']:.4f}")