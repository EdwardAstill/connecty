"""
Bolt force calculation using Elastic and ICR methods.

Elastic Method (AISC permitted, conservative):
- Direct shear: R_p = P / n (uniform distribution)
- Moment shear: R_m = M × r / J (perpendicular to radius, linear with distance)
- Vector sum of components

ICR Method (AISC preferred for eccentrically loaded bolt groups):
- Iterative solution finding instantaneous center of rotation
- Uses non-linear load-deformation curves per Crawford-Kulak
- Accounts for ductile redistribution of bolt forces
"""
from __future__ import annotations
from typing import List, Tuple, TYPE_CHECKING
import math
import numpy as np

from .icr_solver import (
    ZERO_TOLERANCE,
    POSITION_TOLERANCE,
    ICRSearchConfig,
    CrawfordKulakParams,
    calculate_perpendicular_direction,
    calculate_search_bounds,
    find_icr_distance,
    crawford_kulak_force,
)

if TYPE_CHECKING:
    from .bolt import BoltGroup, BoltResult, BoltForce
    from .force import Force

# Type alias
Point = Tuple[float, float]


def calculate_elastic_bolt_force(
    bolt_group: BoltGroup,
    force: Force
) -> BoltResult:
    """
    Calculate bolt forces using the Elastic Method.
    
    Per AISC Manual Part 7, the elastic method:
    1. Direct shear: R_p = P / n (uniform, all bolts share equally)
    2. Moment shear: R_m = M × r / Σr² (perpendicular to radius, proportional to distance)
    3. Vector sum for resultant
    
    Args:
        bolt_group: BoltGroup object
        force: Applied Force
        
    Returns:
        BoltResult with force at each bolt
    """
    from .bolt import BoltForce, BoltResult
    
    props = bolt_group._calculate_properties()
    
    n = props.n
    Cy, Cz = props.Cy, props.Cz
    Ip = props.Ip
    
    # Get total moment about bolt group centroid (in-plane torsion)
    Mx_total, _, _ = force.get_moments_about(Cy, Cz)
    
    # Convert forces to kN (input is in N)
    Fy_kN = force.Fy / 1000
    Fz_kN = force.Fz / 1000
    Mx_kNmm = Mx_total / 1000  # N·mm to kN·mm
    
    bolt_forces: List[BoltForce] = []
    
    for (y, z) in bolt_group.positions:
        # Distance from centroid
        dy = y - Cy
        dz = z - Cz
        
        # Direct shear (uniform): R = P / n
        R_direct_y = Fy_kN / n if n > 0 else 0.0
        R_direct_z = Fz_kN / n if n > 0 else 0.0
        
        # Moment shear (perpendicular to radius, linear with distance)
        # R_m = M × r / Σr², direction perpendicular to (dy, dz)
        # Perpendicular direction (CCW): (-dz, dy)
        R_moment_y = 0.0
        R_moment_z = 0.0
        
        if Ip > ZERO_TOLERANCE:
            # r_y = -M × dz / Ip (y-component, perpendicular)
            # r_z = M × dy / Ip (z-component, perpendicular)
            R_moment_y = -Mx_kNmm * dz / Ip
            R_moment_z = Mx_kNmm * dy / Ip
        
        # Total force on bolt
        total_Fy = R_direct_y + R_moment_y
        total_Fz = R_direct_z + R_moment_z
        
        bolt_forces.append(BoltForce(
            point=(y, z),
            Fy=total_Fy,
            Fz=total_Fz
        ))
    
    return BoltResult(
        bolt_group=bolt_group,
        force=force,
        method="elastic",
        bolt_forces=bolt_forces
    )


def calculate_icr_bolt_force(
    bolt_group: BoltGroup,
    force: Force,
    max_iterations: int = 100,
    tolerance: float = 1e-6
) -> BoltResult:
    """
    Calculate bolt forces using the Instantaneous Center of Rotation (ICR) method.
    
    Per AISC Manual Part 7, the ICR method:
    1. Iteratively finds the center of rotation
    2. Bolt deformation is proportional to distance from ICR
    3. Uses non-linear load-deformation curve: R = R_ult (1 - e^(-μΔ))^λ
    
    The Crawford-Kulak model parameters:
    - μ = 10 (curve shape parameter)
    - λ = 0.55 (curve shape parameter)
    - Δ_max = 0.34 in = 8.64 mm (ultimate deformation for A325/A490)
    
    Args:
        bolt_group: BoltGroup object
        force: Applied Force
        max_iterations: Maximum solver iterations
        tolerance: Convergence tolerance
        
    Returns:
        BoltResult with ICR-specific data
    """
    from .bolt import BoltForce, BoltResult
    
    props = bolt_group._calculate_properties()
    
    Cy, Cz = props.Cy, props.Cz
    
    # Get applied loads (convert to kN)
    Mx_total, _, _ = force.get_moments_about(Cy, Cz)
    Fy_app = force.Fy / 1000  # kN
    Fz_app = force.Fz / 1000  # kN
    Mx_app = Mx_total / 1000  # kN·mm
    
    # Total in-plane shear
    P_total = math.hypot(Fy_app, Fz_app)
    
    # If no moment or no shear, fall back to elastic
    if P_total < ZERO_TOLERANCE or abs(Mx_app) < ZERO_TOLERANCE:
        return calculate_elastic_bolt_force(bolt_group, force)
    
    # Prepare bolt data
    y_arr = np.array([p[0] for p in bolt_group.positions], dtype=float)
    z_arr = np.array([p[1] for p in bolt_group.positions], dtype=float)
    
    # Bolt ultimate capacity (kN) - nominal, without phi factor
    R_ult = bolt_group.parameters.capacity / bolt_group.parameters.phi
    
    # Crawford-Kulak parameters
    ck_params = CrawfordKulakParams()
    
    # ICR search setup
    perp_y, perp_z = calculate_perpendicular_direction(Fy_app, Fz_app)
    eccentricity = abs(Mx_app) / P_total
    moment_sign = -1.0 if Mx_app > 0 else 1.0
    target_ratio = -Mx_app / P_total
    
    dist_min, dist_max = calculate_search_bounds(
        y_arr, z_arr, eccentricity,
        characteristic_size=bolt_group.parameters.diameter
    )
    
    def evaluate_icr(icr_dist: float) -> Tuple[float, dict] | None:
        """Evaluate ICR solution for a given distance from centroid."""
        icr_offset = moment_sign * icr_dist
        icr_y = Cy + perp_y * icr_offset
        icr_z = Cz + perp_z * icr_offset
        
        # Distance from each bolt to ICR
        dy_icr = y_arr - icr_y
        dz_icr = z_arr - icr_z
        c_arr = np.hypot(dy_icr, dz_icr)
        c_arr = np.where(c_arr < POSITION_TOLERANCE, POSITION_TOLERANCE, c_arr)
        
        # Maximum distance determines reference deformation
        c_max = float(np.max(c_arr))
        if c_max < POSITION_TOLERANCE:
            return None
        
        # Deformation proportional to distance from ICR
        # Critical bolt (farthest) is at ultimate deformation
        delta_arr = ck_params.delta_max * c_arr / c_max
        
        # Load-deformation curve
        R_arr = crawford_kulak_force(delta_arr, R_ult, ck_params)
        
        # Force direction perpendicular to radius from ICR (CCW)
        dir_y = -dz_icr / c_arr
        dir_z = dy_icr / c_arr
        
        # Sum forces
        R_y_arr = R_arr * dir_y
        R_z_arr = R_arr * dir_z
        
        sum_Fy = float(np.sum(R_y_arr))
        sum_Fz = float(np.sum(R_z_arr))
        
        # Check direction matches applied load
        dot = Fy_app * sum_Fy + Fz_app * sum_Fz
        if dot < 0:
            # Flip direction
            R_y_arr = -R_y_arr
            R_z_arr = -R_z_arr
            dir_y = -dir_y
            dir_z = -dir_z
            sum_Fy = -sum_Fy
            sum_Fz = -sum_Fz
        
        P_base = math.hypot(sum_Fy, sum_Fz)
        if P_base < POSITION_TOLERANCE:
            return None
        
        # Sum moments about centroid
        dy_cent = y_arr - Cy
        dz_cent = z_arr - Cz
        sum_M = float(np.sum(dy_cent * R_z_arr - dz_cent * R_y_arr))
        
        ratio = sum_M / P_base
        
        return ratio, {
            "icr_y": icr_y,
            "icr_z": icr_z,
            "R_arr": R_arr,
            "dir_y": dir_y,
            "dir_z": dir_z,
            "P_base": P_base
        }
    
    # Run ICR search
    config = ICRSearchConfig(
        max_iterations=max_iterations,
        tolerance=tolerance,
        refine_bisection=True
    )
    
    result = find_icr_distance(
        evaluate_icr,
        target_ratio,
        dist_min,
        dist_max,
        eccentricity,
        config
    )
    
    if result is None:
        # Fall back to elastic method
        return calculate_elastic_bolt_force(bolt_group, force)
    
    best_distance, best_data, _ = result
    
    # Scale forces to match applied load
    P_base = float(best_data["P_base"])
    if P_base < POSITION_TOLERANCE:
        return calculate_elastic_bolt_force(bolt_group, force)
    
    scale = P_total / P_base
    
    R_arr = best_data["R_arr"] * scale
    dir_y_arr = best_data["dir_y"]
    dir_z_arr = best_data["dir_z"]
    
    bolt_forces: List[BoltForce] = []
    
    for idx, (y, z) in enumerate(bolt_group.positions):
        R = float(R_arr[idx])
        
        bolt_forces.append(BoltForce(
            point=(y, z),
            Fy=R * float(dir_y_arr[idx]),
            Fz=R * float(dir_z_arr[idx])
        ))
    
    icr_point = (float(best_data["icr_y"]), float(best_data["icr_z"]))
    
    return BoltResult(
        bolt_group=bolt_group,
        force=force,
        method="icr",
        bolt_forces=bolt_forces,
        icr_point=icr_point
    )
