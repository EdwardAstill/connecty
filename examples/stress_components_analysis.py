"""
Detailed stress component breakdown

Demonstrates accessing individual stress components and plotting
them separately for detailed analysis.
"""
from sectiony.library import rhs
from connecty import Weld, WeldParams, Load, LoadedWeld
from pathlib import Path

# Create RHS section
section = rhs(b=100, h=150, t=8, r=10)

# 6 mm fillet weld (geometry only)
params = WeldParams(
    type="fillet",
    leg=6.0
)

weld = Weld.from_section(section=section, parameters=params)

# Combined loading to see all stress components
load = Load(
    Fx=20000,       # 20 kN axial
    Fy=-60000,      # 60 kN vertical shear
    Fz=30000,       # 30 kN horizontal shear
    Mx=3e6,         # 3 kN·m torsion
    My=2e6,         # 2 kN·m bending about y
    Mz=5e6,         # 5 kN·m bending about z
    location=(0, 50, 25)  # Eccentric application
)

# Calculate stress
loaded = LoadedWeld(weld, load, method="elastic")

# Print detailed breakdown
print("STRESS COMPONENT BREAKDOWN")
print("=" * 60)
print(f"\nWeld Properties:")
print(f"  Type: {params.type.upper()}")
print(f"  Leg size: {params.leg:.1f} mm")
print(f"  Throat: {weld.parameters.throat:.2f} mm")
print(f"  Length: {weld.L:.1f} mm")
print(f"  Area: {weld.A:.1f} mm²")

print(f"\nApplied Loading:")
print(f"  Fx = 20 kN | Fy = -60 kN | Fz = 30 kN")
print(f"  Mx = 3 kN·m | My = 2 kN·m | Mz = 5 kN·m")
print(f"  Location: (50, 25) mm")
print()

print(f"Overall Results:")
print(f"  Max stress: {loaded.max:.1f} MPa")
print(f"  Min stress: {loaded.min:.1f} MPa")
print(f"  Mean stress: {loaded.mean:.1f} MPa")
print(f"  Range: {loaded.range:.1f} MPa")
print()

# Get max point details
pt = loaded.max_point
if pt:
    print(f"Maximum Stress Point:")
    print(f"  Location: ({pt.y:.1f}, {pt.z:.1f})")
    print()
    print(f"  Stress Components (MPa):")
    c = pt.components
    print(f"    Direct shear Y (Fy): {c.f_direct_y:.1f}")
    print(f"    Direct shear Z (Fz): {c.f_direct_z:.1f}")
    print(f"    Moment shear Y (Mx): {c.f_moment_y:.1f}")
    print(f"    Moment shear Z (Mx): {c.f_moment_z:.1f}")
    print(f"    Axial (Fx):          {c.f_axial:.1f}")
    print(f"    Bending (My, Mz):    {c.f_bending:.1f}")
    print()
    print(f"  Combined Stresses (MPa):")
    print(f"    Total shear Y:  {c.total_y:.1f}")
    print(f"    Total shear Z:  {c.total_z:.1f}")
    print(f"    Shear resultant: {c.shear_resultant:.1f}")
    print(f"    Total axial:    {c.total_axial:.1f}")
    print(f"    Resultant:      {c.resultant:.1f}")

# Access stress at specific point
print()
print(f"Stress at arbitrary point (y=0, z=50):")
c_at = loaded.at(y=0, z=50)
print(f"  Shear resultant: {c_at.shear_resultant:.1f} MPa")
print(f"  Total axial: {c_at.total_axial:.1f} MPa")
print(f"  Resultant: {c_at.resultant:.1f} MPa")

# Design check
print()
print("DESIGN CHECK (E70 electrode):")
F_EXX = 483.0  # MPa
phi = 0.75
allowable = phi * 0.60 * F_EXX
utilization = loaded.max / allowable
print(f"  Allowable stress: {allowable:.1f} MPa")
print(f"  Utilization: {utilization:.1%}")
print(f"  Status: {'✓ PASS' if utilization <= 1.0 else '✗ FAIL'}")

# Plot
gallery_dir = Path(__file__).parent.parent / "gallery"
gallery_dir.mkdir(exist_ok=True)
save_path = gallery_dir / "stress_components_breakdown.svg"

loaded.plot(
    section=True,
    force=True,
    cmap="coolwarm",
    weld_linewidth=5.0,
    show=False,
    save_path=str(save_path)
)
print(f"\nSaved: {save_path}")
