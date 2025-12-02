"""
Example 2: RHS with eccentric load and torsion

Shows how eccentric loading creates torsional and bending stresses.
"""
from sectiony.library import rhs
from weldy import WeldedSection, WeldParameters, Force

section = rhs(b=150, h=300, t=12, r=20)
welded = WeldedSection(section=section)

weld_params = WeldParameters(
    weld_type="fillet",
    throat_thickness=5.0,
    leg_size=7.0
)

welded.weld_all_segments(weld_params)

# Eccentric load with torsion
force = Force(
    Fy=-80000,   # 80kN downward
    Fz=20000,    # 20kN horizontal
    Mx=2e6,      # 2kNm torsion
    location=(120, 50)  # Eccentric location
)

from pathlib import Path

# ... (imports)

# ... (code)

gallery_dir = Path(__file__).parent.parent / "gallery"
gallery_dir.mkdir(exist_ok=True)
save_path = gallery_dir / "example2_rhs_eccentric.svg"

welded.plot_weld_stress(
    force,
    cmap="plasma",
    weld_linewidth=6.0,
    show=False,
    save_path=str(save_path)
)
print(f"Saved: {save_path}")

