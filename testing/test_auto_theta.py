"""Test auto_theta_deg feature for AISC weld checks."""

from pathlib import Path

from connecty import Load, WeldBaseMetal, WeldConnection, WeldParams


def test_auto_theta_deg():
    """Test that auto_theta_deg computes theta at the max stress point."""
    # Setup weld connection
    root = Path(__file__).resolve().parents[1]
    dxf_path = root / "examples" / "base1.dxf"
    
    base_metal = WeldBaseMetal(t=10.0, fy=350.0, fu=450.0)
    params = WeldParams(type="fillet", leg=6.0)
    connection = WeldConnection.from_dxf(
        dxf_path,
        parameters=params,
        base_metal=base_metal,
        is_double_fillet=False,
        is_rect_hss_end_connection=False,
    )
    
    # Load with in-plane shear (should create an angle)
    load = Load(
        Fy=-120_000.0,
        Fz=45_000.0,
        location=(0.0, 0.0, 0.0),
    )
    
    # Analyze with ICR method
    result = connection.analyze(load, method="icr")
    
    # Test 1: Default behavior (automatic theta computation)
    check_default = result.check(standard="aisc")
    print(f"\nCheck with default (automatic theta):")
    print(f"  theta_deg: {check_default.details[0].theta_deg}")
    print(f"  k_ds: {check_default.details[0].k_ds:.4f}")
    assert check_default.details[0].theta_deg is not None
    assert check_default.details[0].k_ds > 1.0  # Should have directional benefit
    
    # Test 2: Conservative mode (force k_ds=1.0)
    check_conservative = result.check(standard="aisc", conservative_k_ds=True)
    print(f"\nCheck with conservative_k_ds=True:")
    print(f"  theta_deg: {check_conservative.details[0].theta_deg}")
    print(f"  k_ds: {check_conservative.details[0].k_ds:.4f}")
    assert check_conservative.details[0].theta_deg is None
    assert check_conservative.details[0].k_ds == 1.0
    
    # Test 3: Verify auto theta is reasonable (between 0 and 90 degrees)
    auto_theta = check_default.details[0].theta_deg
    assert 0.0 <= auto_theta <= 90.0, f"Auto theta {auto_theta} not in valid range"
    
    print(f"\nAll tests passed!")
    print(f"  Auto-computed theta: {auto_theta:.2f}°")
    print(f"  k_ds with auto theta: {check_default.details[0].k_ds:.4f}")
    print(f"  Governing utilization (default): {check_default.governing_utilization:.4f}")
    print(f"  Governing utilization (conservative): {check_conservative.governing_utilization:.4f}")


if __name__ == "__main__":
    test_auto_theta_deg()

