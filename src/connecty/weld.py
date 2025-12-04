"""
Weld class and WeldParameters for weld stress analysis.

Supports fillet, PJP, CJP, and plug/slot welds per AISC 360.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal, List, Tuple, TYPE_CHECKING, Union, Sequence
import math
import numpy as np

if TYPE_CHECKING:
    from sectiony import Section, Geometry
    from .stress import StressResult

# Type aliases
Point = Tuple[float, float]
WeldType = Literal["fillet", "pjp", "cjp", "plug", "slot", "butt"]

# Electrode strength lookup (MPa)
ELECTRODE_STRENGTH: dict[str, float] = {
    "E60": 414.0,
    "E70": 483.0,
    "E80": 552.0,
    "E90": 621.0,
    "E100": 690.0,
    "E110": 759.0,
}


@dataclass
class WeldParameters:
    """
    Parameters defining weld configuration per AISC 360.
    
    Attributes:
        weld_type: Type of weld - "fillet", "pjp", "cjp", "plug", or "slot"
        leg: Fillet weld leg size (w) in length units
        throat: Effective throat thickness (a or E) in length units
        area: Plug/slot weld area in length² units
        electrode: Electrode classification (E60, E70, etc.)
        F_EXX: Override electrode tensile strength (stress units)
        F_y: Base metal yield strength (for CJP checks)
        F_u: Base metal ultimate strength (for CJP checks)
        t_base: Base metal thickness (for CJP checks)
        phi: Resistance factor (AISC default 0.75)
    """
    weld_type: WeldType
    
    # Geometry
    leg: float | None = None
    throat: float | None = None
    area: float | None = None
    
    # Legacy aliases for compatibility
    leg_size: float | None = None
    throat_thickness: float | None = None
    
    # Material
    electrode: str = "E70"
    F_EXX: float | None = None
    strength: float | None = None  # Allowable stress override (MPa)
    
    # Base metal (for CJP)
    F_y: float | None = None
    F_u: float | None = None
    t_base: float | None = None
    
    # Resistance factor
    phi: float = 0.75
    
    _capacity_override: float | None = field(default=None, init=False, repr=False)
    
    def __post_init__(self) -> None:
        # Map legacy weld type name
        if self.weld_type == "butt":
            # Treat butt welds as partial-joint-penetration welds by default
            self.weld_type = "pjp"
        
        # Apply alias fields if provided
        if self.leg is None and self.leg_size is not None:
            self.leg = self.leg_size
        if self.throat is None and self.throat_thickness is not None:
            self.throat = self.throat_thickness
        
        # Auto-calculate throat from leg for fillet welds
        if self.weld_type == "fillet":
            if self.throat is None and self.leg is not None:
                # Equal leg 45° fillet: a = w × 0.707
                self.throat = self.leg * 0.707
            elif self.throat is not None and self.leg is None:
                # Back-calculate leg from throat
                self.leg = self.throat / 0.707
        
        # Lookup electrode strength if not provided
        if self.F_EXX is None:
            if self.electrode in ELECTRODE_STRENGTH:
                self.F_EXX = ELECTRODE_STRENGTH[self.electrode]
            else:
                raise ValueError(f"Unknown electrode '{self.electrode}'. "
                               f"Valid: {list(ELECTRODE_STRENGTH.keys())} or provide F_EXX directly.")
        
        if self.strength is not None:
            self._capacity_override = self.strength
    
    @property
    def capacity(self) -> float:
        """
        Design capacity: φ(0.60 × F_EXX) in stress units.
        
        Per AISC 360 Table J2.5.
        """
        if self._capacity_override is not None:
            return self._capacity_override
        if self.F_EXX is None:
            raise ValueError("F_EXX not set")
        return self.phi * 0.60 * self.F_EXX


@dataclass
class WeldProperties:
    """
    Calculated geometric properties of a weld group.
    
    All properties are calculated about the weld group centroid.
    """
    Cy: float  # Centroid y-coordinate
    Cz: float  # Centroid z-coordinate
    A: float   # Total weld area (throat × length)
    L: float   # Total weld length
    Iy: float  # Second moment about y-axis (Σz²·dA)
    Iz: float  # Second moment about z-axis (Σy²·dA)
    Ip: float  # Polar moment (Iy + Iz)


@dataclass
class Weld:
    """
    A weld group defined by geometry and weld parameters.
    
    Can be created directly from geometry or from a section's contour.
    
    Attributes:
        geometry: Weld path as sectiony Geometry
        parameters: WeldParameters configuration
        section: Optional Section reference for plotting
    """
    geometry: Geometry
    parameters: WeldParameters
    section: Section | None = None
    
    # Cached properties
    _properties: WeldProperties | None = field(default=None, repr=False, init=False)
    _discretized_points: List[Tuple[Point, float, Point, object]] | None = field(default=None, repr=False, init=False)
    
    def __post_init__(self) -> None:
        # Validate geometry
        if self.geometry is None:
            raise ValueError("geometry is required")
        if not self.geometry.contours:
            raise ValueError("geometry must have at least one contour")
    
    @classmethod
    def from_section(
        cls,
        section: Section,
        parameters: WeldParameters,
        contour_index: int = 0
    ) -> Weld:
        """
        Create a Weld from a section's contour.
        
        Args:
            section: sectiony Section object
            parameters: WeldParameters for the weld
            contour_index: Which contour to use (0 = outer)
            
        Returns:
            Weld with geometry extracted from section
        """
        if section.geometry is None:
            raise ValueError("Section has no geometry")
        if not section.geometry.contours:
            raise ValueError("Section has no contours")
        if contour_index >= len(section.geometry.contours):
            raise ValueError(f"Contour index {contour_index} out of range")
        
        from sectiony import Geometry
        
        # Extract the specified contour
        contour = section.geometry.contours[contour_index]
        geometry = Geometry(contours=[contour])
        
        return cls(
            geometry=geometry,
            parameters=parameters,
            section=section
        )
    
    def _discretize(self, discretization: int = 200) -> List[Tuple[Point, float, Point, object]]:
        """
        Discretize weld geometry into uniformly-spaced points with segment lengths.
        
        Uses sectiony's discretize_uniform for equal arc-length spacing across the
        entire weld path, which ensures stress continuity at segment boundaries.
        
        Args:
            discretization: Total number of points along the weld path
            
        Returns:
            List of ((y, z), ds, (t_y, t_z), contour) tuples containing the midpoint,
            its arc length, the local unit tangent direction, and the source contour.
        """
        if self._discretized_points is not None and len(self._discretized_points) >= discretization:
            return self._discretized_points
        
        points_with_ds: List[Tuple[Point, float, Point, object]] = []
        
        for contour in self.geometry.contours:
            # Use uniform discretization for equal arc-length spacing
            # This ensures smooth stress distribution without jumps at segment boundaries
            uniform_points = contour.discretize_uniform(count=discretization)
            
            if len(uniform_points) < 2:
                continue
            
            # Calculate arc length and tangent for each midpoint
            for i in range(len(uniform_points) - 1):
                p1 = uniform_points[i]
                p2 = uniform_points[i + 1]
                
                mid_y = (p1[0] + p2[0]) / 2
                mid_z = (p1[1] + p2[1]) / 2
                ds = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
                
                if ds > 1e-12:
                    t_y = (p2[0] - p1[0]) / ds
                    t_z = (p2[1] - p1[1]) / ds
                    points_with_ds.append(((mid_y, mid_z), ds, (t_y, t_z), contour))
            
            # Handle closed contour: add segment from last point back to first
            if contour.is_closed and len(uniform_points) >= 2:
                p1 = uniform_points[-1]
                p2 = uniform_points[0]
                mid_y = (p1[0] + p2[0]) / 2
                mid_z = (p1[1] + p2[1]) / 2
                ds = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
                
                if ds > 1e-12:
                    t_y = (p2[0] - p1[0]) / ds
                    t_z = (p2[1] - p1[1]) / ds
                    points_with_ds.append(((mid_y, mid_z), ds, (t_y, t_z), contour))
        
        self._discretized_points = points_with_ds
        return points_with_ds
    
    def _calculate_properties(self, discretization: int = 200) -> WeldProperties:
        """Calculate weld group geometric properties."""
        if self._properties is not None:
            return self._properties
        
        points_ds = self._discretize(discretization)
        
        if not points_ds:
            raise ValueError("Weld has no discretized points")
        
        # Get throat thickness
        throat = self.parameters.throat
        if throat is None:
            if self.parameters.weld_type in ("plug", "slot") and self.parameters.area is not None:
                # For plug/slot, use area directly
                throat = 1.0  # Placeholder, area is used directly
            else:
                raise ValueError("Throat thickness not defined")
        
        # Calculate centroid
        y_arr = np.array([p[0][0] for p in points_ds])
        z_arr = np.array([p[0][1] for p in points_ds])
        ds_arr = np.array([p[1] for p in points_ds])
        
        if self.parameters.weld_type in ("plug", "slot"):
            # For plug/slot, use provided area
            dA_arr = ds_arr  # Weight by length for centroid
            total_area = self.parameters.area if self.parameters.area else 0.0
        else:
            dA_arr = throat * ds_arr
            total_area = float(np.sum(dA_arr))
        
        total_length = float(np.sum(ds_arr))
        
        if total_area < 1e-12:
            raise ValueError("Weld has zero area")
        
        # Centroid (weighted by dA for proper calculation)
        Cy = float(np.sum(y_arr * dA_arr) / np.sum(dA_arr))
        Cz = float(np.sum(z_arr * dA_arr) / np.sum(dA_arr))
        
        # Second moments about centroid
        dy_arr = y_arr - Cy
        dz_arr = z_arr - Cz
        
        Iz = float(np.sum(dy_arr**2 * dA_arr))  # Σy²·dA
        Iy = float(np.sum(dz_arr**2 * dA_arr))  # Σz²·dA
        Ip = Iy + Iz
        
        self._properties = WeldProperties(
            Cy=Cy,
            Cz=Cz,
            A=total_area,
            L=total_length,
            Iy=Iy,
            Iz=Iz,
            Ip=Ip
        )
        
        return self._properties
    
    # Property accessors
    @property
    def A(self) -> float:
        """Total weld area (throat × length)."""
        return self._calculate_properties().A
    
    @property
    def L(self) -> float:
        """Total weld length."""
        return self._calculate_properties().L
    
    @property
    def Cy(self) -> float:
        """Centroid y-coordinate."""
        return self._calculate_properties().Cy
    
    @property
    def Cz(self) -> float:
        """Centroid z-coordinate."""
        return self._calculate_properties().Cz
    
    @property
    def Iy(self) -> float:
        """Second moment about y-axis."""
        return self._calculate_properties().Iy
    
    @property
    def Iz(self) -> float:
        """Second moment about z-axis."""
        return self._calculate_properties().Iz
    
    @property
    def Ip(self) -> float:
        """Polar moment of inertia."""
        return self._calculate_properties().Ip
    
    def stress(
        self,
        force: Force,
        method: str = "elastic",
        discretization: int = 200
    ) -> StressResult:
        """
        Calculate stress distribution along the weld.
        
        Args:
            force: Applied Force object
            method: Analysis method - "elastic" or "icr" (fillet only)
            discretization: Points per segment
            
        Returns:
            StressResult with stress at all points
        """
        from .stress import calculate_elastic_stress, calculate_icr_stress, StressResult
        
        # Validate method for weld type
        valid_methods = {
            "fillet": ["elastic", "icr"],
            "pjp": ["elastic"],
            "cjp": ["base_metal", "elastic"],
            "plug": ["elastic"],
            "slot": ["elastic"],
        }
        
        weld_type = self.parameters.weld_type
        if method not in valid_methods[weld_type]:
            raise ValueError(f"Method '{method}' not valid for {weld_type} welds. "
                           f"Use: {valid_methods[weld_type]}")
        
        # Calculate properties if needed
        self._calculate_properties(discretization)
        
        if method == "elastic":
            return calculate_elastic_stress(self, force, discretization)
        elif method == "icr":
            return calculate_icr_stress(self, force, discretization)
        elif method == "base_metal":
            return calculate_elastic_stress(self, force, discretization)  # TODO: proper base metal check
        else:
            raise ValueError(f"Unknown method: {method}")

    def plot(
        self,
        stress: Union[StressResult, Sequence[StressResult], None] = None,
        info: bool = True,
        cmap: str = "coolwarm",
        section: bool = True,
        weld_linewidth: float = 5.0,
        show: bool = True,
        save_path: str | None = None,
        legend: bool = False,
        method: str | None = None,
        force: Force | None = None
    ):
        """
        Plot weld geometry or stress distribution.

        Args:
            stress: Optional StressResult (or list) to plot.
            info: Show stress info (Max/Util) in title (if stress provided).
            cmap: Colormap for stress.
            section: Show section outline.
            weld_linewidth: Width of weld lines.
            show: Display the plot.
            save_path: Path to save figure.
            legend: Show legend.
            method: Analysis method used for title or to trigger comparison.
                   If method="both", plots comparison of Elastic and ICR.
            force: Force object (required if stress is None and method is provided).
        """
        from .plotter import plot_stress_result, plot_weld_geometry, plot_stress_comparison

        # Handle comparison case: method="both" OR multiple results provided
        is_comparison = False
        results = []

        if isinstance(stress, (list, tuple)) and len(stress) > 1:
            is_comparison = True
            results = list(stress)
        elif method == "both":
            is_comparison = True
            if stress is not None:
                if isinstance(stress, (list, tuple)):
                    results = list(stress)
                else:
                    results = [stress]
                    # If single result provided but "both" requested, try to calculate others
                    if force is None and hasattr(stress, 'force'):
                         force = stress.force

        if is_comparison:
            # Calculate missing results if force available
            if force is not None:
                # Determine which methods we have
                existing_methods = {r.method for r in results}
                
                if "elastic" not in existing_methods:
                    results.append(self.stress(force, method="elastic"))
                if "icr" not in existing_methods and self.parameters.weld_type == "fillet":
                    results.append(self.stress(force, method="icr"))
            
            if len(results) >= 2:
                # Ensure correct order: Elastic then ICR usually prefers
                results.sort(key=lambda r: r.method)
                return plot_stress_comparison(
                    results,
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
            elif len(results) == 1:
                # Fallback if we only ended up with one result
                stress = results[0]

        # Standard single plot case
        if stress is not None:
            if isinstance(stress, (list, tuple)):
                # If list passed but not method="both", just plot the first one?
                # Or warn? Let's just plot the first one to be safe.
                stress = stress[0]
                
            return plot_stress_result(
                stress,
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
        elif force is not None and method is not None:
             # Calculate and plot
             result = self.stress(force, method=method)
             return plot_stress_result(
                result,
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
            return plot_weld_geometry(
                self,
                section=section,
                weld_linewidth=weld_linewidth,
                show=show,
                save_path=save_path
            )

# Import Force here to avoid circular import at module level
from .force import Force
