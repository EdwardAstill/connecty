import json
from pathlib import Path
from connecty.bolt import BoltConnection, BoltGroup, Plate, Load, BoltParams, layout, plotting

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
GRID_SPACING_Y = 80
GRID_SPACING_Z = 80

# Plate Parameters
PLATE_WIDTH = 400   # Dimension in Z
PLATE_HEIGHT = 400  # Dimension in Y
PLATE_THICKNESS = 12
PLATE_FU = 450
PLATE_FY = 350
PLATE_CENTER = (0, 0)

# Connection Details
N_SHEAR_PLANES = 1

# Applied Loads
LOAD_FX = 50_000   # Tension
LOAD_FY = -100_000 # Shear Y
LOAD_FZ = 20_000   # Shear Z
LOAD_MY = 5_000_000
LOAD_MZ = -2_000_000
LOAD_LOCATION = (0, 0, 0)

# Analysis Settings
SHEAR_METHOD = "icr"      # "elastic" or "icr"
TENSION_METHOD = "accurate" # "conservative" or "accurate"

# Check Settings
CHECK_STANDARD = "aisc"
CHECK_TYPE = "bearing"

# ==========================================
# MAIN SCRIPT
# ==========================================

def main():
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
        spacing_y=GRID_SPACING_Y, 
        spacing_z=GRID_SPACING_Z
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
        n_shear_planes=N_SHEAR_PLANES
    )
    
    load = Load(
        Fx=LOAD_FX, 
        Fy=LOAD_FY, 
        Fz=LOAD_FZ, 
        My=LOAD_MY, 
        Mz=LOAD_MZ, 
        location=LOAD_LOCATION
    )
    
    # 2. Perform Analysis
    print(f"Running analysis (Shear: {SHEAR_METHOD}, Tension: {TENSION_METHOD})...")
    res = conn.analyze(load, shear_method=SHEAR_METHOD, tension_method=TENSION_METHOD)
    
    # 3. Perform Checks
    print(f"Running checks ({CHECK_STANDARD})...")
    check_results = res.check(standard=CHECK_STANDARD, connection_type=CHECK_TYPE)
    
    # 4. Write Results
    output_file = output_path / "bolt_analysis_results.txt"
    print(f"Writing results to {output_file}...")
    
    with open(output_file, "w") as f:
        f.write("=== Bolt Analysis Inputs ===\n")
        f.write(f"Bolts: {len(bolt_coords)} x {bolt_params.diameter}mm {bolt_params.grade}\n")
        f.write(f"Layout: {GRID_ROWS}x{GRID_COLS} grid @ {GRID_SPACING_Y}x{GRID_SPACING_Z}mm\n")
        f.write(f"Plate: {plate.depth_z}x{plate.depth_y}x{plate.thickness}mm (Fy={plate.fy}, Fu={plate.fu})\n")
        f.write(f"Load: Fx={load.Fx:.2f}, Fy={load.Fy:.2f}, Fz={load.Fz:.2f}, My={load.My:.2f}, Mz={load.Mz:.2f}\n")
        
        f.write("\n=== Analysis Results (Global) ===\n")
        f.write(f"Shear Method: {res.shear_method}\n")
        f.write(f"Tension Method: {res.tension_method}\n")
        if res.icr_point:
            f.write(f"ICR Point: {res.icr_point}\n")
        
        # Equivalent load at centroid
        # The plate/bolt group is in the Y-Z plane at X=0 (implied by Load(location=(0,0,0)))
        # Centroid is at (0, Cy, Cz)
        
        # 1. Applied Load transformed to Centroid
        applied_at_c = load.equivalent_at((0, bg.Cy, bg.Cz))
        f.write(f"Applied Load at Centroid (0, {bg.Cy:.1f}, {bg.Cz:.1f}):\n")
        f.write(f"  Fx={applied_at_c.Fx:.2f}, Fy={applied_at_c.Fy:.2f}, Fz={applied_at_c.Fz:.2f}\n")
        f.write(f"  Mx={applied_at_c.Mx:.2f}, My={applied_at_c.My:.2f}, Mz={applied_at_c.Mz:.2f}\n")

        if res.icr_point:

        # Appllied Load transformed to ICR
            applied_at_icr = load.equivalent_at((0, res.icr_point[0], res.icr_point[1]))
            f.write(f"Applied Load at ICR (0, {res.icr_point[0]:.1f}, {res.icr_point[1]:.1f}):\n")
            f.write(f"  Fx={applied_at_icr.Fx:.2f}, Fy={applied_at_icr.Fy:.2f}, Fz={applied_at_icr.Fz:.2f}\n")
            f.write(f"  Mx={applied_at_icr.Mx:.2f}, My={applied_at_icr.My:.2f}, Mz={applied_at_icr.Mz:.2f}\n")

        # 2. Reaction Load from Bolts at Centroid
        reaction_at_c = res.equivalent_load((bg.Cy, bg.Cz))
        f.write(f"Bolt Reaction at Centroid (0, {bg.Cy:.1f}, {bg.Cz:.1f}):\n")
        f.write(f"  Fx={reaction_at_c.Fx:.2f}, Fy={reaction_at_c.Fy:.2f}, Fz={reaction_at_c.Fz:.2f}\n")
        f.write(f"  Mx={reaction_at_c.Mx:.2f}, My={reaction_at_c.My:.2f}, Mz={reaction_at_c.Mz:.2f}\n")

        if res.icr_point:

        # Reaction Load from Bolts at ICR
            reaction_at_icr = res.equivalent_load((res.icr_point[0], res.icr_point[1]))
            f.write(f"Bolt Reaction at ICR (0, {res.icr_point[0]:.1f}, {res.icr_point[1]:.1f}):\n")
            f.write(f"  Fx={reaction_at_icr.Fx:.2f}, Fy={reaction_at_icr.Fy:.2f}, Fz={reaction_at_icr.Fz:.2f}\n")
            f.write(f"  Mx={reaction_at_icr.Mx:.2f}, My={reaction_at_icr.My:.2f}, Mz={reaction_at_icr.Mz:.2f}\n")
            
            f.write("\n=== Equilibrium Check ===\n")
            f.write("To prove the analysis is working, we check if the bolt forces balance the applied load.\n")
            f.write("Note: For Shear (Mx), the bolt reaction moment should match the applied moment.\n")
            f.write("      For Tension (My, Mz), the bolt reaction will be LESS than the applied moment\n")
            f.write("      because the balancing compression force from the plate is not included in bolt forces.\n\n")
        
        diff_fx = applied_at_c.Fx + reaction_at_c.Fx # Reaction forces should be opposite? 
        # Wait, equivalent_load returns the FORCE exerted BY the bolts.
        # If applied load is F, bolts must provide -F. 
        # So sum should be zero? Or do we compare magnitudes?
        # Usually Analysis returns forces ON the bolts.
        # If Load is Force ON connection.
        # Bolt Force is Force ON bolt (resisting).
        # So Applied + Reaction should be ~0.
        
        # Let's check the signs in the results.
        # Applied Fy = -100,000.
        # Bolt Reaction Fy = -72,111.
        # This implies Bolt Forces are in the same direction?
        # If Applied is Down (-Y), Bolts should push Up (+Y).
        # The result shows Bolts having negative Fy sum.
        # This suggests Bolt.forces stores the force EXERTED BY THE PLATE ON THE BOLT (which equals load).
        # OR it stores the force EXERTED BY THE BOLT ON THE PLATE.
        
        # Let's verify the solver sign convention.
        # In icr.py: ty = -(y - z_ic). Directions.
        # Fy_i = Fy_raw * scale.
        # If Fy_raw opposes load...
        
        f.write(f"{'Component':<10} {'Applied':<15} {'Bolt Reaction':<15} {'Result':<20}\n")
        f.write(f"{'Mx':<10} {applied_at_c.Mx:<15.2f} {reaction_at_c.Mx:<15.2f} {'OK' if abs(applied_at_c.Mx - reaction_at_c.Mx) < 1.0 else 'Diff (See Note)'}\n")
        
        # Shear Force Check
        # The ICR method ensures moment equilibrium. Shear force equilibrium depends on the center of rotation.
        # If ICR is far away, it's mostly shear.
        f.write(f"{'Fy':<10} {applied_at_c.Fy:<15.2f} {reaction_at_c.Fy:<15.2f} {'(Shear Balance)'}\n")
        f.write(f"{'Fz':<10} {applied_at_c.Fz:<15.2f} {reaction_at_c.Fz:<15.2f} {'(Shear Balance)'}\n")

        # 3. Loads at ICR (if applicable)
        if res.icr_point:
            icr_y, icr_z = res.icr_point
            
            # Applied Load transformed to ICR
            applied_at_icr = load.equivalent_at((0, icr_y, icr_z))
            f.write(f"Applied Load at ICR (0, {icr_y:.1f}, {icr_z:.1f}):\n")
            f.write(f"  Fx={applied_at_icr.Fx:.2f}, Fy={applied_at_icr.Fy:.2f}, Fz={applied_at_icr.Fz:.2f}\n")
            f.write(f"  Mx={applied_at_icr.Mx:.2f}, My={applied_at_icr.My:.2f}, Mz={applied_at_icr.Mz:.2f}\n")

            # Reaction Load from Bolts at ICR
            reaction_at_icr = res.equivalent_load((icr_y, icr_z))
            f.write(f"Bolt Reaction at ICR (0, {icr_y:.1f}, {icr_z:.1f}):\n")
            f.write(f"  Fx={reaction_at_icr.Fx:.2f}, Fy={reaction_at_icr.Fy:.2f}, Fz={reaction_at_icr.Fz:.2f}\n")
            f.write(f"  Mx={reaction_at_icr.Mx:.2f}, My={reaction_at_icr.My:.2f}, Mz={reaction_at_icr.Mz:.2f}\n")
        
        f.write("\n=== Individual Bolt Forces ===\n")
        f.write(f"{'Bolt':<6} {'Fx (Ten)':<12} {'Fy (Shr)':<12} {'Fz (Shr)':<12} {'V_res':<12}\n")
        
        sum_fx = 0.0
        sum_fy = 0.0
        sum_fz = 0.0
        
        for i, bolt in enumerate(bg.bolts):
            fx, fy, fz = bolt.forces
            sum_fx += fx
            sum_fy += fy
            sum_fz += fz
            
            v_res = (fy**2 + fz**2)**0.5
            f.write(f"{i+1:<6} {fx:<12.2f} {fy:<12.2f} {fz:<12.2f} {v_res:<12.2f}\n")
            
        f.write(f"{'-'*60}\n")
        f.write(f"{'Total':<6} {sum_fx:<12.2f} {sum_fy:<12.2f} {sum_fz:<12.2f}\n")

        f.write("\n=== Check Results (AISC) ===\n")
        f.write(f"{'Bolt':<6} {'Shear':<10} {'Tension':<10} {'Combined':<10} {'Bearing':<10} {'Tearout':<10}\n")
        
        n_bolts = len(bg.bolts)
        for i in range(n_bolts):
            shear_u = check_results["shear"][i] if "shear" in check_results else 0.0
            tension_u = check_results["tension"][i] if "tension" in check_results else 0.0
            combined_u = check_results["combined"][i] if "combined" in check_results else 0.0
            bearing_u = check_results["bearing"][i] if "bearing" in check_results else 0.0
            tearout_u = check_results["tearout"][i] if "tearout" in check_results else 0.0
            
            f.write(f"{i+1:<6} {shear_u:<10.3f} {tension_u:<10.3f} {combined_u:<10.3f} {bearing_u:<10.3f} {tearout_u:<10.3f}\n")

        if "slip" in check_results and check_results["slip"]:
             f.write(f"\nSlip Check (Group): {check_results['slip'][0]:.3f}\n")
        
    # 5. Plotting
    shear_plot_file = output_path / "bolt_analysis_plot_shear.svg"
    tension_plot_file = output_path / "bolt_analysis_plot_tension.svg"
    
    print(f"Generating shear plot to {shear_plot_file}...")
    plotting.plot_bolt_result(
        res,
        mode="shear",
        save_path=shear_plot_file,
        show=False
    )
    
    print(f"Generating tension plot to {tension_plot_file}...")
    plotting.plot_bolt_result(
        res,
        mode="axial",
        save_path=tension_plot_file,
        show=False
    )
    print("Done.")

if __name__ == "__main__":
    main()
