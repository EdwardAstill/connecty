"""
Example 9: Weld Method Comparison (Elastic vs ICR)

Demonstrates how to plot both Elastic and ICR results side-by-side (stacked)
with a shared color scale for easy comparison.
"""
from sectiony.library import rhs
from connecty import Weld, WeldParameters, Force
from pathlib import Path

# 1. Create RHS section and weld
section = rhs(b=150, h=250, t=10, r=15)
params = WeldParameters(
    weld_type="fillet",
    leg=6.0,
    electrode="E70"
)

weld = Weld.from_section(section=section, parameters=params)

# 2. Define eccentric load
# Large eccentricity to show difference between methods
force = Force(
    Fy=-150000,        # 150kN downward
    location=(0, 100)  # 100mm eccentricity (creates Mx torsion)
)

# 3. Calculate both results explicitly (Optional)
# You can pass these to plot, or just let plot calculate them from force
elastic = weld.stress(force, method="elastic")
icr = weld.stress(force, method="icr")

print(" Comparison:")
print(f"Elastic Max: {elastic.max:.1f} MPa")
print(f"ICR Max:     {icr.max:.1f} MPa")
print(f"Difference:  {(1 - icr.max/elastic.max):.1%}")

# 4. Plot Comparison
gallery_dir = Path(__file__).parent.parent / "gallery"
gallery_dir.mkdir(exist_ok=True)
save_path = gallery_dir / "example9_comparison.svg"

# Option A: Pass results explicitly
# legend=True shows applied loads in a legend box
weld.plot(
    stress=[elastic, icr],
    # method="both",  # Not required if list of results passed
    section=True,
    legend=True,  # Shows applied loads legend (Fy, Mx, etc.)
    save_path=str(save_path),
    show=False
)

# Option B: Let plot calculate them (equivalent)
# weld.plot(
#     force=force,
#     method="both",
#     section=True,
#     legend=True,
#     save_path=str(save_path)
# )

print(f"\nSaved comparison plot to: {save_path}")

