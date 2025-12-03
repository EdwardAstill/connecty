"""
Weldy - Weld and Bolt Connection Analysis Package

Calculate and visualize stress/force distribution along welded and bolted
connections per AISC 360 using Elastic and ICR methods.

Example usage (Welds):
    from sectiony.library import rhs
    from weldy import Weld, WeldParameters, Force
    
    # Create weld from section
    section = rhs(b=100, h=200, t=10, r=15)
    params = WeldParameters(weld_type="fillet", leg=6.0, electrode="E70")
    weld = Weld.from_section(section=section, parameters=params)
    
    # Define force
    force = Force(Fy=-100e3, location=(100, 0))
    
    # Calculate stress (elastic or icr method)
    result = weld.stress(force, method="elastic")
    
    # Access results (beamy-style)
    print(f"Max stress: {result.max:.1f} MPa")
    print(f"Utilization: {result.utilization():.1%}")
    
    # Plot
    result.plot(section=True, force=True)

Example usage (Bolts):
    from weldy import BoltGroup, BoltParameters, Force
    
    # Create bolt group from pattern
    params = BoltParameters(diameter=20, grade="A325")
    bolts = BoltGroup.from_pattern(
        rows=3, cols=2, spacing_y=75, spacing_z=60, parameters=params
    )
    
    # Define force
    force = Force(Fy=-100e3, location=(150, 0))
    
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
    WeldParameters,
    WeldProperties,
    ELECTRODE_STRENGTH,
)

from .welded_section import (
    WeldedSection,
    WeldGroup,
    WeldSegment,
)

from .force import Force

from .stress import (
    StressComponents,
    PointStress,
    StressResult,
    calculate_elastic_stress,
    calculate_icr_stress,
)

from .plotter import (
    plot_stress_result,
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
    "WeldParameters",
    "WeldProperties",
    "WeldedSection",
    "WeldGroup",
    "WeldSegment",
    "Force",
    # Weld stress results
    "StressComponents",
    "PointStress",
    "StressResult",
    # Weld functions
    "calculate_elastic_stress",
    "calculate_icr_stress",
    "plot_stress_result",
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
