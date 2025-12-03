"""
Weldy - Weld Stress Analysis Package

Calculate and visualize stress distribution along welded connections
per AISC 360 using Elastic and ICR methods.

Example usage:
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

__all__ = [
    # Main classes
    "Weld",
    "WeldParameters",
    "WeldProperties",
    "WeldedSection",
    "WeldGroup",
    "WeldSegment",
    "Force",
    # Stress results
    "StressComponents",
    "PointStress",
    "StressResult",
    # Functions
    "calculate_elastic_stress",
    "calculate_icr_stress",
    "plot_stress_result",
    "plot_stress_components",
    # Data
    "ELECTRODE_STRENGTH",
]

__version__ = "0.2.0"
