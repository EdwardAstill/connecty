"""
Refactored Example 2: Comparisons and stacking layouts.
"""
from pathlib import Path
from common_geometry import get_rhs_weld, get_wide_rhs_weld
from common_loads import get_eccentric_load

def run():
    from connecty import LoadedWeld
    
    gallery_dir = Path(__file__).parent.parent / "gallery"
    gallery_dir.mkdir(exist_ok=True)

    # 1. Standard Comparison (Horizontal stack usually)
    weld = get_rhs_weld()
    # High eccentricity to emphasize difference
    load = get_eccentric_load(mag_kn=150, ecc_z=100)
    loaded = LoadedWeld(weld, load, method="both")
    
    loaded.plot(
        section=True,
        legend=True,
        save_path=str(gallery_dir / "elastic_vs_icr_rhs.svg"),
        show=False
    )
    print("Saved elastic_vs_icr_rhs.svg")

    # 2. Wide/Long Weld Comparison (Vertical stack)
    weld_wide = get_wide_rhs_weld()
    load_wide = get_eccentric_load(mag_kn=150, ecc_z=0, ecc_y=30)
    loaded_wide = LoadedWeld(weld_wide, load_wide, method="both")
    
    loaded_wide.plot(
        section=True,
        legend=True,
        save_path=str(gallery_dir / "elastic_vs_icr_wide_rhs_vertical_stack.svg"),
        show=False
    )
    print("Saved elastic_vs_icr_wide_rhs_vertical_stack.svg")

if __name__ == "__main__":
    run()

