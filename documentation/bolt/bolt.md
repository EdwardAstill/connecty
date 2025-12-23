# Connecty - Bolt Analysis

## Overview

The bolt analysis module calculates **force distribution** on bolt groups using elastic and ICR methods per AISC 360. It focuses on geometry and force calculation—leave design checks and capacity comparisons to your application.

---

## Analysis Methods

Connecty provides two methods for calculating force at each bolt location:

**Elastic Method (3D)**
- Conservative vector analysis for full 6DOF loading
- **In-plane** (Fy, Fz, Mx): Direct shear + Torsion
  - Direct shear: $P/n$ (uniform distribution)
  - Torsional shear: $Tr/I_p$ (perpendicular to radius)
- **Out-of-plane** (Fx, My, Mz): Direct axial + Bending
  - Direct axial: $Fx/n$ (uniform distribution)
  - Bending: Linear variation with distance from centroid
- Vector superposition of all components
- Output: 3D force vector (Fx, Fy, Fz) at each bolt

**ICR Method (2D)**
- Iterative Instantaneous Center of Rotation method
- **Handles in-plane loading only** (Fy, Fz, Mx)
- **Ignores out-of-plane loads** (Fx, My, Mz)
- Accounts for non-linear load-deformation behavior
- Uses Crawford-Kulak load-deformation curves: $R = R_{ult}(1 - e^{-\mu \Delta})^\lambda$
- More accurate force distribution for eccentrically loaded bolt groups
- Output: In-plane force vector (Fy, Fz) at each bolt

---

## Core Classes

### 1. `BoltGroup`

A collection of bolts defined by coordinates or a pattern.

```python
from connecty import BoltGroup, BoltParameters

# Option A: Explicit coordinates
bolts = BoltGroup(
    positions=[(0, 0), (0, 75), (0, 150)],
    parameters=BoltParameters(diameter=20)
)

# Option B: Pattern generation (rectangular)
bolts = BoltGroup.from_pattern(
    rows=3, 
    cols=2, 
    spacing_y=75, 
    spacing_z=60,
    diameter=20,
    origin=(0, 0)
)

# Option C: Circular pattern
bolts = BoltGroup.from_circle(
    n=8,
    radius=100,
    diameter=20,
    center=(0, 0),
    start_angle=0
)
```

### 2. `BoltParameters`

Configuration for bolt geometry (for visualization and ICR calculations).

```python
from connecty import BoltParameters

params = BoltParameters(
    diameter=20  # Bolt diameter in mm
)
```

That's it! Only diameter is needed. Material properties are outside the scope of force calculation.

### 3. `Load` (Shared)

Uses the existing `Load` class for consistent load definition.

```python
from connecty import Load

# 2D in-plane loading (supported by both elastic and ICR)
load = Load(
    Fy=-100000,           # 100 kN downward (N)
    Fz=50000,             # 50 kN horizontal (N)
    Mx=3000000,           # 3 kN·m torsion (N·mm)
    location=(0, 0, 150)  # (x, y, z) application point
)

# Full 3D loading (elastic method only)
load_3d = Load(
    Fx=50000,             # 50 kN axial tension (N)
    Fy=-100000,           # 100 kN downward (N)
    Fz=60000,             # 60 kN horizontal (N)
    Mx=5000000,           # 5 kN·m torsion (N·mm)
    My=2500000,           # 2.5 kN·m bending about y (N·mm)
    Mz=-2000000,          # 2 kN·m bending about z (N·mm)
    location=(0, 0, 120)  # (x, y, z) application point
)
```

---

## Analysis Workflow

The API is straightforward:

```python
from connecty import BoltGroup, BoltParameters, Load

# Setup
params = BoltParameters(diameter=20)
bolts = BoltGroup.from_pattern(rows=3, cols=2, spacing_y=75, spacing_z=60, diameter=20)
load = Load(Fy=-100000, location=(75, 150))

# Elastic analysis
result = bolts.analyze(load, method="elastic")
print(f"Max bolt force: {result.max_force:.1f} kN")

# ICR analysis (more accurate for eccentric loads)
result_icr = bolts.analyze(load, method="icr")
print(f"ICR Max force: {result_icr.max_force:.1f} kN")
```

### Elastic Method Details (3D)

**Geometric Properties:**
1. **Centroid**: Calculated from bolt coordinates
   - $C_y = \frac{\sum y_i}{n}$, $C_z = \frac{\sum z_i}{n}$

2. **Moments of Inertia**: About centroid
   - $I_y = \sum (z_i - C_z)^2$ (for My bending)
   - $I_z = \sum (y_i - C_y)^2$ (for Mz bending)
   - $I_p = I_y + I_z$ (polar moment for Mx torsion)

**In-Plane Forces (y-z plane):**
3. **Direct Shear**: $R_{direct,y} = F_y / n$, $R_{direct,z} = F_z / n$ (uniform)

4. **Torsional Shear**: $R_{torsion} = \frac{M_x \cdot r}{I_p}$ (perpendicular to radius)
   - Direction perpendicular to $(\Delta y, \Delta z)$
   - Magnitude proportional to distance from centroid

**Out-of-Plane Forces (x-direction):**
5. **Direct Axial**: $R_{direct,x} = F_x / n$ (uniform)

6. **Bending Forces**: Linear variation with distance
   - $R_{bend,x} = \frac{M_y \cdot \Delta z}{I_y} + \frac{M_z \cdot \Delta y}{I_z}$
   - Creates tension/compression varying across pattern

**Resultant:**
7. **Vector Sum**: $R_{total} = \sqrt{R_x^2 + R_y^2 + R_z^2}$

### ICR Method Details

1. **Iterative Solver**: Finds instantaneous center of rotation satisfying equilibrium

2. **Load-Deformation**: Crawford-Kulak model
   - $R = R_{ult}(1 - e^{-\mu\Delta/\Delta_{max}})^\lambda$
   - $\mu = 10$, $\lambda = 0.55$, $\Delta_{max} = 8.64$ mm

3. **Benefit**: Accounts for ductile redistribution; typically yields more realistic force distribution than elastic method

---

## Result Access

`BoltResult` provides force data at each bolt:

```python
result = bolts.analyze(force, method="elastic")

# Force properties
result.max_force       # Maximum resultant force on any bolt (kN)
result.min_force       # Minimum resultant force on any bolt (kN)
result.mean            # Average bolt force (kN)

# Stress properties (if diameter set)
result.max_stress      # Maximum in-plane shear stress (MPa)
result.min_stress      # Minimum in-plane shear stress (MPa)
result.mean_stress     # Average shear stress (MPa)

result.max_axial_stress   # Maximum out-of-plane axial stress (MPa)
result.min_axial_stress   # Minimum out-of-plane axial stress (MPa)
result.mean_axial_stress  # Average axial stress (MPa)

result.max_combined_stress   # Maximum combined stress (MPa)
result.min_combined_stress   # Minimum combined stress (MPa)
result.mean_combined_stress  # Average combined stress (MPa)

# Critical bolt info
result.critical_bolt   # BoltForce object at max location
result.critical_index  # Index of most stressed bolt

# All bolt data
result.bolt_forces     # List of all BoltForce objects

# ICR-specific
result.icr_point       # (y, z) location of instantaneous center
result.method          # "elastic" or "icr"
```

### BoltForce Object

Each bolt's force is stored as a `BoltForce`:

```python
for bf in result.bolt_forces:
    print(f"Bolt at ({bf.y}, {bf.z})")
    
    # In-plane forces
    print(f"  Fy = {bf.Fy:.2f} kN")
    print(f"  Fz = {bf.Fz:.2f} kN")
    print(f"  Shear = {bf.shear:.2f} kN")
    
    # Out-of-plane force
    print(f"  Fx = {bf.Fx:.2f} kN")
    print(f"  Axial = {bf.axial:.2f} kN")
    
    # Total 3D force
    print(f"  Resultant = {bf.resultant:.2f} kN")
    print(f"  Angle = {bf.angle:.1f}°")
    
    # Stresses (if diameter set)
    print(f"  Shear stress = {bf.shear_stress:.1f} MPa")
    print(f"  Axial stress = {bf.axial_stress:.1f} MPa")
    print(f"  Combined stress = {bf.combined_stress:.1f} MPa")
```

**Stress Calculations:**

- **Shear stress** (τ): In-plane shear stress
  - τ = √(Fy² + Fz²) / A
  - Where A = π(d/2)² is bolt cross-sectional area
  
- **Axial stress** (σ): Out-of-plane axial stress (signed)
  - σ = Fx / A
  - Positive values indicate tension, negative values indicate compression
  
- **Combined stress**: Total stress magnitude
  - √(τ² + |σ|²)

**Important:** The shear stress calculation is the same for both bearing-type and slip-critical connections:
- **Bearing-type**: Shear stress is the primary resistance mechanism (checked against φFnv per AISC J3.6)
- **Slip-critical**: Shear stress represents the post-slip capacity; primary resistance comes from friction between plates (AISC J3.8-J3.9). AISC requires checking both slip resistance AND shear/bearing limit states.

---

## Visualization

```python
# Plot analysis results
result.plot(
    mode="shear",        # "shear" or "axial" - type of force to visualize
    force=True,          # Show applied load location
    bolt_forces=True,    # Show reaction vectors at each bolt (arrows shown for shear mode only)
    colorbar=True,       # Show force magnitude colorbar
    cmap="coolwarm",     # Matplotlib colormap (e.g., "RdBu_r" for axial)
    show=True,           # Display immediately
    save_path="bolt_analysis.svg"  # Save to file
)
```

**Plotting Modes:**

- **`mode="shear"`** (default): Visualizes in-plane shear forces
  - Bolts colored by shear magnitude (always positive)
  - Force arrows shown at each bolt
  - Suitable for both elastic and ICR results
  
- **`mode="axial"`**: Visualizes out-of-plane axial forces
  - Bolts colored by signed axial force (positive = tension, negative = compression)
  - No force arrows shown
  - Only available for elastic method (raises error for ICR)
  - Recommended colormap: `"RdBu_r"` (red=tension, blue=compression)
  - Colorbar label includes "[+tension/-compression]"

Normalization: Colors scale to the actual data range (min→max); the palette is not forcibly centered at zero.

**Features:**
- Bolts shown as circles colored by force magnitude
- Applied load location marked with red ×
- ICR point shown (if ICR method used and shear mode)
- Title shows bolt count, size, and max force

### Pattern Visualization

```python
from connecty.bolt_plotter import plot_bolt_pattern

# Visualize bolt layout before analysis
plot_bolt_pattern(bolts, save_path="pattern.svg")
```

---

## Design Checks (AISC 360-22)

Connecty provides **automatic AISC 360-22 checks** for A325 and A490 bolts, supporting both bearing-type and slip-critical connections. Checks include shear, tension, bearing/tear-out, and slip resistance limits with per-bolt utilization reporting.

### Quick Start

```python
from connecty import BoltGroup, BoltDesignParams, Load

# Create bolt group
bolts = BoltGroup.from_pattern(rows=3, cols=2, spacing_y=75, spacing_z=60, diameter=20)
force = Load(Fy=-100000, Fz=30000, location=(75, 150))

# Define design parameters (A325, standard holes, bearing-type)
design = BoltDesignParams(
    grade="A325",
    hole_type="standard",
    slot_orientation="perpendicular",
    threads_in_shear_plane=True,
    slip_class="A",
    n_s=1,
    fillers=0,
    plate_fu=450.0,      # MPa
    plate_thickness=12.0, # mm
    edge_distance_y=50.0, # mm
    edge_distance_z=50.0  # mm
)

# Run check
check = bolts.check_aisc(
    force=force,
    design=design,
    method="elastic",
    connection_type="bearing"
)

# Access results
print(f"Governing utilization: {check.governing_utilization:.2f}")
print(f"Governing bolt: {check.governing_bolt_index}")
print(f"Governing limit state: {check.governing_limit_state}")

if check.governing_utilization <= 1.0:
    print("PASS")
else:
    print("FAIL")
```

### BoltDesignParams

Defines all design-only inputs required for AISC checks. This dataclass captures material properties, geometry, and connection details not needed for analysis:

```python
from connecty import BoltDesignParams

design = BoltDesignParams(
    # Grade and bolt geometry
    grade="A325",              # "A325" or "A490"
    hole_type="standard",      # "standard", "oversize", "short_slotted", "long_slotted"
    slot_orientation="perpendicular",  # "perpendicular" or "parallel" (for slotted holes)
    threads_in_shear_plane=True,  # Threads in or excluded from shear plane
    
    # Slip-critical parameters
    slip_class="A",            # "A" (μ=0.30) or "B" (μ=0.50)
    n_s=1,                      # Number of slip planes
    fillers=0,                  # Count of fillers (affects h_f factor)
    
    # Connected material properties
    plate_fu=450.0,             # Ultimate tensile stress (MPa)
    plate_thickness=12.0,       # Plate thickness (mm)
    edge_distance_y=50.0,       # Edge distance in y-direction (mm)
    edge_distance_z=50.0,       # Edge distance in z-direction (mm)
    
    # Optional overrides
    tension_per_bolt=None,      # kN override (if None, derives from Fx/n)
    n_b_tension=None,           # Bolts carrying applied tension (for k_sc reduction)
    pretension_override=None    # kN override (if None, uses AISC Table J3.1)
)
```

### BoltCheckResult

Returned by `check_aisc()` with complete utilization information:

```python
check = bolts.check_aisc(force, design, connection_type="bearing")

# Summary properties
print(check.governing_utilization)    # Max util across all bolts/limit states
print(check.governing_bolt_index)     # Index of critical bolt
print(check.governing_limit_state)    # "shear", "tension", "bearing", or "slip"
print(check.connection_type)          # "bearing" or "slip-critical"
print(check.method)                   # "elastic" or "icr"

# Per-bolt details for reporting
for detail in check.details:
    print(f"Bolt {detail.bolt_index}:")
    print(f"  Shear demand: {detail.shear_demand:.2f} kN")
    print(f"  Tension demand: {detail.tension_demand:.2f} kN")
    print(f"  Shear util: {detail.shear_util:.3f}")
    print(f"  Tension util: {detail.tension_util:.3f}")
    print(f"  Bearing util: {detail.bearing_util:.3f}")
    if detail.slip_util is not None:
        print(f"  Slip util: {detail.slip_util:.3f}")
    print(f"  Governing: {detail.governing_util:.3f} ({detail.governing_limit_state})")

# Dictionary export (for tables/reports)
info_dict = check.info  # Nested dict with all results
```

### Connection Types

**Bearing-Type**
```python
check = bolts.check_aisc(force, design, connection_type="bearing")
```
Checks J3.6, J3.7, J3.10:
- Shear rupture: $U_V = \frac{V_u}{\phi F_{nv} A_b}$
- Tension rupture (with J3.7 interaction): $U_T = \frac{T_u}{\phi F'_{nt} A_b}$
- Bearing/tear-out: $U_{bear} = \frac{V_u}{\phi R_n}$ where $R_n = \min(2.4dtF_u, 1.2l_ctF_u)$

**Slip-Critical**
```python
check = bolts.check_aisc(force, design, connection_type="slip-critical")
```
Checks J3.8–J3.9 (plus all bearing-type):
- Slip resistance: $U_{slip} = \frac{V_u}{\phi \mu D_u h_f T_b n_s k_{sc}}$

Where:
- $\phi = 1.00$ (standard holes, short slots ⊥ load), 0.85 (oversize, short slots ∥), 0.70 (long slots)
- $\mu = 0.30$ (Class A) or 0.50 (Class B)
- $D_u = 1.13$ (mean installed pretension multiplier)
- $h_f = 1.0$ (≤1 filler) or 0.85 (≥2 fillers)
- $T_b$ = pretension from AISC Table J3.1
- $k_{sc} = \max(0, 1 - T_u / (D_u T_b n_b))$ (combined tension–shear reduction)

### Examples

**Bearing-Type Check**
```python
from connecty import BoltGroup, BoltDesignParams, Load

bolts = BoltGroup.from_pattern(rows=2, cols=3, spacing_y=80, spacing_z=70, diameter=20)
force = Load(Fy=-100000, Fz=25000, location=(40, 120))

design = BoltDesignParams(
    grade="A325",
    hole_type="standard",
    threads_in_shear_plane=True,
    plate_fu=450.0,
    plate_thickness=14.0,
    edge_distance_y=55.0,
    edge_distance_z=60.0
)

check = bolts.check_aisc(force, design, method="elastic", connection_type="bearing")
print(f"Utilization: {check.governing_utilization:.1%}")
```

**Slip-Critical Check (A325 Class B)**
```python
design = BoltDesignParams(
    grade="A325",
    hole_type="short_slotted",
    slot_orientation="perpendicular",
    threads_in_shear_plane=False,
    slip_class="B",
    n_s=2,
    fillers=0,
    plate_fu=450.0,
    plate_thickness=14.0,
    edge_distance_y=55.0,
    edge_distance_z=60.0,
    n_b_tension=6  # All 6 bolts carry applied tension
)

check = bolts.check_aisc(force, design, method="elastic", connection_type="slip-critical")
print(f"Utilization: {check.governing_utilization:.1%}")
```

### AISC Reference Data

The following AISC 360-22 data are built into the checker:

**Table J3.1 (Minimum Pretension, kN)**
| Bolt Size | A325 | A490 |
|-----------|------|------|
| M20       | 142  | 179  |
| M22       | 176  | 221  |
| M24       | 205  | 257  |

**Table J3.2 (Nominal Stresses, MPa)**
| Grade | $F_{nt}$ | $F_{nv}$ (N) | $F_{nv}$ (X) |
|-------|----------|--------------|-------------|
| A325  | 620      | 370          | 470         |
| A490  | 780      | 470          | 580         |

For complete AISC 360-22 standard reference, see [../standards/AISC 360-22.md](../standards/AISC%20360-22.md).
