"""
Connecty - Weld and Bolt Connection Analysis Package

Calculate and visualize stress/force distribution along welded and bolted
connections per AISC 360 using Elastic and ICR methods.

Example usage (Welds):
    from sectiony.library import rhs
    from connecty import Weld, WeldParams, Load, LoadedWeld
    
    # Create weld from section
    section = rhs(b=100, h=200, t=10, r=15)
    params = WeldParams(type="fillet", leg=6.0, electrode="E70")
    weld = Weld.from_section(section=section, parameters=params)
    
    # Define load
    load = Load(Fy=-100e3, location=(100, 0))
    
    # Create loaded weld with analysis method
    loaded = LoadedWeld(weld, load, method="elastic")
    
    # Access results (beamy-style)
    print(f"Max stress: {loaded.max:.1f} MPa")
    print(f"Utilization: {loaded.utilization():.1%}")
    
    # Plot results
    loaded.plot(section=True)
    
    # Or compare methods
    loaded_both = LoadedWeld(weld, load, method="both")
    loaded_both.plot()

Example usage (Bolts):
    from connecty import BoltGroup, BoltParameters, Load
    
    # Create bolt group from pattern
    params = BoltParameters(diameter=20, grade="A325")
    bolts = BoltGroup.from_pattern(
        rows=3, cols=2, spacing_y=75, spacing_z=60, parameters=params
    )
    
    # Define load
    load = Load(Fy=-100e3, location=(150, 0))
    
    # Analyze (elastic or icr method)
    result = bolts.analyze(force, method="elastic")
    
    # Access results
    print(f"Max force: {result.max_force:.1f} kN")
    print(f"Utilization: {result.utilization():.1%}")
    
    # Plot
    result.plot(force=True, bolt_forces=True)
"""

from .weld import (
    Weld,
    WeldParams,
    WeldProperties,
    ELECTRODE_STRENGTH,
)

from .welded_section import (
    WeldedSection,
    WeldGroup,
    WeldSegment,
)

from .load import Load

from .loaded_weld import LoadedWeld

from .weld_stress import (
    StressComponents,
    PointStress,
    calculate_elastic_stress,
    calculate_icr_stress,
)

from .weld_plotter import (
    plot_stress_result,
    plot_stress_comparison,
    plot_weld_geometry,
    plot_stress_components,
)

from .bolt import (
    BoltGroup,
    BoltParameters,
    BoltProperties,
    BoltForce,
    BoltResult,
    BOLT_SHEAR_STRENGTH,
    SLIP_CLASS_FACTORS,
    BOLT_PRETENSION,
)

from .bolt_stress import (
    calculate_elastic_bolt_force,
    calculate_icr_bolt_force,
)

from .bolt_plotter import (
    plot_bolt_result,
    plot_bolt_pattern,
)

__all__ = [
    # Main weld classes
    "Weld",
    "WeldParams",
    "WeldProperties",
    "WeldedSection",
    "WeldGroup",
    "WeldSegment",
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
    # Weld data
    "ELECTRODE_STRENGTH",
    # Bolt classes
    "BoltGroup",
    "BoltParameters",
    "BoltProperties",
    "BoltForce",
    "BoltResult",
    # Bolt functions
    "calculate_elastic_bolt_force",
    "calculate_icr_bolt_force",
    "plot_bolt_result",
    "plot_bolt_pattern",
    # Bolt data
    "BOLT_SHEAR_STRENGTH",
    "SLIP_CLASS_FACTORS",
    "BOLT_PRETENSION",
]

__version__ = "0.3.0"
