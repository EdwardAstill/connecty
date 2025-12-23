"""
Elastic vs ICR method comparison for fillet welds.
"""
from pathlib import Path
from common.common_geometry import get_rhs_weld, get_wide_rhs_weld
from common.common_loads import get_eccentric_load


def run():
    from connecty import LoadedWeld

    gallery_dir = Path(__file__).parent.parent / "gallery"
    gallery_dir.mkdir(exist_ok=True)

    print("1. Standard RHS - Elastic vs ICR comparison...")
    weld = get_rhs_weld()
    load = get_eccentric_load(mag_kn=150, ecc_z=100)

    loaded_elastic = LoadedWeld(weld, load, method="elastic")
    loaded_icr = LoadedWeld(weld, load, method="icr")
    reduction = (1 - loaded_icr.max / loaded_elastic.max) * 100
    print(f"   Elastic: {loaded_elastic.max:.1f} MPa | ICR: {loaded_icr.max:.1f} MPa | Reduction: {reduction:.1f}%")

    loaded_elastic.plot(section=True, force=True, save_path=str(gallery_dir / "elastic_vs_icr_rhs_elastic.svg"), show=False)
    loaded_icr.plot(section=True, force=True, save_path=str(gallery_dir / "elastic_vs_icr_rhs_icr.svg"), show=False)

    print("\n2. Wide RHS - Vertical eccentricity...")
    weld_wide = get_wide_rhs_weld()
    load_wide = get_eccentric_load(mag_kn=150, ecc_z=0, ecc_y=30)

    loaded_wide_elastic = LoadedWeld(weld_wide, load_wide, method="elastic")
    loaded_wide_icr = LoadedWeld(weld_wide, load_wide, method="icr")
    reduction_wide = (1 - loaded_wide_icr.max / loaded_wide_elastic.max) * 100
    print(f"   Elastic: {loaded_wide_elastic.max:.1f} MPa | ICR: {loaded_wide_icr.max:.1f} MPa | Reduction: {reduction_wide:.1f}%")

    loaded_wide_elastic.plot(section=True, force=True, save_path=str(gallery_dir / "elastic_vs_icr_wide_rhs_elastic.svg"), show=False)
    loaded_wide_icr.plot(section=True, force=True, save_path=str(gallery_dir / "elastic_vs_icr_wide_rhs_icr.svg"), show=False)

    print("\nAll plots saved to gallery/")


if __name__ == "__main__":
    run()
