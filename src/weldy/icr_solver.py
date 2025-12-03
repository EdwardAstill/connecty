"""
Common ICR (Instantaneous Center of Rotation) solver framework.

Provides shared infrastructure for ICR analysis of welds and bolts,
with pluggable load-deformation models.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Tuple, Callable, TypeVar, Generic
import math
import numpy as np

# Type aliases
Point = Tuple[float, float]

# Numerical tolerances (consistent across all solvers)
ZERO_TOLERANCE = 1e-12  # For checking near-zero values
POSITION_TOLERANCE = 1e-9  # For position/distance checks


@dataclass
class ICRSearchConfig:
    """Configuration for ICR search algorithm."""
    max_iterations: int = 100
    tolerance: float = 1e-6
    min_candidates: int = 60
    refine_bisection: bool = True
    bisection_iterations: int = 20


@dataclass  
class ICRSolution:
    """Result from ICR solver."""
    icr_y: float
    icr_z: float
    icr_distance: float
    converged: bool
    error: float
    iterations: int


def calculate_perpendicular_direction(
    Fy: float,
    Fz: float
) -> Tuple[float, float]:
    """
    Calculate unit vector perpendicular to applied load direction.
    
    The ICR lies along a line perpendicular to the resultant shear,
    passing through the centroid.
    
    Args:
        Fy: Force in y-direction
        Fz: Force in z-direction
        
    Returns:
        (perp_y, perp_z) unit vector perpendicular to load
    """
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
    characteristic_size: float = 1.0
) -> Tuple[float, float]:
    """
    Calculate search bounds for ICR distance from centroid.
    
    Args:
        positions_y: Array of y-coordinates
        positions_z: Array of z-coordinates
        eccentricity: Approximate eccentricity |M/P|
        characteristic_size: Characteristic dimension (weld leg, bolt diameter, etc.)
        
    Returns:
        (dist_min, dist_max) search bounds
    """
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


def find_icr_distance(
    evaluate_fn: Callable[[float], Tuple[float, dict] | None],
    target_ratio: float,
    dist_min: float,
    dist_max: float,
    eccentricity: float,
    config: ICRSearchConfig = ICRSearchConfig()
) -> Tuple[float, dict, float] | None:
    """
    Find ICR distance that satisfies moment-shear equilibrium.
    
    Uses a two-phase approach:
    1. Coarse search with logarithmic spacing to find bracket
    2. Bisection refinement within bracket
    
    Args:
        evaluate_fn: Function(distance) -> (ratio, data_dict) or None
        target_ratio: Target moment/shear ratio (-Mx/P)
        dist_min: Minimum search distance
        dist_max: Maximum search distance  
        eccentricity: Approximate eccentricity for seeding
        config: Search configuration
        
    Returns:
        (best_distance, best_data, error) or None if no solution found
    """
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
    bracket: Tuple[float, float] | None = None
    
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


def compute_torsional_forces(
    positions_y: np.ndarray,
    positions_z: np.ndarray,
    centroid_y: float,
    centroid_z: float,
    icr_y: float,
    icr_z: float,
    force_magnitudes: np.ndarray
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute force components and directions for elements rotating about ICR.
    
    Each element's force acts perpendicular to the radius from ICR.
    
    Args:
        positions_y: Element y-coordinates
        positions_z: Element z-coordinates
        centroid_y: Group centroid y
        centroid_z: Group centroid z
        icr_y: ICR y-coordinate
        icr_z: ICR z-coordinate
        force_magnitudes: Force/stress magnitude at each element
        
    Returns:
        (Fy_arr, Fz_arr, dir_y_arr, dir_z_arr)
    """
    # Distance from each element to ICR
    dy_icr = positions_y - icr_y
    dz_icr = positions_z - icr_z
    c_arr = np.hypot(dy_icr, dz_icr)
    c_arr = np.where(c_arr < POSITION_TOLERANCE, POSITION_TOLERANCE, c_arr)
    
    # Force direction perpendicular to radius (CCW rotation)
    dir_y = -dz_icr / c_arr
    dir_z = dy_icr / c_arr
    
    # Force components
    Fy_arr = force_magnitudes * dir_y
    Fz_arr = force_magnitudes * dir_z
    
    return (Fy_arr, Fz_arr, dir_y, dir_z)


def compute_equilibrium_ratio(
    positions_y: np.ndarray,
    positions_z: np.ndarray,
    centroid_y: float,
    centroid_z: float,
    Fy_arr: np.ndarray,
    Fz_arr: np.ndarray,
    applied_Fy: float,
    applied_Fz: float
) -> Tuple[float, float, float, bool]:
    """
    Compute moment-to-shear ratio and check direction.
    
    Args:
        positions_y: Element y-coordinates
        positions_z: Element z-coordinates
        centroid_y: Group centroid y
        centroid_z: Group centroid z
        Fy_arr: y-component of forces
        Fz_arr: z-component of forces
        applied_Fy: Applied force y-component
        applied_Fz: Applied force z-component
        
    Returns:
        (ratio, sum_P, sum_M, direction_flipped)
    """
    sum_Fy = float(np.sum(Fy_arr))
    sum_Fz = float(np.sum(Fz_arr))
    
    # Check if direction matches applied load
    dot = applied_Fy * sum_Fy + applied_Fz * sum_Fz
    flipped = dot < 0
    
    if flipped:
        sum_Fy = -sum_Fy
        sum_Fz = -sum_Fz
    
    P_total = math.hypot(sum_Fy, sum_Fz)
    
    if P_total < ZERO_TOLERANCE:
        return (0.0, 0.0, 0.0, flipped)
    
    # Sum moments about centroid
    dy_cent = positions_y - centroid_y
    dz_cent = positions_z - centroid_z
    
    if flipped:
        sum_M = float(np.sum(dy_cent * (-Fz_arr) - dz_cent * (-Fy_arr)))
    else:
        sum_M = float(np.sum(dy_cent * Fz_arr - dz_cent * Fy_arr))
    
    ratio = sum_M / P_total
    
    return (ratio, P_total, sum_M, flipped)


# ============================================================================
# Load-Deformation Models
# ============================================================================

@dataclass
class CrawfordKulakParams:
    """Parameters for Crawford-Kulak bolt load-deformation model."""
    mu: float = 10.0  # Curve shape parameter
    lambda_exp: float = 0.55  # Curve shape exponent
    delta_max: float = 8.64  # Ultimate deformation (mm)


def crawford_kulak_force(
    delta: np.ndarray,
    R_ult: float,
    params: CrawfordKulakParams = CrawfordKulakParams()
) -> np.ndarray:
    """
    Crawford-Kulak load-deformation model for bolts.
    
    R = R_ult × (1 - e^(-μΔ/Δ_max))^λ
    
    Args:
        delta: Deformation at each bolt (mm)
        R_ult: Ultimate bolt capacity (kN)
        params: Model parameters
        
    Returns:
        Force at each bolt (kN)
    """
    rho = np.clip(delta / params.delta_max, 1e-6, 1.0)
    return R_ult * np.power(1.0 - np.exp(-params.mu * rho), params.lambda_exp)


@dataclass
class AISCWeldParams:
    """Parameters for AISC fillet weld load-deformation model."""
    leg: float  # Weld leg size (mm)
    throat: float  # Effective throat (mm)
    F_EXX: float  # Electrode strength (MPa)


def aisc_weld_deformation_limits(
    theta: np.ndarray,
    leg: float
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Calculate angle-dependent deformation limits per AISC.
    
    Args:
        theta: Load angle relative to weld axis (degrees)
        leg: Weld leg size (mm)
        
    Returns:
        (delta_u, delta_m) - ultimate and maximum deformation
    """
    delta_u = np.minimum(
        0.17 * leg,
        1.087 * np.power(theta + 6.0, -0.65) * leg
    )
    delta_m = 0.209 * np.power(theta + 2.0, -0.32) * leg
    
    return (delta_u, delta_m)


def aisc_weld_strength_factor(theta: np.ndarray) -> np.ndarray:
    """
    Calculate directional strength factor for fillet welds.
    
    Factor = 1.0 + 0.5 × sin^1.5(θ)
    
    Args:
        theta: Load angle relative to weld axis (degrees)
        
    Returns:
        Strength factor at each point
    """
    sin_term = np.power(np.sin(np.radians(theta)), 1.5)
    return 1.0 + 0.5 * sin_term


def aisc_weld_stress(
    delta: np.ndarray,
    delta_m: np.ndarray,
    delta_u: np.ndarray,
    theta: np.ndarray,
    F_EXX: float
) -> np.ndarray:
    """
    AISC fillet weld stress from deformation.
    
    f_w = 0.60 × F_EXX × (1 + 0.5 sin^1.5 θ) × [p(1.9 - 0.9p)]^0.3
    
    where p = Δ/Δ_m (normalized deformation ratio)
    
    Args:
        delta: Deformation at each point (mm)
        delta_m: Maximum deformation at each point (mm)
        delta_u: Ultimate deformation at each point (mm)
        theta: Load angle at each point (degrees)
        F_EXX: Electrode tensile strength (MPa)
        
    Returns:
        Stress at each point (MPa)
    """
    # Clamp deformation to ultimate
    delta_clamped = np.minimum(delta, delta_u)
    
    # Normalized deformation ratio
    p_arr = np.clip(delta_clamped / delta_m, 1e-6, 2.1)
    
    # Strength factor (angle-dependent)
    strength_factor = 0.60 * F_EXX * aisc_weld_strength_factor(theta)
    
    # Deformation factor
    deform_term = np.clip(p_arr * (1.9 - 0.9 * p_arr), 1e-6, None)
    deform_factor = np.power(deform_term, 0.3)
    
    return strength_factor * deform_factor

