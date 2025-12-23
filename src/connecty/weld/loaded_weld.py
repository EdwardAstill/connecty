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
        method: Analysis method - "elastic", "icr", or "both"
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
            "fillet": ["elastic", "icr", "both"],
            "pjp": ["elastic"],
            "cjp": ["base_metal", "elastic"],
            "plug": ["elastic"],
            "slot": ["elastic"],
        }
        
        weld_type = self.weld.parameters.type
        if self.method not in valid_methods.get(weld_type, ["elastic"]):
            raise ValueError(
                f"Method '{self.method}' not valid for {weld_type} welds. "
                f"Valid options: {valid_methods.get(weld_type, ['elastic'])}"
            )
        
        # Calculate stress based on method
        # Functions modify self in place, setting point_stresses, icr_point, rotation
        if self.method == "elastic":
            calculate_elastic_stress(self, self.discretization)
            self.icr_point = None
            self.rotation = None
        elif self.method == "icr":
            calculate_icr_stress(self, self.discretization)
        elif self.method == "both":
            # For "both", calculate elastic method
            # (could enhance later to store both results)
            calculate_elastic_stress(self, self.discretization)
            self.icr_point = None
            self.rotation = None
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
        For comparison plots, use method="both" when creating the LoadedWeld.
        
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
        from .weld_plotter import plot_loaded_weld, plot_loaded_weld_comparison
        
        if self.method == "both":
            # Calculate both results for comparison
            elastic_loaded = LoadedWeld(self.weld, self.load, method="elastic", discretization=self.discretization)
            
            loaded_list = [elastic_loaded]
            
            # Only add ICR if it's a fillet weld
            if self.weld.parameters.type == "fillet":
                icr_loaded = LoadedWeld(self.weld, self.load, method="icr", discretization=self.discretization)
                loaded_list.append(icr_loaded)
            
            if len(loaded_list) >= 2:
                return plot_loaded_weld_comparison(
                    loaded_list,
                    section=section,
                    force=True,
                    colorbar=True,
                    cmap=cmap,
                    weld_linewidth=weld_linewidth,
                    show=show,
                    save_path=save_path,
                    info=info,
                    legend=legend
                )
            else:
                # Fallback to single plot
                return plot_loaded_weld(
                    elastic_loaded,
                    section=section,
                    force=True,
                    colorbar=True,
                    cmap=cmap,
                    weld_linewidth=weld_linewidth,
                    show=show,
                    save_path=save_path,
                    info=info,
                    legend=legend
                )
        else:
            # Standard single method plot
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
                legend=legend
            )

