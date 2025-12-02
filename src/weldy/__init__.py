"""
Weldy - Weld Stress Analysis Package

A package for calculating and visualizing stress distribution along welded
connections in structural engineering applications.

Example usage:
    from sectiony.library import rhs
    from weldy import WeldedSection, WeldParameters, Force
    
    # Create a section
    section = rhs(b=100, h=200, t=10, r=15)
    
    # Create welded section and add welds
    welded = WeldedSection(section=section)
    params = WeldParameters(weld_type="fillet", throat_thickness=5.0)
    welded.weld_all_segments(params)
    
    # Define force
    force = Force(Fy=-50000, location=(100, 50))
    
    # Plot stress distribution
    welded.plot_weld_stress(force)
"""

from .weld import (
    WeldParameters,
    WeldSegment,
    WeldGroup,
    WeldGroupProperties,
)

from .force import Force

from .stress import (
    StressComponents,
    PointStress,
    WeldStressResult,
    WeldStressCalculator,
    calculate_weld_stress,
)

from .section import (
    WeldedSection,
    create_welded_section,
)

from .plotter import (
    plot_weld_stress,
    plot_weld_stress_components,
)

__all__ = [
    # Weld definitions
    "WeldParameters",
    "WeldSegment", 
    "WeldGroup",
    "WeldGroupProperties",
    # Force
    "Force",
    # Stress calculation
    "StressComponents",
    "PointStress",
    "WeldStressResult",
    "WeldStressCalculator",
    "calculate_weld_stress",
    # Section
    "WeldedSection",
    "create_welded_section",
    # Plotting
    "plot_weld_stress",
    "plot_weld_stress_components",
]

__version__ = "0.1.0"
