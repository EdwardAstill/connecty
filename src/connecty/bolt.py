"""
Bolt group analysis for bolted connections.

Supports elastic and ICR analysis methods per AISC 360.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal, List, Tuple, TYPE_CHECKING
import math
import numpy as np

if TYPE_CHECKING:
    from .force import Force

# Type aliases
Point = Tuple[float, float]
BoltGrade = Literal["A325", "A490", "8.8", "10.9"]
HoleType = Literal["STD", "OVS", "SSL", "LSL"]
ThreadCondition = Literal["N", "X"]  # N = threads Not excluded, X = threads eXcluded


# Bolt material properties (nominal shear strength, MPa)
# Per AISC 360 Table J3.2
BOLT_SHEAR_STRENGTH: dict[str, dict[str, float]] = {
    "A325": {"N": 372.0, "X": 457.0},   # F_nv = 54 ksi (N) or 68 ksi (X)
    "A490": {"N": 457.0, "X": 579.0},   # F_nv = 68 ksi (N) or 84 ksi (X)
    # Metric grades (MPa)
    "8.8": {"N": 372.0, "X": 457.0},    # Similar to A325
    "10.9": {"N": 457.0, "X": 579.0},   # Similar to A490
}

# Slip-critical surface class factors (μ) per AISC 360 Table J3.1
SLIP_CLASS_FACTORS: dict[str, float] = {
    "A": 0.30,  # Class A (unpainted clean mill scale, or Class A coating)
    "B": 0.50,  # Class B (unpainted blast-cleaned, or Class B coating)
    "C": 0.35,  # Class C (hot-dipped galvanized with wire brushed surfaces)
}

# Minimum bolt pretension (kN) per AISC Table J3.1
BOLT_PRETENSION: dict[str, dict[float, float]] = {
    # A325 / 8.8
    "A325": {
        16: 91.0, 20: 142.0, 22: 176.0, 24: 205.0,
        27: 267.0, 30: 326.0, 36: 475.0
    },
    # A490 / 10.9
    "A490": {
        16: 114.0, 20: 179.0, 22: 221.0, 24: 257.0,
        27: 334.0, 30: 408.0, 36: 595.0
    },
}
BOLT_PRETENSION["8.8"] = BOLT_PRETENSION["A325"]
BOLT_PRETENSION["10.9"] = BOLT_PRETENSION["A490"]


@dataclass
class BoltParameters:
    """
    Parameters defining bolt configuration per AISC 360.
    
    Attributes:
        diameter: Bolt diameter in mm
        grade: Bolt grade (A325, A490, 8.8, 10.9)
        threads_excluded: Thread condition - True for X (excluded), False for N (not excluded)
        hole_type: Hole type - STD, OVS (oversized), SSL/LSL (slotted)
        shear_planes: Number of shear planes (1 for single, 2 for double)
        slip_critical: If True, uses slip resistance instead of shear capacity
        slip_class: Surface class for slip-critical connections (A, B, C)
        phi: Resistance factor (0.75 for bearing, 0.85/1.0 for slip-critical)
    """
    diameter: float
    grade: BoltGrade = "A325"
    threads_excluded: bool = False
    hole_type: HoleType = "STD"
    shear_planes: int = 1
    slip_critical: bool = False
    slip_class: str = "B"
    phi: float = 0.75
    
    # Override values
    F_nv: float | None = None  # Override nominal shear strength
    R_n: float | None = None   # Override nominal capacity per bolt
    
    def __post_init__(self) -> None:
        """Validate parameters and calculate derived values."""
        if self.diameter <= 0:
            raise ValueError("Bolt diameter must be positive")
        if self.grade not in BOLT_SHEAR_STRENGTH:
            raise ValueError(f"Unknown bolt grade '{self.grade}'. "
                           f"Valid: {list(BOLT_SHEAR_STRENGTH.keys())}")
        if self.shear_planes < 1:
            raise ValueError("shear_planes must be at least 1")
        if self.slip_critical and self.slip_class not in SLIP_CLASS_FACTORS:
            raise ValueError(f"Unknown slip class '{self.slip_class}'. "
                           f"Valid: {list(SLIP_CLASS_FACTORS.keys())}")
        
        # Set appropriate phi for slip-critical
        if self.slip_critical and self.phi == 0.75:
            # Default phi for slip-critical depends on hole type
            if self.hole_type == "STD":
                self.phi = 1.0  # Standard holes
            else:
                self.phi = 0.85  # Oversized/slotted holes
    
    @property
    def thread_condition(self) -> ThreadCondition:
        """Get thread condition code."""
        return "X" if self.threads_excluded else "N"
    
    @property
    def area(self) -> float:
        """Bolt shank area (mm²)."""
        return math.pi * (self.diameter / 2) ** 2
    
    @property
    def nominal_shear_strength(self) -> float:
        """
        Nominal shear strength F_nv (MPa).
        
        Per AISC 360 Table J3.2.
        """
        if self.F_nv is not None:
            return self.F_nv
        return BOLT_SHEAR_STRENGTH[self.grade][self.thread_condition]
    
    @property
    def pretension(self) -> float:
        """
        Minimum bolt pretension T_b (kN).
        
        Per AISC 360 Table J3.1. Interpolates for non-standard diameters.
        """
        pretension_table = BOLT_PRETENSION[self.grade]
        diameters = sorted(pretension_table.keys())
        
        # Exact match
        if self.diameter in pretension_table:
            return pretension_table[self.diameter]
        
        # Interpolate
        if self.diameter < diameters[0]:
            # Extrapolate below minimum
            ratio = (self.diameter / diameters[0]) ** 2
            return pretension_table[diameters[0]] * ratio
        elif self.diameter > diameters[-1]:
            # Extrapolate above maximum
            ratio = (self.diameter / diameters[-1]) ** 2
            return pretension_table[diameters[-1]] * ratio
        else:
            # Linear interpolation
            for i, d in enumerate(diameters):
                if d > self.diameter:
                    d0, d1 = diameters[i - 1], d
                    t0, t1 = pretension_table[d0], pretension_table[d1]
                    t = (self.diameter - d0) / (d1 - d0)
                    return t0 + t * (t1 - t0)
        
        return 0.0
    
    @property
    def capacity(self) -> float:
        """
        Design capacity φR_n per bolt (kN).
        
        For bearing-type: φR_n = φ × F_nv × A_b × n_s
        For slip-critical: φR_n = φ × μ × D_u × h_f × T_b × n_s
        """
        if self.R_n is not None:
            return self.phi * self.R_n
        
        if self.slip_critical:
            # Slip resistance per AISC Eq. J3-4
            mu = SLIP_CLASS_FACTORS[self.slip_class]
            D_u = 1.13  # Ratio of mean installed pretension to specified minimum
            h_f = 1.0   # Filler factor (1.0 for no fillers)
            T_b = self.pretension  # kN
            R_n = mu * D_u * h_f * T_b * self.shear_planes
        else:
            # Shear capacity per AISC Eq. J3-1
            # R_n = F_nv × A_b (per shear plane)
            # Convert to kN: MPa × mm² = N, divide by 1000 for kN
            R_n = self.nominal_shear_strength * self.area * self.shear_planes / 1000
        
        return self.phi * R_n


@dataclass
class BoltProperties:
    """
    Calculated geometric properties of a bolt group.
    
    All properties are calculated about the bolt group centroid.
    """
    Cy: float  # Centroid y-coordinate
    Cz: float  # Centroid z-coordinate
    n: int     # Number of bolts
    Iy: float  # Second moment about y-axis (Σz²)
    Iz: float  # Second moment about z-axis (Σy²)
    Ip: float  # Polar moment (Iy + Iz)


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
        parameters: BoltParameters,
        origin: Point = (0.0, 0.0)
    ) -> BoltGroup:
        """
        Create a bolt group from a rectangular pattern.
        
        Args:
            rows: Number of rows (y-direction)
            cols: Number of columns (z-direction)
            spacing_y: Spacing between rows (mm)
            spacing_z: Spacing between columns (mm)
            parameters: BoltParameters for all bolts
            origin: (y, z) location of bottom-left bolt
            
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
        
        return cls(positions=positions, parameters=parameters)
    
    @classmethod
    def from_circle(
        cls,
        n: int,
        radius: float,
        parameters: BoltParameters,
        center: Point = (0.0, 0.0),
        start_angle: float = 0.0
    ) -> BoltGroup:
        """
        Create a bolt group arranged in a circle.
        
        Args:
            n: Number of bolts
            radius: Circle radius (mm)
            parameters: BoltParameters for all bolts
            center: (y, z) center of circle
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
        """Centroid y-coordinate."""
        return self._calculate_properties().Cy
    
    @property
    def Cz(self) -> float:
        """Centroid z-coordinate."""
        return self._calculate_properties().Cz
    
    @property
    def Iy(self) -> float:
        """Second moment about y-axis (Σz²)."""
        return self._calculate_properties().Iy
    
    @property
    def Iz(self) -> float:
        """Second moment about z-axis (Σy²)."""
        return self._calculate_properties().Iz
    
    @property
    def Ip(self) -> float:
        """Polar moment of inertia (Σr²)."""
        return self._calculate_properties().Ip
    
    def analyze(
        self,
        force: Force,
        method: str = "elastic"
    ) -> BoltResult:
        """
        Analyze bolt group for applied forces.
        
        Args:
            force: Applied Force object
            method: Analysis method - "elastic" or "icr"
            
        Returns:
            BoltResult with force on each bolt
        """
        from .bolt_stress import calculate_elastic_bolt_force, calculate_icr_bolt_force
        
        if method == "elastic":
            return calculate_elastic_bolt_force(self, force)
        elif method == "icr":
            return calculate_icr_bolt_force(self, force)
        else:
            raise ValueError(f"Unknown method: {method}. Use 'elastic' or 'icr'.")


@dataclass
class BoltForce:
    """
    Force result at a specific bolt.
    """
    point: Point
    Fy: float  # Force in y-direction (kN)
    Fz: float  # Force in z-direction (kN)
    
    @property
    def y(self) -> float:
        """Y-coordinate of bolt."""
        return self.point[0]
    
    @property
    def z(self) -> float:
        """Z-coordinate of bolt."""
        return self.point[1]
    
    @property
    def resultant(self) -> float:
        """Resultant force magnitude (kN)."""
        return math.hypot(self.Fy, self.Fz)
    
    @property
    def angle(self) -> float:
        """Angle of resultant force (degrees from +z axis)."""
        return math.degrees(math.atan2(self.Fy, self.Fz))


@dataclass
class BoltResult:
    """
    Complete analysis result for a bolt group.
    
    Follows the same pattern as StressResult for consistent API.
    """
    bolt_group: BoltGroup
    force: Force
    method: str
    bolt_forces: List[BoltForce] = field(default_factory=list)
    
    # ICR-specific results
    icr_point: Point | None = None
    
    # Cached values
    _forces: np.ndarray | None = field(default=None, repr=False)
    
    def _get_forces(self) -> np.ndarray:
        """Get array of resultant forces."""
        if self._forces is None:
            self._forces = np.array([bf.resultant for bf in self.bolt_forces])
        return self._forces
    
    # === Properties (beamy-style) ===
    
    @property
    def max_force(self) -> float:
        """Maximum resultant force on any bolt (kN)."""
        forces = self._get_forces()
        return float(np.max(forces)) if len(forces) > 0 else 0.0
    
    @property
    def max(self) -> float:
        """Alias for max_force."""
        return self.max_force
    
    @property
    def min_force(self) -> float:
        """Minimum resultant force on any bolt (kN)."""
        forces = self._get_forces()
        return float(np.min(forces)) if len(forces) > 0 else 0.0
    
    @property
    def min(self) -> float:
        """Alias for min_force."""
        return self.min_force
    
    @property
    def mean(self) -> float:
        """Average bolt force (kN)."""
        forces = self._get_forces()
        return float(np.mean(forces)) if len(forces) > 0 else 0.0
    
    @property
    def capacity(self) -> float:
        """Design capacity per bolt φR_n (kN)."""
        return self.bolt_group.parameters.capacity
    
    @property
    def critical_bolt(self) -> BoltForce | None:
        """BoltForce at maximum force location."""
        if not self.bolt_forces:
            return None
        return max(self.bolt_forces, key=lambda bf: bf.resultant)
    
    @property
    def critical_index(self) -> int | None:
        """Index of the most stressed bolt."""
        if not self.bolt_forces:
            return None
        max_force = 0.0
        max_idx = 0
        for i, bf in enumerate(self.bolt_forces):
            if bf.resultant > max_force:
                max_force = bf.resultant
                max_idx = i
        return max_idx
    
    @property
    def forces(self) -> List[BoltForce]:
        """All bolt forces."""
        return self.bolt_forces
    
    def utilization(self, capacity: float | None = None) -> float:
        """
        Calculate utilization ratio.
        
        Args:
            capacity: Override capacity (kN). If None, uses bolt capacity.
            
        Returns:
            max_force / capacity (< 1.0 means acceptable)
        """
        if capacity is None:
            capacity = self.capacity
        if capacity <= 0:
            raise ValueError("Capacity must be positive")
        return self.max_force / capacity
    
    def is_adequate(self, capacity: float | None = None) -> bool:
        """Check if bolt group is adequate (utilization ≤ 1.0)."""
        return self.utilization(capacity) <= 1.0
    
    def plot(
        self,
        force: bool = True,
        bolt_forces: bool = True,
        colorbar: bool = True,
        cmap: str = "coolwarm",
        ax=None,
        show: bool = True,
        save_path: str | None = None
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
            
        Returns:
            Matplotlib axes
        """
        from .bolt_plotter import plot_bolt_result
        return plot_bolt_result(
            self,
            force=force,
            bolt_forces=bolt_forces,
            colorbar=colorbar,
            cmap=cmap,
            ax=ax,
            show=show,
            save_path=save_path
        )


# Import Force here to avoid circular import at module level
from .force import Force

