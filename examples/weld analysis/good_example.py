"""
ICR method for an eccentrically loaded RHS.

Highlights ICR vs elastic stress distribution for an offset weld.
"""
from pathlib import Path
from sectiony.library import rhs
from connecty import Load, Weld, WeldParams, LoadedWeld


def run() -> None:
    section = rhs(b=150, h=75, t=10, r=12)
    Fy = -140000
    Fz = 45000
    location = (0, 20, -55)

    params = WeldParams(type="fillet", leg=8.0)
    weld = Weld.from_section(section=section, parameters=params)

    load = Load(Fy=Fy, Fz=Fz, location=location)
    Mx, _, _ = load.get_moments_about(0, weld.Cy, weld.Cz)

    print("=" * 60)
    print("Eccentrically Loaded RHS Weld - ICR vs Elastic")
    print("=" * 60)
    print(f"Mx (eccentric) = {Mx/1e6:.1f} kN·m")

    loaded_elastic = LoadedWeld(weld, load, method="elastic")
    loaded_icr = LoadedWeld(weld, load, method="icr")

    print("\nElastic Method:")
    print(f"  Max: {loaded_elastic.max:.1f} MPa | Range: {loaded_elastic.range:.1f} MPa")

    print("\nICR Method:")
    print(f"  Max: {loaded_icr.max:.1f} MPa | Range: {loaded_icr.range:.1f} MPa")
    if loaded_icr.icr_point is not None:
        print(f"  ICR: ({loaded_icr.icr_point[0]:.1f}, {loaded_icr.icr_point[1]:.1f}) mm")

    # Design check example
    F_EXX = 483.0
    phi = 0.75
    allowable = phi * 0.60 * F_EXX
    elastic_util = loaded_elastic.max / allowable
    icr_util = loaded_icr.max / allowable
    print("\nDesign Check (E70):")
    print(f"  Elastic util: {elastic_util:.1%}")
    print(f"  ICR util:    {icr_util:.1%}")

    # Plot
    gallery_dir = Path(__file__).parent.parent / "gallery"
    gallery_dir.mkdir(exist_ok=True)
    save_path_icr = gallery_dir / "icr_rhs_eccentric_load.svg"
    loaded_icr.plot(
        section=True,
        force=True,
        cmap="coolwarm",
        weld_linewidth=5.0,
        info=True,
        show=False,
        save_path=str(save_path_icr)
    )
    print(f"Saved: {save_path_icr}")


if __name__ == "__main__":
    run()
