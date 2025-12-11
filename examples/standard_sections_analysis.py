"""
Standard section geometries with common loads.

Demonstrates weld stress analysis on typical structural sections
(RHS, I-beam, channel, CHS).
"""
from pathlib import Path
from common_geometry import (
    get_rhs_weld, 
    get_ibeam_weld, 
    get_channel_weld, 
    get_chs_weld
)
from common_loads import get_vertical_shear, get_combined_load

def run():
    from connecty import LoadedWeld
    
    gallery_dir = Path(__file__).parent.parent / "gallery"
    gallery_dir.mkdir(exist_ok=True)

    # 1. RHS - Simple vertical load
    print("1. RHS with vertical shear...")
    weld = get_rhs_weld()
    load = get_vertical_shear(100)
    loaded = LoadedWeld(weld, load, method="elastic")
    print(f"   Max stress: {loaded.max:.1f} MPa")
    loaded.plot(
        section=True,
        force=True,
        save_path=str(gallery_dir / "rhs_simple_vertical_load.svg"), 
        show=False
    )

    # 2. I-Beam - Combined loading
    print("2. I-beam with combined loading...")
    weld = get_ibeam_weld()
    load = get_combined_load()
    loaded = LoadedWeld(weld, load, method="elastic")
    print(f"   Max stress: {loaded.max:.1f} MPa")
    loaded.plot(
        section=True,
        force=True,
        save_path=str(gallery_dir / "i_beam_combined_load.svg"), 
        show=False
    )

    # 3. Channel - Vertical load
    print("3. Channel with vertical shear...")
    weld = get_channel_weld()
    load = get_vertical_shear(50)
    loaded = LoadedWeld(weld, load, method="elastic")
    print(f"   Max stress: {loaded.max:.1f} MPa")
    loaded.plot(
        section=True,
        force=True,
        save_path=str(gallery_dir / "u_channel_vertical_load.svg"), 
        show=False
    )

    # 4. CHS - Vertical load
    print("4. CHS with vertical shear...")
    weld = get_chs_weld()
    load = get_vertical_shear(80)
    loaded = LoadedWeld(weld, load, method="elastic")
    print(f"   Max stress: {loaded.max:.1f} MPa")
    loaded.plot(
        section=True,
        force=True,
        save_path=str(gallery_dir / "chs_vertical_load.svg"), 
        show=False
    )

    print("\nAll plots saved to gallery/")

if __name__ == "__main__":
    run()
