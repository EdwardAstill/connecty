import math
from pathlib import Path
from connecty.bolt import BoltConnection, BoltGroup, Plate, Load, BoltParams, layout

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
GRID_SPACING_X = 80 #mm
GRID_SPACING_Y = 80 #mm

# Plate Parameters
PLATE_WIDTH = 400   # Dimension in X
PLATE_HEIGHT = 400  # Dimension in Y
PLATE_THICKNESS = 12
PLATE_FU = 450 # (MPa)
PLATE_FY = 350 # (MPa)
PLATE_CENTER = (0, 0)

# Connection Details
N_SHEAR_PLANES = 1

# Applied Loads
# System: X-Y Plane (Shear), Z (Axial/Tension)
LOAD_FX = 100_000   # Shear X (N)
LOAD_FY = 0        # Shear Y (N)
LOAD_FZ = 1000        # Tension (N)
# NOTE:
# In `connecty.bolt.load.Load`, torsion about the bolt-group plane is **Mz**.
# Mx/My are bending moments about the x/y axes (used by the tension solver).
LOAD_MZ = 10_000_000  # Torsion (moment about Z) (Nmm)
LOAD_MX = 200_000     # Moment about X (Nmm)
LOAD_MY = 5_000_000   # Moment about Y (Nmm)
LOAD_LOCATION = (0, 0, 0) # (mm)

# Analysis Settings
SHEAR_METHOD = "icr"      # "elastic" or "icr"

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
        threaded_in_shear_plane=BOLT_THREADED_IN_SHEAR
    )
    
    bolt_coords = layout.grid_layout(
        rows=GRID_ROWS, 
        cols=GRID_COLS, 
        spacing_x=GRID_SPACING_X, 
        spacing_y=GRID_SPACING_Y
    )
    
    bg = BoltGroup.create(layout=bolt_coords, params=bolt_params)
    
    plate = Plate.from_dimensions(
        width=PLATE_WIDTH, 
        height=PLATE_HEIGHT, 
        thickness=PLATE_THICKNESS, 
        fu=PLATE_FU, 
        fy=PLATE_FY,
        center=PLATE_CENTER
    )
    
    conn = BoltConnection(
        bolt_group=bg, 
        plate=plate, 
        n_shear_planes=N_SHEAR_PLANES,
        total_thickness=PLATE_THICKNESS
    )
    
    load = Load(
        Fx=LOAD_FX, 
        Fy=LOAD_FY, 
        Fz=LOAD_FZ, 
        My=LOAD_MY, 
        Mz=LOAD_MZ,
        Mx=LOAD_MX,
        location=LOAD_LOCATION
    )
    
    # 2. Perform Analysis
    print(f"Running analysis (Shear: {SHEAR_METHOD})")
    res = conn.analyze(load, shear_method=SHEAR_METHOD)
    
    # 3. Perform Checks
    print(f"Running checks ({CHECK_STANDARD})...")
    check_results = res.check(standard=CHECK_STANDARD, connection_type=CHECK_TYPE)
    
    # 4. Write Results
    output_file = output_path / "bolt_analysis_results.txt"
    print(f"Writing results to {output_file}...")
    
    with open(output_file, "w") as f:
        f.write("=== Bolt Analysis Inputs ===\n")
        f.write(f"Bolts: {len(bolt_coords)} x {bolt_params.diameter}mm {bolt_params.grade}\n")
        f.write(f"Layout: {GRID_ROWS}x{GRID_COLS} grid @ {GRID_SPACING_X}x{GRID_SPACING_Y}mm\n")
        f.write(f"Plate: {plate.depth_x}x{plate.depth_y}x{plate.thickness}mm (Fy={plate.fy}, Fu={plate.fu})\n")
        f.write(f"Load: Fx={load.Fx:.2f}, Fy={load.Fy:.2f}, Fz={load.Fz:.2f}, Mx={load.Mx:.2f}, My={load.My:.2f}, Mz={load.Mz:.2f}\n")
        
        f.write("\n=== Analysis Results (Global) ===\n")
        f.write(f"Shear Method: {res.shear_method}\n")
        icr_point: tuple[float, float] | None = None
        if res.icr_point is not None:
            icr_point = (float(res.icr_point[0]), float(res.icr_point[1]))
            f.write(f"ICR Point: {icr_point}\n")
        
        # Equivalent load at centroid
        applied_at_c = load.equivalent_at((bg.Cx, bg.Cy, 0))
        f.write(f"Applied Load at Centroid ({bg.Cx:.1f}, {bg.Cy:.1f}, 0):\n")
        f.write(f"  Fx={applied_at_c.Fx:.2f}, Fy={applied_at_c.Fy:.2f}, Fz={applied_at_c.Fz:.2f}\n")
        f.write(f"  Mx={applied_at_c.Mx:.2f}, My={applied_at_c.My:.2f}, Mz={applied_at_c.Mz:.2f}\n")

        # Note: equivalent_load on result (reaction) is not currently implemented in LoadedBoltConnection
        # so we skip the equilibrium check printout here.
        
        f.write("\n=== Individual Bolt Forces ===\n")
        f.write(f"{'Bolt':<6} {'Fx (Shr)':<12} {'Fy (Shr)':<12} {'Fz (Ten)':<12} {'V_res':<12} {'r_to_ICR':<12}\n")
        
        sum_fx = 0.0
        sum_fy = 0.0
        sum_fz = 0.0
        
        for i, bolt in enumerate(bg.bolts):
            fx, fy, fz = bolt.forces
            sum_fx += fx
            sum_fy += fy
            sum_fz += fz
            
            v_res = (fx**2 + fy**2)**0.5

            if icr_point is None:
                r_to_icr_str = "n/a"
            else:
                bx, by = bolt.position
                r_to_icr = math.hypot(float(bx) - icr_point[0], float(by) - icr_point[1])
                r_to_icr_str = f"{r_to_icr:.2f}"

            f.write(f"{i+1:<6} {fx:<12.2f} {fy:<12.2f} {fz:<12.2f} {v_res:<12.2f} {r_to_icr_str:<12}\n")
            
        f.write(f"{'-'*60}\n")
        f.write(f"{'Total':<6} {sum_fx:<12.2f} {sum_fy:<12.2f} {sum_fz:<12.2f}\n")

        f.write("\n=== Check Results (AISC) ===\n")
        f.write(
            f"{'Bolt':<6} {'Shear':<10} {'Tension':<10} {'Combined':<10} {'Bearing':<10} {'Tearout':<10} {'Governing':<10}\n"
        )
        
        n_bolts = len(bg.bolts)
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
        show=False
    )
    
    print(f"Generating tension plot to {tension_plot_file}...")
    res.plot_tension(
        save_path=tension_plot_file,
        show=False
    )
    print("Done.")

if __name__ == "__main__":
    main()
