"""
Refactored Example 1: Standard geometries with common loads.
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

    # 1. RHS Simple
    weld = get_rhs_weld()
    load = get_vertical_shear(100)
    loaded = LoadedWeld(weld, load, method="elastic")
    loaded.plot(save_path=str(gallery_dir / "rhs_simple_vertical_load.svg"), show=False)
    print("Saved rhs_simple_vertical_load.svg")

    # 2. I-Beam Combined
    weld = get_ibeam_weld()
    load = get_combined_load()
    loaded = LoadedWeld(weld, load, method="elastic")
    loaded.plot(save_path=str(gallery_dir / "i_beam_combined_load.svg"), show=False)
    print("Saved i_beam_combined_load.svg")

    # 3. Channel Vertical
    weld = get_channel_weld()
    load = get_vertical_shear(50)
    loaded = LoadedWeld(weld, load, method="elastic")
    loaded.plot(save_path=str(gallery_dir / "u_channel_vertical_load.svg"), show=False)
    print("Saved u_channel_vertical_load.svg")

    # 4. CHS Vertical
    weld = get_chs_weld()
    load = get_vertical_shear(80)
    loaded = LoadedWeld(weld, load, method="elastic")
    loaded.plot(save_path=str(gallery_dir / "chs_vertical_load.svg"), show=False)
    print("Saved chs_vertical_load.svg")

if __name__ == "__main__":
    run()

