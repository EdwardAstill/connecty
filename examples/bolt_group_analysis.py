"""
Bolt Group Analysis (Elastic and ICR Methods)

Demonstrates bolt group force distribution for rectangular and circular
bolt patterns with eccentric loading.
"""
from connecty import BoltGroup, BoltParameters, Load
from pathlib import Path


def main():
    # ========================================
    # Case A: Rectangular bolt pattern with eccentric load
    # ========================================
    print("=" * 60)
    print("Case A: Rectangular Bolt Pattern with Eccentric Load")
    print("=" * 60)
    
    # Create bolt parameters (geometry only)
    params = BoltParameters(diameter=20)  # M20 bolts
    
    # Create bolt group from rectangular pattern
    # 3 rows × 2 columns, 75mm vertical spacing, 60mm horizontal spacing
    bolts = BoltGroup.from_pattern(
        rows=3,
        cols=2,
        spacing_y=75,      # 75mm between rows
        spacing_z=60,      # 60mm between columns
        diameter=20
    )
    
    # Print bolt group properties
    print(f"\nBolt Group Properties:")
    print(f"  Number of bolts: {bolts.n}")
    print(f"  Bolt diameter: {params.diameter} mm")
    print(f"  Centroid: ({bolts.Cy:.1f}, {bolts.Cz:.1f}) mm")
    print(f"  Polar moment Ip: {bolts.Ip:.0f} mm²")
    
    # Applied load: 100 kN at offset from centroid (creating torsion)
    # Centroid is at (75, 30). Force at (75, 150) creates eccentricity in z-direction.
    # Torsion Mx = Fz × dy - Fy × dz = 0 - (-100000) × (150-30) = 12,000,000 N·mm
    load = Load(
        Fy=-100000,            # 100 kN downward (N)
        location=(0, 75, 150)  # Offset 120 mm in z-direction from centroid
    )
    
    # Analyze using elastic method
    result_elastic = bolts.analyze(load, method="elastic")
    
    print(f"\nElastic Method Results:")
    print(f"  Max bolt force: {result_elastic.max_force:.2f} kN")
    print(f"  Min bolt force: {result_elastic.min_force:.2f} kN")
    print(f"  Mean force: {result_elastic.mean:.2f} kN")
    print(f"  Critical bolt index: {result_elastic.critical_index}")
    
    # Show force at each bolt
    print(f"\n  Individual bolt forces:")
    for i, bf in enumerate(result_elastic.bolt_forces):
        print(f"    Bolt {i+1} at ({bf.y:.0f}, {bf.z:.0f}): "
              f"Fy={bf.Fy:.2f} kN, Fz={bf.Fz:.2f} kN, R={bf.resultant:.2f} kN")
    
    # Plot elastic results
    gallery_dir = Path(__file__).parent.parent / "gallery"
    gallery_dir.mkdir(exist_ok=True)
    
    result_elastic.plot(
        force=True,
        bolt_forces=True,
        colorbar=True,
        show=False,
        save_path=str(gallery_dir / "bolt_group_elastic.svg")
    )
    
    # ========================================
    # Case B: ICR method comparison
    # ========================================
    print("\n" + "=" * 60)
    print("Case B: ICR Method Comparison")
    print("=" * 60)
    
    result_icr = bolts.analyze(load, method="icr")
    
    print(f"\nICR Method Results:")
    print(f"  Max bolt force: {result_icr.max_force:.2f} kN")
    print(f"  Min bolt force: {result_icr.min_force:.2f} kN")
    print(f"  Mean force: {result_icr.mean:.2f} kN")
    print(f"  Critical bolt index: {result_icr.critical_index}")
    if result_icr.icr_point:
        print(f"  ICR location: ({result_icr.icr_point[0]:.1f}, {result_icr.icr_point[1]:.1f}) mm")
    
    # Compare methods
    reduction = (1 - result_icr.max_force / result_elastic.max_force) * 100
    print(f"\n  ICR vs Elastic: {reduction:.0f}% reduction in max force")
    
    print(f"\n  Individual bolt forces:")
    for i, bf in enumerate(result_icr.bolt_forces):
        print(f"    Bolt {i+1} at ({bf.y:.0f}, {bf.z:.0f}): "
              f"Fy={bf.Fy:.2f} kN, Fz={bf.Fz:.2f} kN, R={bf.resultant:.2f} kN")
    
    result_icr.plot(
        force=True,
        bolt_forces=True,
        colorbar=True,
        show=False,
        save_path=str(gallery_dir / "bolt_group_icr.svg")
    )
    
    # ========================================
    # Case C: Circular bolt pattern
    # ========================================
    print("\n" + "=" * 60)
    print("Case C: Circular Bolt Pattern")
    print("=" * 60)
    
    # Create circular bolt pattern
    circular_bolts = BoltGroup.from_circle(
        n=8,              # 8 bolts
        radius=100,       # 100 mm radius
        diameter=20,
        center=(0, 0),
        start_angle=22.5  # Start 22.5° from vertical for symmetry
    )
    
    print(f"\nCircular Bolt Group Properties:")
    print(f"  Number of bolts: {circular_bolts.n}")
    print(f"  Centroid: ({circular_bolts.Cy:.1f}, {circular_bolts.Cz:.1f}) mm")
    print(f"  Polar moment Ip: {circular_bolts.Ip:.0f} mm²")
    
    # Eccentric load
    circular_load = Load(
        Fy=-80000,             # 80 kN downward
        Fz=30000,              # 30 kN to the right
        location=(0, 0, 150)   # 150 mm right of center
    )
    
    result_circular = circular_bolts.analyze(circular_load, method="elastic")
    
    print(f"\nElastic Results:")
    print(f"  Max bolt force: {result_circular.max_force:.2f} kN")
    print(f"  Mean force: {result_circular.mean:.2f} kN")
    
    result_circular.plot(
        force=True,
        bolt_forces=True,
        show=False,
        save_path=str(gallery_dir / "bolt_group_circular.svg")
    )
    
    # ========================================
    # Case D: Design check example
    # ========================================
    print("\n" + "=" * 60)
    print("Case D: Design Check Example")
    print("=" * 60)
    
    # Use rectangular bolt pattern
    design_load = Load(Fy=-100000, location=(0, 75, 150))
    design_result = bolts.analyze(design_load, method="elastic")
    
    # Define bolt capacity (A325 M20 bearing-type)
    # Nominal shear strength: 372 MPa
    # Area: π(20/2)² = 314.16 mm²
    # φ × Fnv × A / 1000 = 0.75 × 372 × 314.16 / 1000 ≈ 87.8 kN
    bolt_capacity_kN = 87.8
    
    print(f"\nDesign Check (A325 M20 Bearing):")
    print(f"  Max bolt force: {design_result.max_force:.2f} kN")
    print(f"  Bolt capacity: {bolt_capacity_kN:.2f} kN")
    utilization = design_result.max_force / bolt_capacity_kN
    print(f"  Utilization: {utilization:.1%}")
    print(f"  Status: {'✓ PASS' if utilization <= 1.0 else '✗ FAIL'}")
    
    print("\n" + "=" * 60)
    print("All examples complete! Check gallery/ for saved plots.")
    print("=" * 60)


if __name__ == "__main__":
    main()
