"""
LoadedWeld class combining a Weld with a Load.

This module provides the main user-facing API for weld stress analysis.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, List
import math

if TYPE_CHECKING:
    from .weld import Weld
    from ..common.load import Load
    from .weld_stress import PointStress

Point = tuple[float, float]


@dataclass
class LoadedWeld:
    """
    A weld subjected to a load, with calculated stress results.
    
    This is the primary interface for weld stress analysis. It combines
    a Weld (geometry + parameters) with a Load (forces + moments), calculates
    the stress distribution using the specified method, and provides access
    to results through properties and methods.
    
    Attributes:
        weld: Weld object defining geometry and parameters
        load: Load object defining applied forces and moments
        method: Analysis method - "elastic" or "icr"
        discretization: Number of points to discretize the weld path
        
    Example:
        >>> from sectiony.library import rhs
        >>> from connecty import Weld, WeldParams, Load, LoadedWeld
        >>> 
        >>> section = rhs(b=100, h=200, t=10, r=15)
        >>> params = WeldParams(type="fillet", leg=6.0)
        >>> weld = Weld.from_section(section, params)
        >>> 
        >>> load = Load(Fy=-100e3, location=(50, 0))
        >>> 
        >>> # Analyze using elastic method
        >>> loaded = LoadedWeld(weld, load, method="elastic")
        >>> print(f"Max stress: {loaded.max:.1f} MPa")
        >>> 
        >>> # Or use ICR method (for fillet welds)
        >>> loaded_icr = LoadedWeld(weld, load, method="icr")
        >>> 
        >>> # Plot results
        >>> loaded.plot()
    """
    weld: Weld
    load: Load
    method: str = "elastic"
    discretization: int = 200
    F_EXX: float | None = None
    include_kds: bool = True
    
    # Calculated results (set in __post_init__)
    point_stresses: List[PointStress] = field(default_factory=list, init=False, repr=False)
    icr_point: Point | None = field(default=None, init=False, repr=False)
    rotation: float | None = field(default=None, init=False, repr=False)
    
    _stresses_array: list[float] | None = field(default=None, init=False, repr=False)
    
    def __post_init__(self) -> None:
        """Calculate stress results based on the specified method."""
        from .weld_stress import calculate_elastic_stress, calculate_icr_stress
        
        # Validate method for weld type
        valid_methods = {
            "fillet": ["elastic", "icr"],
            "pjp": ["elastic"],
            "cjp": ["base_metal", "elastic"],
            "plug": ["elastic"],
            "slot": ["elastic"],
        }
        
        weld_type = self.weld.parameters.type
        allowed_methods = valid_methods[weld_type] if weld_type in valid_methods else ["elastic"]
        if self.method not in allowed_methods:
            raise ValueError(
                f"Method '{self.method}' not valid for {weld_type} welds. "
                f"Valid options: {allowed_methods}"
            )
        
        # Calculate stress based on method
        # Functions modify self in place, setting point_stresses, icr_point, rotation
        if self.method == "elastic":
            calculate_elastic_stress(self, self.discretization)
            self.icr_point = None
            self.rotation = None
        elif self.method == "icr":
            calculate_icr_stress(self, self.discretization)
        else:
            raise ValueError(f"Unknown method: {self.method}")
    
    # === Result Properties (beamy-style API) ===
    
    @property
    def max(self) -> float:
        """Maximum resultant stress."""
        if not self.point_stresses:
            return 0.0
        return max(ps.stress for ps in self.point_stresses)
    
    @property
    def max_stress(self) -> float:
        """Alias for maximum resultant stress (API compatibility)."""
        return self.max
    
    @property
    def min(self) -> float:
        """Minimum resultant stress."""
        if not self.point_stresses:
            return 0.0
        return min(ps.stress for ps in self.point_stresses)
    
    @property
    def min_stress(self) -> float:
        """Alias for minimum resultant stress (API compatibility)."""
        return self.min
    
    @property
    def mean(self) -> float:
        """Average stress."""
        if not self.point_stresses:
            return 0.0
        return sum(ps.stress for ps in self.point_stresses) / len(self.point_stresses)
    
    @property
    def range(self) -> float:
        """Stress range (max - min)."""
        return self.max - self.min
    
    @property
    def max_point(self):
        """PointStress at maximum stress location."""
        if not self.point_stresses:
            return None
        return max(self.point_stresses, key=lambda ps: ps.stress)
    
    @property
    def all(self):
        """All point stresses."""
        return self.point_stresses
    
    def at(self, y: float, z: float):
        """
        Get stress components at or near a point.
        
        Returns components at the nearest discretized point.
        
        Args:
            y: Y-coordinate
            z: Z-coordinate
            
        Returns:
            StressComponents at the nearest point
        """
        from .weld_stress import StressComponents
        
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
    
    def weld_metal_utilizations(
        self,
        *,
        F_EXX: float | None = None,
        phi_w: float = 0.75,
        conservative_k_ds: bool = False,
    ) -> list[float]:
        """
        Return pointwise weld-metal utilisation values aligned to `self.point_stresses`.

        Definition (AISC fillet weld metal capacity basis):
            u_i = stress_i / (phi_w * 0.60 * F_EXX * k_ds_i)

        Notes:
        - If `self.include_kds` is False, k_ds_i is forced to 1.0.
        - If `conservative_k_ds` is True, k_ds_i is forced to 1.0.
        - Uses the local in-plane resultant direction (y-z) and the local weld tangent
          from `Weld._discretize(...)` to compute theta and k_ds_i.
        """
        if not self.point_stresses:
            return []

        F_EXX_value: float
        if F_EXX is not None:
            F_EXX_value = float(F_EXX)
        elif self.F_EXX is not None:
            F_EXX_value = float(self.F_EXX)
        else:
            raise ValueError("F_EXX must be provided (or set on LoadedWeld) to compute utilization.")

        points_ds = self.weld._discretize(self.discretization)
        if len(points_ds) != len(self.point_stresses):
            raise ValueError("Discretization mismatch: cannot map stresses to weld tangents.")

        def _aisc_kds(theta_deg: float) -> float:
            theta = abs(float(theta_deg))
            sin_val = abs(math.sin(math.radians(theta)))
            return 1.0 + 0.50 * (sin_val**1.5)

        utils: list[float] = []
        for ps, (_, _, (tan_y, tan_z), _) in zip(self.point_stresses, points_ds):
            k_ds = 1.0

            if not conservative_k_ds and bool(self.include_kds):
                fy = float(ps.components.total_y)
                fz = float(ps.components.total_z)
                mag = math.hypot(fy, fz)

                if mag >= 1e-12:
                    dir_y = fy / mag
                    dir_z = fz / mag

                    cos_theta = abs(dir_y * float(tan_y) + dir_z * float(tan_z))
                    cos_theta = min(max(cos_theta, 0.0), 1.0)
                    theta = math.degrees(math.acos(cos_theta))
                    k_ds = _aisc_kds(theta)

            denom = float(phi_w) * 0.60 * float(F_EXX_value) * float(k_ds)
            util = float(ps.stress) / denom if denom > 0.0 else math.inf
            utils.append(util)

        return utils

    def directional_factors(
        self,
        *,
        conservative_k_ds: bool = False,
    ) -> list[float]:
        """
        Return pointwise AISC directional strength factors (k_ds) aligned to `self.point_stresses`.

        Definition (AISC fillet weld directional strength increase):
            k_ds = 1.0 + 0.50 * sin(theta)^1.5

        Where theta is the angle between the local in-plane resultant direction (y-z)
        and the local weld tangent direction.

        Notes:
        - If `self.include_kds` is False, k_ds is forced to 1.0.
        - If `conservative_k_ds` is True, k_ds is forced to 1.0.
        - If the local in-plane resultant magnitude is near zero, theta is undefined;
          this function returns k_ds=1.0 at that point (no directional benefit).
        """
        if not self.point_stresses:
            return []

        points_ds = self.weld._discretize(self.discretization)
        if len(points_ds) != len(self.point_stresses):
            raise ValueError("Discretization mismatch: cannot map stresses to weld tangents.")

        def _aisc_kds(theta_deg: float) -> float:
            theta = abs(float(theta_deg))
            sin_val = abs(math.sin(math.radians(theta)))
            return 1.0 + 0.50 * (sin_val**1.5)

        kds_list: list[float] = []
        for ps, (_, _, (tan_y, tan_z), _) in zip(self.point_stresses, points_ds):
            k_ds = 1.0

            if not conservative_k_ds and bool(self.include_kds):
                fy = float(ps.components.total_y)
                fz = float(ps.components.total_z)
                mag = math.hypot(fy, fz)

                if mag >= 1e-12:
                    dir_y = fy / mag
                    dir_z = fz / mag

                    cos_theta = abs(dir_y * float(tan_y) + dir_z * float(tan_z))
                    cos_theta = min(max(cos_theta, 0.0), 1.0)
                    theta = math.degrees(math.acos(cos_theta))
                    k_ds = _aisc_kds(theta)

            kds_list.append(float(k_ds))

        return kds_list

    def plot_utilization(
        self,
        *,
        section: bool = True,
        info: bool = True,
        cmap: str = "viridis",
        weld_linewidth: float = 5.0,
        show: bool = True,
        save_path: str | None = None,
        legend: bool = False,
        F_EXX: float | None = None,
        conservative_k_ds: bool = False,
    ):
        """
        Plot weld-metal utilisation along the weld path (AISC weld metal basis).

        Args:
            section: Show section outline (default True)
            info: Show max utilisation in title (default True)
            cmap: Colormap for utilisation visualization (default "viridis")
            weld_linewidth: Width of weld lines (default 5.0)
            show: Display the plot (default True)
            save_path: Path to save figure (.svg recommended)
            legend: Show legend with applied loads (default False)
            F_EXX: Electrode strength (MPa). If None, uses `self.F_EXX`.
            conservative_k_ds: If True, force k_ds=1.0 for utilisation.
        """
        from .weld_plotter import plot_loaded_weld_utilization

        return plot_loaded_weld_utilization(
            self,
            section=section,
            force=True,
            colorbar=True,
            cmap=cmap,
            weld_linewidth=weld_linewidth,
            show=show,
            save_path=save_path,
            info=info,
            legend=legend,
            F_EXX=F_EXX,
            conservative_k_ds=conservative_k_ds,
        )

    def plot_directional_factor(
        self,
        *,
        section: bool = True,
        info: bool = True,
        cmap: str = "plasma",
        weld_linewidth: float = 5.0,
        show: bool = True,
        save_path: str | None = None,
        legend: bool = False,
        conservative_k_ds: bool = False,
    ):
        """
        Plot AISC directional strength factor (k_ds) along the weld path.

        Args:
            section: Show section outline (default True)
            info: Show min/max k_ds in title (default True)
            cmap: Colormap for k_ds visualization (default "plasma")
            weld_linewidth: Width of weld lines (default 5.0)
            show: Display the plot (default True)
            save_path: Path to save figure (.svg recommended)
            legend: Show legend with applied loads (default False)
            conservative_k_ds: If True, force k_ds=1.0 at all points
        """
        from .weld_plotter import plot_loaded_weld_directional_factor

        return plot_loaded_weld_directional_factor(
            self,
            section=section,
            force=True,
            colorbar=True,
            cmap=cmap,
            weld_linewidth=weld_linewidth,
            show=show,
            save_path=save_path,
            info=info,
            legend=legend,
            conservative_k_ds=conservative_k_ds,
        )
    
    
    def plot(
        self,
        section: bool = True,
        info: bool = True,
        cmap: str = "coolwarm",
        weld_linewidth: float = 5.0,
        show: bool = True,
        save_path: str | None = None,
        legend: bool = False,
        **kwargs
    ):
        """
        Plot weld stress distribution.
        
        Uses the method specified when creating the LoadedWeld.
        
        Args:
            section: Show section outline (default True)
            info: Show stress info (Max/Util) in title (default True)
            cmap: Colormap for stress visualization (default "coolwarm")
            weld_linewidth: Width of weld lines (default 5.0)
            show: Display the plot (default True)
            save_path: Path to save figure (.svg recommended)
            legend: Show legend with applied loads (default False)
            **kwargs: Additional arguments passed to plotting functions
            
        Returns:
            Matplotlib axes or figure object
        """
        from .weld_plotter import plot_loaded_weld
        
        return plot_loaded_weld(
            self,
            section=section,
            force=True,
            colorbar=True,
            cmap=cmap,
            weld_linewidth=weld_linewidth,
            show=show,
            save_path=save_path,
            info=info,
            legend=legend,
        )

