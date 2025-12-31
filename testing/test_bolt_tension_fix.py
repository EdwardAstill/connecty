"""Comprehensive tests for bolt tension calculation with proper compression handling.

Tests verify that:
1. Uniaxial bending: bolts below NA have zero tension
2. Biaxial bending: compression from one axis can cancel tension from another
3. Direct Fx + moments: all contributions sum correctly
"""

import pytest
from connecty import BoltConnection, BoltLayout, BoltParams, Load, Plate


class TestUniaxialBending:
    """Test uniaxial bending (single moment direction)."""
    
    def test_my_moment_accurate_method(self) -> None:
        """Test My moment with accurate NA (d/6 method)."""
        # Create bolt pattern with bolts at different z heights
        bolt_positions = [
            (0.0, -180.0),  # Below NA (should be in compression)
            (0.0, -100.0),  # Above NA
            (0.0,    0.0),
            (0.0, +100.0),
            (0.0, +180.0),
        ]
        
        layout = BoltLayout(points=bolt_positions)
        bolt = BoltParams(diameter=20.0, grade="A325")
        plate = Plate.from_dimensions(
            width=200.0, height=400.0, thickness=10.0, fu=400.0, center=(0.0, 0.0)
        )
        
        connection = BoltConnection(layout=layout, bolt=bolt, plate=plate, n_shear_planes=1)
        
        # Positive My causes compression at z_min
        load = Load(Fx=0.0, Fy=0.0, Fz=0.0, Mx=0.0, My=500000.0, Mz=0.0)
        result = connection.analyze(load=load, tension_method="accurate")
        
        na_z = plate.z_min + plate.depth_z / 6.0  # -200 + 400/6 = -133.33
        
        for idx, (y, z) in enumerate(bolt_positions):
            tension = result.bolt_forces[idx].Fx
            
            if z < na_z:
                # Bolt in compression zone should have zero tension
                assert abs(tension) < 0.01, f"Bolt {idx+1} at z={z} below NA should have Fx≈0, got {tension}"
            else:
                # Bolt in tension zone should have positive tension
                assert tension > 0.0, f"Bolt {idx+1} at z={z} above NA should have Fx>0, got {tension}"
    
    def test_my_moment_conservative_method(self) -> None:
        """Test My moment with conservative NA (centroid method)."""
        bolt_positions = [
            (0.0, -100.0),
            (0.0,    0.0),
            (0.0, +100.0),
        ]
        
        layout = BoltLayout(points=bolt_positions)
        bolt = BoltParams(diameter=20.0, grade="A325")
        plate = Plate.from_dimensions(
            width=200.0, height=300.0, thickness=10.0, fu=400.0, center=(0.0, 0.0)
        )
        
        connection = BoltConnection(layout=layout, bolt=bolt, plate=plate, n_shear_planes=1)
        
        load = Load(Fx=0.0, Fy=0.0, Fz=0.0, Mx=0.0, My=100000.0, Mz=0.0)
        result = connection.analyze(load=load, tension_method="conservative")
        
        na_z = layout.Cz  # Should be 0.0
        
        for idx, (y, z) in enumerate(bolt_positions):
            tension = result.bolt_forces[idx].Fx
            
            if z < na_z:
                assert abs(tension) < 0.01, f"Bolt {idx+1} below centroid should have Fx≈0"
            else:
                assert tension >= 0.0, f"Bolt {idx+1} above centroid should have Fx≥0"
    
    def test_mz_moment_accurate_method(self) -> None:
        """Test Mz moment with accurate NA (d/6 method)."""
        bolt_positions = [
            (-150.0, 0.0),  # Below NA in y direction (should be in compression)
            (-50.0, 0.0),   # Above NA
            (+50.0, 0.0),
            (+150.0, 0.0),
        ]
        
        layout = BoltLayout(points=bolt_positions)
        bolt = BoltParams(diameter=20.0, grade="A325")
        plate = Plate.from_dimensions(
            width=400.0, height=200.0, thickness=10.0, fu=400.0, center=(0.0, 0.0)
        )
        
        connection = BoltConnection(layout=layout, bolt=bolt, plate=plate, n_shear_planes=1)
        
        # Positive Mz causes compression at y_min
        load = Load(Fx=0.0, Fy=0.0, Fz=0.0, Mx=0.0, My=0.0, Mz=500000.0)
        result = connection.analyze(load=load, tension_method="accurate")
        
        na_y = plate.y_min + plate.depth_y / 6.0  # -200 + 400/6 = -133.33
        
        for idx, (y, z) in enumerate(bolt_positions):
            tension = result.bolt_forces[idx].Fx
            
            if y < na_y:
                assert abs(tension) < 0.01, f"Bolt {idx+1} at y={y} below NA should have Fx≈0"
            else:
                assert tension > 0.0, f"Bolt {idx+1} at y={y} above NA should have Fx>0"


class TestBiaxialBending:
    """Test biaxial bending (both My and Mz moments)."""
    
    def test_opposing_moments_cancel(self) -> None:
        """Test that compression from one axis cancels tension from another."""
        # Create bolts where some experience opposing effects from My vs Mz
        # We need multiple bolts to create a valid tension distribution
        
        bolt_positions = [
            (-120.0, +80.0),   # Well below NA_y (-50), well above NA_z (-50) 
            (+80.0, +80.0),    # Above both NAs (tension from both)
            (+80.0, -120.0),   # Above NA_y, below NA_z
        ]
        
        layout = BoltLayout(points=bolt_positions)
        bolt = BoltParams(diameter=20.0, grade="A325")
        plate = Plate.from_dimensions(
            width=300.0, height=300.0, thickness=10.0, fu=400.0, center=(0.0, 0.0)
        )
        
        connection = BoltConnection(layout=layout, bolt=bolt, plate=plate, n_shear_planes=1)
        
        # NA_y = -150 + 300/6 = -100 + 50 = -50
        # NA_z = -150 + 300/6 = -50
        
        # Test bolt 0: y=-120 < NA_y=-50 (compression from Mz), z=+80 > NA_z=-50 (tension from My)
        
        # Test 1: Only My (should give positive tension to bolt 0)
        load_my = Load(Fx=0.0, Fy=0.0, Fz=0.0, Mx=0.0, My=100000.0, Mz=0.0)
        result_my = connection.analyze(load=load_my, tension_method="accurate")
        tension_my_bolt0 = result_my.bolt_forces[0].Fx
        
        assert tension_my_bolt0 > 0.0, "My alone should create tension for bolt 0 (above NA_z)"
        
        # Test 2: Only Mz (should give zero tension to bolt 0 - below NA_y)
        load_mz = Load(Fx=0.0, Fy=0.0, Fz=0.0, Mx=0.0, My=0.0, Mz=100000.0)
        result_mz = connection.analyze(load=load_mz, tension_method="accurate")
        tension_mz_bolt0 = result_mz.bolt_forces[0].Fx
        
        assert abs(tension_mz_bolt0) < 0.01, "Mz alone should give zero (bolt 0 below NA_y)"
        
        # Test 3: Both moments (compression from Mz should reduce tension from My for bolt 0)
        load_both = Load(Fx=0.0, Fy=0.0, Fz=0.0, Mx=0.0, My=100000.0, Mz=100000.0)
        result_both = connection.analyze(load=load_both, tension_method="accurate")
        tension_both_bolt0 = result_both.bolt_forces[0].Fx
        
        # The combined tension should be less than My alone (cancelled by Mz compression)
        assert tension_both_bolt0 < tension_my_bolt0, \
            f"Biaxial bolt 0: {tension_both_bolt0:.2f} should be < My alone: {tension_my_bolt0:.2f}"
        
        print(f"  Bolt 0 - My alone: {tension_my_bolt0:.2f} N")
        print(f"  Bolt 0 - Mz alone: {tension_mz_bolt0:.2f} N") 
        print(f"  Bolt 0 - My + Mz: {tension_both_bolt0:.2f} N")
    
    def test_biaxial_symmetry(self) -> None:
        """Test biaxial bending on a symmetric bolt pattern."""
        bolt_positions = [
            (-80.0, -80.0),  # Bottom-left
            (-80.0, +80.0),  # Top-left
            (+80.0, -80.0),  # Bottom-right
            (+80.0, +80.0),  # Top-right
        ]
        
        layout = BoltLayout(points=bolt_positions)
        bolt = BoltParams(diameter=20.0, grade="A325")
        plate = Plate.from_dimensions(
            width=300.0, height=300.0, thickness=10.0, fu=400.0, center=(0.0, 0.0)
        )
        
        connection = BoltConnection(layout=layout, bolt=bolt, plate=plate, n_shear_planes=1)
        
        # Apply equal moments in both directions
        load = Load(Fx=0.0, Fy=0.0, Fz=0.0, Mx=0.0, My=200000.0, Mz=200000.0)
        result = connection.analyze(load=load, tension_method="accurate")
        
        tensions = [br.Fx for br in result.bolt_forces]
        
        # Top-right bolt should have highest tension (furthest from both NAs)
        assert tensions[3] > tensions[0], "Top-right should have more tension than bottom-left"
        assert tensions[3] > tensions[1], "Top-right should have more tension than top-left"
        assert tensions[3] > tensions[2], "Top-right should have more tension than bottom-right"
        
        # By symmetry, top-left and bottom-right should have equal tension
        assert abs(tensions[1] - tensions[2]) < 1.0, "Top-left and bottom-right should be equal by symmetry"


class TestDirectTensionWithMoments:
    """Test combination of direct Fx tension with moments."""
    
    def test_direct_fx_dominates_compression(self) -> None:
        """Test that large direct Fx creates tension even for bolts in moment compression zone."""
        bolt_positions = [
            (0.0, -150.0),  # Would be in compression from My
            (0.0, +150.0),  # Would be in tension from My
        ]
        
        layout = BoltLayout(points=bolt_positions)
        bolt = BoltParams(diameter=20.0, grade="A325")
        plate = Plate.from_dimensions(
            width=200.0, height=400.0, thickness=10.0, fu=400.0, center=(0.0, 0.0)
        )
        
        connection = BoltConnection(layout=layout, bolt=bolt, plate=plate, n_shear_planes=1)
        
        # Large direct Fx with moment
        load = Load(Fx=50000.0, Fy=0.0, Fz=0.0, Mx=0.0, My=100000.0, Mz=0.0)
        result = connection.analyze(load=load, tension_method="accurate")
        
        # Both bolts should have positive tension (direct Fx dominates)
        for idx, (y, z) in enumerate(bolt_positions):
            tension = result.bolt_forces[idx].Fx
            assert tension > 0.0, f"Bolt {idx+1} should have tension from large direct Fx"
            
            # Direct component
            direct = 50000.0 / 2
            assert tension >= direct * 0.9, f"Bolt {idx+1} tension should include most of direct component"
    
    def test_moment_can_reduce_but_not_eliminate_direct_fx(self) -> None:
        """Test that moment compression reduces but doesn't eliminate large direct Fx."""
        bolt_positions = [(0.0, -150.0), (0.0, +150.0)]
        
        layout = BoltLayout(points=bolt_positions)
        bolt = BoltParams(diameter=20.0, grade="A325")
        plate = Plate.from_dimensions(
            width=200.0, height=400.0, thickness=10.0, fu=400.0, center=(0.0, 0.0)
        )
        
        connection = BoltConnection(layout=layout, bolt=bolt, plate=plate, n_shear_planes=1)
        
        # Moderate direct Fx
        load_fx_only = Load(Fx=10000.0, Fy=0.0, Fz=0.0, Mx=0.0, My=0.0, Mz=0.0)
        result_fx_only = connection.analyze(load=load_fx_only, tension_method="accurate")
        
        load_fx_and_my = Load(Fx=10000.0, Fy=0.0, Fz=0.0, Mx=0.0, My=100000.0, Mz=0.0)
        result_fx_and_my = connection.analyze(load=load_fx_and_my, tension_method="accurate")
        
        # Bottom bolt: direct Fx should be reduced by My compression
        tension_bottom_fx_only = result_fx_only.bolt_forces[0].Fx
        tension_bottom_combined = result_fx_and_my.bolt_forces[0].Fx
        
        assert tension_bottom_combined < tension_bottom_fx_only, "Moment compression should reduce tension"
        
        # Top bolt: direct Fx should be increased by My tension
        tension_top_fx_only = result_fx_only.bolt_forces[1].Fx
        tension_top_combined = result_fx_and_my.bolt_forces[1].Fx
        
        assert tension_top_combined > tension_top_fx_only, "Moment tension should increase tension"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_all_bolts_in_compression_zone(self) -> None:
        """Test case where all bolts would be in compression (no positive tension)."""
        # Place bolts well below the NA
        # Plate z: [-100, +100], NA_z = -100 + 200/6 = -100 + 33.33 = -66.67
        # So bolts at z < -66.67 are in compression
        bolt_positions = [(0.0, -90.0), (0.0, -80.0)]
        
        layout = BoltLayout(points=bolt_positions)
        bolt = BoltParams(diameter=20.0, grade="A325")
        plate = Plate.from_dimensions(
            width=200.0, height=200.0, thickness=10.0, fu=400.0, center=(0.0, 0.0)
        )
        
        connection = BoltConnection(layout=layout, bolt=bolt, plate=plate, n_shear_planes=1)
        
        na_z = plate.z_min + plate.depth_z / 6.0  # -100 + 33.33 = -66.67
        
        # Verify bolts are actually below NA
        for _, z in bolt_positions:
            assert z < na_z, f"Test setup error: bolt at z={z} should be below NA={na_z}"
        
        # Only moment, no direct Fx
        load = Load(Fx=0.0, Fy=0.0, Fz=0.0, Mx=0.0, My=100000.0, Mz=0.0)
        result = connection.analyze(load=load, tension_method="accurate")
        
        # All bolts should have zero tension (all in compression zone)
        for idx in range(len(bolt_positions)):
            tension = result.bolt_forces[idx].Fx
            assert abs(tension) < 0.01, f"Bolt {idx+1} in compression zone should have Fx≈0"
    
    def test_zero_moment(self) -> None:
        """Test with zero moment (only direct Fx)."""
        bolt_positions = [(0.0, -50.0), (0.0, +50.0)]
        
        layout = BoltLayout(points=bolt_positions)
        bolt = BoltParams(diameter=20.0, grade="A325")
        plate = Plate.from_dimensions(
            width=200.0, height=200.0, thickness=10.0, fu=400.0, center=(0.0, 0.0)
        )
        
        connection = BoltConnection(layout=layout, bolt=bolt, plate=plate, n_shear_planes=1)
        
        load = Load(Fx=10000.0, Fy=0.0, Fz=0.0, Mx=0.0, My=0.0, Mz=0.0)
        result = connection.analyze(load=load, tension_method="accurate")
        
        expected_per_bolt = 10000.0 / 2
        
        for idx in range(len(bolt_positions)):
            tension = result.bolt_forces[idx].Fx
            assert abs(tension - expected_per_bolt) < 0.1, f"Bolt {idx+1} should have {expected_per_bolt} N"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

