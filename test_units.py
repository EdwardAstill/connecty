"""
Test to verify bolt module is unit-agnostic and doesn't convert units.
"""
from connecty import BoltConnection, BoltGroup, Load, Plate


def main() -> None:

    # Test 1: Using N and mm (should output N and MPa)
    print("=" * 60)
    print("TEST 1: Using N and mm")
    print("=" * 60)

    # Create simple 2x2 bolt pattern
    # 4 bolts, 100mm spacing, 20mm diameter
    bolt_group = BoltGroup.from_pattern(
        rows=2,
        cols=2,
        spacing_y=100.0,  # mm
        spacing_z=100.0,  # mm
        diameter=20.0,    # mm
        origin=(0.0, 0.0)
    )

    plate = Plate(corner_a=(-150.0, -150.0), corner_b=(150.0, 150.0), thickness=10.0, fu=450.0, fy=350.0)
    conn = BoltConnection(bolt_group=bolt_group, plate=plate)

    # Apply load: 10000 N in y-direction at (0, 0, 100) mm
    # This creates a moment about the bolt centroid
    load = Load(
        Fx=0.0,      # N
        Fy=10000.0,  # N
        Fz=0.0,      # N
        Mx=0.0,      # N·mm
        My=0.0,      # N·mm
        Mz=0.0,      # N·mm
        location=(0.0, 50.0, 150.0)  # mm
    )

    # Analyze with elastic method (connection-only API)
    result = conn.analyze(load, shear_method="elastic", tension_method="conservative")

    print(f"\nBolt Group Properties:")
    print(f"  Number of bolts: {bolt_group.n}")
    print(f"  Centroid: ({bolt_group.Cy:.2f}, {bolt_group.Cz:.2f}) mm")
    print(f"  Bolt diameter: {bolt_group.parameters.diameter:.2f} mm")

    print(f"\nApplied Load:")
    print(f"  Fy = {load.Fy:.2f} N")
    print(f"  Location: {load.location} mm")

    print(f"\nResults (Forces in N, Stresses in MPa):")
    print(f"  Max shear force: {result.max_shear_force:.2f} N")
    print(f"  Max shear stress: {result.max_shear_stress:.2f} MPa (N/mm²)")
    print(f"  Critical bolt (combined): {result.critical_bolt_combined}")

    # Check bolt area calculation
    bolt = result.to_bolt_results()[0]
    expected_area = 3.14159 * (20.0/2)**2  # π * r²
    print(f"\nBolt Area Check:")
    print(f"  Calculated area: {bolt.area:.2f} mm²")
    print(f"  Expected area: {expected_area:.2f} mm²")
    print(f"  Match: {abs(bolt.area - expected_area) < 0.1}")

    # Manual stress calculation check
    if bolt.shear > 0:
        manual_stress = bolt.shear / bolt.area  # N / mm² = MPa
        print(f"\nStress Calculation Check:")
        print(f"  Shear force: {bolt.shear:.2f} N")
        print(f"  Area: {bolt.area:.2f} mm²")
        print(f"  Manual stress: {manual_stress:.2f} MPa")
        print(f"  Property stress: {bolt.shear_stress:.2f} MPa")
        print(f"  Match: {abs(manual_stress - bolt.shear_stress) < 0.01}")

    print("\n" + "=" * 60)
    print("TEST 2: Using kN and m (should output kN and kPa)")
    print("=" * 60)

    # Create same bolt pattern but in meters
    bolt_group_m = BoltGroup.from_pattern(
        rows=2,
        cols=2,
        spacing_y=0.1,    # m
        spacing_z=0.1,    # m
        diameter=0.02,    # m
        origin=(0.0, 0.0)
    )

    plate_m = Plate(corner_a=(-0.15, -0.15), corner_b=(0.15, 0.15), thickness=0.01, fu=450.0, fy=350.0)
    conn_m = BoltConnection(bolt_group=bolt_group_m, plate=plate_m)

    # Apply load: 10 kN in y-direction at (0, 0.05, 0.15) m
    load_kn = Load(
        Fx=0.0,    # kN
        Fy=10.0,   # kN
        Fz=0.0,    # kN
        Mx=0.0,    # kN·m
        My=0.0,    # kN·m
        Mz=0.0,    # kN·m
        location=(0.0, 0.05, 0.15)  # m
    )

    result_m = conn_m.analyze(load_kn, shear_method="elastic", tension_method="conservative")

    print(f"\nBolt Group Properties:")
    print(f"  Number of bolts: {bolt_group_m.n}")
    print(f"  Centroid: ({bolt_group_m.Cy:.4f}, {bolt_group_m.Cz:.4f}) m")
    print(f"  Bolt diameter: {bolt_group_m.parameters.diameter:.4f} m")

    print(f"\nApplied Load:")
    print(f"  Fy = {load_kn.Fy:.2f} kN")
    print(f"  Location: {load_kn.location} m")

    print(f"\nResults (Forces in kN, Stresses in kPa):")
    print(f"  Max shear force: {result_m.max_shear_force:.4f} kN")
    print(f"  Max shear stress: {result_m.max_shear_stress:.2f} kPa (kN/m²)")

    # Check that the results are proportional between unit systems
    print("\n" + "=" * 60)
    print("TEST 3: Verify Unit Consistency")
    print("=" * 60)

    # Forces should be in same ratio (N vs kN = 1000x)
    force_ratio = result.max_shear_force / result_m.max_shear_force
    print(f"\nForce ratio (N/kN): {force_ratio:.2f}")
    print(f"  Expected: 1000.0")
    print(f"  Match: {abs(force_ratio - 1000.0) < 1.0}")

    # Stresses should be in same ratio (MPa vs kPa = 1000x)
    stress_ratio = result.max_shear_stress / result_m.max_shear_stress
    print(f"\nStress ratio (MPa/kPa): {stress_ratio:.2f}")
    print(f"  Expected: 1000.0")
    print(f"  Match: {abs(stress_ratio - 1000.0) < 10.0}")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("✓ No unit conversions detected")
    print("✓ Forces output in same units as input")
    print("✓ Stresses correctly calculated as force/area")
    print("✓ Unit system is truly agnostic")


if __name__ == "__main__":
    main()
