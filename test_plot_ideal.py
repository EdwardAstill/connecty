"""Test the ideal API with plotting."""

from connecty.bolt import BoltGroup, BoltConnection, Plate, ConnectionLoad, ConnectionResult


def main() -> None:

    # Create bolt group
    bg = BoltGroup.from_pattern(rows=3, cols=2, spacing_y=100, spacing_z=75, diameter=20)

    # Create plate
    plate = Plate(corner_a=(-100, -150), corner_b=(100, 150), thickness=15, fu=450.0, fy=350.0)

    # Create connection
    conn = BoltConnection(bolt_group=bg, plate=plate, n_shear_planes=1)

    # Create load with moments
    load = ConnectionLoad(
        Fy=50000,
        Fz=10000,
        My=5e6,
        Mz=2e6,
        location=(0, 0, 100)
    )

    # Analyze
    result = ConnectionResult(
        connection=conn,
        load=load,
        shear_method="elastic",
        tension_method="accurate"
    )

    # Print results
    print(f"Max shear force: {result.max_shear_force:.1f} N")
    print(f"Max axial force: {result.max_axial_force:.1f} N")
    print(f"Max combined stress: {result.max_combined_stress:.1f} MPa")

    # Plot
    result.plot(
        mode="shear",
        show=False,
        save_path="test_ideal_plot.svg"
    )

    print("Plot saved to test_ideal_plot.svg")


if __name__ == "__main__":
    main()
