import math
import numpy as np

def golden_search(a, b, residual_fn, tolerance=1e-6, max_iter=1000):
    phi = (1 + math.sqrt(5)) / 2
    inv_phi = 1 / phi

    c = b - (b - a) * inv_phi
    d = a + (b - a) * inv_phi

    fc = residual_fn(c)
    fd = residual_fn(d)

    for _ in range(max_iter):
        if abs(b - a) < tolerance:
            break

        if fc < fd:
            b = d
            d = c
            fd = fc
            c = b - (b - a) * inv_phi
            fc = residual_fn(c)
        else:
            a = c
            c = d
            fc = fd
            d = a + (b - a) * inv_phi
            fd = residual_fn(d)

    return (a + b) / 2


def solve_bolt_icr(
    bolt_coords: np.ndarray,
    Fx: float,
    Fy: float,
    Mz: float,
    x_loc: float,
    y_loc: float,
    mu: float = 10.0,
    lam: float = 0.55,
    delta_max: float = 8.64,
    tolerance: float = 1e-6
) -> tuple[np.ndarray, np.ndarray, tuple[float, float, int]]:
    """
    Solves for the ICR using a 1D search along the perpendicular axis 
    to the applied load vector.

    Positive moments about z-axis are counter-clockwise (right handed rule).
    Coordinates: x (horizontal), y (vertical).
    """
    bolt_coords = np.array(bolt_coords)
    centroid = np.mean(bolt_coords, axis=0)
    # print(f"Centroid: {centroid}")
    Cx, Cy = centroid[0], centroid[1]
    # print(f"Cx: {Cx}, Cy: {Cy}")

    # 1. Moment Transfer to Centroid
    # Mz_total = Mz + dx*Fy - dy*Fx
    Mz_centroid = Mz + (x_loc - Cx) * Fy - (y_loc - Cy) * Fx
    # print(f"Moment at centroid: {Mz_centroid}")
    
    # need a moment at the centroid otherwise icr will not work
    if abs(Mz_centroid) < 1e-9:
        # Avoid division by zero if moment is effectively zero
        # This technically shouldn't happen in standard ICR use cases unless pure translation
        # But if it does, it's just elastic distribution of forces (uniform)
        # For now, raise or handle. Original code raised.
        # Let's handle pure translation if P > 0
        pass 
    
    if Mz_centroid == 0:
         raise ValueError("Moment at centroid is 0, ICR will not work")

    P = math.hypot(Fx, Fy)

    if P < 1e-9:
        # Pure torsion case: ICR is at the centroid
        return _calculate_final_state(bolt_coords, Cx, Cy, Fx, Fy, Mz_centroid, mu, lam, delta_max)

    # 2. Define Perpendicular Search Direction
    # Unit vector of load: (Fx/P, Fy/P). 
    # Perpendicular (90 deg CCW): (-Fy/P, Fx/P)
    # If Moment is Positive (CCW), ICR should be to the 'Left' of the force vector (relative to direction)
    # So we search along +Perp.
    # If Moment is Negative (CW), ICR should be to the 'Right'.
    
    moment_sign = 1.0 if Mz_centroid >= 0 else -1.0
    
    # Vector perpendicular to Force (CCW rotation of Force vector)
    # u_perp = (-Fy, Fx) normalized
    perp_x = -Fy / P
    perp_y =  Fx / P
    
    # Adjust search direction based on moment sign
    # If M > 0, we search in +u_perp direction?
    # Test: Force Up (0, 1). M > 0 (CCW). ICR should be Left (-1, 0).
    # perp_x = -1, perp_y = 0.
    # Search along +1 * (-1, 0) -> (-1, 0). Correct.
    
    # Test: Force Up (0, 1). M < 0 (CW). ICR should be Right (1, 0).
    # moment_sign = -1.
    # Search along -1 * (-1, 0) -> (1, 0). Correct.
    
    search_dir_x = moment_sign * perp_x
    search_dir_y = moment_sign * perp_y

    # print("icr exists on this vector passing through the centroid:")
    # print(f"({search_dir_x}, {search_dir_y})")

    # 3. Define the Residual Function for 1D distance 'r'
    def get_moment_residual(r):
        # assume the icr is a distance r from the centroid
        icr_x = Cx + r * search_dir_x
        icr_y = Cy + r * search_dir_y
        
        # calculate the distance from the icr to each bolt
        r_vecs = bolt_coords - np.array([icr_x, icr_y])
        dist_i = np.linalg.norm(r_vecs, axis=1)
        dist_i = np.where(dist_i < 1e-9, 1e-9, dist_i)
        
        # find the maximum distance from the icr to a bolt
        c_max = np.max(dist_i)
        
        # normalized resistance
        Ri = (1 - np.exp(-mu * (dist_i / c_max) * (c_max / delta_max)))**lam
        
        # Direction of force on bolt: Perpendicular to radius vector (r_vecs)
        # Rotation direction matches Moment sign.
        # r_vec = (dx, dy). 
        # CCW Force dir: (-dy, dx) / dist
        # CW Force dir: (dy, -dx) / dist
        # We can just use the CCW unit vector and let the sign handle itself?
        # M_int calculation below uses cross product logic.
        
        # Unit vector perpendicular (CCW) to radius
        tx = -r_vecs[:, 1] / dist_i # -dy
        ty =  r_vecs[:, 0] / dist_i # dx
        
        # Internal Moment contribution (M = r x F)
        # F = R * t
        # M = dx * Fy - dy * Fx = dx * (R*ty) - dy * (R*tx)
        #   = R * (dx * dx/dist - dy * (-dy/dist))
        #   = R * (dx^2 + dy^2) / dist = R * dist
        # So sum(Ri * dist_i) is the scalar moment magnitude if we assume CCW rotation.
        # If Mz_centroid is negative, we want CW rotation.
        # But we are matching magnitudes usually?
        # The solver usually balances the scalar values.
        
        M_int_mag = np.sum(Ri * dist_i)
        
        # Shear force Resultant from internal forces
        # We need to scale Ri so that Resultant = Applied Load P?
        # No, ICR method: Resultant of bolt forces must equal Applied Force.
        # V_int = sum(Force_vectors)
        V_int_x = np.sum(Ri * tx)
        V_int_y = np.sum(Ri * ty)
        V_int_mag = math.hypot(V_int_x, V_int_y)
        
        # Scale factor
        virtual_scale = P / V_int_mag if V_int_mag > 1e-9 else 0
        
        # Scaled Moment
        M_int_scaled = M_int_mag * virtual_scale
        
        # Residual
        return abs(M_int_scaled - abs(Mz_centroid))
    
    r = golden_search(0.01, 1e7, get_moment_residual, tolerance, max_iter=10000)
    # print(f"r: {r}")

    final_x_ic = Cx + r * search_dir_x
    final_y_ic = Cy + r * search_dir_y

    return _calculate_final_state(
        bolt_coords, final_x_ic, final_y_ic, Fx, Fy, Mz_centroid, mu, lam, delta_max
    )

def _calculate_final_state(bolt_coords, x_ic, y_ic, Fx, Fy, Mz_total, mu, lam, delta_max, iterations=0):
    r_vecs = bolt_coords - np.array([x_ic, y_ic])
    dist_i = np.linalg.norm(r_vecs, axis=1)
    dist_i = np.where(dist_i < 1e-9, 1e-9, dist_i)
    c_max = np.max(dist_i)
    
    Ri = (1 - np.exp(-mu * (dist_i / c_max) * (c_max / delta_max)))**lam
    
    # Unit vectors perpendicular to radius (CCW assumed)
    tx = -r_vecs[:, 1] / dist_i
    ty =  r_vecs[:, 0] / dist_i
    
    # Check direction relative to moment
    # If Mz_total is negative, forces should be CW.
    # The search placed IC such that the forces oppose the load (or balance it).
    # But for moment balance:
    # If IC is correct, the resultant force direction matches the applied load direction?
    # No, internal forces resist applied load. So Internal Resultant should equal -Applied Load?
    # Wait, usually we say "Bolt Forces" as the forces ON the bolts (reaction from plate).
    # Applied Load on Plate. Bolt Forces on Plate resist Applied Load.
    # So Sum(F_bolt) + F_applied = 0 => Sum(F_bolt) = -F_applied.
    # But usually in engineering we calculate the "Shear in the bolt", which matches the direction of the load on the connection (if we consider the load flowing through).
    # Let's check elastic.
    # F_bolt = F_load / n. (Same direction).
    # So Bolt Force vector should match Applied Load direction.
    
    # In ICR:
    # If we use tx, ty (CCW around IC).
    # And we scale by P / V_int.
    # We need to ensure the final vector sums to (Fx, Fy).
    
    V_int_x = np.sum(Ri * tx)
    V_int_y = np.sum(Ri * ty)
    V_int_mag = math.hypot(V_int_x, V_int_y)
    
    scale = math.hypot(Fx, Fy) / V_int_mag if V_int_mag > 1e-9 else 0.0
    
    # We apply the sign of the moment to the direction?
    # If M > 0, we are CCW. tx, ty are CCW.
    # If M < 0, we are CW. tx, ty are CCW. We should flip?
    # But `r` logic placed IC on one side or the other.
    # If IC is on "Left", rotation causes Up force?
    # Let's assume the solver found the correct IC location such that rotation provides the correct translation component direction.
    # However, we must ensure the sign of rotation matches `Mz_total`.
    # If `Mz_total` < 0, we want CW rotation.
    
    rotation_sign = 1.0 if Mz_total >= 0 else -1.0
    
    bolt_forces_x = Ri * tx * scale * rotation_sign
    bolt_forces_y = Ri * ty * scale * rotation_sign
    
    # But wait, if we flip the forces, we might flip the resultant direction too?
    # If the IC is placed correctly, the resultant of the rotation-induced forces + translation...
    # ICR formulation is purely rotational about IC.
    # $F_{bolt} = k \times r$.
    # The resultant of these rotational forces equals the applied load.
    
    # If we simply multiply by rotation_sign, we assume tx, ty are CCW.
    # If M < 0 (CW), we want CW forces. -tx, -ty.
    # Does this sum to (Fx, Fy)?
    # Only if the IC location was chosen such that CW rotation produces (Fx, Fy).
    # We chose search direction based on M sign.
    
    return bolt_forces_x, bolt_forces_y, (float(x_ic), float(y_ic))

def check_icr(bolt_forces_x, bolt_forces_y, icr_point, bolt_coords, Fx, Fy, Mz_centroid) -> None:
    """
    Verifies that the calculated bolt forces satisfy equilibrium with the 
    applied loads at the centroid.
    """
    # 1. Calculate Resultant Reactions
    total_Rx = np.sum(bolt_forces_x)
    total_Ry = np.sum(bolt_forces_y)
    
    # 2. Calculate Internal Moment about Centroid (0,0) assumptions
    # M = sum( r x F )_z
    centroid = np.mean(bolt_coords, axis=0)
    Cx, Cy = centroid[0], centroid[1]
    
    # Moment = (x - Cx)*Fy - (y - Cy)*Fx
    moments = (bolt_coords[:, 0] - Cx) * bolt_forces_y - \
              (bolt_coords[:, 1] - Cy) * bolt_forces_x
    total_Mz = np.sum(moments)

    print("\n=== Equilibrium Verification ===")
    print(f"{'Component':<12} | {'Applied':<12} | {'Reaction':<12} | {'Error':<12}")
    print("-" * 60)
    print(f"{'Fx (Shear)':<12} | {Fx:<12.4f} | {total_Rx:<12.4f} | {abs(Fx - total_Rx):<12.4e}")
    print(f"{'Fy (Shear)':<12} | {Fy:<12.4f} | {total_Ry:<12.4f} | {abs(Fy - total_Ry):<12.4e}")
    print(f"{'Mz (Moment)':<12} | {Mz_centroid:<12.4f} | {total_Mz:<12.4f} | {abs(Mz_centroid - total_Mz):<12.4e}")
    
    # 3. Geometric Check: Perpendicularity
    icr_x, icr_y = icr_point
    r_vecs = bolt_coords - np.array([icr_x, icr_y])
    
    dot_products = []
    for i in range(len(bolt_coords)):
        force_vec = np.array([bolt_forces_x[i], bolt_forces_y[i]])
        dot = np.dot(r_vecs[i], force_vec)
        dot_products.append(dot)
    
    max_dot = np.max(np.abs(dot_products))
    print(f"{'Max Perp Err':<12} | {'0.0':<12} | {max_dot:<12.4e} | (Radial Dot Product)")

def main():
    bolt_coords = np.array([[-1, -1], [1, -1], [1, 1], [-1, 1]])
    Fx = 0
    Fy = 1
    Mz = 1
    x_loc = 1
    y_loc = 0
    
    centroid = np.mean(bolt_coords, axis=0)
    Mz_centroid = Mz + (x_loc - centroid[0]) * Fy - (y_loc - centroid[1]) * Fx

    bolt_forces_x, bolt_forces_y, icr_point = solve_bolt_icr(
        bolt_coords, Fx, Fy, Mz, x_loc, y_loc
    )
    
    check_icr(bolt_forces_x, bolt_forces_y, icr_point, bolt_coords, Fx, Fy, Mz_centroid)

if __name__ == "__main__":
    main()
