
import sys
from pathlib import Path
import math

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from connecty import WeldedSection, WeldParameters, Force, WeldGroup, WeldSegment
from sectiony.geometry import Line
from sectiony import Section, Geometry, Contour

def test_elastic_method_verification():
    """
    Verify connecty calculations against manual Elastic Method calculation.
    
    Case: Single vertical weld line under eccentric vertical load.
    
    Parameters:
    - Length L = 100 mm
    - Throat t = 10 mm
    - Weld on y-axis, centered at origin (0, 0)
    - Load P = 10,000 N (downward)
    - Eccentricity e = 100 mm (applied at z = 100)
    
    Manual Calculation:
    1. Properties:
       A = L * t = 100 * 10 = 1000 mm²
       Iz = t * L^3 / 12 = 10 * 100^3 / 12 = 833,333.33 mm⁴
       Iy ≈ 0 (thin line approximation)
       Ip = Iz + Iy = 833,333.33 mm⁴
       
    2. Load:
       Fy = -10,000 N
       Mx = P * e = 10,000 * 100 = 1,000,000 Nmm
       
    3. Stresses at Top Point (y=50, z=0):
       a) Direct Shear (y-direction):
          τ_direct = Fy / A = -10,000 / 1000 = -10 MPa
          
       b) Torsional Shear:
          Horizontal component (z-direction) due to Mx
          τ_torsion_z = Mx * y / Ip
                      = 1,000,000 * 50 / 833,333.33
                      = 60 MPa
          Vertical component (y-direction) due to Mx
          τ_torsion_y = -Mx * z / Ip = 0 (since z=0)
          
       c) Resultant:
          τ_total_y = -10 MPa
          τ_total_z = 60 MPa
          τ_res = sqrt((-10)^2 + 60^2) = 60.8276 MPa
    """
    print("Verifying Elastic Method Implementation...")
    
    # 1. Setup Model
    # Create a dummy section geometry just to hold the weld
    # Line from (y=-50, z=0) to (y=50, z=0)
    line = Line(( -50.0, 0.0), (50.0, 0.0))
    contour = Contour([line])
    geometry = Geometry(contours=[contour])
    section = Section(name="Dummy", geometry=geometry)
    
    welded = WeldedSection(section=section)
    weld_params = WeldParameters(weld_type="butt", throat_thickness=10.0)
    
    # Weld the single line
    welded.add_weld(0, weld_params)
    welded.calculate_properties()
    
    props = welded.weld_group.properties
    print(f"\nProperties:")
    print(f"Area: {props.A:.2f} mm² (Expected: 1000.00)")
    print(f"Ip: {props.Ip:.2f} mm⁴ (Expected: ~833333.33)")
    
    # 2. Apply Load
    # Force at z=100, y=0. Fy = -10000
    force = Force(Fy=-10000, location=(0, 100))
    
    # 3. Calculate
    result = welded.calculate_weld_stress(force, discretization=21) # Ensure point at top
    
    # 4. Check Point at Top (y=50)
    # Find point closest to y=50
    top_point = max(result.point_stresses, key=lambda ps: ps.y)
    
    print(f"\nResults at Top Point (y={top_point.y:.2f}, z={top_point.z:.2f}):")
    
    comps = top_point.components
    print(f"Direct Shear Y: {comps.f_direct_y:.4f} MPa (Expected: -10.0000)")
    print(f"Torsion Shear Z: {comps.f_moment_z:.4f} MPa (Expected: 60.0000)")
    print(f"Resultant: {top_point.stress:.4f} MPa (Expected: ~60.8276)")
    
    # Verification assertions
    assert abs(props.A - 1000.0) < 1.0, "Area calculation failed"
    # Note: Discretized Ip might slightly differ from theoretical L^3/12 due to integration
    assert abs(props.Ip - 833333.33) < 1000.0, f"Ip calculation failed: {props.Ip}"
    
    assert abs(comps.f_direct_y - (-10.0)) < 0.1, "Direct shear incorrect"
    assert abs(comps.f_moment_z - 60.0) < 1.0, f"Torsion shear incorrect: {comps.f_moment_z}"
    assert abs(top_point.stress - 60.8276) < 1.0, "Resultant stress incorrect"
    
    print("\nSUCCESS: Implementation matches Elastic Method manual calculation.")

if __name__ == "__main__":
    test_elastic_method_verification()

