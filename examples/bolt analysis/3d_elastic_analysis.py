"""
Demonstrate 3D elastic bolt analysis with full 6DOF loading.

This example shows how the elastic method handles:
- In-plane shear: Fy, Fz
- Torsion: Mx
- Out-of-plane axial: Fx
- Bending: My, Mz
"""

from connecty import BoltGroup, Load

# Create bolt group - 3x3 rectangular pattern
bolt_group = BoltGroup.from_pattern(
    rows=3,
    cols=3,
    spacing_y=60,  # mm
    spacing_z=80,  # mm
    diameter=20,   # M20 bolts
    origin=(-60, -80)  # Center the pattern at origin
)

print("=" * 60)
print("3D ELASTIC BOLT ANALYSIS")
print("=" * 60)
print(f"\nBolt Configuration:")
print(f"  Pattern: 3x3 rectangular grid")
print(f"  Spacing: 60 mm (y) × 80 mm (z)")
print(f"  Diameter: M20 (20 mm)")
print(f"  Centroid: ({bolt_group.Cy:.1f}, {bolt_group.Cz:.1f}) mm")
print(f"  Number of bolts: {bolt_group.n}")

# Test Case 1: In-plane shear only (2D baseline)
print("\n" + "=" * 60)
print("CASE 1: In-Plane Shear Only (2D)")
print("=" * 60)

load1 = Load(
    Fy=-80000,   # 80 kN vertical shear
    Fz=40000,    # 40 kN horizontal shear
    Mx=3000000,  # 3 kN·m torsion
    location=(0, 0, 150)  # 150 mm above pattern
)

result1 = bolt_group.analyze(load1, method="elastic")

print(f"\nApplied Load:")
print(f"  Fy = {load1.Fy/1000:.1f} kN")
print(f"  Fz = {load1.Fz/1000:.1f} kN")
print(f"  Mx = {load1.Mx/1e6:.1f} kN·m")
print(f"  Location: z = {load1.location[2]} mm")

print(f"\nResults:")
print(f"  Max in-plane shear: {result1.max_force:.2f} kN")
print(f"  Max axial force: {max(bf.axial for bf in result1.bolt_forces):.2f} kN")
print(f"  Max shear stress: {result1.max_stress:.1f} MPa")
print(f"  Max axial stress: {result1.max_axial_stress:.1f} MPa")
print(f"  Max combined stress: {result1.max_combined_stress:.1f} MPa")

# Test Case 2: Out-of-plane axial load
print("\n" + "=" * 60)
print("CASE 2: Out-of-Plane Axial Load")
print("=" * 60)

load2 = Load(
    Fx=90000,  # 90 kN axial tension
    location=(0, 0, 0)
)

result2 = bolt_group.analyze(load2, method="elastic")

print(f"\nApplied Load:")
print(f"  Fx = {load2.Fx/1000:.1f} kN (tension)")

print(f"\nResults:")
print(f"  Max in-plane shear: {result2.max_force:.2f} kN")
print(f"  Max axial force: {max(bf.axial for bf in result2.bolt_forces):.2f} kN")
print(f"  Max shear stress: {result2.max_stress:.1f} MPa")
print(f"  Max axial stress: {result2.max_axial_stress:.1f} MPa")
print(f"  Max combined stress: {result2.max_combined_stress:.1f} MPa")

print(f"\n  Per-Bolt Axial Forces:")
for i, bf in enumerate(result2.bolt_forces, 1):
    print(f"    Bolt {i}: Fx = {bf.Fx:.2f} kN (uniform)")

# Test Case 3: Bending moments (My, Mz)
print("\n" + "=" * 60)
print("CASE 3: Bending Moments (My, Mz)")
print("=" * 60)

load3 = Load(
    My=4000000,   # 4 kN·m bending about y-axis
    Mz=-3000000,  # 3 kN·m bending about z-axis
    location=(0, 0, 0)
)

result3 = bolt_group.analyze(load3, method="elastic")

print(f"\nApplied Load:")
print(f"  My = {load3.My/1e6:.1f} kN·m (bending about y)")
print(f"  Mz = {load3.Mz/1e6:.1f} kN·m (bending about z)")

print(f"\nResults:")
print(f"  Max in-plane shear: {result3.max_force:.2f} kN")
print(f"  Max axial force: {max(bf.axial for bf in result3.bolt_forces):.2f} kN")
print(f"  Max shear stress: {result3.max_stress:.1f} MPa")
print(f"  Max axial stress: {result3.max_axial_stress:.1f} MPa")
print(f"  Max combined stress: {result3.max_combined_stress:.1f} MPa")

print(f"\n  Per-Bolt Axial Forces (linear variation):")
for i, bf in enumerate(result3.bolt_forces, 1):
    print(f"    Bolt {i} at (y={bf.y:.1f}, z={bf.z:.1f}): Fx = {bf.Fx:+.2f} kN")

# Test Case 4: Combined 3D loading (all 6 DOF)
print("\n" + "=" * 60)
print("CASE 4: Combined 3D Loading (All 6 DOF)")
print("=" * 60)

load4 = Load(
    Fx=50000,     # 50 kN axial tension
    Fy=-100000,   # 100 kN vertical shear
    Fz=60000,     # 60 kN horizontal shear
    Mx=5000000,   # 5 kN·m torsion
    My=2500000,   # 2.5 kN·m bending about y
    Mz=-2000000,  # 2 kN·m bending about z
    location=(0, 0, 120)  # 120 mm above pattern
)

result4 = bolt_group.analyze(load4, method="elastic")

print(f"\nApplied Load:")
print(f"  Fx = {load4.Fx/1000:.1f} kN")
print(f"  Fy = {load4.Fy/1000:.1f} kN")
print(f"  Fz = {load4.Fz/1000:.1f} kN")
print(f"  Mx = {load4.Mx/1e6:.1f} kN·m")
print(f"  My = {load4.My/1e6:.1f} kN·m")
print(f"  Mz = {load4.Mz/1e6:.1f} kN·m")
print(f"  Location: z = {load4.location[2]} mm")

print(f"\nResults:")
print(f"  Max in-plane shear: {result4.max_force:.2f} kN")
print(f"  Max axial force: {max(bf.axial for bf in result4.bolt_forces):.2f} kN")
print(f"  Max shear stress: {result4.max_stress:.1f} MPa")
print(f"  Max axial stress: {result4.max_axial_stress:.1f} MPa")
print(f"  Max combined stress: {result4.max_combined_stress:.1f} MPa")

# Find critical bolt
critical = result4.critical_bolt
if critical:
    print(f"\nCritical Bolt:")
    print(f"  Location: (y={critical.y:.1f}, z={critical.z:.1f}) mm")
    print(f"  In-plane shear: {critical.shear:.2f} kN")
    print(f"  Axial force: {critical.Fx:+.2f} kN")
    print(f"  Total 3D force: {critical.resultant:.2f} kN")
    print(f"  Shear stress: {critical.shear_stress:.1f} MPa")
    print(f"  Axial stress: {critical.axial_stress:.1f} MPa")
    print(f"  Combined stress: {critical.combined_stress:.1f} MPa")

# Summary comparison
print("\n" + "=" * 60)
print("SUMMARY COMPARISON")
print("=" * 60)
print(f"\n{'Case':<30} {'Shear (MPa)':<15} {'Axial (MPa)':<15} {'Combined (MPa)':<15}")
print("-" * 75)
print(f"{'1. In-Plane Only':<30} {result1.max_stress:>12.1f}   {result1.max_axial_stress:>12.1f}   {result1.max_combined_stress:>12.1f}")
print(f"{'2. Axial Load Only':<30} {result2.max_stress:>12.1f}   {result2.max_axial_stress:>12.1f}   {result2.max_combined_stress:>12.1f}")
print(f"{'3. Bending Moments':<30} {result3.max_stress:>12.1f}   {result3.max_axial_stress:>12.1f}   {result3.max_combined_stress:>12.1f}")
print(f"{'4. Full 3D Combined':<30} {result4.max_stress:>12.1f}   {result4.max_axial_stress:>12.1f}   {result4.max_combined_stress:>12.1f}")

print("\n" + "=" * 60)
print("VISUALIZATION")
print("=" * 60)

# Demonstrate shear mode plotting (Case 1 - in-plane shear)
print("\nGenerating shear mode plot (Case 1)...")
result1.plot(
    mode="shear",
    force=True,
    bolt_forces=True,
    colorbar=True,
    cmap="coolwarm",
    show=False,
    save_path="gallery/bolt analysis/3d_case1_shear.svg"
)

# Demonstrate axial mode plotting (Case 2 - pure axial)
print("Generating axial mode plot (Case 2)...")
result2.plot(
    mode="axial",
    force=True,
    colorbar=True,
    cmap="RdBu_r",  # Diverging: red=tension, blue=compression
    show=False,
    save_path="gallery/bolt analysis/3d_case2_axial.svg"
)

# Demonstrate axial mode with bending (Case 3)
print("Generating axial mode plot with bending (Case 3)...")
result3.plot(
    mode="axial",
    force=True,
    colorbar=True,
    cmap="RdBu_r",  # Diverging: red=tension, blue=compression
    show=False,
    save_path="gallery/bolt analysis/3d_case3_bending.svg"
)

# Demonstrate combined loading - both modes (Case 4)
print("Generating shear mode plot for combined loading (Case 4)...")
result4.plot(
    mode="shear",
    force=True,
    bolt_forces=True,
    colorbar=True,
    cmap="coolwarm",
    show=False,
    save_path="gallery/bolt analysis/3d_case4_shear.svg"
)

print("Generating axial mode plot for combined loading (Case 4)...")
result4.plot(
    mode="axial",
    force=True,
    colorbar=True,
    cmap="RdBu_r",  # Diverging: red=tension, blue=compression
    show=False,
    save_path="gallery/bolt analysis/3d_case4_axial.svg"
)

print("\n" + "=" * 60)
print("Analysis complete! Check gallery/bolt analysis/ for plots.")
print("=" * 60)
