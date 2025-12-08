"""
PJP Weld Analysis

Demonstrates analysis of a Partial Joint Penetration (PJP) weld.
PJP welds typically use the effective throat thickness (E) for calculation.
"""
from pathlib import Path
from sectiony.library import i
from connecty import Weld, WeldParams, Load, LoadedWeld

def run():
    gallery_dir = Path(__file__).parent.parent / "gallery"
    gallery_dir.mkdir(exist_ok=True)

    # 1. Geometry: I-Beam with PJP Weld on flanges and web
    # For PJP, we specify the effective throat 'E' directly via 'throat' parameter
    # or by specifying leg/depth if applicable. Here we define effective throat.
    section = i(d=300, b=150, tf=12, tw=8, r=12)
    
    # Define PJP weld parameters
    # E70 electrode, 8mm effective throat
    params = WeldParams(
        type="pjp",
        throat=8.0,      # Effective throat (E)
        electrode="E70"
    )
    
    weld = Weld.from_section(section=section, parameters=params)

    # 2. Loading: Combined shear and moment
    load = Load(
        Fy=-80000,      # 80kN vertical shear
        Mx=2e6,         # 2kNm torsion
        Mz=15e6,        # 15kNm bending
        location=(0, 0, 0)
    )
    
    # 3. Analysis (Elastic method is standard for PJP)
    loaded = LoadedWeld(weld, load, method="elastic")
    
    print("=" * 60)
    print("PJP WELD ANALYSIS")
    print("=" * 60)
    print(f"Throat (Effective): {weld.parameters.throat} mm")
    print(f"Weld Length: {weld.L:.1f} mm")
    print(f"Weld Area:   {weld.A:.1f} mm²")
    print("-" * 60)
    print(f"Max Stress:  {loaded.max:.1f} MPa")
    print(f"Capacity:    {loaded.capacity:.1f} MPa")
    print(f"Utilization: {loaded.utilization():.1%}")
    print("=" * 60)

    # 4. Plot
    save_path = gallery_dir / "pjp_weld_analysis.svg"
    loaded.plot(
        section=True,
        legend=True,
        save_path=str(save_path),
        show=False
    )
    print(f"Saved plot to: {save_path.name}")

if __name__ == "__main__":
    run()

