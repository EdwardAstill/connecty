import numpy as np

def solve_bolt_icr(
    bolt_coords: np.ndarray,
    Fy: float,
    Fz: float,
    Mx: float,
    y_loc: float,
    z_loc: float,
    mu: float = 10.0,
    lam: float = 0.55,
    delta_max: float = 8.64,
    max_iterations: int = 5000
) -> tuple[np.ndarray, np.ndarray, tuple[float, float, int]]:
    """
    Solves for the ICR and individual bolt forces by minimizing 
    translation and rotation residuals simultaneously.
    """
    bolt_coords = np.array(bolt_coords) # [y, z]
    
    # 1. Centroid and Moment Transfer
    centroid = np.mean(bolt_coords, axis=0)
    Cy, Cz = centroid[0], centroid[1]
    Mx_total = Mx - Fz * (y_loc - Cy) + Fy * (z_loc - Cz) #

    def get_residuals(icr_pos: np.ndarray):
        """Calculates Fx, Fy, and Mx residuals for the current ICR."""
        y_ic, z_ic = icr_pos
        
        # 2. Kinematics
        r_vecs = bolt_coords - np.array([y_ic, z_ic])
        c_i = np.linalg.norm(r_vecs, axis=1)
        c_i = np.where(c_i < 1e-9, 1e-9, c_i)
        
        # 3. Crawford-Kulak Nonlinear Forces
        c_max = np.max(c_i)
        # Forces are relative to the most highly deformed bolt reaching capacity
        # We don't scale by applied shear; we let ICR position dictate magnitude
        rho_i = (c_i / c_max) 
        Ri_normalized = (1 - np.exp(-mu * rho_i * (c_max/delta_max)))**lam
        
        # 4. Force Vectors (Perpendicular to radius)
        ty = -(bolt_coords[:, 1] - z_ic) / c_i
        tz =  (bolt_coords[:, 0] - y_ic) / c_i
        
        # 5. Internal Summation
        # We need an ultimate strength R_ult for the bolts to get real force units
        # For a solver, we minimize the ratio of internal to external loads
        Fy_int = np.sum(Ri_normalized * ty)
        Fz_int = np.sum(Ri_normalized * tz)
        # Resisting moment relative to bolt centroid
        M_int = np.sum((Ri_normalized * ty) * bolt_coords[:, 1] - 
                       (Ri_normalized * tz) * bolt_coords[:, 0])
        
        # 6. Return vector of residuals
        # We normalize by external loads to keep gradients stable
        res_y = Fy_int / abs(Fy) - (Fy / abs(Fy)) if Fy != 0 else Fy_int
        res_z = Fz_int / abs(Fz) - (Fz / abs(Fz)) if Fz != 0 else Fz_int
        res_m = M_int / abs(Mx_total) - (Mx_total / abs(Mx_total)) if Mx_total != 0 else M_int
        
        return np.array([res_y, res_z, res_m]), Ri_normalized, ty, tz

    # --- Iterative Solver (Minimizing Sum of Squared Residuals) ---
    icr = np.mean(bolt_coords, axis=0) + 1.0 
    learning_rate = 0.1
    
    final_iterations = 0
    for i in range(max_iterations):
        final_iterations = i
        res, Ri, ty, tz = get_residuals(icr)
        cost = np.sum(res**2) # Goal is cost -> 0
        
        if cost < 1e-8:
            break
            
        # Numerical Gradients
        eps = 1e-7
        grad_y = (np.sum(get_residuals(icr + [eps, 0])[0]**2) - cost) / eps
        grad_z = (np.sum(get_residuals(icr + [0, eps])[0]**2) - cost) / eps
        
        icr -= np.array([grad_y, grad_z]) * learning_rate

    # Final Force Calculation
    res, Ri, ty, tz = get_residuals(icr)
    # Re-scale normalized Ri to actual force units based on applied loads
    applied_shear = np.sqrt(Fy**2 + Fz**2)
    internal_shear_mag = np.sqrt(np.sum(Ri*ty)**2 + np.sum(Ri*tz)**2)
    final_scale = applied_shear / internal_shear_mag
    
    bolt_fy = Ri * ty * final_scale
    bolt_fz = Ri * tz * final_scale
    
    return bolt_fy, bolt_fz, (float(icr[0]), float(icr[1]), final_iterations)