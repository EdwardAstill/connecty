import math
from pathlib import Path
from connecty import BoltConnection, BoltLayout, BoltParams, Load, Plate

# ==========================================
# INPUTS
# ==========================================

# Output Settings
OUTPUT_DIR = "gallery/bolt"

# Bolt Parameters
BOLT_DIAMETER = 20
BOLT_GRADE = "A325"
BOLT_THREADED_IN_SHEAR = True

# Bolt Layout (Grid)
GRID_ROWS = 3
GRID_COLS = 3
GRID_SPACING_Y = 80  # mm (vertical in section plane)
GRID_SPACING_Z = 80  # mm (horizontal in section plane)

# Plate Parameters
PLATE_WIDTH = 400   # Dimension in Z (horizontal)
PLATE_HEIGHT = 400  # Dimension in Y (vertical)
PLATE_THICKNESS = 12
PLATE_FU = 450  # (MPa)
PLATE_FY = 350  # (MPa)
PLATE_CENTER = (0, 0)

# Connection Details
N_SHEAR_PLANES = 1

# Applied Loads
# Coordinate system:
#   x: along member (out-of-plane)  -> Fx = tension
#   y: vertical in section plane    -> Fy = shear
#   z: horizontal in section plane  -> Fz = shear
#   Mx = torsion (in-plane rotation)
#   My = bending about y (gradient in z)
#   Mz = bending about z (gradient in y)
LOAD_FX = 1000         # Tension (N)
LOAD_FY = 100_000      # Shear Y (N)
LOAD_FZ = 0            # Shear Z (N)
LOAD_MX = 10_000_000   # Torsion (Nmm)
LOAD_MY = 5_000_000    # Bending about Y (Nmm)
LOAD_MZ = 200_000      # Bending about Z (Nmm)
LOAD_LOCATION = (0, 0, 0)  # (mm)

# Analysis Settings
SHEAR_METHOD = "icr"      # "elastic" or "icr"
TENSION_METHOD = "conservative"  # "conservative" or "accurate"

# Check Settings
CHECK_STANDARD = "aisc"
CHECK_TYPE = "bearing"

# ==========================================
# MAIN SCRIPT
# ==========================================

def main() -> None:
    # 1. Setup
    print("Setting up inputs...")
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)

    # Create Objects from Inputs
    bolt_params = BoltParams(
        diameter=BOLT_DIAMETER,
        grade=BOLT_GRADE,
        threaded_in_shear_plane=BOLT_THREADED_IN_SHEAR,
    )

    bolt_layout = BoltLayout.from_pattern(
        rows=GRID_ROWS,
        cols=GRID_COLS,
        spacing_y=GRID_SPACING_Y,
        spacing_z=GRID_SPACING_Z,
    )

    plate = Plate.from_dimensions(
        width=PLATE_WIDTH,
        height=PLATE_HEIGHT,
        thickness=PLATE_THICKNESS,
        fu=PLATE_FU,
        fy=PLATE_FY,
        center=PLATE_CENTER,
    )

    conn = BoltConnection(
        layout=bolt_layout,
        bolt=bolt_params,
        plate=plate,
        n_shear_planes=N_SHEAR_PLANES,
    )

    load = Load(
        Fx=LOAD_FX,
        Fy=LOAD_FY,
        Fz=LOAD_FZ,
        Mx=LOAD_MX,
        My=LOAD_MY,
        Mz=LOAD_MZ,
        location=LOAD_LOCATION,
    )

    # 2. Perform Analysis
    print(f"Running analysis (Shear: {SHEAR_METHOD}, Tension: {TENSION_METHOD})")
    res = conn.analyze(load, shear_method=SHEAR_METHOD, tension_method=TENSION_METHOD)

    # 3. Perform Checks
    print(f"Running checks ({CHECK_STANDARD})...")
    check_results = res.check(standard=CHECK_STANDARD, connection_type=CHECK_TYPE)

    # 4. Write Results
    output_file = output_path / "bolt_analysis_results.txt"
    print(f"Writing results to {output_file}...")

    bg = conn.bolt_group
    bolt_forces = res.to_bolt_forces()

    with open(output_file, "w") as f:
        f.write("=== Bolt Analysis Inputs ===\n")
        f.write(f"Bolts: {bolt_layout.n} x {bolt_params.diameter}mm {bolt_params.grade}\n")
        f.write(f"Layout: {GRID_ROWS}x{GRID_COLS} grid @ {GRID_SPACING_Y}x{GRID_SPACING_Z}mm\n")
        f.write(f"Plate: {plate.depth_y}x{plate.depth_z}x{plate.thickness}mm (Fy={plate.fy}, Fu={plate.fu})\n")
        f.write(f"Load: Fx={load.Fx:.2f}, Fy={load.Fy:.2f}, Fz={load.Fz:.2f}, Mx={load.Mx:.2f}, My={load.My:.2f}, Mz={load.Mz:.2f}\n")

        f.write("\n=== Analysis Results (Global) ===\n")
        f.write(f"Shear Method: {res.shear_method}\n")
        f.write(f"Tension Method: {res.tension_method}\n")
        icr_point: tuple[float, float] | None = None
        if res.icr_point is not None:
            icr_point = (float(res.icr_point[0]), float(res.icr_point[1]))
            f.write(f"ICR Point: {icr_point}\n")

        # Equivalent load at centroid
        applied_at_c = load.equivalent_at((0, bg.Cy, bg.Cz))
        f.write(f"Applied Load at Centroid ({bg.Cy:.1f}, {bg.Cz:.1f}):\n")
        f.write(f"  Fx={applied_at_c.Fx:.2f}, Fy={applied_at_c.Fy:.2f}, Fz={applied_at_c.Fz:.2f}\n")
        f.write(f"  Mx={applied_at_c.Mx:.2f}, My={applied_at_c.My:.2f}, Mz={applied_at_c.Mz:.2f}\n")

        f.write("\n=== Individual Bolt Forces ===\n")
        f.write(f"{'Bolt':<6} {'Fx (Ten)':<12} {'Fy (Shr)':<12} {'Fz (Shr)':<12} {'V_res':<12} {'r_to_ICR':<12}\n")

        sum_fx = 0.0
        sum_fy = 0.0
        sum_fz = 0.0

        for i, bf in enumerate(bolt_forces):
            sum_fx += bf.Fx
            sum_fy += bf.Fy
            sum_fz += bf.Fz

            v_res = bf.shear

            if icr_point is None:
                r_to_icr_str = "n/a"
            else:
                by, bz = bolt_layout.points[i]
                r_to_icr = math.hypot(by - icr_point[0], bz - icr_point[1])
                r_to_icr_str = f"{r_to_icr:.2f}"

            f.write(f"{i+1:<6} {bf.Fx:<12.2f} {bf.Fy:<12.2f} {bf.Fz:<12.2f} {v_res:<12.2f} {r_to_icr_str:<12}\n")

        f.write(f"{'-'*60}\n")
        f.write(f"{'Total':<6} {sum_fx:<12.2f} {sum_fy:<12.2f} {sum_fz:<12.2f}\n")

        f.write("\n=== Check Results (AISC) ===\n")
        f.write(
            f"{'Bolt':<6} {'Shear':<10} {'Tension':<10} {'Combined':<10} {'Bearing':<10} {'Tearout':<10} {'Governing':<10}\n"
        )

        n_bolts = bolt_layout.n
        for i in range(n_bolts):
            shear_u = check_results["shear"][i] if "shear" in check_results else 0.0
            tension_u = check_results["tension"][i] if "tension" in check_results else 0.0
            combined_u = check_results["combined"][i] if "combined" in check_results else 0.0
            bearing_u = check_results["bearing"][i] if "bearing" in check_results else 0.0
            tearout_u = check_results["tearout"][i] if "tearout" in check_results else 0.0

            utilizations = [
                ("Shear", float(shear_u)),
                ("Tension", float(tension_u)),
                ("Combined", float(combined_u)),
                ("Bearing", float(bearing_u)),
                ("Tearout", float(tearout_u)),
            ]
            governing = max(utilizations, key=lambda x: x[1])[0] if utilizations else "n/a"

            f.write(
                f"{i+1:<6} {shear_u:<10.3f} {tension_u:<10.3f} {combined_u:<10.3f} {bearing_u:<10.3f} {tearout_u:<10.3f} {governing:<10}\n"
            )

        if "slip" in check_results and check_results["slip"]:
            f.write(f"\nSlip Check (Group): {check_results['slip'][0]:.3f}\n")

    # 5. Plotting
    shear_plot_file = output_path / "bolt_analysis_plot_shear.svg"
    tension_plot_file = output_path / "bolt_analysis_plot_tension.svg"

    print(f"Generating shear plot to {shear_plot_file}...")
    res.plot_shear(
        save_path=shear_plot_file,
        show=False,
    )

    print(f"Generating tension plot to {tension_plot_file}...")
    res.plot_tension(
        save_path=tension_plot_file,
        show=False,
    )
    print("Done.")

if __name__ == "__main__":
    main()
