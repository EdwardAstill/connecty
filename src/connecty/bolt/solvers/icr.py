import math
import numpy as np



import math
import numpy as np

# ----------------------------
# NEW: small 2D Nelder–Mead
# ----------------------------
def nelder_mead_2d(f, x0, step=1.0, tol=1e-8, max_iter=500):
    """
    Very small Nelder–Mead for 2D (no scipy).
    Minimizes scalar f(xy) where xy is shape (2,).
    """
    x0 = np.asarray(x0, dtype=float)

    # Initial simplex: x0, x0+[step,0], x0+[0,step]
    simplex = np.array([x0, x0 + [step, 0.0], x0 + [0.0, step]], dtype=float)
    vals = np.array([f(p) for p in simplex], dtype=float)

    # Coeffs
    alpha = 1.0   # reflection
    gamma = 2.0   # expansion
    rho   = 0.5   # contraction
    sigma = 0.5   # shrink

    for _ in range(max_iter):
        # Order
        order = np.argsort(vals)
        simplex = simplex[order]
        vals = vals[order]

        best = simplex[0]
        worst = simplex[-1]

        # Convergence: simplex size + function spread
        if np.max(np.linalg.norm(simplex - best, axis=1)) < tol and (vals[-1] - vals[0]) < tol:
            break

        centroid = np.mean(simplex[:-1], axis=0)

        # Reflect
        xr = centroid + alpha * (centroid - worst)
        fr = f(xr)

        if fr < vals[0]:
            # Expand
            xe = centroid + gamma * (xr - centroid)
            fe = f(xe)
            if fe < fr:
                simplex[-1], vals[-1] = xe, fe
            else:
                simplex[-1], vals[-1] = xr, fr
            continue

        if fr < vals[-2]:
            simplex[-1], vals[-1] = xr, fr
            continue

        # Contract
        if fr < vals[-1]:
            # outside contraction
            xc = centroid + rho * (xr - centroid)
        else:
            # inside contraction
            xc = centroid - rho * (centroid - worst)
        fc = f(xc)

        if fc < vals[-1]:
            simplex[-1], vals[-1] = xc, fc
            continue

        # Shrink
        for i in range(1, len(simplex)):
            simplex[i] = best + sigma * (simplex[i] - best)
            vals[i] = f(simplex[i])

    order = np.argsort(vals)
    return simplex[order][0], float(vals[order][0])


# ----------------------------
# PATCH: replace _calculate_final_state
# ----------------------------
def _calculate_final_state(
    bolt_coords,
    x_ic,
    y_ic,
    Fx,
    Fy,
    Mz_total,
    mu,
    lam,
    delta_max,
    scale_mode="magnitude",
):
    """
    Computes bolt forces for a given ICR.
    scale_mode:
      - "magnitude": scale to match |P| (your prior behavior, requires direction to be right)
      - "projection": least-squares scalar scale to best match (Fx,Fy) even if small misalignment
    Handles pure torsion (P ~ 0) by scaling to match moment instead of shear.
    """
    bolt_coords = np.asarray(bolt_coords, dtype=float)
    r_vecs = bolt_coords - np.array([x_ic, y_ic], dtype=float)

    dist_i = np.linalg.norm(r_vecs, axis=1)
    dist_i = np.where(dist_i < 1e-9, 1e-9, dist_i)
    c_max = float(np.max(dist_i))

    Ri = (1.0 - np.exp(-mu * (dist_i / c_max) * (c_max / delta_max))) ** lam

    # CCW tangential unit vectors
    tx = -r_vecs[:, 1] / dist_i
    ty =  r_vecs[:, 0] / dist_i

    V_int_x = float(np.sum(Ri * tx))
    V_int_y = float(np.sum(Ri * ty))
    V_int_sq = V_int_x * V_int_x + V_int_y * V_int_y
    V_int_mag = math.sqrt(V_int_sq)

    P = math.hypot(Fx, Fy)

    # Moment “capacity” per unit scale about the ICR:
    M_int_mag = float(np.sum(Ri * dist_i))

    if P < 1e-12:
        # Pure torsion: pick scale so internal moment matches Mz_total
        if M_int_mag < 1e-12:
            scale = 0.0
        else:
            scale = abs(Mz_total) / M_int_mag
        rot_sign = 1.0 if Mz_total >= 0 else -1.0
        bolt_forces_x = Ri * tx * scale * rot_sign
        bolt_forces_y = Ri * ty * scale * rot_sign
        return bolt_forces_x, bolt_forces_y, (float(x_ic), float(y_ic))

    if V_int_mag < 1e-12:
        return np.zeros(len(bolt_coords)), np.zeros(len(bolt_coords)), (float(x_ic), float(y_ic))

    if scale_mode == "projection":
        # least squares scalar: minimize || scale*V_int - P_applied ||^2
        scale = (Fx * V_int_x + Fy * V_int_y) / max(V_int_sq, 1e-30)
        # fold sign into rot_sign (keep scale >= 0)
        rot_sign = 1.0
        if scale < 0.0:
            scale = -scale
            rot_sign = -1.0
    else:
        # match magnitude, then choose sign to align with applied
        scale = P / V_int_mag
        rot_sign = 1.0
        dot = (V_int_x * Fx + V_int_y * Fy) / (V_int_mag * P)
        if dot < 0.0:
            rot_sign = -1.0

    bolt_forces_x = Ri * tx * scale * rot_sign
    bolt_forces_y = Ri * ty * scale * rot_sign
    return bolt_forces_x, bolt_forces_y, (float(x_ic), float(y_ic))


# ----------------------------
# PATCH: replace solve_bolt_icr (adds 2D solver)
# ----------------------------
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
    tolerance: float = 1e-6,
    method: str = "auto",   # "1d", "2d", or "auto"
) -> tuple[np.ndarray, np.ndarray, tuple[float, float, int]]:
    bolt_coords = np.array(bolt_coords, dtype=float)
    centroid = np.mean(bolt_coords, axis=0)
    Cx, Cy = float(centroid[0]), float(centroid[1])

    # Moment transfer to centroid
    Mz_centroid = Mz + (x_loc - Cx) * Fy - (y_loc - Cy) * Fx
    if abs(Mz_centroid) < 1e-12 and math.hypot(Fx, Fy) < 1e-12:
        raise ValueError("Both shear and centroid moment are ~0 (nothing to solve).")

    P = math.hypot(Fx, Fy)

    # Characteristic length for nondimensional residuals
    L_char = float(np.max(np.linalg.norm(bolt_coords - np.array([Cx, Cy]), axis=1)))
    force_scale = max(P, 1.0)
    moment_scale = max(abs(Mz_centroid), 1.0)

    def moment_about_centroid(bfx, bfy):
        r = bolt_coords - np.array([Cx, Cy], dtype=float)
        return float(np.sum(r[:, 0] * bfy - r[:, 1] * bfx))

    def objective_xy(xy):
        x_ic, y_ic = float(xy[0]), float(xy[1])
        bfx, bfy, _ = _calculate_final_state(
            bolt_coords, x_ic, y_ic, Fx, Fy, Mz_centroid, mu, lam, delta_max, scale_mode="projection"
        )
        dFx = float(np.sum(bfx) - Fx)
        dFy = float(np.sum(bfy) - Fy)
        dMz = float(moment_about_centroid(bfx, bfy) - Mz_centroid)

        # nondimensional weighted SSE
        return (dFx / force_scale) ** 2 + (dFy / force_scale) ** 2 + (dMz / (moment_scale / max(L_char, 1e-9))) ** 2

    # ----------------------------
    # 1D solve (your current approach), unchanged logic
    # ----------------------------
    def solve_1d():
        if P < 1e-12:
            # pure torsion: ICR at centroid
            return _calculate_final_state(bolt_coords, Cx, Cy, Fx, Fy, Mz_centroid, mu, lam, delta_max, scale_mode="magnitude")

        moment_sign = 1.0 if Mz_centroid >= 0 else -1.0
        perp_x = -Fy / P
        perp_y =  Fx / P
        search_dir_x = moment_sign * perp_x
        search_dir_y = moment_sign * perp_y

        def get_residual_r(r):
            icr_x = Cx + r * search_dir_x
            icr_y = Cy + r * search_dir_y
            # Evaluate objective but on the 1D line; use projection scaling so force residual is meaningful
            return objective_xy([icr_x, icr_y])

        r = golden_search(0.01, 1e7, get_residual_r, tolerance=tolerance, max_iter=10000)
        x_ic = Cx + r * search_dir_x
        y_ic = Cy + r * search_dir_y
        return _calculate_final_state(bolt_coords, x_ic, y_ic, Fx, Fy, Mz_centroid, mu, lam, delta_max, scale_mode="projection")

    # ----------------------------
    # 2D solve
    # ----------------------------
    def solve_2d(seed_xy=None):
        # Seed: 1D result if available; otherwise centroid
        if seed_xy is None:
            seed_xy = np.array([Cx, Cy], dtype=float)

        # Coarse multi-start around centroid to avoid bad simplex starts
        # Search radius based on required lever arm ~ |Mz|/P (clamped)
        r_req = abs(Mz_centroid) / max(P, 1e-9)
        R = max(0.5 * L_char, min(5.0 * L_char, r_req if np.isfinite(r_req) else 2.0 * L_char))

        candidates = [seed_xy]
        # add a small ring of candidates
        for ang in np.linspace(0.0, 2.0 * math.pi, 12, endpoint=False):
            candidates.append(np.array([Cx + R * math.cos(ang), Cy + R * math.sin(ang)], dtype=float))
        # include centroid too
        candidates.append(np.array([Cx, Cy], dtype=float))

        best_xy = None
        best_f = float("inf")
        for c in candidates:
            fc = objective_xy(c)
            if fc < best_f:
                best_f, best_xy = fc, c

        step = 0.25 * max(L_char, 1.0)
        xy_star, _ = nelder_mead_2d(objective_xy, best_xy, step=step, tol=tolerance, max_iter=800)

        return _calculate_final_state(
            bolt_coords, float(xy_star[0]), float(xy_star[1]),
            Fx, Fy, Mz_centroid, mu, lam, delta_max,
            scale_mode="projection"
        )

    # ----------------------------
    # Select method
    # ----------------------------
    method = method.lower().strip()
    if method not in ("1d", "2d", "auto"):
        raise ValueError("method must be '1d', '2d', or 'auto'")

    if method == "1d":
        return solve_1d()

    if method == "2d":
        return solve_2d()

    # auto: run 1D, check residual, then 2D if needed
    bfx1, bfy1, icr1 = solve_1d()
    dFx1 = float(np.sum(bfx1) - Fx)
    dFy1 = float(np.sum(bfy1) - Fy)
    dMz1 = float(moment_about_centroid(bfx1, bfy1) - Mz_centroid)
    f1 = objective_xy([icr1[0], icr1[1]])

    # Trigger 2D if force or moment residual is meaningfully nonzero
    if abs(dFx1) > 1e-3 or abs(dFy1) > 1e-3 or abs(dMz1) > 1e-3:
        bfx2, bfy2, icr2 = solve_2d(seed_xy=np.array([icr1[0], icr1[1]], dtype=float))
        f2 = objective_xy([icr2[0], icr2[1]])
        if f2 < f1:
            return bfx2, bfy2, icr2

    return bfx1, bfy1, icr1


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
    """
    Batch test harness for solve_bolt_icr().

    What it checks (per case):
      1) Force equilibrium: sum(bolt_forces) == (Fx, Fy)
      2) Moment equilibrium about centroid: sum(r_i x F_i)_z == Mz_centroid   <-- this is currently FAILING in your code
      3) Moment equilibrium about ICR: sum((bolt-ICR) x F_i)_z == M_applied_about_ICR
      4) “Reasonableness”: shear magnitude should generally increase with radius-to-ICR
         (at least strongly non-decreasing when sorted by radius; prints a correlation + monotonicity info)

    NOTE: With your current residual definition, you will likely see:
      - Force equilibrium passes
      - Centroid moment equilibrium fails by about r_icr * P (where P = hypot(Fx,Fy))
      - This points to the residual matching moment about the wrong reference point (ICR vs centroid).
    """

    def applied_moment_about_point(x0, y0, Fx, Fy, Mz_centroid, Cx, Cy):
        """
        Applied loads are represented as:
          - resultant shear (Fx, Fy) acting at the centroid
          - plus a free moment Mz_centroid about the centroid

        Moment about an arbitrary point (x0,y0) is:
          Mz_about_point = Mz_centroid + (r_centroid - r_point) x F
                         = Mz_centroid + (Cx-x0)*Fy - (Cy-y0)*Fx
        """
        return Mz_centroid + (Cx - x0) * Fy - (Cy - y0) * Fx

    def internal_moment_about_point(x0, y0, bolt_coords, bolt_fx, bolt_fy):
        r = bolt_coords - np.array([x0, y0], dtype=float)
        return float(np.sum(r[:, 0] * bolt_fy - r[:, 1] * bolt_fx))

    def rank_corr(x, y):
        # small, dependency-free Spearman-like correlation via ranks
        x = np.asarray(x)
        y = np.asarray(y)
        rx = np.argsort(np.argsort(x))
        ry = np.argsort(np.argsort(y))
        if len(x) < 2:
            return float("nan")
        return float(np.corrcoef(rx, ry)[0, 1])

    def run_case(name, bolt_coords, Fx, Fy, Mz, x_loc, y_loc, mu=10.0, lam=0.55, delta_max=8.64):
        bolt_coords = np.array(bolt_coords, dtype=float)
        centroid = np.mean(bolt_coords, axis=0)
        Cx, Cy = float(centroid[0]), float(centroid[1])

        # Moment transferred to centroid (your exact convention)
        Mz_centroid = Mz + (x_loc - Cx) * Fy - (y_loc - Cy) * Fx
        P = math.hypot(Fx, Fy)

        bolt_fx, bolt_fy, icr = solve_bolt_icr(
            bolt_coords=bolt_coords,
            Fx=Fx, Fy=Fy, Mz=Mz,
            x_loc=x_loc, y_loc=y_loc,
            mu=mu, lam=lam, delta_max=delta_max
        )
        icr_x, icr_y = icr

        # Equilibrium checks
        sum_fx = float(np.sum(bolt_fx))
        sum_fy = float(np.sum(bolt_fy))

        Mint_centroid = internal_moment_about_point(Cx, Cy, bolt_coords, bolt_fx, bolt_fy)
        Mint_icr      = internal_moment_about_point(icr_x, icr_y, bolt_coords, bolt_fx, bolt_fy)

        Mappl_icr = applied_moment_about_point(icr_x, icr_y, Fx, Fy, Mz_centroid, Cx, Cy)

        # Per-bolt reasonableness metrics
        r_to_icr = np.linalg.norm(bolt_coords - np.array([icr_x, icr_y]), axis=1)
        shear_mag = np.hypot(bolt_fx, bolt_fy)

        order = np.argsort(r_to_icr)
        r_sorted = r_to_icr[order]
        s_sorted = shear_mag[order]

        # count how many adjacent decreases in shear after sorting by radius
        decreases = int(np.sum(np.diff(s_sorted) < -1e-9))

        # Correlations (linear + rank)
        corr_lin = float(np.corrcoef(r_to_icr, shear_mag)[0, 1]) if len(r_to_icr) > 1 else float("nan")
        corr_rank = rank_corr(r_to_icr, shear_mag)

        print("\n" + "=" * 88)
        print(f"CASE: {name}")
        print(f"Bolts: {bolt_coords.tolist()}")
        print(f"Loads: Fx={Fx:.6g}, Fy={Fy:.6g}, Mz={Mz:.6g} @ ({x_loc:.6g},{y_loc:.6g})")
        print(f"Centroid: ({Cx:.6g},{Cy:.6g})  |  Mz_centroid={Mz_centroid:.6g}  |  P={P:.6g}")
        print(f"ICR: ({icr_x:.6g},{icr_y:.6g})")

        print("\n-- Equilibrium --")
        print(f"SumFx = {sum_fx:.6g}   (err {sum_fx - Fx:+.3e})")
        print(f"SumFy = {sum_fy:.6g}   (err {sum_fy - Fy:+.3e})")
        print(f"Mint about centroid = {Mint_centroid:.6g}   (target {Mz_centroid:.6g}, err {Mint_centroid - Mz_centroid:+.3e})")
        print(f"Mint about ICR      = {Mint_icr:.6g}        (target {Mappl_icr:.6g}, err {Mint_icr - Mappl_icr:+.3e})")

        # This diagnostic tends to reveal your current bug very clearly:
        # If centroid moment error ~ r_icr * P, you're matching the wrong moment reference in the residual.
        r_icr = math.hypot(icr_x - Cx, icr_y - Cy)
        print("\n-- Diagnostic --")
        print(f"|ICR-centroid| = {r_icr:.6g}  =>  r*P = {r_icr * P:.6g}")

        print("\n-- Per-bolt (sorted by radius to ICR) --")
        print(f"{'i':>2} | {'x':>9} {'y':>9} | {'r_to_icr':>10} | {'|V_i|':>10} | {'Fx_i':>10} {'Fy_i':>10}")
        print("-" * 88)
        for k, idx in enumerate(order):
            x, y = bolt_coords[idx]
            print(f"{idx:2d} | {x:9.4f} {y:9.4f} | {r_to_icr[idx]:10.4f} | {shear_mag[idx]:10.6f} | {bolt_fx[idx]:10.6f} {bolt_fy[idx]:10.6f}")

        print("\n-- Radius vs shear trend --")
        print(f"Linear corr(r,|V|) = {corr_lin:+.4f}")
        print(f"Rank   corr(r,|V|) = {corr_rank:+.4f}")
        print(f"Adjacent decreases in |V| after sorting by r: {decreases}")

        return {
            "name": name,
            "icr": icr,
            "centroid": (Cx, Cy),
            "Mz_centroid": Mz_centroid,
            "sum_fx_err": sum_fx - Fx,
            "sum_fy_err": sum_fy - Fy,
            "Mz_centroid_err": Mint_centroid - Mz_centroid,
            "Mz_icr_err": Mint_icr - Mappl_icr,
            "rP": r_icr * P,
            "corr_lin": corr_lin,
            "corr_rank": corr_rank,
            "decreases": decreases,
        }

    # ----------------------------
    # Test configurations
    # ----------------------------
    configs = [
        ("Square 2x2", np.array([[-1, -1], [ 1, -1], [ 1,  1], [-1,  1]])),
        ("Wide rect",  np.array([[-2, -1], [ 2, -1], [ 2,  1], [-2,  1]])),
        ("Tall rect",  np.array([[-1, -2], [ 1, -2], [ 1,  2], [-1,  2]])),
        ("Triangle",   np.array([[ 0,  0], [ 2,  0], [ 1,  1.5]])),
        ("6-bolt ring",np.array([[ 2, 0],[ 1, 1.732],[ -1, 1.732],[ -2,0],[ -1,-1.732],[ 1,-1.732]])),
    ]

    # Load cases (keep Mz nonzero, otherwise your solver intentionally errors)
    load_cases = [
        ("Shear + moment (Y)",  0.0, 10.0,  50.0,  1.0, 0.0),
        ("Shear + moment (X)", 10.0,  0.0,  50.0,  0.0, 1.0),
        ("Diagonal shear + M",  7.0,  7.0,  40.0,  0.5, -0.5),
        ("Mostly moment",       1.0,  1.0, 200.0,  0.0,  0.0),
        ("Opp sign M",          0.0, 10.0, -50.0,  1.0,  0.0),
    ]

    # Run all combinations
    summary = []
    for cfg_name, bolts in configs:
        for lc_name, Fx, Fy, Mz, x_loc, y_loc in load_cases:
            name = f"{cfg_name} :: {lc_name}"
            out = run_case(name, bolts, Fx, Fy, Mz, x_loc, y_loc)
            summary.append(out)

    # Quick summary of “bad” cases
    print("\n" + "=" * 88)
    print("SUMMARY FLAGS")
    print("Flagged if: |centroid moment err| > 1e-3 OR |force err| > 1e-6")
    for s in summary:
        if (abs(s["sum_fx_err"]) > 1e-6) or (abs(s["sum_fy_err"]) > 1e-6) or (abs(s["Mz_centroid_err"]) > 1e-3):
            print(f"- {s['name']}")
            print(f"    force errs: dFx={s['sum_fx_err']:+.2e}, dFy={s['sum_fy_err']:+.2e}")
            print(f"    centroid moment err: {s['Mz_centroid_err']:+.3e}   (r*P={s['rP']:.6g})")
            print(f"    ICR moment err:      {s['Mz_icr_err']:+.3e}")
            print(f"    trend: rank corr={s['corr_rank']:+.3f}, decreases={s['decreases']}")

if __name__ == "__main__":
    main()
