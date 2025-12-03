"""
Example 1: Simple RHS with vertical load (Elastic Method)

Demonstrates basic weld stress analysis on a rectangular hollow section
with a simple vertical load applied at the centroid.
"""
from sectiony.library import rhs
from weldy import Weld, WeldParameters, Force
from pathlib import Path

# Create RHS section
section = rhs(b=100, h=200, t=10, r=15)

# Create weld with 6mm fillet weld
params = WeldParameters(
    weld_type="fillet",
    leg=6.0,           # 6mm leg → throat ≈ 4.2mm
    electrode="E70"    # F_EXX = 483 MPa
)

# Create weld from section
weld = Weld.from_section(section=section, parameters=params)

# Simple vertical load at centroid (no eccentricity)
force = Force(
    Fy=-100000,      # 100kN downward
    location=(0, 0)  # At centroid
)

# Calculate stress using elastic method
result = weld.stress(force, method="elastic")

# Print results
print(f"Weld Properties:")
print(f"  Length: {weld.L:.1f} mm")
print(f"  Area: {weld.A:.1f} mm²")
print(f"  Centroid: ({weld.Cy:.1f}, {weld.Cz:.1f})")
print()
print(f"Stress Results (Elastic Method):")
print(f"  Max stress: {result.max:.1f} MPa")
print(f"  Min stress: {result.min:.1f} MPa")
print(f"  Capacity: {result.capacity:.1f} MPa")
print(f"  Utilization: {result.utilization():.1%}")
print(f"  Adequate: {'✓' if result.is_adequate() else '✗'}")

# Plot and save
gallery_dir = Path(__file__).parent.parent / "gallery"
gallery_dir.mkdir(exist_ok=True)
save_path = gallery_dir / "example1_rhs_simple.svg"

result.plot(
    section=True,
    force=True,
    cmap="coolwarm",
    weld_linewidth=5.0,
    show=False,
    save_path=str(save_path)
)
print(f"\nSaved: {save_path}")
