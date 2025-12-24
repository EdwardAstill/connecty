"""Test plotting with both My and Mz moments to show both neutral axes."""

from connecty.bolt import BoltGroup, BoltConnection, Plate, ConnectionLoad, ConnectionResult


def main() -> None:

    # Create bolt group
    bg = BoltGroup.from_pattern(rows=4, cols=3, spacing_y=80, spacing_z=60, diameter=20)

    # Create plate (larger to show plate boundary clearly)
    plate = Plate(corner_a=(-120, -100), corner_b=(120, 100), thickness=12, fu=450.0, fy=350.0)

    # Create connection
    conn = BoltConnection(bolt_group=bg, plate=plate, n_shear_planes=1)

    # Create load with BOTH My and Mz moments (should show both NA lines)
    load = ConnectionLoad(
        Fy=30000,
        Fz=15000,
        My=8e6,   # Bending about y-axis -> NA vertical line
        Mz=6e6,   # Bending about z-axis -> NA horizontal line
        location=(0, 0, 50)
    )

    # Analyze with accurate method (NA at d/6 from compression edge)
    result = ConnectionResult(
        connection=conn,
        load=load,
        shear_method="elastic",
        tension_method="accurate"
    )

    # Print results
    print("=" * 60)
    print("CONNECTION ANALYSIS RESULTS")
    print("=" * 60)
    print(f"Bolt group: {bg.n} bolts, {bg.parameters.diameter:.0f} mm diameter")
    print(f"Plate: {plate.depth_y:.0f} × {plate.depth_z:.0f} mm, {plate.thickness:.0f} mm thick")
    print(f"Shear method: {result.shear_method}")
    print(f"Tension method: {result.tension_method}")
    print()
    print("Force Distribution:")
    print(f"  Max shear force: {result.max_shear_force:.1f} N")
    print(f"  Max axial force: {result.max_axial_force:.1f} N")
    print(f"  Max resultant: {result.max_resultant_force:.1f} N")
    print()
    print("Stress Distribution:")
    print(f"  Max shear stress: {result.max_shear_stress:.1f} MPa")
    print(f"  Max axial stress: {result.max_axial_stress:.1f} MPa")
    print(f"  Max combined stress: {result.max_combined_stress:.1f} MPa")
    print("=" * 60)

    # Plot with all features
    result.plot(
        mode="shear",
        force=True,
        bolt_forces=True,
        colorbar=True,
        show=False,
        save_path="test_full_plot.svg"
    )

    print("\nPlot saved to test_full_plot.svg")
    print("Features shown:")
    print("  ✓ Plate boundary (gray rectangle)")
    print("  ✓ Neutral axis for My (blue dashed vertical line)")
    print("  ✓ Neutral axis for Mz (green dashed horizontal line)")
    print("  ✓ Bolt positions with force arrows")
    print("  ✓ Force colormap")
    print("  ✓ Applied load location")


if __name__ == "__main__":
    main()
