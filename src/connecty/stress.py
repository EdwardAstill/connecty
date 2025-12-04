"""
Weld stress calculation using Elastic and ICR methods.

Elastic Method (AISC permitted, conservative):
- Direct shear: r_p = P / L (force per unit length, uniform)
- Moment shear: r_m = M × c / I_p (perpendicular to radius, linear)
- Vector sum of components

ICR Method (AISC preferred for fillet welds):
- Iterative solution finding instantaneous center of rotation
- Accounts for load angle benefit: (1.0 + 0.5 sin^1.5 θ)
- Uses curved load-deformation relationship
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, TYPE_CHECKING
import math
import numpy as np

from .icr_solver import (
    ZERO_TOLERANCE,
    POSITION_TOLERANCE,
    ICRSearchConfig,
    calculate_perpendicular_direction,
    calculate_search_bounds,
    find_icr_distance,
    aisc_weld_deformation_limits,
    aisc_weld_stress,
    aisc_weld_strength_factor,
)

if TYPE_CHECKING:
    from .weld import Weld
    from .force import Force

# Type alias
Point = Tuple[float, float]


@dataclass
class StressComponents:
    """
    Stress components at a single point on the weld.
    
    All values are force per unit area (stress).
    
    In-plane stresses (y-z plane):
        f_direct_y, f_direct_z: From direct shear forces Fy, Fz
        f_moment_y, f_moment_z: From in-plane moment Mx (torsion)
    
    Out-of-plane stresses:
        f_axial: From axial force Fx
        f_bending: From bending moments My, Mz
    """
    f_direct_y: float = 0.0
    f_direct_z: float = 0.0
    f_moment_y: float = 0.0
    f_moment_z: float = 0.0
    f_axial: float = 0.0
    f_bending: float = 0.0
    
    @property
    def total_y(self) -> float:
        """Total in-plane stress in y-direction."""
        return self.f_direct_y + self.f_moment_y
    
    @property
    def total_z(self) -> float:
        """Total in-plane stress in z-direction."""
        return self.f_direct_z + self.f_moment_z
    
    @property
    def total_axial(self) -> float:
        """Total out-of-plane (axial) stress."""
        return self.f_axial + self.f_bending
    
    @property
    def shear_resultant(self) -> float:
        """Resultant in-plane shear stress."""
        return math.sqrt(self.total_y**2 + self.total_z**2)
    
    @property
    def resultant(self) -> float:
        """Total resultant stress magnitude."""
        return math.sqrt(
            self.total_axial**2 +
            self.total_y**2 +
            self.total_z**2
        )


@dataclass
class PointStress:
    """
    Stress result at a specific point on the weld.
    """
    point: Point
    components: StressComponents
    segment: object | None = None
    
    @property
    def y(self) -> float:
        """Y-coordinate of point."""
        return self.point[0]
    
    @property
    def z(self) -> float:
        """Z-coordinate of point."""
        return self.point[1]
    
    @property
    def stress(self) -> float:
        """Resultant stress magnitude."""
        return self.components.resultant


@dataclass
class StressResult:
    """
    Complete stress analysis result for a weld group.
    
    Follows beamy's Result pattern for convenient access.
    """
    weld: Weld
    force: Force
    method: str
    point_stresses: List[PointStress] = field(default_factory=list)
    
    # ICR-specific results
    icr_point: Point | None = None
    rotation: float | None = None
    
    # Cached values
    _stresses: np.ndarray | None = field(default=None, repr=False)
    
    def _get_stresses(self) -> np.ndarray:
        """Get array of resultant stresses."""
        if self._stresses is None:
            self._stresses = np.array([ps.stress for ps in self.point_stresses])
        return self._stresses
    
    # === Beamy-style properties ===
    
    @property
    def max(self) -> float:
        """Maximum resultant stress."""
        stresses = self._get_stresses()
        return float(np.max(stresses)) if len(stresses) > 0 else 0.0
    
    @property
    def max_stress(self) -> float:
        """Alias for maximum resultant stress (API compatibility)."""
        return self.max
    
    @property
    def min(self) -> float:
        """Minimum resultant stress."""
        stresses = self._get_stresses()
        return float(np.min(stresses)) if len(stresses) > 0 else 0.0
    
    @property
    def min_stress(self) -> float:
        """Alias for minimum resultant stress (API compatibility)."""
        return self.min
    
    @property
    def mean(self) -> float:
        """Average stress."""
        stresses = self._get_stresses()
        return float(np.mean(stresses)) if len(stresses) > 0 else 0.0
    
    @property
    def range(self) -> float:
        """Stress range (max - min)."""
        return self.max - self.min
    
    @property
    def capacity(self) -> float:
        """Design capacity φ(0.60 × F_EXX) from weld parameters."""
        return self.weld.parameters.capacity
    
    @property
    def max_point(self) -> PointStress | None:
        """PointStress at maximum stress location."""
        if not self.point_stresses:
            return None
        return max(self.point_stresses, key=lambda ps: ps.stress)
    
    @property
    def all(self) -> List[PointStress]:
        """All point stresses."""
        return self.point_stresses
    
    def at(self, y: float, z: float) -> StressComponents:
        """
        Get stress components at or near a point.
        
        Returns components at the nearest discretized point.
        """
        if not self.point_stresses:
            return StressComponents()
        
        # Find nearest point
        min_dist = float('inf')
        nearest = self.point_stresses[0]
        
        for ps in self.point_stresses:
            dist = math.hypot(ps.y - y, ps.z - z)
            if dist < min_dist:
                min_dist = dist
                nearest = ps
        
        return nearest.components
    
    def utilization(self, allowable: float | None = None) -> float:
        """
        Calculate utilization ratio.
        
        Args:
            allowable: Allowable stress. If None, uses capacity from parameters.
            
        Returns:
            max_stress / allowable (< 1.0 means acceptable)
        """
        if allowable is None:
            allowable = self.capacity
        if allowable <= 0:
            raise ValueError("Allowable stress must be positive")
        return self.max / allowable
    
    def is_adequate(self, allowable: float | None = None) -> bool:
        """Check if weld is adequate (utilization ≤ 1.0)."""
        return self.utilization(allowable) <= 1.0
    
    def plot(
        self,
        section: bool = True,
        force: bool = True,
        colorbar: bool = True,
        cmap: str = "coolwarm",
        weld_linewidth: float = 5.0,
        ax=None,
        show: bool = True,
        save_path: str | None = None
    ):
        """
        Plot stress distribution along the weld.
        
        Args:
            section: Show section outline (if weld has section reference)
            force: Show force arrow at application point
            colorbar: Show stress colorbar
            cmap: Matplotlib colormap name
            weld_linewidth: Width of weld lines
            ax: Matplotlib axes (creates new if None)
            show: Display the plot
            save_path: Path to save figure (.svg recommended)
            
        Returns:
            Matplotlib axes
        """
        from .plotter import plot_stress_result
        return plot_stress_result(
            self,
            section=section,
            force=force,
            colorbar=colorbar,
            cmap=cmap,
            weld_linewidth=weld_linewidth,
            ax=ax,
            show=show,
            save_path=save_path
        )
    
    def plot_components(
        self,
        components: List[str] | None = None,
        layout: str = "grid",
        **kwargs
    ):
        """
        Plot individual stress components.
        
        Args:
            components: Which to show ["direct", "moment", "axial", "bending"]
            layout: "grid" or "row"
            **kwargs: Passed to plot()
        """
        from .plotter import plot_stress_components
        if components is None:
            components = ["direct", "moment", "axial", "bending"]
        return plot_stress_components(self, components, layout, **kwargs)


def calculate_elastic_stress(
    weld: Weld,
    force: Force,
    discretization: int = 200
) -> StressResult:
    """
    Calculate weld stress using the Elastic Method.
    
    Per AISC Manual Part 8, the elastic method:
    1. Splits load into concentric + moment components
    2. Concentric: r_p = P / A (uniform)
    3. Moment: r_m = M × c / I_p (perpendicular to radius, linear)
    4. Vector sum for resultant
    
    Args:
        weld: Weld object with calculated properties
        force: Applied Force
        discretization: Points per segment
        
    Returns:
        StressResult
    """
    props = weld._calculate_properties(discretization)
    points_ds = weld._discretize(discretization)
    
    A = props.A
    Cy, Cz = props.Cy, props.Cz
    Iy, Iz, Ip = props.Iy, props.Iz, props.Ip
    
    # Get total moments about weld centroid
    Mx_total, My_total, Mz_total = force.get_moments_about(Cy, Cz)
    
    point_stresses: List[PointStress] = []
    
    for (y, z), ds, _, segment_ref in points_ds:
        # Distance from centroid
        dy = y - Cy
        dz = z - Cz
        
        # === In-plane stresses ===
        
        # Direct shear (uniform): f = F / A
        f_direct_y = force.Fy / A if A > 0 else 0.0
        f_direct_z = force.Fz / A if A > 0 else 0.0
        
        # Moment shear (perpendicular to radius, linear with distance)
        # r_m = M × c / I_p, components perpendicular to (dy, dz)
        # Perpendicular direction (CCW): (-dz, dy)
        f_moment_y = 0.0
        f_moment_z = 0.0
        
        if Ip > ZERO_TOLERANCE:
            # r_mx = -M × dz / I_p (y-component, perpendicular)
            # r_mz = M × dy / I_p (z-component, perpendicular)
            f_moment_y = -Mx_total * dz / Ip
            f_moment_z = Mx_total * dy / Ip
        
        # === Out-of-plane stresses ===
        
        # Direct axial (uniform)
        f_axial = force.Fx / A if A > 0 else 0.0
        
        # Bending stress (linear with distance)
        # σ = My × z / Iy + Mz × y / Iz
        f_bending = 0.0
        if Iy > ZERO_TOLERANCE:
            f_bending += My_total * dz / Iy
        if Iz > ZERO_TOLERANCE:
            f_bending += Mz_total * dy / Iz
        
        components = StressComponents(
            f_direct_y=f_direct_y,
            f_direct_z=f_direct_z,
            f_moment_y=f_moment_y,
            f_moment_z=f_moment_z,
            f_axial=f_axial,
            f_bending=f_bending
        )
        
        point_stresses.append(PointStress(
            point=(y, z),
            components=components,
            segment=segment_ref
        ))
    
    return StressResult(
        weld=weld,
        force=force,
        method="elastic",
        point_stresses=point_stresses
    )


def calculate_icr_stress(
    weld: Weld,
    force: Force,
    discretization: int = 200,
    max_iterations: int = 100,
    tolerance: float = 1e-6
) -> StressResult:
    """
    Calculate weld stress using the Instantaneous Center of Rotation (ICR) method.
    
    Per AISC Manual Part 8 and AWS D1.1, the ICR method:
    1. Iteratively finds the center of rotation
    2. Applies directional strength increase: (1.0 + 0.5 sin^1.5 θ)
    3. Uses curved load-deformation relationships
    
    The stress at each weld element depends on:
    - Distance from ICR (deformation proportional to distance)
    - Angle between force and weld axis (strength increase)
    
    Args:
        weld: Weld object (must be fillet type)
        force: Applied Force
        discretization: Points per segment
        max_iterations: Maximum solver iterations
        tolerance: Convergence tolerance
        
    Returns:
        StressResult with ICR-specific data
    """
    if weld.parameters.weld_type != "fillet":
        raise ValueError("ICR method only valid for fillet welds")
    
    props = weld._calculate_properties(discretization)
    points_ds = weld._discretize(discretization)
    
    leg = weld.parameters.leg
    throat = weld.parameters.throat
    if leg is None or throat is None:
        raise ValueError("Leg and throat sizes are required for the ICR method")
    
    F_EXX = weld.parameters.F_EXX
    if F_EXX is None:
        raise ValueError("F_EXX required for ICR method")
    
    Cy, Cz = props.Cy, props.Cz
    
    # Get applied loads at centroid
    Mx_total, _, _ = force.get_moments_about(Cy, Cz)
    Fy_app = force.Fy
    Fz_app = force.Fz
    
    # Total in-plane shear
    P_total = math.hypot(Fy_app, Fz_app)
    
    if P_total < ZERO_TOLERANCE and abs(Mx_total) < ZERO_TOLERANCE:
        # No in-plane loading, return elastic result
        return calculate_elastic_stress(weld, force, discretization)
    
    if abs(Mx_total) < ZERO_TOLERANCE:
        # Pure shear (no eccentricity) behaves like elastic solution
        return calculate_elastic_stress(weld, force, discretization)
    
    # Prepare discretized weld data
    y_arr = np.array([p[0][0] for p in points_ds], dtype=float)
    z_arr = np.array([p[0][1] for p in points_ds], dtype=float)
    ds_arr = np.array([p[1] for p in points_ds], dtype=float)
    tan_y_arr = np.array([p[2][0] for p in points_ds], dtype=float)
    tan_z_arr = np.array([p[2][1] for p in points_ds], dtype=float)
    
    if len(y_arr) == 0:
        raise ValueError("ICR method requires discretized weld points")
    
    dy_cent = y_arr - Cy
    dz_cent = z_arr - Cz
    
    # Use shared perpendicular direction calculation
    perp_y, perp_z = calculate_perpendicular_direction(Fy_app, Fz_app)
    
    # Target ratio between torsion and shear (eccentricity)
    target_ratio = -Mx_total / P_total
    eccentricity = abs(Mx_total) / P_total
    moment_sign = -1.0 if Mx_total > 0 else 1.0
    
    # Use shared search bounds calculation
    dist_min, dist_max = calculate_search_bounds(
        y_arr, z_arr, eccentricity,
        characteristic_size=leg
    )
    
    def evaluate_distance(distance: float) -> Tuple[float, dict[str, np.ndarray]] | None:
        """Evaluate ICR response for a distance from centroid."""
        icr_offset = moment_sign * distance
        icr_y = Cy + perp_y * icr_offset
        icr_z = Cz + perp_z * icr_offset
        
        dy_icr = y_arr - icr_y
        dz_icr = z_arr - icr_z
        c_arr = np.hypot(dy_icr, dz_icr)
        c_arr = np.where(c_arr < POSITION_TOLERANCE, POSITION_TOLERANCE, c_arr)
        
        dir_y = -dz_icr / c_arr
        dir_z = dy_icr / c_arr
        
        # Calculate angle between force direction and weld tangent
        cos_theta = np.clip(np.abs(dir_y * tan_y_arr + dir_z * tan_z_arr), 0.0, 1.0)
        theta = np.degrees(np.arccos(cos_theta))
        
        # Use shared deformation limit functions
        delta_u, delta_m = aisc_weld_deformation_limits(theta, leg)
        
        lambda_limit = float(np.min(delta_u / c_arr))
        if not math.isfinite(lambda_limit) or lambda_limit <= POSITION_TOLERANCE:
            return None
        
        delta = np.minimum(lambda_limit * c_arr, delta_u)
        
        # Use shared stress calculation
        F_w = aisc_weld_stress(delta, delta_m, delta_u, theta, F_EXX)
        R_mag = F_w * throat * ds_arr
        
        R_y = R_mag * dir_y
        R_z = R_mag * dir_z
        
        sum_Fy = float(np.sum(R_y))
        sum_Fz = float(np.sum(R_z))
        
        dot = Fy_app * sum_Fy + Fz_app * sum_Fz
        if dot < 0:
            R_y = -R_y
            R_z = -R_z
            dir_y = -dir_y
            dir_z = -dir_z
            sum_Fy = -sum_Fy
            sum_Fz = -sum_Fz
        
        P_base = math.hypot(sum_Fy, sum_Fz)
        if P_base < POSITION_TOLERANCE or not math.isfinite(P_base):
            return None
        
        sum_M = float(np.sum(dy_cent * R_z - dz_cent * R_y))
        ratio = sum_M / P_base
        
        return ratio, {
            "icr_y": icr_y,
            "icr_z": icr_z,
            "icr_dist": icr_offset,
            "F_w": F_w,
            "dir_y": dir_y,
            "dir_z": dir_z,
            "sum_Fy": sum_Fy,
            "sum_Fz": sum_Fz,
            "sum_M": sum_M,
            "P_base": P_base
        }
    
    # Use shared ICR search
    config = ICRSearchConfig(
        max_iterations=max_iterations,
        tolerance=tolerance,
        refine_bisection=True
    )
    
    result = find_icr_distance(
        evaluate_distance,
        target_ratio,
        dist_min,
        dist_max,
        eccentricity,
        config
    )
    
    if result is None:
        # Fallback to elastic method if ICR solver cannot converge
        return calculate_elastic_stress(weld, force, discretization)
    
    _, best_result, _ = result
    
    P_base = float(best_result["P_base"])
    if P_base < POSITION_TOLERANCE:
        return calculate_elastic_stress(weld, force, discretization)
    
    scale = P_total / P_base
    
    F_w_scaled = best_result["F_w"] * scale
    dir_y_arr = best_result["dir_y"]
    dir_z_arr = best_result["dir_z"]
    
    point_stresses: List[PointStress] = []
    
    for idx, ((y, z), _, _, segment_ref) in enumerate(points_ds):
        stress_value = float(F_w_scaled[idx])
        
        # Normalize stress by the angle strength factor to allow direct comparison
        # with base metal capacity (phi * 0.60 * F_EXX).
        # F_w includes the (1 + 0.5 sin^1.5 theta) factor.
        # By removing it, we get an "Equivalent Base Stress" that yields the correct utilization.
        dir_y = float(dir_y_arr[idx])
        dir_z = float(dir_z_arr[idx])
        
        cos_theta = abs(dir_y * float(tan_y_arr[idx]) + dir_z * float(tan_z_arr[idx]))
        theta = math.degrees(math.acos(min(cos_theta, 1.0)))
        
        # Use shared strength factor
        strength_factor = float(aisc_weld_strength_factor(np.array([theta]))[0])
        
        equiv_stress = stress_value / strength_factor
        
        components = StressComponents(
            f_direct_y=0.0,
            f_direct_z=0.0,
            f_moment_y=equiv_stress * dir_y,
            f_moment_z=equiv_stress * dir_z,
            f_axial=0.0,
            f_bending=0.0
        )
        
        point_stresses.append(PointStress(
            point=(y, z),
            components=components,
            segment=segment_ref
        ))
    
    icr_point = (float(best_result["icr_y"]), float(best_result["icr_z"]))
    rotation = float(best_result["icr_dist"])
    
    return StressResult(
        weld=weld,
        force=force,
        method="icr",
        point_stresses=point_stresses,
        icr_point=icr_point,
        rotation=rotation
    )
