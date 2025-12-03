"""
Test script to verify stress continuity around welds.

This script checks that stress values change smoothly as we move around
the weld perimeter, ensuring there are no discontinuities or jumps.
"""
import sys
from pathlib import Path
from typing import Tuple, Dict, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sectiony.library import rhs, chs, i
from connecty import WeldedSection, WeldParameters, Force
import math


def test_stress_continuity(
    welded_section: WeldedSection,
    force: Force,
    discretization: int = 200,
    max_relative_change: float = 0.02,  # 2% max change between consecutive points
    max_absolute_change: Optional[float] = None,  # Will be set based on max stress
    max_gradient_factor: float = 0.10,  # 10% of max stress per mm as gradient threshold
    verbose: bool = True
) -> Tuple[bool, Dict]:
    """
    Test that stress is continuous around the weld perimeter.
    
    Args:
        welded_section: The welded section to test
        force: Applied force
        discretization: Points per segment for stress calculation
        max_relative_change: Maximum allowed relative change (as fraction of stress)
        max_absolute_change: Maximum allowed absolute change (if None, uses relative)
        verbose: Whether to print detailed results
        
    Returns:
        (passed, results_dict) where results_dict contains test statistics
    """
    # Calculate stress distribution
    result = welded_section.calculate_weld_stress(force, discretization=discretization)
    
    if not result.point_stresses:
        raise ValueError("No stress points calculated")
    
    all_points = result.point_stresses
    max_stress = result.max_stress
    min_stress = result.min_stress
    
    # Calculate typical segment length to determine if points are adjacent
    # Get average distance between consecutive points within segments
    within_segment_distances = []
    for i in range(len(all_points) - 1):
        p1 = all_points[i]
        p2 = all_points[i + 1]
        if p1.segment is p2.segment:  # Same segment
            dy = p2.y - p1.y
            dz = p2.z - p1.z
            dist = math.sqrt(dy**2 + dz**2)
            if dist > 1e-6:  # Avoid zero distances
                within_segment_distances.append(dist)
    
    avg_step_size = sum(within_segment_distances) / len(within_segment_distances) if within_segment_distances else 1.0
    max_adjacent_distance = avg_step_size * 2.0  # Allow 2x average step for adjacent points
    
    # Set absolute threshold if not provided (use 1% of max stress)
    # But also calculate a gradient threshold (MPa per mm)
    if max_absolute_change is None:
        max_absolute_change = max_stress * max_relative_change
    
    # Gradient threshold: max allowed change per mm
    # For smooth stress distribution, gradient should be reasonable
    # Use configurable factor (default 10%) of max stress per mm as threshold
    max_gradient_threshold = (max_stress * max_gradient_factor) / avg_step_size if avg_step_size > 0 else max_absolute_change
    
    # Statistics
    max_change = 0.0
    max_gradient = 0.0  # Change per unit distance
    max_change_idx = -1
    max_change_location = None
    total_changes = []
    total_gradients = []
    segment_boundary_changes = []
    
    # Check continuity between consecutive points
    for i in range(len(all_points) - 1):
        p1 = all_points[i]
        p2 = all_points[i + 1]
        
        # Calculate distance between points
        dy = p2.y - p1.y
        dz = p2.z - p1.z
        dist = math.sqrt(dy**2 + dz**2)
        
        # Skip if points are too far apart (non-adjacent segments)
        if dist > max_adjacent_distance:
            continue
        
        stress1 = p1.stress
        stress2 = p2.stress
        
        # Calculate change and gradient
        abs_change = abs(stress2 - stress1)
        gradient = abs_change / dist if dist > 1e-6 else 0.0
        
        if stress1 > 1e-9:  # Avoid division by zero
            rel_change = abs_change / stress1
        else:
            rel_change = abs_change / max_stress if max_stress > 1e-9 else 0.0
        
        total_changes.append(abs_change)
        total_gradients.append(gradient)
        
        # Check if crossing segment boundary
        is_boundary = (p1.segment is not p2.segment)
        if is_boundary:
            segment_boundary_changes.append(abs_change)
        
        # Track maximum change and gradient
        if abs_change > max_change:
            max_change = abs_change
            max_change_idx = i
            max_change_location = (
                (p1.y, p1.z),
                (p2.y, p2.z),
                is_boundary,
                dist
            )
        
        if gradient > max_gradient:
            max_gradient = gradient
    
    # Also check continuity at the wrap-around (last point to first point)
    # This checks if the weld forms a closed loop
    p_last = all_points[-1]
    p_first = all_points[0]
    
    # Calculate distance to see if they're actually connected
    dy = p_first.y - p_last.y
    dz = p_first.z - p_last.z
    dist = math.sqrt(dy**2 + dz**2)
    
    wrap_around_change = None
    if dist <= max_adjacent_distance:  # Points are close, likely a closed loop
        wrap_around_change = abs(p_first.stress - p_last.stress)
        total_changes.append(wrap_around_change)
        if dist > 1e-6:
            total_gradients.append(wrap_around_change / dist)
    
    # Calculate statistics
    avg_change = sum(total_changes) / len(total_changes) if total_changes else 0.0
    avg_gradient = sum(total_gradients) / len(total_gradients) if total_gradients else 0.0
    max_boundary_change = max(segment_boundary_changes) if segment_boundary_changes else 0.0
    
    # Check if test passed
    # Pass if both absolute change and gradient are within thresholds
    # For segments that vary significantly (like long straight segments), gradient is more meaningful
    passed_absolute = max_change <= max_absolute_change
    passed_gradient = max_gradient <= max_gradient_threshold
    passed = passed_absolute and passed_gradient
    
    results = {
        "passed": passed,
        "passed_absolute": passed_absolute,
        "passed_gradient": passed_gradient,
        "max_change": max_change,
        "max_gradient": max_gradient,
        "max_change_idx": max_change_idx,
        "max_change_location": max_change_location,
        "avg_change": avg_change,
        "avg_gradient": avg_gradient,
        "max_boundary_change": max_boundary_change,
        "wrap_around_change": wrap_around_change,
        "max_stress": max_stress,
        "min_stress": min_stress,
        "num_points": len(all_points),
        "threshold_absolute": max_absolute_change,
        "threshold_gradient": max_gradient_threshold,
        "avg_step_size": avg_step_size
    }
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"Stress Continuity Test Results")
        print(f"{'='*60}")
        print(f"Max stress: {max_stress:.2f} MPa")
        print(f"Min stress: {min_stress:.2f} MPa")
        print(f"Number of points: {len(all_points)}")
        print(f"Average step size: {avg_step_size:.3f} mm")
        print(f"\nContinuity Statistics:")
        print(f"  Maximum change: {max_change:.4f} MPa")
        print(f"  Average change: {avg_change:.4f} MPa")
        print(f"  Maximum gradient: {max_gradient:.4f} MPa/mm")
        print(f"  Average gradient: {avg_gradient:.4f} MPa/mm")
        print(f"  Threshold (absolute): {max_absolute_change:.4f} MPa")
        print(f"  Threshold (gradient): {max_gradient_threshold:.4f} MPa/mm")
        if max_change_location:
            loc1, loc2, is_boundary, dist = max_change_location
            print(f"  Max change location: ({loc1[0]:.2f}, {loc1[1]:.2f}) -> ({loc2[0]:.2f}, {loc2[1]:.2f})")
            print(f"  Distance: {dist:.3f} mm")
            print(f"  At segment boundary: {is_boundary}")
        if segment_boundary_changes:
            print(f"  Max change at boundary: {max_boundary_change:.4f} MPa")
        if wrap_around_change is not None:
            print(f"  Wrap-around change: {wrap_around_change:.4f} MPa")
        print(f"\nTest Result: {'PASSED' if passed else 'FAILED'}")
        if not passed:
            if not passed_absolute:
                print(f"  - Failed absolute threshold check")
            if not passed_gradient:
                print(f"  - Failed gradient threshold check")
        print(f"{'='*60}\n")
    
    return passed, results


def test_multiple_scenarios():
    """Test stress continuity for multiple loading scenarios."""
    
    print("Testing Stress Continuity Around Welds")
    print("=" * 60)
    
    all_passed = True
    
    # Test 1: Simple RHS with vertical load
    print("\n[Test 1] RHS 100x200x10 - Vertical Load at Centroid")
    section1 = rhs(b=100, h=200, t=10, r=15)
    welded1 = WeldedSection(section=section1)
    weld_params1 = WeldParameters(weld_type="fillet", throat_thickness=4.2, leg_size=6.0)
    welded1.weld_all_segments(weld_params1)
    
    force1 = Force(Fy=-100000, location=(0, 0))
    passed1, results1 = test_stress_continuity(welded1, force1, discretization=200)
    all_passed = all_passed and passed1
    
    # Test 2: RHS with eccentric load (creates torsion)
    print("\n[Test 2] RHS 100x200x10 - Eccentric Vertical Load")
    section2 = rhs(b=100, h=200, t=10, r=15)
    welded2 = WeldedSection(section=section2)
    weld_params2 = WeldParameters(weld_type="fillet", throat_thickness=4.2, leg_size=6.0)
    welded2.weld_all_segments(weld_params2)
    
    force2 = Force(Fy=-100000, location=(50, 0))  # Eccentric
    passed2, results2 = test_stress_continuity(welded2, force2, discretization=200)
    all_passed = all_passed and passed2
    
    # Test 3: RHS with combined loading (shear + torsion)
    print("\n[Test 3] RHS 100x200x10 - Combined Shear and Torsion")
    section3 = rhs(b=100, h=200, t=10, r=15)
    welded3 = WeldedSection(section=section3)
    weld_params3 = WeldParameters(weld_type="fillet", throat_thickness=4.2, leg_size=6.0)
    welded3.weld_all_segments(weld_params3)
    
    force3 = Force(Fy=-80000, Fz=20000, Mx=2000000, location=(0, 0))
    passed3, results3 = test_stress_continuity(welded3, force3, discretization=200)
    all_passed = all_passed and passed3
    
    # Test 4: Circular Hollow Section (CHS) - tests arc segments
    print("\n[Test 4] CHS 200x10 - Vertical Load with Torsion")
    section4 = chs(d=200, t=10)
    welded4 = WeldedSection(section=section4)
    weld_params4 = WeldParameters(weld_type="butt", throat_thickness=10.0)
    welded4.weld_all_segments(weld_params4)
    
    force4 = Force(Fy=-50000, Mx=3e6, location=(0, 0))
    passed4, results4 = test_stress_continuity(welded4, force4, discretization=200)
    all_passed = all_passed and passed4
    
    # Test 5: I-beam - tests multiple segments
    print("\n[Test 5] I-Beam 400x200x20x10 - Bending Moment")
    section5 = i(d=400, b=200, tf=20, tw=10, r=15)
    welded5 = WeldedSection(section=section5)
    weld_params5 = WeldParameters(weld_type="fillet", throat_thickness=6.0)
    welded5.add_welds([0, 1, 2, 3], weld_params5)  # Top flange
    welded5.add_welds([8, 9, 10, 11], weld_params5)  # Bottom flange
    welded5.calculate_properties()
    
    force5 = Force(My=5e6, location=(0, 0))
    passed5, results5 = test_stress_continuity(welded5, force5, discretization=200)
    all_passed = all_passed and passed5
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Tests passed: {sum([passed1, passed2, passed3, passed4, passed5])} / 5")
    print(f"Overall result: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
    print("=" * 60)
    
    assert all_passed


# Treat helper as non-test so pytest does not try to collect it independently.
test_stress_continuity.__test__ = False


if __name__ == "__main__":
    import sys
    
    success = test_multiple_scenarios()
    sys.exit(0 if success else 1)

