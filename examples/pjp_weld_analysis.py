"""
PJP Weld Analysis

Demonstrates analysis of a Partial Joint Penetration (PJP) weld.
PJP welds use the effective throat thickness (E) for calculation.
"""
from pathlib import Path
from sectiony.library import i
from connecty import Weld, WeldParams, Load, LoadedWeld

def run():
    gallery_dir = Path(__file__).parent.parent / "gallery"
    gallery_dir.mkdir(exist_ok=True)

    # Geometry: I-Beam with PJP Weld on flanges and web
    # For PJP, we specify the effective throat 'E' directly
    section = i(d=300, b=150, tf=12, tw=8, r=12)
    
    # Define PJP weld parameters (geometry only)
    # Effective throat: 8 mm
    params = WeldParams(
        type="pjp",
        throat=8.0  # Effective throat (E)
    )
    
    weld = Weld.from_section(section=section, parameters=params)

    # Loading: Combined shear and moment
    load = Load(
        Fy=-80000,      # 80 kN vertical shear
        Mx=2e6,         # 2 kN·m torsion
        Mz=15e6,        # 15 kN·m bending
        location=(0, 0, 0)
    )
    
    # Analysis (Elastic method for PJP)
    loaded = LoadedWeld(weld, load, method="elastic")
    
    print("=" * 60)
    print("PJP WELD ANALYSIS")
    print("=" * 60)
    print(f"Weld Type: {params.type.upper()}")
    print(f"Effective Throat (E): {weld.parameters.throat} mm")
    print(f"Weld Length: {weld.L:.1f} mm")
    print(f"Weld Area: {weld.A:.1f} mm²")
    print(f"Centroid: ({weld.Cy:.1f}, {weld.Cz:.1f})")
    print("-" * 60)
    print(f"Max Stress: {loaded.max:.1f} MPa")
    print(f"Min Stress: {loaded.min:.1f} MPa")
    print(f"Mean Stress: {loaded.mean:.1f} MPa")
    print("-" * 60)
    
    # Design check example
    print("\nDESIGN CHECK (E70 electrode):")
    F_EXX = 483.0  # MPa
    phi = 0.75
    allowable = phi * 0.60 * F_EXX
    utilization = loaded.max / allowable
    print(f"Allowable stress: {allowable:.1f} MPa")
    print(f"Utilization: {utilization:.1%}")
    print(f"Status: {'✓ PASS' if utilization <= 1.0 else '✗ FAIL'}")
    print("=" * 60)

    # Plot
    save_path = gallery_dir / "pjp_weld_analysis.svg"
    loaded.plot(
        section=True,
        force=True,
        save_path=str(save_path),
        show=False
    )
    print(f"Saved plot to: {save_path.name}")

if __name__ == "__main__":
    run()
