"""ICR (instantaneous center of rotation) in-plane shear distribution for bolt groups."""

from __future__ import annotations

import math

import numpy as np

from ..geometry import BoltLayout, Point2D
from ..results import BoltForce
from ...common.icr_solver import (
    ZERO_TOLERANCE,
    POSITION_TOLERANCE,
    ICRSearchConfig,
    CrawfordKulakParams,
    calculate_perpendicular_direction,
    calculate_search_bounds,
    find_icr_distance,
    crawford_kulak_force,
)
from ...common.load import Load
from .elastic import solve_elastic_shear


def solve_icr_shear(
    *, layout: BoltLayout, bolt_diameter: float, load: Load
) -> tuple[list[BoltForce], Point2D | None]:
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
        return solve_elastic_shear(layout=layout, bolt_diameter=float(bolt_diameter), load=load), None

    y_arr = np.array([p[0] for p in layout.points], dtype=float)
    z_arr = np.array([p[1] for p in layout.points], dtype=float)

    R_ult = 100.0
    ck_params = CrawfordKulakParams()

    perp_y, perp_z = calculate_perpendicular_direction(Fy_app, Fz_app)
    eccentricity = abs(Mx_app) / P_total
    moment_sign = -1.0 if Mx_app > 0.0 else 1.0
    target_ratio = -Mx_app / P_total

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
        R_arr = np.array([crawford_kulak_force(delta, R_ult, ck_params) for delta in deformation_arr], dtype=float)

        dir_y = -dz_arr / r_arr
        dir_z = dy_arr / r_arr

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
    result = find_icr_distance(evaluate_icr, target_ratio, dist_min, dist_max, eccentricity, config)
    if result is None:
        return solve_elastic_shear(layout=layout, bolt_diameter=float(bolt_diameter), load=load), None

    _, best_data, _ = result
    P_base = float(best_data["P_base"])
    if P_base < POSITION_TOLERANCE:
        return solve_elastic_shear(layout=layout, bolt_diameter=float(bolt_diameter), load=load), None

    scale = P_total / P_base
    R_arr = best_data["R_arr"] * scale
    dir_y_arr = best_data["dir_y"]
    dir_z_arr = best_data["dir_z"]

    bolt_results: list[BoltForce] = []
    for idx, (y, z) in enumerate(layout.points):
        R = float(R_arr[idx])
        bolt_results.append(
            BoltForce(
                point=(y, z),
                Fy=R * float(dir_y_arr[idx]),
                Fz=R * float(dir_z_arr[idx]),
                Fx=0.0,
                diameter=float(bolt_diameter),
            )
        )

    icr_point: Point2D = (float(best_data["icr_y"]), float(best_data["icr_z"]))
    return bolt_results, icr_point


