"""Not sure what to call this method.

Assumes compression is from plate only
Pretension neglected
Linear elastic assumption (bolt and plate are elastic their deforemation and force is proportional to distance from neutral axis)
plate is rigid
Bolts cannot provide compression
Plate cannot provide tension

Conventions (consistent with `analysis.py`):
- Bolt axial forces are positive in tension (+Fz).
- Plate bearing forces are negative in compression (-Fz).
- Moments about the origin are:
  - Mx = sum(y_i * Fz_i)
  - My = sum((-x_i) * Fz_i)
"""

from __future__ import annotations

import numpy as np

def cells_from_rectangle(
    *,
    x_min: float,
    x_max: float,
    y_min: float,
    y_max: float,
    n_cells_x: int,
    n_cells_y: int,
    L_grip: float,
) -> tuple[np.ndarray, float]:
    if n_cells_x <= 0 or n_cells_y <= 0:
        raise ValueError("n_cells_x and n_cells_y must be > 0")
    if x_max <= x_min or y_max <= y_min:
        raise ValueError("invalid bounds")
    if L_grip <= 0:
        raise ValueError("L_grip must be > 0")

    E = 210000.0  # N/mm^2 (MPa)
    dx = (x_max - x_min) / n_cells_x
    dy = (y_max - y_min) / n_cells_y
    A_cell = dx * dy
    k_cell = E * A_cell / L_grip  # N/mm

    xs = np.linspace(x_min + dx/2, x_max - dx/2, n_cells_x)
    ys = np.linspace(y_min + dy/2, y_max - dy/2, n_cells_y)

    cells = np.array([[x, y, k_cell] for x in xs for y in ys], dtype=float)
    return cells, A_cell



def _distance_to_na(x: np.ndarray, y: np.ndarray, theta: float, c: float) -> np.ndarray:
    """Signed distance from points (x, y) to the neutral axis."""
    return np.cos(theta) * x + np.sin(theta) * y - c


def _unit_forces_and_unit_moments(
    theta: float,
    c: float,
    bolt_coords: np.ndarray,
    cells: np.ndarray,
) -> tuple[float, float, float, np.ndarray, np.ndarray]:
    """Unit-scale forces/moments (s=1) with tension/compression gating."""
    # bolts: tension-only (d > 0)
    b_dist = _distance_to_na(bolt_coords[:, 0], bolt_coords[:, 1], theta, c)
    b_f1 = np.where(b_dist > 0.0, bolt_coords[:, 2] * b_dist, 0.0)

    # cells: compression-only (d < 0) -> negative force because d<0
    c_dist = _distance_to_na(cells[:, 0], cells[:, 1], theta, c)
    c_f1 = np.where(c_dist < 0.0, cells[:, 2] * c_dist, 0.0)

    S = float(np.sum(b_f1) + np.sum(c_f1))
    Mx1 = float(np.sum(b_f1 * bolt_coords[:, 1]) + np.sum(c_f1 * cells[:, 1]))
    My1 = float(np.sum(b_f1 * (-bolt_coords[:, 0])) + np.sum(c_f1 * (-cells[:, 0])))

    return S, Mx1, My1, b_f1, c_f1


def _scale_from_axial(P_target: float, S: float, tiny: float) -> float | None:
    if abs(S) < tiny:
        return None
    return float(P_target / S)


def _scale_from_moments(
    Mx1: float,
    My1: float,
    Mx_target: float,
    My_target: float,
    tiny: float,
) -> float | None:
    """Best-fit positive scale factor when axial load is ~0."""
    denom = Mx1 * Mx1 + My1 * My1
    if denom < tiny:
        return None
    s = (Mx1 * Mx_target + My1 * My_target) / denom
    return float(s)


def _moment_error(Mx: float, My: float, Mx_target: float, My_target: float) -> float:
    return float(np.hypot(Mx - Mx_target, My - My_target))


def _c_bounds(theta: float, bolts: np.ndarray, cells: np.ndarray, margin: float) -> tuple[float, float]:
    all_pts = np.vstack([bolts[:, :2], cells[:, :2]])
    projs = np.cos(theta) * all_pts[:, 0] + np.sin(theta) * all_pts[:, 1]
    return float(np.min(projs) - margin), float(np.max(projs) + margin)


def _bracket_root_for_S(
    theta: float,
    bolts: np.ndarray,
    cells: np.ndarray,
    c_min: float,
    c_max: float,
    n_samples: int,
    tiny: float,
) -> tuple[float, float] | None:
    """Find [c_low, c_high] where S(theta,c) changes sign (or hits ~0)."""
    cs = np.linspace(c_min, c_max, int(max(2, n_samples)), dtype=float)
    S_prev, *_ = _unit_forces_and_unit_moments(theta, float(cs[0]), bolts, cells)
    if abs(S_prev) < tiny:
        return float(cs[0]), float(cs[0])

    for i in range(1, cs.size):
        c_i = float(cs[i])
        S_i, *_ = _unit_forces_and_unit_moments(theta, c_i, bolts, cells)
        if abs(S_i) < tiny:
            return c_i, c_i
        if S_prev * S_i < 0.0:
            return float(cs[i - 1]), c_i
        S_prev = S_i
    return None


def _bisect_root_for_S(
    theta: float,
    bolts: np.ndarray,
    cells: np.ndarray,
    c_low: float,
    c_high: float,
    tiny: float,
    max_iter: int = 80,
) -> float:
    """Bisection solve for S(theta,c)=0 on a bracket [c_low,c_high]."""
    if c_low == c_high:
        return float(c_low)

    S_low, *_ = _unit_forces_and_unit_moments(theta, float(c_low), bolts, cells)
    S_high, *_ = _unit_forces_and_unit_moments(theta, float(c_high), bolts, cells)
    if abs(S_low) < tiny:
        return float(c_low)
    if abs(S_high) < tiny:
        return float(c_high)
    if S_low * S_high > 0.0:
        # not actually bracketed
        return float(0.5 * (c_low + c_high))

    lo = float(c_low)
    hi = float(c_high)
    for _ in range(int(max_iter)):
        mid = 0.5 * (lo + hi)
        S_mid, *_ = _unit_forces_and_unit_moments(theta, mid, bolts, cells)
        if abs(S_mid) < tiny:
            return float(mid)
        # keep the sub-interval that contains the sign change
        if S_low * S_mid <= 0.0:
            hi = mid
            S_high = S_mid
        else:
            lo = mid
            S_low = S_mid
    return float(0.5 * (lo + hi))

def solve_neutral_axis(
    bolts: np.ndarray,
    cells: np.ndarray,
    Fz: float,
    Mx: float,
    My: float,
    *,
    theta_steps: int = 180,
    c_steps: int = 220,
    margin: float = 10.0,
    tiny: float = 1e-9,
) -> tuple[float, float, float, np.ndarray, np.ndarray]:
    """
    Solve for (theta, c, s) where:
      d = cos(theta)*x + sin(theta)*y - c
      F = s*k*d with gating (bolts tension-only, cells compression-only)

    Returns:
      theta_best, c_best, s_best, b_f1_best, c_f1_best
    where b_f1_best and c_f1_best are the *unit-scale* forces (s=1) at the best NA.
    Final forces are s_best * b_f1_best and s_best * c_f1_best.
    
    Note: c_f1_best represents unit compressive forces (negative) on the cells.
    """
    # Degenerate: no targets at all
    if abs(Fz) < tiny and abs(Mx) < tiny and abs(My) < tiny:
        # choose arbitrary NA and zero scale
        theta0 = 0.0
        c0 = 0.0
        s0 = 0.0
        _, _, _, b_f1, c_f1 = _unit_forces_and_unit_moments(theta0, c0, bolts, cells)
        return theta0, c0, s0, b_f1, c_f1

    best_err = float("inf")
    best_secondary = float("inf")
    best_theta = None
    best_c = None
    best_s = None
    best_b_f1 = None
    best_c_f1 = None

    theta_search = np.linspace(0.0, 2.0 * np.pi, int(theta_steps), endpoint=False, dtype=float)

    for theta in theta_search:
        c_min, c_max = _c_bounds(theta, bolts, cells, margin=margin)




        # ------------------------------------------------------------
        # Branch A: Fz ~ 0 (pure bending): enforce S(theta,c)=0 first,
        # then scale from moments.
        # ------------------------------------------------------------
        if abs(Fz) < tiny:
            bracket = _bracket_root_for_S(
                theta, bolts, cells, c_min, c_max, n_samples=int(c_steps), tiny=tiny
            )
            if bracket is None:
                continue

            c_low, c_high = bracket
            c = _bisect_root_for_S(theta, bolts, cells, c_low, c_high, tiny=tiny)

            S, Mx1, My1, b_f1, c_f1 = _unit_forces_and_unit_moments(theta, c, bolts, cells)

            # Enforce axial equilibrium for pure bending (unit-scale net force ~ 0)
            if abs(S) > 1e-6:
                continue

            s = _scale_from_moments(Mx1, My1, Mx, My, tiny=tiny)
            if s is None or s < 0.0:
                continue

            Mx_s = s * Mx1
            My_s = s * My1
            err = _moment_error(Mx_s, My_s, Mx, My)

            # Secondary: prefer less compression "waste" + lower peak bolt
            bolt_forces = s * b_f1
            cell_forces = s * c_f1
            total_cell_comp = float(-np.sum(np.minimum(cell_forces, 0.0)))  # magnitude of compression
            max_bolt = float(np.max(bolt_forces)) if bolt_forces.size else 0.0
            secondary = total_cell_comp + 1e-6 * max_bolt

            if (err < best_err - 1e-12) or (abs(err - best_err) <= 1e-12 and secondary < best_secondary):
                best_err = err
                best_secondary = secondary
                best_theta, best_c, best_s = float(theta), float(c), float(s)
                best_b_f1, best_c_f1 = b_f1, c_f1

        # ------------------------------------------------------------
        # Branch B: Fz != 0: determine s from axial equilibrium (s=Fz/S),
        # then match moments.
        # ------------------------------------------------------------
        else:
            for c in np.linspace(c_min, c_max, int(c_steps), dtype=float):
                S, Mx1, My1, b_f1, c_f1 = _unit_forces_and_unit_moments(theta, float(c), bolts, cells)

                s = _scale_from_axial(Fz, S, tiny=tiny)
                if s is None or s < 0.0:
                    continue

                Mx_s = s * Mx1
                My_s = s * My1
                err = _moment_error(Mx_s, My_s, Mx, My)

                bolt_forces = s * b_f1
                cell_forces = s * c_f1
                total_cell_comp = float(-np.sum(np.minimum(cell_forces, 0.0)))
                max_bolt = float(np.max(bolt_forces)) if bolt_forces.size else 0.0
                secondary = total_cell_comp + 1e-6 * max_bolt

                if (err < best_err - 1e-12) or (abs(err - best_err) <= 1e-12 and secondary < best_secondary):
                    best_err = err
                    best_secondary = secondary
                    best_theta, best_c, best_s = float(theta), float(c), float(s)
                    best_b_f1, best_c_f1 = b_f1, c_f1

    if best_theta is None or best_b_f1 is None or best_c_f1 is None or best_s is None or best_c is None:
        raise ValueError("No equilibrium solution found. Check targets/stiffness/plate geometry.")

    return best_theta, best_c, best_s, best_b_f1, best_c_f1


def solve_bolt_tension(
    bolt_coords: np.ndarray,
    Fz: float,
    Mx: float,
    My: float,
    *,
    plate_bounds: tuple[float, float, float, float],
    bolt_ks: np.ndarray | None = None,
    theta_steps: int | None = 720,
    c_steps: int | None = 400,
    margin: float = 10.0,
    n_cells_x: int | None = 50,
    n_cells_y: int | None = 50,
    L_grip: float | None = None,
    tiny: float = 1e-9,
) -> np.ndarray:
    """
    Wrapper that:
      1) builds bolt and cell arrays
      2) solves neutral axis (theta,c,s)
      3) returns final bolt tensions (>=0)
    """
    bolt_coords_arr = np.asarray(bolt_coords, dtype=float)
    if bolt_coords_arr.ndim != 2 or bolt_coords_arr.shape[1] != 2:
        raise ValueError("bolt_coords must be an (N,2) array")

    n_bolts = int(bolt_coords_arr.shape[0])
    if n_bolts <= 0:
        raise ValueError("bolt_coords must contain at least one bolt")


    k_arr = np.asarray(bolt_ks, dtype=float)


    bolts = np.column_stack([bolt_coords_arr[:, 0], bolt_coords_arr[:, 1], k_arr])

    x_min, x_max, y_min, y_max = plate_bounds


    cells, _ = cells_from_rectangle(
        x_min=float(x_min),
        x_max=float(x_max),
        y_min=float(y_min),
        y_max=float(y_max),
        n_cells_x=n_cells_x,
        n_cells_y=n_cells_y,
        L_grip=L_grip,
    )

    if abs(Mx) < 1e-6 and abs(My) < 1e-6 and Fz > 0:
        w = k_arr / np.sum(k_arr)
        return np.maximum(0.0, Fz * w)


    theta, c, s, b_f1, _c_f1 = solve_neutral_axis(
        bolts,
        cells,
        Fz,
        Mx,
        My,
        theta_steps=theta_steps,
        c_steps=c_steps,
        margin=margin,
        tiny=tiny,
    )

    bolt_forces = s * b_f1
    return np.maximum(0.0, np.asarray(bolt_forces, dtype=float))




def main() -> None:
    np.set_printoptions(precision=6, suppress=True)

    bolt_coords = np.array(
        [
            [-50.0, -50.0],
            [ 50.0, -50.0],
            [ 50.0,  50.0],
            [-50.0,  50.0],
        ],
        dtype=float,
    )

    plate_bounds = (-100.0, 100.0, -100.0, 100.0)
    bolt_ks = np.ones(bolt_coords.shape[0], dtype=float)

    common_kwargs = dict(
        plate_bounds=plate_bounds,
        bolt_ks=bolt_ks,
        theta_steps=180,
        c_steps=180,
        n_cells_x=25,
        n_cells_y=25,
        margin=10.0,
        tiny=1e-9,
        L_grip=50.0, #mm
    )

    def run_case(name: str, Fz: float, Mx: float, My: float) -> None:
        tensions = solve_bolt_tension(bolt_coords, Fz, Mx, My, **common_kwargs)

        print(f"\n=== {name} ===")
        print(f"Target: Fz={Fz:.6g}, Mx={Mx:.6g}, My={My:.6g}")
        print("Bolt tensions:", tensions)
        print("Sum tension:", float(np.sum(tensions)))
        print("Min/Max:", float(np.min(tensions)), float(np.max(tensions)))

        # For pure axial tension, NA is not meaningful in this contact model.
        if abs(Mx) < 1e-6 and abs(My) < 1e-6 and Fz > 0:
            print("NA: (pure axial tension -> no-contact assumption; NA not solved)")
            print(f"Achieved: Fz={float(np.sum(tensions)):.6g}, Mx=0, My=0")
            return

        # Otherwise, compute NA + achieved actions for debugging
        bolt_coords_arr = np.asarray(bolt_coords, dtype=float)
        k_arr = np.asarray(common_kwargs["bolt_ks"], dtype=float)
        bolts = np.column_stack([bolt_coords_arr[:, 0], bolt_coords_arr[:, 1], k_arr])

        x_min, x_max, y_min, y_max = common_kwargs["plate_bounds"]
        cells, _ = cells_from_rectangle(
            x_min=float(x_min),
            x_max=float(x_max),
            y_min=float(y_min),
            y_max=float(y_max),
            n_cells_x=int(common_kwargs["n_cells_x"]),
            n_cells_y=int(common_kwargs["n_cells_y"]),
            L_grip=float(common_kwargs["L_grip"]),
        )

        theta, c, s, b_f1, c_f1 = solve_neutral_axis(
            bolts,
            cells,
            Fz,
            Mx,
            My,
            theta_steps=int(common_kwargs["theta_steps"]),
            c_steps=int(common_kwargs["c_steps"]),
            margin=float(common_kwargs["margin"]),
            tiny=float(common_kwargs["tiny"]),
        )

        P_ach = float(s * (np.sum(b_f1) + np.sum(c_f1)))
        Mx_ach = float(s * (np.sum(b_f1 * bolts[:, 1]) + np.sum(c_f1 * cells[:, 1])))
        My_ach = float(s * (np.sum(b_f1 * (-bolts[:, 0])) + np.sum(c_f1 * (-cells[:, 0]))))

        print(f"NA: theta={theta:.6f} rad ({np.rad2deg(theta):.3f} deg), c={c:.6f}, s={s:.6g}")
        print(f"Achieved: Fz={P_ach:.6g}, Mx={Mx_ach:.6g}, My={My_ach:.6g}")


    run_case("Case 1: Pure axial tension", Fz=100.0, Mx=0.0, My=0.0)
    run_case("Case 2: Pure Mx", Fz=0.0, Mx=5000.0, My=0.0)
    run_case("Case 3: Pure My", Fz=0.0, Mx=0.0, My=5000.0)
    run_case("Case 4: Combined", Fz=200.0, Mx=3000.0, My=-1500.0)
    run_case("Case 5: Combined flipped", Fz=200.0, Mx=-3000.0, My=1500.0)

    print("\nDone.")


if __name__ == "__main__":
    main()
