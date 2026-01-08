"""ICR (instantaneous center of rotation) in-plane shear distribution for bolt groups."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

import numpy as np

from ..bolt import BoltGroup
from ..load import Load
from .elastic import solve_elastic_shear

Point2D = tuple[float, float]

# Numerical tolerances
ZERO_TOLERANCE = 1e-12
POSITION_TOLERANCE = 1e-9


@dataclass
class ICRSearchConfig:
    """Configuration for ICR search algorithm."""
    max_iterations: int = 100
    tolerance: float = 1e-6
    min_candidates: int = 60
    refine_bisection: bool = True
    bisection_iterations: int = 20


@dataclass
class CrawfordKulakParams:
    """Parameters for Crawford-Kulak bolt load-deformation model."""
    mu: float = 10.0
    lambda_exp: float = 0.55
    delta_max: float = 8.64


def calculate_perpendicular_direction(
    Fy: float, Fz: float
) -> tuple[float, float]:
    """Calculate unit vector perpendicular to applied load direction."""
    P = math.hypot(Fy, Fz)

    if P < ZERO_TOLERANCE:
        # No shear - default perpendicular direction
        return (1.0, 0.0)

    # Load direction
    load_y = Fy / P
    load_z = Fz / P

    # Perpendicular (rotate 90° CCW)
    return (-load_z, load_y)


def calculate_search_bounds(
    positions_y: np.ndarray,
    positions_z: np.ndarray,
    eccentricity: float,
    characteristic_size: float = 1.0,
) -> tuple[float, float]:
    """Calculate search bounds for ICR distance from centroid."""
    # Characteristic length from geometry extent
    span_y = float(np.ptp(positions_y)) if len(positions_y) > 1 else 0.0
    span_z = float(np.ptp(positions_z)) if len(positions_z) > 1 else 0.0

    char_length = max(span_y, span_z, characteristic_size * 2, 1.0)

    # Search bounds
    dist_min = max(POSITION_TOLERANCE, 0.02 * char_length, 0.1 * characteristic_size)
    dist_max = max(dist_min * 50.0, 10.0 * char_length, 5.0 * eccentricity)

    # Ensure valid range
    if dist_max <= dist_min:
        dist_max = dist_min * 10.0

    return (dist_min, dist_max)


def crawford_kulak_force(
    delta: np.ndarray,
    R_ult: float,
    params: CrawfordKulakParams | None = None,
) -> np.ndarray:
    """Crawford-Kulak load-deformation model for bolts."""
    if params is None:
        params = CrawfordKulakParams()

    rho = np.clip(delta / params.delta_max, 1e-6, 1.0)
    return R_ult * np.power(1.0 - np.exp(-params.mu * rho), params.lambda_exp)


def find_icr_distance(
    evaluate_fn: Callable[[float], tuple[float, dict] | None],
    target_ratio: float,
    dist_min: float,
    dist_max: float,
    eccentricity: float,
    config: ICRSearchConfig | None = None,
) -> tuple[float, dict, float] | None:
    """Find ICR distance that satisfies moment-shear equilibrium."""
    if config is None:
        config = ICRSearchConfig()

    ratio_tolerance = config.tolerance * max(1.0, abs(target_ratio))

    # Generate candidate distances (log spacing)
    n_candidates = min(config.min_candidates, config.max_iterations * 2)
    candidates = np.geomspace(dist_min, dist_max, num=n_candidates)

    # Include eccentricity as a candidate (often close to solution)
    if eccentricity > dist_min:
        candidates = np.sort(np.unique(np.append(candidates, eccentricity)))

    # Phase 1: Coarse search
    best_result: dict | None = None
    best_distance = 0.0
    best_error = float("inf")

    # Track for bracketing
    prev_ratio: float | None = None
    prev_dist: float | None = None
    bracket: tuple[float, float] | None = None

    for dist in candidates:
        eval_result = evaluate_fn(float(dist))
        if eval_result is None:
            continue

        ratio, data = eval_result
        error = abs(ratio - target_ratio)

        # Check for bracket (sign change)
        if prev_ratio is not None and prev_dist is not None:
            if (ratio - target_ratio) * (prev_ratio - target_ratio) < 0:
                bracket = (prev_dist, float(dist))

        prev_ratio = ratio
        prev_dist = float(dist)

        # Track best
        if error < best_error:
            best_error = error
            best_result = data
            best_distance = float(dist)

        # Early termination if converged
        if error <= ratio_tolerance:
            return (float(dist), data, error)

    # Phase 2: Bisection refinement if bracket found
    if config.refine_bisection and bracket is not None:
        d_lo, d_hi = bracket

        for _ in range(config.bisection_iterations):
            d_mid = (d_lo + d_hi) / 2
            eval_result = evaluate_fn(d_mid)

            if eval_result is None:
                break

            ratio, data = eval_result
            error = abs(ratio - target_ratio)

            if error < best_error:
                best_error = error
                best_result = data
                best_distance = d_mid

            if error <= ratio_tolerance:
                return (d_mid, data, error)

            # Update bracket
            eval_lo = evaluate_fn(d_lo)
            if eval_lo is not None:
                ratio_lo = eval_lo[0]
                if (ratio - target_ratio) * (ratio_lo - target_ratio) < 0:
                    d_hi = d_mid
                else:
                    d_lo = d_mid
            else:
                break

    if best_result is not None:
        return (best_distance, best_result, best_error)

    return None


def solve_icr_shear(
    *, layout: BoltGroup, bolt_diameter: float, load: Load
) -> tuple[list[float], list[float], Point2D | None]:
    """Return per-bolt in-plane shear forces using the ICR method."""
    props = layout._calculate_properties()
    Cy = props.Cy
    Cz = props.Cz

    Mx_total, _, _ = load.get_moments_about(0.0, Cy, Cz)
    Fy_app = load.Fy
    Fz_app = load.Fz
    Mx_app = float(Mx_total)

    P_total = math.hypot(Fy_app, Fz_app)
    if P_total < ZERO_TOLERANCE or abs(Mx_app) < ZERO_TOLERANCE:
        fys, fzs = solve_elastic_shear(
            layout=layout, bolt_diameter=float(bolt_diameter), load=load
        )
        return fys, fzs, None

    y_arr = np.array([p[0] for p in layout.points], dtype=float)
    z_arr = np.array([p[1] for p in layout.points], dtype=float)

    R_ult = 100.0
    ck_params = CrawfordKulakParams()

    perp_y, perp_z = calculate_perpendicular_direction(Fy_app, Fz_app)
    eccentricity = abs(Mx_app) / P_total
    moment_sign = -1.0 if Mx_app > 0.0 else 1.0
    target_ratio = Mx_app / P_total

    dist_min, dist_max = calculate_search_bounds(
        y_arr,
        z_arr,
        eccentricity,
        characteristic_size=float(bolt_diameter),
    )

    def evaluate_icr(icr_dist: float) -> tuple[float, dict] | None:
        icr_y = Cy + moment_sign * perp_y * icr_dist
        icr_z = Cz + moment_sign * perp_z * icr_dist

        dy_arr = y_arr - icr_y
        dz_arr = z_arr - icr_z
        r_arr = np.sqrt(dy_arr**2 + dz_arr**2)

        if np.any(r_arr < POSITION_TOLERANCE):
            return None

        max_r = float(np.max(r_arr))
        if max_r < POSITION_TOLERANCE:
            return None

        deformation_arr = r_arr / max_r
        R_arr = np.array(
            [
                crawford_kulak_force(delta, R_ult, ck_params)
                for delta in deformation_arr
            ],
            dtype=float,
        )

        # Direction vector perpendicular to radius (CCW if moment_sign is -1? Wait)
        # We want direction to match Mx sign.
        # If Mx > 0 (CCW), we want CCW forces: (dz, -dy)
        # If Mx < 0 (CW), we want CW forces: (-dz, dy)
        sign = 1.0 if Mx_app >= 0.0 else -1.0

        dir_y = sign * dz_arr / r_arr
        dir_z = -sign * dy_arr / r_arr

        Fy_arr = R_arr * dir_y
        Fz_arr = R_arr * dir_z

        P_y = float(np.sum(Fy_arr))
        P_z = float(np.sum(Fz_arr))
        P_base = math.hypot(P_y, P_z)
        if P_base < ZERO_TOLERANCE:
            return None

        M_base = float(np.sum(Fy_arr * dz_arr - Fz_arr * dy_arr))
        ratio = M_base / P_base

        return (
            ratio,
            {
                "R_arr": R_arr,
                "dir_y": dir_y,
                "dir_z": dir_z,
                "P_base": P_base,
                "icr_y": icr_y,
                "icr_z": icr_z,
            },
        )

    config = ICRSearchConfig(max_iterations=100, tolerance=1e-6, refine_bisection=True)
    result = find_icr_distance(
        evaluate_icr, target_ratio, dist_min, dist_max, eccentricity, config
    )
    if result is None:
        fys, fzs = solve_elastic_shear(
            layout=layout, bolt_diameter=float(bolt_diameter), load=load
        )
        return fys, fzs, None

    _, best_data, _ = result
    P_base = float(best_data["P_base"])
    if P_base < POSITION_TOLERANCE:
        fys, fzs = solve_elastic_shear(
            layout=layout, bolt_diameter=float(bolt_diameter), load=load
        )
        return fys, fzs, None

    scale = P_total / P_base
    R_arr = best_data["R_arr"] * scale
    dir_y_arr = best_data["dir_y"]
    dir_z_arr = best_data["dir_z"]

    Fys = []
    Fzs = []
    for idx, (y, z) in enumerate(layout.points):
        R = float(R_arr[idx])
        Fys.append(R * float(dir_y_arr[idx]))
        Fzs.append(R * float(dir_z_arr[idx]))

    icr_point: Point2D = (float(best_data["icr_y"]), float(best_data["icr_z"]))
    return Fys, Fzs, icr_point
