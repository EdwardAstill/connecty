"""
Connecty - Weld and Bolt Connection Analysis Package

Calculate and visualize stress/force distribution along welded and bolted
connections per AISC 360 using Elastic and ICR methods.

Example usage (Welds):
    from sectiony.library import rhs
    from connecty import Weld, WeldParams, Load, LoadedWeld
    
    # Create weld from section
    section = rhs(b=100, h=200, t=10, r=15)
    params = WeldParams(type="fillet", leg=6.0)
    weld = Weld.from_section(section=section, parameters=params)
    
    # Define load
    load = Load(Fy=-100e3, location=(100, 0))
    
    # Create loaded weld with analysis method
    loaded = LoadedWeld(weld, load, method="elastic")
    
    # Access results (beamy-style)
    print(f"Max stress: {loaded.max:.1f} MPa")
    
    # Plot results
    loaded.plot(section=True)
    
    # Design check (you define allowable)
    allowable_stress = 0.75 * 0.60 * 483.0  # E70 electrode
    if loaded.max <= allowable_stress:
        print(f"OK: {loaded.max/allowable_stress:.1%}")

Example usage (Bolts):
    from connecty import BoltGroup, Plate, BoltConnection, Load
    
    # 1. Create bolt group from pattern
    bolts = BoltGroup.from_pattern(
        rows=3, cols=2, spacing_y=75, spacing_z=60, diameter=20,
        offset_y=10.0, offset_z=-5.0
    )
    
    # 2. Define plate and connection
    plate = Plate.from_dimensions(width=200.0, height=300.0, center=(0.0, 0.0), thickness=12.0, fu=450.0, fy=350.0)
    connection = BoltConnection(bolt_group=bolts, plate=plate)
    
    # 3. Define load
    load = Load(Fy=-100e3, location=(75, 150, 100))
    
    # 4. Analyze
    result = connection.analyze(load, shear_method="elastic", tension_method="conservative")
    
    # 5. Access results
    print(f"Max shear force: {result.max_shear_force:.1f} N")
    
    # 6. Design check (AISC 360-22)
    check = result.check(connection_type="bearing", threads_in_shear_plane=True)
    if check.governing_utilization <= 1.0:
        print(f"OK: {check.governing_utilization:.1%}")
    
    # 7. Plot
    result.plot(force=True, bolt_forces=True)
"""

from .weld import (
    Weld,
    WeldParams,
    WeldProperties,
    WeldedSection,
    WeldGroup,
    WeldSegment,
    WeldConnection,
    WeldBaseMetal,
    LoadedWeldConnection,
    LoadedWeld,
    StressComponents,
    PointStress,
    calculate_elastic_stress,
    calculate_icr_stress,
    plot_stress_result,
    plot_stress_comparison,
    plot_weld_geometry,
    plot_stress_components,
    plot_loaded_weld,
    plot_loaded_weld_comparison,
)

from .common import Load

from .bolt import (
    BoltGroup,
    BoltParameters,
    BoltProperties,
    BoltResult,
    LoadedBoltConnection,
    plot_bolt_result,
    plot_bolt_pattern,
    BoltConnection,
    Plate,
)

from .bolt.checks import BoltCheckDetail, BoltCheckResult
from .weld.checks import WeldCheckDetail, WeldCheckResult

__all__ = [
    # Main weld classes
    "Weld",
    "WeldParams",
    "WeldProperties",
    "WeldedSection",
    "WeldGroup",
    "WeldSegment",
    "WeldConnection",
    "WeldBaseMetal",
    "LoadedWeldConnection",
    "Load",
    "LoadedWeld",
    # Weld stress results
    "StressComponents",
    "PointStress",
    # Weld functions
    "calculate_elastic_stress",
    "calculate_icr_stress",
    "plot_stress_result",
    "plot_stress_comparison",
    "plot_weld_geometry",
    "plot_stress_components",
    "plot_loaded_weld",
    "plot_loaded_weld_comparison",
    # Bolt classes
    "BoltGroup",
    "BoltParameters",
    "BoltProperties",
    "BoltResult",
    "LoadedBoltConnection",
    "BoltConnection",
    "Plate",
    "BoltCheckResult",
    "BoltCheckDetail",
    "WeldCheckResult",
    "WeldCheckDetail",
    # Bolt functions
    "plot_bolt_result",
    "plot_bolt_pattern",
]

__version__ = "0.3.0"
