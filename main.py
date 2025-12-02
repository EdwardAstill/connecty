"""
Weldy Example: Weld stress analysis on an RHS section.

This example demonstrates:
1. Creating a section from sectiony
2. Adding welds to specific edges
3. Applying a force
4. Visualizing the stress distribution
"""
from sectiony.library import rhs

from weldy import (
    WeldedSection,
    WeldParameters,
    Force,
)


def main() -> None:
    # 1. Create a section using sectiony
    # RHS 200x100x10 with 15mm corner radius
    section = rhs(b=100, h=200, t=10, r=15)
    
    print(f"Section: {section.name}")
    print(f"Area: {section.A:.1f} mm²")
    
    # 2. Create a WeldedSection and inspect segments
    welded = WeldedSection(section=section)
    
    print("\nAvailable segments (outer contour):")
    for info in welded.get_segment_info(contour_index=0):
        print(f"  Segment {info['index']}: {info['type']}")
    
    # 3. Define weld parameters
    # 6mm fillet weld (throat ≈ 4.2mm)
    weld_params = WeldParameters(
        weld_type="fillet",
        throat_thickness=4.2,
        leg_size=6.0,
        strength=220.0  # Allowable stress in MPa (optional)
    )
    
    # 4. Add welds to all outer segments
    welded.weld_all_segments(weld_params, contour_index=0)
    
    # Calculate weld group properties
    welded.calculate_properties()
    
    props = welded.weld_group.properties
    print(f"\nWeld Group Properties:")
    print(f"  Centroid: ({props.Cy:.1f}, {props.Cz:.1f})")
    print(f"  Total Length: {props.L:.1f} mm")
    print(f"  Total Area: {props.A:.1f} mm²")
    print(f"  Ix: {props.Ix:.0f} mm⁴")
    print(f"  Iy: {props.Iy:.0f} mm⁴")
    print(f"  Ip: {props.Ip:.0f} mm⁴")
    
    # 5. Define applied force
    # 50kN vertical load at an eccentric location
    force = Force(
        Fy=-50000,  # 50kN downward
        Fz=10000,   # 10kN horizontal
        Mx=1e6,     # 1kNm torsion
        location=(100, 30)  # Applied at (y=100, z=30)
    )
    
    print(f"\nApplied Force:")
    print(f"  Fy: {force.Fy/1000:.1f} kN")
    print(f"  Fz: {force.Fz/1000:.1f} kN")
    print(f"  Mx: {force.Mx/1e6:.1f} kNm")
    print(f"  Location: ({force.y_loc}, {force.z_loc})")
    
    # 6. Calculate stress
    result = welded.calculate_weld_stress(force)
    
    print(f"\nStress Results:")
    print(f"  Max Stress: {result.max_stress:.2f} MPa")
    print(f"  Min Stress: {result.min_stress:.2f} MPa")
    
    if weld_params.strength:
        utilization = result.utilization(weld_params.strength)
        print(f"  Utilization: {utilization*100:.1f}%")
    
    # 7. Plot the results
    print("\nGenerating plot...")
    welded.plot_weld_stress(
        force,
        cmap="coolwarm",
        weld_linewidth=5.0,
        show_force=True,
        save_path="weld_stress_example.svg"
    )


if __name__ == "__main__":
    main()
