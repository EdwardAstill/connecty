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
    from .checks import BoltCheckResult
    from .connection import BoltConnection

from .load import ConnectionLoad

# Type aliases
Point = Tuple[float, float]


@dataclass
class BoltParameters:
    """
    Parameters defining bolt configuration.
    
    Attributes:
        diameter: Bolt diameter in consistent length units (e.g., mm or m)
        grade: Bolt grade/material ("A325", "A490", "8.8", "10.9")
    """
    diameter: float
    grade: str = "A325"
    
    def __post_init__(self) -> None:
        """Validate parameters."""
        if self.diameter <= 0:
            raise ValueError("Bolt diameter must be positive")
        if self.grade not in ("A325", "A490", "8.8", "10.9"):
            raise ValueError(f"Bolt grade must be A325, A490, 8.8, or 10.9, got {self.grade}")


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
        diameter: Bolt diameter in consistent length units
        grade: Bolt grade/material ("A325", "A490", "8.8", "10.9")
    """
    positions: List[Point]
    diameter: float
    grade: str = "A325"
    
    # Cached properties
    _properties: BoltProperties | None = field(default=None, repr=False, init=False)
    
    def __post_init__(self) -> None:
        """Validate bolt group."""
        if not self.positions:
            raise ValueError("Bolt group must have at least one bolt")
        if len(self.positions) < 1:
            raise ValueError("Bolt group must have at least one bolt")
        if self.diameter <= 0:
            raise ValueError("Bolt diameter must be positive")
        if self.grade not in ("A325", "A490", "8.8", "10.9"):
            raise ValueError(f"Bolt grade must be A325, A490, 8.8, or 10.9, got {self.grade}")
    
    @property
    def parameters(self) -> BoltParameters:
        """Get BoltParameters object for this group."""
        return BoltParameters(diameter=self.diameter, grade=self.grade)

    def analyze(self, *args, **kwargs):
        """BoltGroup can no longer be analyzed directly.

        Create a `Plate` and `BoltConnection`, then call `BoltConnection.analyze(...)`.
        """
        raise TypeError(
            "BoltGroup cannot be analyzed directly. "
            "Create a Plate and BoltConnection, then call BoltConnection.analyze(...)."
        )
    
    @classmethod
    def from_pattern(
        cls,
        rows: int,
        cols: int,
        spacing_y: float,
        spacing_z: float,
        diameter: float,
        grade: str = "A325",
        origin: Point = (0.0, 0.0)
    ) -> BoltGroup:
        """
        Create a bolt group from a rectangular pattern centered at origin.
        
        Args:
            rows: Number of rows (y-direction)
            cols: Number of columns (z-direction)
            spacing_y: Spacing between rows (length units)
            spacing_z: Spacing between columns (length units)
            diameter: Bolt diameter (length units)
            origin: (y, z) center location of the bolt pattern (length units)
            
        Returns:
            BoltGroup with generated positions centered at origin
        """
        if rows < 1 or cols < 1:
            raise ValueError("rows and cols must be at least 1")
        
        positions: List[Point] = []
        y0, z0 = origin
        
        # Calculate starting position to center the pattern at origin
        y_start = y0 - (rows - 1) * spacing_y / 2
        z_start = z0 - (cols - 1) * spacing_z / 2
        
        for i in range(rows):
            for j in range(cols):
                y = y_start + i * spacing_y
                z = z_start + j * spacing_z
                positions.append((y, z))
        
        return cls(positions=positions, diameter=diameter, grade=grade)
    
    @classmethod
    def from_circle(
        cls,
        n: int,
        radius: float,
        diameter: float,
        grade: str = "A325",
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
        
        return cls(positions=positions, diameter=diameter, grade=grade)
    
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


@dataclass
class BoltResult:
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
    n_shear_planes: int = 1  # Number of shear planes (>= 1)
    
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
        planes = max(1, int(self.n_shear_planes))
        return self.shear / (self.area * planes)
    
    @property
    def shear_stress_y(self) -> float:
        """Shear stress from y-component force only (force/length²)."""
        if self.area <= 0:
            return 0.0
        planes = max(1, int(self.n_shear_planes))
        return abs(self.Fy) / (self.area * planes)
    
    @property
    def shear_stress_z(self) -> float:
        """Shear stress from z-component force only (force/length²)."""
        if self.area <= 0:
            return 0.0
        planes = max(1, int(self.n_shear_planes))
        return abs(self.Fz) / (self.area * planes)
    
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
class ConnectionResult:
    """
    Complete analysis result for a bolt connection.
    
    Created by specifying connection geometry, applied load, and analysis methods.
    Performs analysis automatically and provides access to per-bolt results.
    
    Units (use consistent unit system):
        - Forces: force units (e.g., N or kN)
        - Stresses: force/length² (e.g., MPa or kPa)
        - Positions: length units (e.g., mm or m)
    
    Example: If using N and mm → forces in N, stress in MPa (N/mm²)
    """
    connection: "BoltConnection"  # The bolt connection being analyzed
    load: "ConnectionLoad"  # Applied loads
    shear_method: str  # Shear analysis method: "elastic" or "icr"
    tension_method: str  # Tension method: "conservative" or "accurate"
    _bolt_results: List[BoltResult] = field(default_factory=list, repr=False, init=False)
    
    # ICR-specific results
    icr_point: Point | None = field(default=None, init=False)
    
    def __post_init__(self) -> None:
        """Perform analysis when ConnectionResult is created."""
        from ..common.force import Force
        from .tension import calculate_plate_bolt_tensions
        
        # Convert ConnectionLoad to Force for internal calculations
        force = Force(
            Fx=self.load.Fx,
            Fy=self.load.Fy,
            Fz=self.load.Fz,
            Mx=self.load.Mx,
            My=self.load.My,
            Mz=self.load.Mz,
            location=self.load.location
        )
        
        # Calculate shear forces using the appropriate method
        if self.shear_method == "elastic":
            self._perform_elastic_analysis(force)
        elif self.shear_method == "icr":
            self._perform_icr_analysis(force)
        else:
            raise ValueError(f"Unknown shear_method: {self.shear_method}. Use 'elastic' or 'icr'.")
        
        # Calculate tension from plate geometry
        tensions = calculate_plate_bolt_tensions(
            bolt_group=self.connection.bolt_group,
            plate=self.connection.plate,
            force=force,
            tension_method=self.tension_method,
        )
        
        # Merge: keep shear components, overwrite Fx and set n_shear_planes
        for idx, bf in enumerate(self._bolt_results):
            bf.Fx = float(tensions[idx])
            bf.n_shear_planes = int(self.connection.n_shear_planes)
    
    def _perform_elastic_analysis(self, force) -> None:
        """Calculate bolt forces using the Elastic Method (in-plane shear)."""
        from ..common.icr_solver import ZERO_TOLERANCE
        
        bolt_group = self.connection.bolt_group
        props = bolt_group._calculate_properties()
        
        n = props.n
        Cy, Cz = props.Cy, props.Cz
        Ip = props.Ip
        
        # Get total moments about bolt group centroid
        Mx_total, _, _ = force.get_moments_about(0, Cy, Cz)
        
        Fx = 0.0
        Fy = force.Fy
        Fz = force.Fz
        Mx = Mx_total
        
        bolt_results = []
        
        for (y, z) in bolt_group.positions:
            dy = y - Cy
            dz = z - Cz
            
            # Direct shear (uniform)
            R_direct_y = Fy / n if n > 0 else 0.0
            R_direct_z = Fz / n if n > 0 else 0.0
            
            # Moment shear (perpendicular to radius)
            R_moment_y = 0.0
            R_moment_z = 0.0
            
            if Ip > ZERO_TOLERANCE:
                R_moment_y = -Mx * dz / Ip
                R_moment_z = Mx * dy / Ip
            
            total_Fy = R_direct_y + R_moment_y
            total_Fz = R_direct_z + R_moment_z
            total_Fx = Fx
            
            bolt_results.append(BoltResult(
                point=(y, z),
                Fy=total_Fy,
                Fz=total_Fz,
                Fx=total_Fx,
                diameter=bolt_group.parameters.diameter
            ))
        
        object.__setattr__(self, '_bolt_results', bolt_results)
    
    def _perform_icr_analysis(self, force) -> None:
        """Calculate bolt forces using the ICR Method."""
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
        
        bolt_group = self.connection.bolt_group
        props = bolt_group._calculate_properties()
        
        Cy, Cz = props.Cy, props.Cz
        
        Mx_total, _, _ = force.get_moments_about(Cy, Cz)
        Fy_app = force.Fy
        Fz_app = force.Fz
        Mx_app = Mx_total
        
        P_total = math.hypot(Fy_app, Fz_app)
        
        # If no moment or no shear, fall back to elastic
        if P_total < ZERO_TOLERANCE or abs(Mx_app) < ZERO_TOLERANCE:
            self._perform_elastic_analysis(force)
            return
        
        # Prepare bolt data
        y_arr = np.array([p[0] for p in bolt_group.positions], dtype=float)
        z_arr = np.array([p[1] for p in bolt_group.positions], dtype=float)
        
        R_ult = 100.0
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
        
        def evaluate_icr(icr_dist: float):
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
            R_arr = np.array([
                crawford_kulak_force(delta, R_ult, ck_params)
                for delta in deformation_arr
            ], dtype=float)
            
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
            
            return (ratio, {
                "R_arr": R_arr,
                "dir_y": dir_y,
                "dir_z": dir_z,
                "P_base": P_base,
                "icr_y": icr_y,
                "icr_z": icr_z
            })
        
        config = ICRSearchConfig(
            max_iterations=100,
            tolerance=1e-6,
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
            self._perform_elastic_analysis(force)
            return
        
        best_distance, best_data, _ = result
        
        P_base = float(best_data["P_base"])
        if P_base < POSITION_TOLERANCE:
            self._perform_elastic_analysis(force)
            return
        
        scale = P_total / P_base
        
        R_arr = best_data["R_arr"] * scale
        dir_y_arr = best_data["dir_y"]
        dir_z_arr = best_data["dir_z"]
        
        bolt_results = []
        
        for idx, (y, z) in enumerate(bolt_group.positions):
            R = float(R_arr[idx])
            
            bolt_results.append(BoltResult(
                point=(y, z),
                Fy=R * float(dir_y_arr[idx]),
                Fz=R * float(dir_z_arr[idx]),
                diameter=bolt_group.parameters.diameter
            ))
        
        icr_point = (float(best_data["icr_y"]), float(best_data["icr_z"]))
        
        object.__setattr__(self, '_bolt_results', bolt_results)
        object.__setattr__(self, 'icr_point', icr_point)
    
    @property
    def bolt_group(self) -> BoltGroup:
        """Access the bolt group from the connection."""
        return self.connection.bolt_group
    
    @property
    def method(self) -> str:
        """Analysis method used (alias for shear_method for compatibility)."""
        return self.shear_method
    
    def to_bolt_results(self) -> List[BoltResult]:
        """Convert to per-bolt result objects.
        
        Returns:
            List of BoltResult objects, one for each bolt in the group
        """
        return list(self._bolt_results)
    
    # === Properties ===
    
    @property
    def max_shear_force(self) -> float:
        """Maximum in-plane shear force on any bolt (force units)."""
        if not self._bolt_results:
            return 0.0
        shears = [bf.shear for bf in self._bolt_results]
        return float(np.max(shears))
    
    @property
    def min_shear_force(self) -> float:
        """Minimum in-plane shear force on any bolt (force units)."""
        if not self._bolt_results:
            return 0.0
        shears = [bf.shear for bf in self._bolt_results]
        return float(np.min(shears))
    
    @property
    def mean_shear_force(self) -> float:
        """Average in-plane shear force across bolts (force units)."""
        if not self._bolt_results:
            return 0.0
        shears = [bf.shear for bf in self._bolt_results]
        return float(np.mean(shears))
    
    @property
    def max_axial_force(self) -> float:
        """Maximum out-of-plane axial force on any bolt (force units). Positive = tension, negative = compression."""
        if not self._bolt_results:
            return 0.0
        axials = [bf.axial for bf in self._bolt_results]
        return float(np.max(axials))
    
    @property
    def min_axial_force(self) -> float:
        """Minimum out-of-plane axial force on any bolt (force units). Positive = tension, negative = compression."""
        if not self._bolt_results:
            return 0.0
        axials = [bf.axial for bf in self._bolt_results]
        return float(np.min(axials))
    
    @property
    def mean_axial_force(self) -> float:
        """Average out-of-plane axial force across bolts (force units). Positive = tension, negative = compression."""
        if not self._bolt_results:
            return 0.0
        axials = [bf.axial for bf in self._bolt_results]
        return float(np.mean(axials))
    
    @property
    def max_resultant_force(self) -> float:
        """Maximum 3D resultant force on any bolt (force units)."""
        if not self._bolt_results:
            return 0.0
        resultants = [bf.resultant for bf in self._bolt_results]
        return float(np.max(resultants))
    
    @property
    def min_resultant_force(self) -> float:
        """Minimum 3D resultant force on any bolt (force units)."""
        if not self._bolt_results:
            return 0.0
        resultants = [bf.resultant for bf in self._bolt_results]
        return float(np.min(resultants))
    
    @property
    def mean_resultant_force(self) -> float:
        """Average 3D resultant force across bolts (force units)."""
        if not self._bolt_results:
            return 0.0
        resultants = [bf.resultant for bf in self._bolt_results]
        return float(np.mean(resultants))
    
    @property
    def max_shear_stress(self) -> float:
        """
        Maximum in-plane shear stress on any bolt (force/length²).
        
        Returns 0.0 if bolt diameter is not set.
        """
        if not self._bolt_results:
            return 0.0
        stresses = [bf.shear_stress for bf in self._bolt_results]
        return float(np.max(stresses))
    
    @property
    def min_shear_stress(self) -> float:
        """
        Minimum in-plane shear stress on any bolt (force/length²).
        
        Returns 0.0 if bolt diameter is not set.
        """
        if not self._bolt_results:
            return 0.0
        stresses = [bf.shear_stress for bf in self._bolt_results]
        return float(np.min(stresses))
    
    @property
    def mean_shear_stress(self) -> float:
        """
        Average in-plane shear stress across bolts (force/length²).
        
        Returns 0.0 if bolt diameter is not set.
        """
        if not self._bolt_results:
            return 0.0
        stresses = [bf.shear_stress for bf in self._bolt_results]
        return float(np.mean(stresses))
    
    @property
    def max_axial_stress(self) -> float:
        """
        Maximum tensile axial stress on any bolt (force/length²).
        
        Compressive forces are assumed to be borne by connected parts, not the bolts.
        Returns 0.0 if no bolts are in tension or if bolt diameter is not set.
        """
        if not self._bolt_results:
            return 0.0
        stresses = [bf.axial_stress for bf in self._bolt_results]
        return float(np.max(stresses))
    
    @property
    def min_axial_stress(self) -> float:
        """
        Minimum out-of-plane axial stress on any bolt (force/length²). Positive = tension, negative = compression.
        
        Returns 0.0 if bolt diameter is not set.
        """
        if not self._bolt_results:
            return 0.0
        stresses = [bf.axial_stress for bf in self._bolt_results]
        return float(np.min(stresses))
    
    @property
    def mean_axial_stress(self) -> float:
        """
        Average out-of-plane axial stress across bolts (force/length²). Positive = tension, negative = compression.
        
        Returns 0.0 if bolt diameter is not set.
        """
        if not self._bolt_results:
            return 0.0
        stresses = [bf.axial_stress for bf in self._bolt_results]
        return float(np.mean(stresses))
    
    @property
    def max_combined_stress(self) -> float:
        """
        Maximum combined stress on any bolt (force/length²).
        
        Combined stress: √(τ² + σ²) where τ is shear and σ is axial.
        Returns 0.0 if bolt diameter is not set.
        """
        if not self._bolt_results:
            return 0.0
        stresses = [bf.combined_stress for bf in self._bolt_results]
        return float(np.max(stresses))
    
    @property
    def min_combined_stress(self) -> float:
        """
        Minimum combined stress on any bolt (force/length²).
        
        Combined stress: √(τ² + σ²) where τ is shear and σ is axial.
        Returns 0.0 if bolt diameter is not set.
        """
        if not self._bolt_results:
            return 0.0
        stresses = [bf.combined_stress for bf in self._bolt_results]
        return float(np.min(stresses))
    
    @property
    def mean_combined_stress(self) -> float:
        """
        Average combined stress across bolts (force/length²).
        
        Combined stress: √(τ² + σ²) where τ is shear and σ is axial.
        Returns 0.0 if bolt diameter is not set.
        """
        if not self._bolt_results:
            return 0.0
        stresses = [bf.combined_stress for bf in self._bolt_results]
        return float(np.mean(stresses))
    
    @property
    def critical_bolt_shear(self) -> int | None:
        """Index of bolt with maximum shear force."""
        if not self._bolt_results:
            return None
        max_bolt = max(self._bolt_results, key=lambda bf: bf.shear)
        return self._bolt_results.index(max_bolt)
    
    @property
    def critical_bolt_axial(self) -> int | None:
        """Index of bolt with maximum absolute axial force (largest tension or compression)."""
        if not self._bolt_results:
            return None
        max_bolt = max(self._bolt_results, key=lambda bf: abs(bf.axial))
        return self._bolt_results.index(max_bolt)
    
    @property
    def critical_bolt_resultant(self) -> int | None:
        """Index of bolt with maximum resultant force."""
        if not self._bolt_results:
            return None
        max_bolt = max(self._bolt_results, key=lambda bf: bf.resultant)
        return self._bolt_results.index(max_bolt)
    
    @property
    def critical_bolt_combined(self) -> int | None:
        """Index of bolt with maximum combined stress (most critical for design)."""
        if not self._bolt_results:
            return None
        max_bolt = max(self._bolt_results, key=lambda bf: bf.combined_stress)
        return self._bolt_results.index(max_bolt)
    
    @property
    def forces(self) -> List[BoltResult]:
        """All bolt forces."""
        return self._bolt_results
    
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

    def check(
        self,
        standard: str | None = None,
        connection_type: str | None = None,
        # Hole configuration
        hole_type: str = "standard",
        # AISC-specific
        slot_orientation: str = "perpendicular",
        threads_in_shear_plane: bool = True,
        slip_class: str = "A",
        n_s: int = 1,
        fillers: int = 0,
        n_b_tension: int | None = None,
        # AS 4100-specific
        hole_type_factor: float = 1.0,
        slip_coefficient: float = 0.35,
        n_e: int = 1,
        nn_shear_planes: int = 1,
        nx_shear_planes: int = 0,
        prying_allowance: float = 0.25,
        reduction_factor_kr: float = 1.0,
        # Other
        tension_per_bolt: float | None = None,
        pretension_override: float | None = None,
        require_explicit_tension: bool = False,
        assume_uniform_tension_if_missing: bool = True,
    ) -> "BoltCheckResult":
        """Apply design checks (AISC 360-22 or AS 4100) to this analysis result.
        
        Parameters
        ----------
        standard : str, optional
            "aisc" or "as4100". If None, automatically selects based on bolt grade:
            - A325/A490 -> AISC 360-22
            - 8.8/10.9 -> AS 4100
        connection_type : str, optional
            "bearing" (default), "slip-critical" (AISC), or "friction" (AS 4100)
        hole_type : str
            AISC: "standard", "oversize", "short_slotted", "long_slotted"
            AS 4100: "standard", "oversize", "slotted"
        slot_orientation : str
            AISC only: "perpendicular" or "parallel"
        threads_in_shear_plane : bool
            AISC only: True if threads are in the shear plane
        slip_class : str
            AISC only: "A" (μ=0.30) or "B" (μ=0.50)
        n_s : int
            AISC only: number of slip planes
        fillers : int
            AISC only: number of fillers (>=2 triggers reduction)
        n_b_tension : int, optional
            AISC only: number of bolts carrying tension
        hole_type_factor : float
            AS 4100 only: kh (1.0 standard, 0.85 oversize, 0.70 slotted)
        slip_coefficient : float
            AS 4100 only: friction coefficient μ
        n_e : int
            AS 4100 only: number of faying surfaces
        nn_shear_planes : int
            AS 4100 only: number of threaded shear planes
        nx_shear_planes : int
            AS 4100 only: number of unthreaded shear planes
        prying_allowance : float
            AS 4100 only: α factor for prying
        reduction_factor_kr : float
            AS 4100 only: reduction for long bolt lines
        tension_per_bolt : float, optional
            Explicit tension per bolt (kN), overrides analysis
        pretension_override : float, optional
            Override for bolt pretension (kN)
        
        Returns
        -------
        BoltCheckResult
            Check results with per-bolt utilizations and governing limit state
            
        Examples
        --------
        >>> # AISC bearing-type check
        >>> check = result.check(
        ...     standard="aisc",
        ...     connection_type="bearing",
        ...     hole_type="standard",
        ...     threads_in_shear_plane=True
        ... )
        
        >>> # AS 4100 friction-type check
        >>> check = result.check(
        ...     standard="as4100",
        ...     connection_type="friction",
        ...     hole_type="standard"
        ... )
        
        >>> # Auto-detect standard from bolt grade
        >>> check = result.check(
        ...     connection_type="bearing"
        ... )
        """
        from .checks import check_bolt_group

        return check_bolt_group(
            result=self,
            standard=standard,
            connection_type=connection_type,
            hole_type=hole_type,
            slot_orientation=slot_orientation,
            threads_in_shear_plane=threads_in_shear_plane,
            slip_class=slip_class,
            n_s=n_s,
            fillers=fillers,
            n_b_tension=n_b_tension,
            hole_type_factor=hole_type_factor,
            slip_coefficient=slip_coefficient,
            n_e=n_e,
            nn_shear_planes=nn_shear_planes,
            nx_shear_planes=nx_shear_planes,
            prying_allowance=prying_allowance,
            reduction_factor_kr=reduction_factor_kr,
            tension_per_bolt=tension_per_bolt,
            pretension_override=pretension_override,
            require_explicit_tension=require_explicit_tension,
            assume_uniform_tension_if_missing=assume_uniform_tension_if_missing,
        )

