"""
Bolt group analysis for bolted connections.

Calculates force distribution using elastic and ICR methods.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, TYPE_CHECKING
import math
import numpy as np

if TYPE_CHECKING:
    from ..common.force import Force
    from .checks.aisc import BoltCheckResult, BoltDesignParams

from ..common.icr_solver import (
    ZERO_TOLERANCE,
    POSITION_TOLERANCE,
    ICRSearchConfig,
    CrawfordKulakParams,
    calculate_perpendicular_direction,
    calculate_search_bounds,
    find_icr_distance,
    crawford_kulak_force,
)

# Type aliases
Point = Tuple[float, float]


@dataclass
class BoltParameters:
    """
    Parameters defining bolt configuration.
    
    Attributes:
        diameter: Bolt diameter in consistent length units (e.g., mm or m)
    """
    diameter: float
    
    def __post_init__(self) -> None:
        """Validate parameters."""
        if self.diameter <= 0:
            raise ValueError("Bolt diameter must be positive")


@dataclass
class BoltProperties:
    """
    Calculated geometric properties of a bolt group.
    
    All properties are calculated about the bolt group centroid.
    Units: All in consistent length units (e.g., mm or m)
    """
    Cy: float  # Centroid y-coordinate (length)
    Cz: float  # Centroid z-coordinate (length)
    n: int     # Number of bolts
    Iy: float  # Second moment about y-axis (Σz²) (length²)
    Iz: float  # Second moment about z-axis (Σy²) (length²)
    Ip: float  # Polar moment (Iy + Iz) (length²)


@dataclass
class BoltGroup:
    """
    A group of bolts defined by coordinates and parameters.
    
    Can be created from explicit positions or generated from a pattern.
    
    Attributes:
        positions: List of (y, z) bolt coordinates
        parameters: BoltParameters configuration
    """
    positions: List[Point]
    parameters: BoltParameters
    
    # Cached properties
    _properties: BoltProperties | None = field(default=None, repr=False, init=False)
    
    def __post_init__(self) -> None:
        """Validate bolt group."""
        if not self.positions:
            raise ValueError("Bolt group must have at least one bolt")
        if len(self.positions) < 1:
            raise ValueError("Bolt group must have at least one bolt")
    
    @classmethod
    def from_pattern(
        cls,
        rows: int,
        cols: int,
        spacing_y: float,
        spacing_z: float,
        diameter: float,
        origin: Point = (0.0, 0.0)
    ) -> BoltGroup:
        """
        Create a bolt group from a rectangular pattern.
        
        Args:
            rows: Number of rows (y-direction)
            cols: Number of columns (z-direction)
            spacing_y: Spacing between rows (length units)
            spacing_z: Spacing between columns (length units)
            diameter: Bolt diameter (length units)
            origin: (y, z) location of bottom-left bolt (length units)
            
        Returns:
            BoltGroup with generated positions
        """
        if rows < 1 or cols < 1:
            raise ValueError("rows and cols must be at least 1")
        
        positions: List[Point] = []
        y0, z0 = origin
        
        for i in range(rows):
            for j in range(cols):
                y = y0 + i * spacing_y
                z = z0 + j * spacing_z
                positions.append((y, z))
        
        parameters = BoltParameters(diameter=diameter)
        return cls(positions=positions, parameters=parameters)
    
    @classmethod
    def from_circle(
        cls,
        n: int,
        radius: float,
        diameter: float,
        center: Point = (0.0, 0.0),
        start_angle: float = 0.0
    ) -> BoltGroup:
        """
        Create a bolt group arranged in a circle.
        
        Args:
            n: Number of bolts
            radius: Circle radius (length units)
            diameter: Bolt diameter (length units)
            center: (y, z) center of circle (length units)
            start_angle: Starting angle in degrees (0 = +z direction)
            
        Returns:
            BoltGroup with circular arrangement
        """
        if n < 1:
            raise ValueError("n must be at least 1")
        if radius <= 0:
            raise ValueError("radius must be positive")
        
        positions: List[Point] = []
        cy, cz = center
        
        for i in range(n):
            angle = math.radians(start_angle + i * 360 / n)
            y = cy + radius * math.sin(angle)
            z = cz + radius * math.cos(angle)
            positions.append((y, z))
        
        parameters = BoltParameters(diameter=diameter)
        return cls(positions=positions, parameters=parameters)
    
    def _calculate_properties(self) -> BoltProperties:
        """Calculate bolt group geometric properties."""
        if self._properties is not None:
            return self._properties
        
        n = len(self.positions)
        
        # Calculate centroid
        y_arr = np.array([p[0] for p in self.positions])
        z_arr = np.array([p[1] for p in self.positions])
        
        Cy = float(np.mean(y_arr))
        Cz = float(np.mean(z_arr))
        
        # Second moments about centroid
        dy_arr = y_arr - Cy
        dz_arr = z_arr - Cz
        
        Iz = float(np.sum(dy_arr**2))  # Σy² about centroid
        Iy = float(np.sum(dz_arr**2))  # Σz² about centroid
        Ip = Iy + Iz
        
        self._properties = BoltProperties(
            Cy=Cy,
            Cz=Cz,
            n=n,
            Iy=Iy,
            Iz=Iz,
            Ip=Ip
        )
        
        return self._properties
    
    # Property accessors
    @property
    def n(self) -> int:
        """Number of bolts."""
        return len(self.positions)
    
    @property
    def Cy(self) -> float:
        """Centroid y-coordinate (length units)."""
        return self._calculate_properties().Cy
    
    @property
    def Cz(self) -> float:
        """Centroid z-coordinate (length units)."""
        return self._calculate_properties().Cz
    
    @property
    def Iy(self) -> float:
        """Second moment about y-axis (Σz²) (length²)."""
        return self._calculate_properties().Iy
    
    @property
    def Iz(self) -> float:
        """Second moment about z-axis (Σy²) (length²)."""
        return self._calculate_properties().Iz
    
    @property
    def Ip(self) -> float:
        """Polar moment of inertia (Σr²) (length²)."""
        return self._calculate_properties().Ip
    
    def analyze(
        self,
        force: Force,
        method: str = "elastic"
    ) -> BoltResult:
        """
        Analyze bolt group for applied forces.
        
        Args:
            force: Applied Force object (forces in force units, moments in force·length)
            method: Analysis method - "elastic" or "icr"
            
        Returns:
            BoltResult with forces on each bolt (same force units as input)
        """
        if method == "elastic":
            return _calculate_elastic_bolt_force(self, force)
        elif method == "icr":
            return _calculate_icr_bolt_force(self, force)
        else:
            raise ValueError(f"Unknown method: {method}. Use 'elastic' or 'icr'.")

    def check_aisc(
        self,
        force: Force,
        design: "BoltDesignParams",
        method: str = "elastic",
        connection_type: str = "bearing",
    ) -> "BoltCheckResult":
        """Run analysis then AISC checks for this bolt group."""
        analysis = self.analyze(force, method=method)
        return analysis.check_aisc(design=design, connection_type=connection_type)


@dataclass
class BoltForce:
    """
    Force result at a specific bolt.
    
    Units (use consistent unit system):
        - Position: length (e.g., mm or m)
        - Forces: force (e.g., N or kN)
        - Stresses: force/length² (e.g., MPa=N/mm² or kPa=kN/m²)
        - Angles: degrees
    
    Example: If using N and mm → stress is in MPa (N/mm²)
    """
    point: Point  # (y, z) coordinates (length units)
    Fy: float  # Force in y-direction (force units)
    Fz: float  # Force in z-direction (force units)
    Fx: float = 0.0  # Force in x-direction (force units) - axial/out-of-plane
    diameter: float = 0.0  # Bolt diameter (length units)
    
    @property
    def y(self) -> float:
        """Y-coordinate of bolt (length units)."""
        return self.point[0]
    
    @property
    def z(self) -> float:
        """Z-coordinate of bolt (length units)."""
        return self.point[1]
    
    @property
    def shear(self) -> float:
        """In-plane shear force magnitude (force units)."""
        return math.hypot(self.Fy, self.Fz)
    
    @property
    def axial(self) -> float:
        """Out-of-plane axial force (force units). Positive = tension, negative = compression."""
        return self.Fx
    
    @property
    def resultant(self) -> float:
        """Total 3D force magnitude (force units)."""
        return math.sqrt(self.Fy**2 + self.Fz**2 + self.Fx**2)
    
    @property
    def angle(self) -> float:
        """Angle of in-plane shear force (degrees from +z axis)."""
        return math.degrees(math.atan2(self.Fy, self.Fz))
    
    @property
    def area(self) -> float:
        """Cross-sectional area of bolt (length²)."""
        if self.diameter <= 0:
            return 0.0
        return math.pi * (self.diameter / 2) ** 2
    
    @property
    def shear_stress(self) -> float:
        """
        In-plane shear stress through bolt cross-section (force/length²).
        
        Calculated as: τ = V / A
        where V is in-plane shear force and A is bolt area
        
        Returns 0.0 if diameter is not set.
        Example: N and mm → MPa (N/mm²)
        """
        if self.area <= 0:
            return 0.0
        return self.shear / self.area
    
    @property
    def shear_stress_y(self) -> float:
        """Shear stress from y-component force only (force/length²)."""
        if self.area <= 0:
            return 0.0
        return abs(self.Fy) / self.area
    
    @property
    def shear_stress_z(self) -> float:
        """Shear stress from z-component force only (force/length²)."""
        if self.area <= 0:
            return 0.0
        return abs(self.Fz) / self.area
    
    @property
    def axial_stress(self) -> float:
        """
        Out-of-plane tensile stress (force/length²). Only reports tension; compression returns 0.0.
        
        Bolts are assumed not to resist compression (borne by connected parts).
        Calculated as: σ = max(0, Fx / A)
        where Fx is axial force and A is bolt area
        
        Returns 0.0 if diameter is not set or bolt is in compression.
        Example: N and mm → MPa (N/mm²)
        """
        if self.area <= 0:
            return 0.0
        stress = self.Fx / self.area
        return max(0.0, stress)
    
    @property
    def combined_stress(self) -> float:
        """
        Combined stress magnitude (force/length²).
        
        Simplified as: σ_combined = √(τ² + σ²)
        where τ is in-plane shear stress and σ is axial stress magnitude.
        
        Returns 0.0 if diameter is not set.
        Example: N and mm → MPa (N/mm²)
        """
        if self.area <= 0:
            return 0.0
        return math.sqrt(self.shear_stress**2 + abs(self.axial_stress)**2)


@dataclass
class BoltResult:
    """
    Complete analysis result for a bolt group.
    
    Follows the same pattern as StressResult for consistent API.
    
    Units (use consistent unit system):
        - Forces: force units (e.g., N or kN)
        - Stresses: force/length² (e.g., MPa or kPa)
        - Positions: length units (e.g., mm or m)
    
    Example: If using N and mm → forces in N, stress in MPa (N/mm²)
    """
    bolt_group: BoltGroup
    force: Force  # Input forces and moments (force·length)
    method: str
    bolt_forces: List[BoltForce] = field(default_factory=list)
    
    # ICR-specific results
    icr_point: Point | None = None
    
    # === Properties ===
    
    @property
    def max_shear_force(self) -> float:
        """Maximum in-plane shear force on any bolt (force units)."""
        if not self.bolt_forces:
            return 0.0
        shears = [bf.shear for bf in self.bolt_forces]
        return float(np.max(shears))
    
    @property
    def min_shear_force(self) -> float:
        """Minimum in-plane shear force on any bolt (force units)."""
        if not self.bolt_forces:
            return 0.0
        shears = [bf.shear for bf in self.bolt_forces]
        return float(np.min(shears))
    
    @property
    def mean_shear_force(self) -> float:
        """Average in-plane shear force across bolts (force units)."""
        if not self.bolt_forces:
            return 0.0
        shears = [bf.shear for bf in self.bolt_forces]
        return float(np.mean(shears))
    
    @property
    def max_axial_force(self) -> float:
        """Maximum out-of-plane axial force on any bolt (force units). Positive = tension, negative = compression."""
        if not self.bolt_forces:
            return 0.0
        axials = [bf.axial for bf in self.bolt_forces]
        return float(np.max(axials))
    
    @property
    def min_axial_force(self) -> float:
        """Minimum out-of-plane axial force on any bolt (force units). Positive = tension, negative = compression."""
        if not self.bolt_forces:
            return 0.0
        axials = [bf.axial for bf in self.bolt_forces]
        return float(np.min(axials))
    
    @property
    def mean_axial_force(self) -> float:
        """Average out-of-plane axial force across bolts (force units). Positive = tension, negative = compression."""
        if not self.bolt_forces:
            return 0.0
        axials = [bf.axial for bf in self.bolt_forces]
        return float(np.mean(axials))
    
    @property
    def max_resultant_force(self) -> float:
        """Maximum 3D resultant force on any bolt (force units)."""
        if not self.bolt_forces:
            return 0.0
        resultants = [bf.resultant for bf in self.bolt_forces]
        return float(np.max(resultants))
    
    @property
    def min_resultant_force(self) -> float:
        """Minimum 3D resultant force on any bolt (force units)."""
        if not self.bolt_forces:
            return 0.0
        resultants = [bf.resultant for bf in self.bolt_forces]
        return float(np.min(resultants))
    
    @property
    def mean_resultant_force(self) -> float:
        """Average 3D resultant force across bolts (force units)."""
        if not self.bolt_forces:
            return 0.0
        resultants = [bf.resultant for bf in self.bolt_forces]
        return float(np.mean(resultants))
    
    @property
    def max_shear_stress(self) -> float:
        """
        Maximum in-plane shear stress on any bolt (force/length²).
        
        Returns 0.0 if bolt diameter is not set.
        """
        if not self.bolt_forces:
            return 0.0
        stresses = [bf.shear_stress for bf in self.bolt_forces]
        return float(np.max(stresses))
    
    @property
    def min_shear_stress(self) -> float:
        """
        Minimum in-plane shear stress on any bolt (force/length²).
        
        Returns 0.0 if bolt diameter is not set.
        """
        if not self.bolt_forces:
            return 0.0
        stresses = [bf.shear_stress for bf in self.bolt_forces]
        return float(np.min(stresses))
    
    @property
    def mean_shear_stress(self) -> float:
        """
        Average in-plane shear stress across bolts (force/length²).
        
        Returns 0.0 if bolt diameter is not set.
        """
        if not self.bolt_forces:
            return 0.0
        stresses = [bf.shear_stress for bf in self.bolt_forces]
        return float(np.mean(stresses))
    
    @property
    def max_axial_stress(self) -> float:
        """
        Maximum tensile axial stress on any bolt (force/length²).
        
        Compressive forces are assumed to be borne by connected parts, not the bolts.
        Returns 0.0 if no bolts are in tension or if bolt diameter is not set.
        """
        if not self.bolt_forces:
            return 0.0
        stresses = [bf.axial_stress for bf in self.bolt_forces]
        return float(np.max(stresses))
    
    @property
    def min_axial_stress(self) -> float:
        """
        Minimum out-of-plane axial stress on any bolt (force/length²). Positive = tension, negative = compression.
        
        Returns 0.0 if bolt diameter is not set.
        """
        if not self.bolt_forces:
            return 0.0
        stresses = [bf.axial_stress for bf in self.bolt_forces]
        return float(np.min(stresses))
    
    @property
    def mean_axial_stress(self) -> float:
        """
        Average out-of-plane axial stress across bolts (force/length²). Positive = tension, negative = compression.
        
        Returns 0.0 if bolt diameter is not set.
        """
        if not self.bolt_forces:
            return 0.0
        stresses = [bf.axial_stress for bf in self.bolt_forces]
        return float(np.mean(stresses))
    
    @property
    def max_combined_stress(self) -> float:
        """
        Maximum combined stress on any bolt (force/length²).
        
        Combined stress: √(τ² + σ²) where τ is shear and σ is axial.
        Returns 0.0 if bolt diameter is not set.
        """
        if not self.bolt_forces:
            return 0.0
        stresses = [bf.combined_stress for bf in self.bolt_forces]
        return float(np.max(stresses))
    
    @property
    def min_combined_stress(self) -> float:
        """
        Minimum combined stress on any bolt (force/length²).
        
        Combined stress: √(τ² + σ²) where τ is shear and σ is axial.
        Returns 0.0 if bolt diameter is not set.
        """
        if not self.bolt_forces:
            return 0.0
        stresses = [bf.combined_stress for bf in self.bolt_forces]
        return float(np.min(stresses))
    
    @property
    def mean_combined_stress(self) -> float:
        """
        Average combined stress across bolts (force/length²).
        
        Combined stress: √(τ² + σ²) where τ is shear and σ is axial.
        Returns 0.0 if bolt diameter is not set.
        """
        if not self.bolt_forces:
            return 0.0
        stresses = [bf.combined_stress for bf in self.bolt_forces]
        return float(np.mean(stresses))
    
    @property
    def critical_bolt_shear(self) -> int | None:
        """Index of bolt with maximum shear force."""
        if not self.bolt_forces:
            return None
        max_bolt = max(self.bolt_forces, key=lambda bf: bf.shear)
        return self.bolt_forces.index(max_bolt)
    
    @property
    def critical_bolt_axial(self) -> int | None:
        """Index of bolt with maximum absolute axial force (largest tension or compression)."""
        if not self.bolt_forces:
            return None
        max_bolt = max(self.bolt_forces, key=lambda bf: abs(bf.axial))
        return self.bolt_forces.index(max_bolt)
    
    @property
    def critical_bolt_resultant(self) -> int | None:
        """Index of bolt with maximum resultant force."""
        if not self.bolt_forces:
            return None
        max_bolt = max(self.bolt_forces, key=lambda bf: bf.resultant)
        return self.bolt_forces.index(max_bolt)
    
    @property
    def critical_bolt_combined(self) -> int | None:
        """Index of bolt with maximum combined stress (most critical for design)."""
        if not self.bolt_forces:
            return None
        max_bolt = max(self.bolt_forces, key=lambda bf: bf.combined_stress)
        return self.bolt_forces.index(max_bolt)
    
    @property
    def forces(self) -> List[BoltForce]:
        """All bolt forces."""
        return self.bolt_forces
    
    def plot(
        self,
        force: bool = True,
        bolt_forces: bool = True,
        colorbar: bool = True,
        cmap: str = "coolwarm",
        ax=None,
        show: bool = True,
        save_path: str | None = None,
        mode: str = "shear",
        force_unit: str = "N",
        length_unit: str = "mm"
    ):
        """
        Plot bolt group with force distribution.
        
        Args:
            force: Show applied load arrow
            bolt_forces: Show reaction vectors at each bolt
            colorbar: Show force colorbar
            cmap: Matplotlib colormap name
            ax: Matplotlib axes (creates new if None)
            show: Display the plot
            save_path: Path to save figure (.svg recommended)
            mode: Visualization mode: "shear" (default) or "axial"
            force_unit: Unit label for forces (e.g., 'N', 'kN', 'lbf')
            length_unit: Unit label for lengths (e.g., 'mm', 'm', 'in')
            
        Returns:
            Matplotlib axes
        """
        from .bolt_plotter import plot_bolt_result
        if mode not in {"shear", "axial"}:
            raise ValueError("mode must be 'shear' or 'axial'")
        return plot_bolt_result(
            self,
            force=force,
            bolt_forces=bolt_forces,
            colorbar=colorbar,
            cmap=cmap,
            ax=ax,
            show=show,
            save_path=save_path,
            mode=mode,
            force_unit=force_unit,
            length_unit=length_unit
        )

    def check_aisc(
        self,
        design: "BoltDesignParams",
        connection_type: str = "bearing",
    ) -> "BoltCheckResult":
        """Apply AISC 360-22 checks to this analysis result."""
        from .checks.aisc import check_bolt_group_aisc

        return check_bolt_group_aisc(result=self, design=design, connection_type=connection_type)


def _calculate_elastic_bolt_force(
    bolt_group: BoltGroup,
    force: Force
) -> BoltResult:
    """
    Calculate bolt forces using the Elastic Method (3D).
    
    The elastic method handles:
    1. In-plane shear (Fy, Fz): Direct + Torsion (Mx)
       - Direct shear: R_p = P / n (uniform, all bolts share equally)
       - Moment shear: R_m = M × r / Σr² (perpendicular to radius, proportional to distance)
    2. Out-of-plane axial (Fx, My, Mz): Direct + Bending
       - Direct axial: R_x = Fx / n (uniform)
       - Bending: R_x = My × z / Iy + Mz × y / Iz (linear with distance)
    
    Args:
        bolt_group: BoltGroup object (positions in length units)
        force: Applied Force (forces in force units, moments in force·length)
        
    Returns:
        BoltResult with 3D force at each bolt (same units as input)
    """
    props = bolt_group._calculate_properties()
    
    n = props.n
    Cy, Cz = props.Cy, props.Cz
    Iy, Iz, Ip = props.Iy, props.Iz, props.Ip
    
    # Get total moments about bolt group centroid
    Mx_total, My_total, Mz_total = force.get_moments_about(0, Cy, Cz)
    
    # Use forces directly (no conversion)
    Fx = force.Fx
    Fy = force.Fy
    Fz = force.Fz
    Mx = Mx_total
    My = My_total
    Mz = Mz_total
    
    bolt_forces: List[BoltForce] = []
    
    for (y, z) in bolt_group.positions:
        # Distance from centroid
        dy = y - Cy
        dz = z - Cz
        
        # === In-plane shear forces (y-z plane) ===
        
        # Direct shear (uniform): R = P / n
        R_direct_y = Fy / n if n > 0 else 0.0
        R_direct_z = Fz / n if n > 0 else 0.0
        
        # Moment shear (perpendicular to radius, linear with distance)
        # R_m = M × r / Σr², direction perpendicular to (dy, dz)
        # Perpendicular direction (CCW): (-dz, dy)
        R_moment_y = 0.0
        R_moment_z = 0.0
        
        if Ip > ZERO_TOLERANCE:
            # r_y = -M × dz / Ip (y-component, perpendicular)
            # r_z = M × dy / Ip (z-component, perpendicular)
            R_moment_y = -Mx * dz / Ip
            R_moment_z = Mx * dy / Ip
        
        # Total in-plane shear
        total_Fy = R_direct_y + R_moment_y
        total_Fz = R_direct_z + R_moment_z
        
        # === Out-of-plane axial force (x-direction) ===
        
        # Direct axial (uniform)
        R_direct_x = Fx / n if n > 0 else 0.0
        
        # Bending contribution (linear with distance from centroid)
        # My bending: Fx ∝ z distance from centroid
        # Mz bending: Fx ∝ y distance from centroid
        R_bending_x = 0.0
        if Iy > ZERO_TOLERANCE:
            R_bending_x += My * dz / Iy
        if Iz > ZERO_TOLERANCE:
            R_bending_x += Mz * dy / Iz
        
        # Total out-of-plane axial
        total_Fx = R_direct_x + R_bending_x
        
        bolt_forces.append(BoltForce(
            point=(y, z),
            Fy=total_Fy,
            Fz=total_Fz,
            Fx=total_Fx,
            diameter=bolt_group.parameters.diameter
        ))
    
    return BoltResult(
        bolt_group=bolt_group,
        force=force,
        method="elastic",
        bolt_forces=bolt_forces
    )


def _calculate_icr_bolt_force(
    bolt_group: BoltGroup,
    force: Force,
    max_iterations: int = 100,
    tolerance: float = 1e-6
) -> BoltResult:
    """
    Calculate bolt forces using the Instantaneous Center of Rotation (ICR) method.
    
    The ICR method:
    1. Iteratively finds the center of rotation
    2. Bolt deformation is proportional to distance from ICR
    3. Uses non-linear load-deformation curve: R = R_ult (1 - e^(-μΔ))^λ
    
    The Crawford-Kulak model parameters:
    - μ = 10 (curve shape parameter)
    - λ = 0.55 (curve shape parameter)
    - Δ_max = 0.34 in = 8.64 mm (ultimate deformation in typical length units)
    
    Args:
        bolt_group: BoltGroup object (positions in length units)
        force: Applied Force (forces in force units, moments in force·length)
        max_iterations: Maximum solver iterations
        tolerance: Convergence tolerance (dimensionless)
        
    Returns:
        BoltResult with ICR-specific data (forces in same units as input, ICR position in length units)
    """
    props = bolt_group._calculate_properties()
    
    Cy, Cz = props.Cy, props.Cz
    
    # Get applied loads (use directly, no conversion)
    Mx_total, _, _ = force.get_moments_about(Cy, Cz)
    Fy_app = force.Fy
    Fz_app = force.Fz
    Mx_app = Mx_total
    
    # Total in-plane shear
    P_total = math.hypot(Fy_app, Fz_app)
    
    # If no moment or no shear, fall back to elastic
    if P_total < ZERO_TOLERANCE or abs(Mx_app) < ZERO_TOLERANCE:
        return _calculate_elastic_bolt_force(bolt_group, force)
    
    # Prepare bolt data
    y_arr = np.array([p[0] for p in bolt_group.positions], dtype=float)
    z_arr = np.array([p[1] for p in bolt_group.positions], dtype=float)
    
    # Bolt ultimate capacity - use typical value for standard bolts
    # This is just for the force distribution shape, not actual capacity checking
    # Will be scaled to match applied load
    R_ult = 100.0  # Reference capacity in force units
    
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
        return _calculate_elastic_bolt_force(bolt_group, force)
    
    best_distance, best_data, _ = result
    
    # Scale forces to match applied load
    P_base = float(best_data["P_base"])
    if P_base < POSITION_TOLERANCE:
        return _calculate_elastic_bolt_force(bolt_group, force)
    
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
            Fz=R * float(dir_z_arr[idx]),
            diameter=bolt_group.parameters.diameter
        ))
    
    icr_point = (float(best_data["icr_y"]), float(best_data["icr_z"]))
    
    return BoltResult(
        bolt_group=bolt_group,
        force=force,
        method="icr",
        bolt_forces=bolt_forces,
        icr_point=icr_point
    )


# Import Force here to avoid circular import at module level
from ..common.force import Force

