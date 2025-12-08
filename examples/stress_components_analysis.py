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

# 6mm fillet weld
params = WeldParams(
    type="fillet",
    leg=6.0,
    electrode="E70"
)

weld = Weld.from_section(section=section, parameters=params)

# Combined loading to see all stress components
load = Load(
    Fx=20000,       # 20kN axial
    Fy=-60000,      # 60kN vertical shear
    Fz=30000,       # 30kN horizontal shear
    Mx=3e6,         # 3kNm torsion
    My=2e6,         # 2kNm bending about y
    Mz=5e6,         # 5kNm bending about z
    location=(0, 50, 25)  # Eccentric application
)

# Calculate stress
loaded = LoadedWeld(weld, load, method="elastic")

# Print detailed breakdown
print("STRESS COMPONENT BREAKDOWN")
print("=" * 60)
print(f"\nLoading:")
print(f"  Fx = 20 kN | Fy = -60 kN | Fz = 30 kN")
print(f"  Mx = 3 kNm | My = 2 kNm | Mz = 5 kNm")
print(f"  Location: (50, 25)")
print()

print(f"Overall Results:")
print(f"  Max stress: {loaded.max:.1f} MPa")
print(f"  Min stress: {loaded.min:.1f} MPa")
print(f"  Mean stress: {loaded.mean:.1f} MPa")
print(f"  Range: {loaded.range:.1f} MPa")
print(f"  Utilization: {loaded.utilization():.1%}")
print()

# Get max point details
pt = loaded.max_point
if pt:
    print(f"Maximum Stress Point:")
    print(f"  Location: ({pt.y:.1f}, {pt.z:.1f})")
    print()
    print(f"  Stress Components:")
    c = pt.components
    print(f"    Direct shear (Fy): {c.f_direct_y:.1f} MPa")
    print(f"    Direct shear (Fz): {c.f_direct_z:.1f} MPa")
    print(f"    Moment shear (y):  {c.f_moment_y:.1f} MPa")
    print(f"    Moment shear (z):  {c.f_moment_z:.1f} MPa")
    print(f"    Axial (Fx):        {c.f_axial:.1f} MPa")
    print(f"    Bending:           {c.f_bending:.1f} MPa")
    print()
    print(f"  Combined:")
    print(f"    Total shear:  {c.shear_resultant:.1f} MPa")
    print(f"    Total axial:  {c.total_axial:.1f} MPa")
    print(f"    Resultant:    {c.resultant:.1f} MPa")

# Access stress at specific point
print()
print(f"Stress at (0, 50):")
c_at = loaded.at(0, 50)
print(f"  Shear resultant: {c_at.shear_resultant:.1f} MPa")
print(f"  Total axial: {c_at.total_axial:.1f} MPa")
print(f"  Resultant: {c_at.resultant:.1f} MPa")

# Plot
gallery_dir = Path(__file__).parent.parent / "gallery"
gallery_dir.mkdir(exist_ok=True)
save_path = gallery_dir / "stress_components_breakdown.svg"

loaded.plot(
    section=True,
    cmap="coolwarm",
    weld_linewidth=5.0,
    show=False,
    save_path=str(save_path)
)
print(f"\nSaved: {save_path}")
