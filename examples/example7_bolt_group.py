"""
Example 7: Bolt Group Analysis (Elastic and ICR Methods)

Demonstrates bolt group analysis for a rectangular pattern
of bolts with eccentric loading.
"""
from weldy import BoltGroup, BoltParameters, Force
from pathlib import Path


def main():
    # ========================================
    # Example A: Simple bolt group with eccentric load (Elastic)
    # ========================================
    print("=" * 60)
    print("Example A: Rectangular Bolt Pattern with Eccentric Load")
    print("=" * 60)
    
    # Create bolt parameters
    params = BoltParameters(
        diameter=20,          # M20 bolts
        grade="A325",         # A325 grade
        threads_excluded=False,  # Threads NOT excluded (N condition)
        shear_planes=1        # Single shear
    )
    
    # Create bolt group from rectangular pattern
    # 3 rows × 2 columns, 75mm vertical spacing, 60mm horizontal spacing
    bolts = BoltGroup.from_pattern(
        rows=3,
        cols=2,
        spacing_y=75,      # 75mm between rows
        spacing_z=60,      # 60mm between columns
        parameters=params,
        origin=(0, 0)      # Bottom-left bolt at origin
    )
    
    # Print bolt group properties
    print(f"\nBolt Group Properties:")
    print(f"  Number of bolts: {bolts.n}")
    print(f"  Bolt diameter: {params.diameter} mm")
    print(f"  Grade: {params.grade}")
    print(f"  Capacity per bolt: {params.capacity:.1f} kN")
    print(f"  Centroid: ({bolts.Cy:.1f}, {bolts.Cz:.1f}) mm")
    print(f"  Polar moment Ip: {bolts.Ip:.0f} mm²")
    
    # Applied load: 100kN at offset from centroid (creating torsion)
    # Centroid is at (75, 30). Force at (75, 150) creates eccentricity in z-direction.
    # Torsion Mx = Fz × dy - Fy × dz = 0 - (-100000) × (150-30) = 12,000,000 N·mm
    force = Force(
        Fy=-100000,            # 100kN downward (N)
        location=(75, 150)     # Same y as centroid, offset 120mm in z-direction
    )
    
    # Analyze using elastic method
    result_elastic = bolts.analyze(force, method="elastic")
    
    print(f"\nElastic Method Results:")
    print(f"  Max bolt force: {result_elastic.max_force:.2f} kN")
    print(f"  Min bolt force: {result_elastic.min_force:.2f} kN")
    print(f"  Critical bolt index: {result_elastic.critical_index}")
    print(f"  Utilization: {result_elastic.utilization():.1%}")
    print(f"  Adequate: {'✓' if result_elastic.is_adequate() else '✗'}")
    
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
        save_path=str(gallery_dir / "example7_bolt_elastic.svg")
    )
    
    # ========================================
    # Example B: Same configuration with ICR method
    # ========================================
    print("\n" + "=" * 60)
    print("Example B: ICR Method Comparison")
    print("=" * 60)
    
    result_icr = bolts.analyze(force, method="icr")
    
    print(f"\nICR Method Results:")
    print(f"  Max bolt force: {result_icr.max_force:.2f} kN")
    print(f"  Min bolt force: {result_icr.min_force:.2f} kN")
    print(f"  Critical bolt index: {result_icr.critical_index}")
    print(f"  Utilization: {result_icr.utilization():.1%}")
    print(f"  ICR location: ({result_icr.icr_point[0]:.1f}, {result_icr.icr_point[1]:.1f}) mm" 
          if result_icr.icr_point else "  ICR: N/A")
    
    print(f"\n  Individual bolt forces:")
    for i, bf in enumerate(result_icr.bolt_forces):
        print(f"    Bolt {i+1} at ({bf.y:.0f}, {bf.z:.0f}): "
              f"Fy={bf.Fy:.2f} kN, Fz={bf.Fz:.2f} kN, R={bf.resultant:.2f} kN")
    
    result_icr.plot(
        force=True,
        bolt_forces=True,
        colorbar=True,
        show=False,
        save_path=str(gallery_dir / "example7_bolt_icr.svg")
    )
    
    # ========================================
    # Example C: Circular bolt pattern
    # ========================================
    print("\n" + "=" * 60)
    print("Example C: Circular Bolt Pattern")
    print("=" * 60)
    
    # Create circular bolt pattern
    circular_bolts = BoltGroup.from_circle(
        n=8,                   # 8 bolts
        radius=100,            # 100mm radius
        parameters=params,
        center=(0, 0),
        start_angle=22.5       # Start 22.5° from vertical for symmetry
    )
    
    print(f"\nCircular Bolt Group Properties:")
    print(f"  Number of bolts: {circular_bolts.n}")
    print(f"  Centroid: ({circular_bolts.Cy:.1f}, {circular_bolts.Cz:.1f}) mm")
    print(f"  Polar moment Ip: {circular_bolts.Ip:.0f} mm²")
    
    # Eccentric load
    circular_force = Force(
        Fy=-80000,             # 80kN downward
        Fz=30000,              # 30kN to the right
        location=(0, 150)      # 150mm right of center
    )
    
    result_circular = circular_bolts.analyze(circular_force, method="elastic")
    
    print(f"\nElastic Results:")
    print(f"  Max bolt force: {result_circular.max_force:.2f} kN")
    print(f"  Utilization: {result_circular.utilization():.1%}")
    
    result_circular.plot(
        force=True,
        bolt_forces=True,
        show=False,
        save_path=str(gallery_dir / "example7_bolt_circular.svg")
    )
    
    # ========================================
    # Example D: Slip-critical connection
    # ========================================
    print("\n" + "=" * 60)
    print("Example D: Slip-Critical Connection")
    print("=" * 60)
    
    slip_params = BoltParameters(
        diameter=20,
        grade="A325",
        threads_excluded=False,
        slip_critical=True,    # Slip-critical design
        slip_class="B",        # Class B surface (blast-cleaned)
        shear_planes=1
    )
    
    slip_bolts = BoltGroup.from_pattern(
        rows=2,
        cols=3,
        spacing_y=75,
        spacing_z=75,
        parameters=slip_params
    )
    
    print(f"\nSlip-Critical Bolt Properties:")
    print(f"  Grade: {slip_params.grade}")
    print(f"  Surface class: {slip_params.slip_class}")
    print(f"  Pretension: {slip_params.pretension:.1f} kN")
    print(f"  Slip resistance per bolt: {slip_params.capacity:.1f} kN")
    
    slip_force = Force(Fy=-50000, location=(75, 75))
    result_slip = slip_bolts.analyze(slip_force, method="elastic")
    
    print(f"\nResults:")
    print(f"  Max bolt force: {result_slip.max_force:.2f} kN")
    print(f"  Utilization: {result_slip.utilization():.1%}")
    print(f"  Adequate: {'✓' if result_slip.is_adequate() else '✗'}")
    
    result_slip.plot(
        force=True,
        bolt_forces=True,
        show=False,
        save_path=str(gallery_dir / "example7_bolt_slip.svg")
    )
    
    print("\n" + "=" * 60)
    print("All examples complete! Check gallery/ for saved plots.")
    print("=" * 60)


if __name__ == "__main__":
    main()

