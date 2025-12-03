"""
Example 3: I-Beam section with combined loading

Demonstrates weld stress analysis on an I-beam section
with axial force, shear, and bending moment.
"""
from sectiony.library import i
from connecty import Weld, WeldParameters, Force
from pathlib import Path

# Create I-section: 200mm deep, 100mm wide, 12mm flange, 8mm web
section = i(d=200, b=100, tf=12, tw=8, r=8)

# 8mm fillet weld around entire section
params = WeldParameters(
    weld_type="fillet",
    leg=8.0,
    electrode="E70"
)

weld = Weld.from_section(section=section, parameters=params)

# Combined loading: axial + shear + moment
force = Force(
    Fx=50000,      # 50kN axial tension
    Fy=-80000,     # 80kN vertical shear
    Mz=20e6,       # 20kNm bending moment
    location=(0, 0)
)

# Calculate stress
result = weld.stress(force, method="elastic")

# Print results
print("I-BEAM WELD ANALYSIS")
print("=" * 50)
print(f"\nSection: I 200×100×12×8")
print(f"Weld: 8mm fillet")
print(f"\nLoading:")
print(f"  Fx = 50 kN (tension)")
print(f"  Fy = -80 kN (shear)")
print(f"  Mz = 20 kNm (bending)")
print()

print(f"Weld Properties:")
print(f"  Length: {weld.L:.1f} mm")
print(f"  Area: {weld.A:.1f} mm²")
print(f"  Iy: {weld.Iy:.0f} mm⁴")
print(f"  Iz: {weld.Iz:.0f} mm⁴")
print()

print(f"Results:")
print(f"  Max stress: {result.max:.1f} MPa")
print(f"  Capacity: {result.capacity:.1f} MPa")
print(f"  Utilization: {result.utilization():.1%}")
print(f"  Adequate: {'✓' if result.is_adequate() else '✗'}")

# Check max point location
pt = result.max_point
if pt:
    print(f"\nMax stress location: ({pt.y:.1f}, {pt.z:.1f})")
    print(f"  Direct shear: {pt.components.shear_resultant:.1f} MPa")
    print(f"  Axial + bending: {pt.components.total_axial:.1f} MPa")

# Plot
gallery_dir = Path(__file__).parent.parent / "gallery"
gallery_dir.mkdir(exist_ok=True)
save_path = gallery_dir / "example3_i_beam.svg"

result.plot(
    section=True,
    force=True,
    cmap="coolwarm",
    weld_linewidth=5.0,
    show=False,
    save_path=str(save_path)
)
print(f"\nSaved: {save_path}")
