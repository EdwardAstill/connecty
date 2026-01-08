import numpy as np

def solve_bolt_icr(bolt_coords, Fx, Fy, P_pos, M_ext, load_def_fn, delta_max=0.34):
    """
    Solves for the ICR of a bolt group under combined Fx, Fy, and Moment.
    
    Parameters:
    bolt_coords : np.array  -> Nx2 array of [x, y] coordinates.
    Fx          : float     -> Force in X direction.
    Fy          : float     -> Force in Y direction.
    P_pos       : list/vec  -> [x, y] where the force (Fx, Fy) is applied.
    M_ext       : float     -> Applied twisting moment (CCW positive).
    load_def_fn : function  -> Callable R = f(delta).
    delta_max   : float     -> Max deformation of the critical bolt.
    """
    bolt_coords = np.array(bolt_coords)
    P_pos = np.array(P_pos)
    
    def get_residuals(icr):
        xi, yi = icr
        
        # 1. Geometry: Vectors from ICR to each bolt
        r_vecs = bolt_coords - np.array([xi, yi])
        distances = np.linalg.norm(r_vecs, axis=1)
        
        # Avoid singularities
        distances = np.where(distances < 1e-9, 1e-9, distances)
        
        # 2. Deformations: Linear distribution relative to furthest bolt
        r_max = np.max(distances)
        deltas = delta_max * (distances / r_max)
        
        # 3. Bolt Forces: Apply custom load-deformation function
        v_load_def = np.vectorize(load_def_fn)
        Ri = v_load_def(deltas)
        
        # 4. Force Components: Bolt forces are perpendicular to radius vectors
        # Vector [dx, dy] rotated 90 deg is [-dy, dx]
        fx_bolts = -Ri * (r_vecs[:, 1] / distances)
        fy_bolts =  Ri * (r_vecs[:, 0] / distances)
        
        # 5. Moment Balance about the ICR
        # Internal resistance moment (sum of distance * force)
        m_internal = np.sum(distances * Ri)
        
        # External moment about ICR from the force components + concentrated M
        rx_p = P_pos[0] - xi
        ry_p = P_pos[1] - yi
        m_external_total = (rx_p * Fy) - (ry_p * Fx) + M_ext
        
        # 6. Residuals: We want these to be zero
        res_x = np.sum(fx_bolts) + Fx
        res_y = np.sum(fy_bolts) + Fy
        res_m = m_internal + m_external_total 
        
        return np.array([res_x, res_y, res_m])

    # --- Iterative Solver (Heuristic Gradient Descent) ---
    # Initial guess at the centroid of the bolts
    icr = np.mean(bolt_coords, axis=0)
    
    # Adjust learning rates based on the scale of the bolt group
    span = np.max(bolt_coords) - np.min(bolt_coords)
    learning_rate = 0.01 if span > 0 else 0.01
    
    for i in range(10000):
        res = get_residuals(icr)
        
        # Convergence threshold
        if np.linalg.norm(res) < 1e-6:
            break
            
        # Update logic: 
        # Residual forces nudge the ICR perpendicular to the error
        icr[0] -= res[1] * learning_rate 
        icr[1] += res[0] * learning_rate
        
        # Residual moment nudges ICR along the moment arm
        icr[0] += res[2] * (learning_rate * 0.01)

    return icr

# --- Example Usage ---

# Define the AISC/Crawford-Kulak curve for a specific bolt
def bolt_curve(delta):
    Rult = 74.0 # kips
    return Rult * (1 - np.exp(-10 * delta))**0.55

# Define a pattern: 2x4 bolt grid
bolts = np.array([
    [0,0], [3,0],
    [0,3], [3,3],
    [0,6], [3,6],
    [0,9], [3,9]
])

# External Load: 
# Fx=20, Fy=-50, Applied at (15, 4.5) with a 200 kip-in CCW moment
icr_loc = solve_bolt_icr_final(
    bolt_coords=bolts,
    Fx=20,
    Fy=-50,
    P_pos=[15, 4.5],
    M_ext=200,
    load_def_fn=bolt_curve
)

print(f"Final ICR Location: [{icr_loc[0]:.4f}, {icr_loc[1]:.4f}]")