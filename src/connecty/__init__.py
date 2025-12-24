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
    from connecty import BoltGroup, BoltParameters, Load
    
    # Create bolt group from pattern
    params = BoltParameters(diameter=20)
    bolts = BoltGroup.from_pattern(
        rows=3, cols=2, spacing_y=75, spacing_z=60, diameter=20
    )
    
    # Define load
    load = Load(Fy=-100e3, location=(150, 0))
    
    # Analyze (elastic or icr method)
    result = bolts.analyze(load, method="elastic")
    
    # Access results
    print(f"Max force: {result.max_force:.1f} kN")
    
    # Design check (you define capacity)
    bolt_capacity = 87.8  # kN (A325 M20)
    if result.max_force <= bolt_capacity:
        print(f"OK: {result.max_force/bolt_capacity:.1%}")
    
    # Plot
    result.plot(force=True, bolt_forces=True)
"""

from .weld import (
    Weld,
    WeldParams,
    WeldProperties,
    WeldedSection,
    WeldGroup,
    WeldSegment,
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

from .common import Load, Force

from .bolt import (
    BoltGroup,
    BoltParameters,
    BoltProperties,
    BoltResult,
    ConnectionResult,
    plot_bolt_result,
    plot_bolt_pattern,
    BoltConnection,
    ConnectionLoad,
    Plate,
)

from .bolt.checks import BoltCheckResult

__all__ = [
    # Main weld classes
    "Weld",
    "WeldParams",
    "WeldProperties",
    "WeldedSection",
    "WeldGroup",
    "WeldSegment",
    "Load",
    "Force",
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
    "ConnectionResult",
    "BoltConnection",
    "ConnectionLoad",
    "Plate",
    "BoltCheckResult",
    # Bolt functions
    "plot_bolt_result",
    "plot_bolt_pattern",
]

# Backward-friendly aliases used by existing scripts/tests.
WeldParameters = WeldParams

__version__ = "0.3.0"
