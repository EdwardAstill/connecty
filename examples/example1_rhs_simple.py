"""
Example 1: Simple RHS with vertical load

Demonstrates basic weld stress analysis on a rectangular hollow section
with a simple vertical load.
"""
from sectiony.library import rhs
from weldy import WeldedSection, WeldParameters, Force

# Create RHS section
section = rhs(b=100, h=200, t=10, r=15)

# Create welded section
welded = WeldedSection(section=section)

# Define 6mm fillet weld
weld_params = WeldParameters(
    weld_type="fillet",
    throat_thickness=4.2,
    leg_size=6.0
)

# Weld all outer edges
welded.weld_all_segments(weld_params)

# Simple vertical load at center
force = Force(
    Fy=-100000,  # 100kN downward
    location=(0, 0)  # At centroid
)

from pathlib import Path

# ... (imports)

# ... (code)

# Plot and save
gallery_dir = Path(__file__).parent.parent / "gallery"
gallery_dir.mkdir(exist_ok=True)
save_path = gallery_dir / "example1_rhs_simple.svg"

welded.plot_weld_stress(
    force,
    cmap="coolwarm",
    weld_linewidth=5.0,
    show=False,
    save_path=str(save_path)
)
print(f"Saved: {save_path}")

