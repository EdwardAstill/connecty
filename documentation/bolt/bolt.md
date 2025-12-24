# Connecty - Bolt Analysis

## Overview

The bolt analysis module calculates **force distribution** on bolt groups using elastic and ICR methods per AISC 360. It focuses on geometry and force calculation—leave design checks and capacity comparisons to your application.

---

## Analysis Methods

Connecty provides two methods for in-plane shear force distribution, plus a separate tension calculation:

**Elastic Method (2D In-Plane)**
- Conservative vector analysis for in-plane loading only
- **Handles** (Fy, Fz, Mx): Direct shear + Torsion
  - Direct shear: $P/n$ (uniform distribution)
  - Torsional shear: $Tr/I_p$ (perpendicular to radius)
- Vector superposition of shear components
- Output: In-plane shear forces (Fy, Fz) at each bolt
- **Note:** Out-of-plane tension from (Fx, My, Mz) is calculated separately

**ICR Method (2D In-Plane)**
- Iterative Instantaneous Center of Rotation method
- **Handles in-plane loading only** (Fy, Fz, Mx)
- Accounts for non-linear load-deformation behavior
- Uses Crawford-Kulak load-deformation curves: $R = R_{ult}(1 - e^{-\mu \Delta})^\lambda$
- More accurate force distribution for eccentrically loaded bolt groups
- Output: In-plane shear forces (Fy, Fz) at each bolt
- **Note:** Out-of-plane tension from (Fx, My, Mz) is calculated separately

**Tension Calculation (Out-of-Plane)**
- Handles axial (Fx) and bending moments (My, Mz) to determine bolt tensions
- Works with both elastic and ICR shear methods
- Two approaches:
  - `tension_method="conservative"`: Neutral axis at mid-depth of plate
  - `tension_method="accurate"`: Neutral axis at d/6 from compression edge
- Output: Axial force (Fx) at each bolt (tension positive, compression clamped to zero)

---

## Core Classes

### 1. `BoltGroup`

A collection of bolts defined by coordinates or a pattern. BoltGroup defines geometry only - no analysis methods.

```python
from connecty import BoltGroup

# Option A: Explicit coordinates
bolts = BoltGroup(
    positions=[(0, 0), (0, 75), (0, 150)],
    diameter=20
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

### 2. `ConnectionLoad`

Represents applied forces and moments at a specific location on the connection.

```python
from connecty import ConnectionLoad

# Define load with forces, moments, and location
load = ConnectionLoad(
    Fx=0.0,               # Axial force (N)
    Fy=-100000,           # Vertical force (N)
    Fz=50000,             # Horizontal force (N)
    Mx=3000000,           # Torsion (N·mm)
    My=0.0,               # Bending about y (N·mm)
    Mz=0.0,               # Bending about z (N·mm)
    location=(0, 0, 150)  # (x, y, z) application point
)

# Get equivalent load at another position
eq_load = load.equivalent_load(position=(50, 100, 0))
```

**Method:**
- `equivalent_load(position)`: Transfers forces and moments to a new position using moment transfer equations: M_new = M_old + r × F

### 3. `Plate`

Defines the plate geometry for tension calculations.

```python
from connecty import Plate

# Define plate dimensions
plate = Plate(
    width=240.0,    # Plate width (mm)
    depth=200.0,    # Plate depth (mm)
    thickness=12.0  # Plate thickness (mm)
)
```

### 4. `BoltConnection`

Combines bolt group and plate geometry to define the complete connection. This is a frozen dataclass - no analysis methods.

```python
from connecty import BoltConnection

# Define connection geometry
connection = BoltConnection(
    bolt_group=bolts,
    plate=plate,
    n_shear_planes=1  # Number of shear planes
)
```

### 5. `ConnectionResult`

Performs analysis automatically upon instantiation. This replaces the old `analyze()` method pattern.

```python
from connecty import ConnectionResult

# Analysis happens in constructor
result = ConnectionResult(
    connection=connection,
    load=load,
    shear_method="elastic",      # "elastic" or "icr"
    tension_method="conservative" # "conservative" or "accurate"
)

# Access results immediately
print(f"Max shear: {result.max_shear_force:.1f} N")
print(f"Max tension: {result.max_axial_force:.1f} N")
print(f"Max stress: {result.max_combined_stress:.1f} MPa")
```

---

## Analysis Workflow

The API is straightforward - create geometry, define load, get results:

```python
from connecty import BoltGroup, Plate, BoltConnection, ConnectionLoad, ConnectionResult

# 1. Define bolt group geometry
bolts = BoltGroup.from_pattern(rows=3, cols=2, spacing_y=75, spacing_z=60, diameter=20)

# 2. Define plate geometry
plate = Plate(width=240, depth=200, thickness=12)

# 3. Create connection
connection = BoltConnection(bolt_group=bolts, plate=plate, n_shear_planes=1)

# 4. Define applied load
load = ConnectionLoad(Fy=-100000, location=(75, 150, 100))

# 5. Get results (analysis happens automatically)
result = ConnectionResult(
    connection=connection,
    load=load,
    shear_method="elastic",
    tension_method="conservative"
)

print(f"Max shear force: {result.max_shear_force:.1f} N")
print(f"Max axial force: {result.max_axial_force:.1f} N")

# ICR analysis (more accurate for eccentric loads)
result_icr = ConnectionResult(
    connection=connection,
    load=load,
    shear_method="icr",
    tension_method="accurate"
)
print(f"ICR Max shear: {result_icr.max_shear_force:.1f} N")
```

### Elastic Method Details (2D In-Plane)

**Geometric Properties:**
1. **Centroid**: Calculated from bolt coordinates
   - $C_y = \frac{\sum y_i}{n}$, $C_z = \frac{\sum z_i}{n}$

2. **Moments of Inertia**: About centroid
   - $I_p = \sum((y_i - C_y)^2 + (z_i - C_z)^2)$ (polar moment for Mx torsion)

**In-Plane Shear Forces (y-z plane):**
3. **Direct Shear**: $R_{direct,y} = F_y / n$, $R_{direct,z} = F_z / n$ (uniform)

4. **Torsional Shear**: $R_{torsion} = \frac{M_x \cdot r}{I_p}$ (perpendicular to radius)
   - Direction perpendicular to $(\Delta y, \Delta z)$
   - Magnitude proportional to distance from centroid

**Resultant In-Plane Force:**
5. **Vector Sum**: $R_{inplane} = \sqrt{R_y^2 + R_z^2}$

**Note:** Out-of-plane axial forces are calculated separately using the tension calculation method.

### ICR Method Details

1. **Iterative Solver**: Finds instantaneous center of rotation satisfying equilibrium

2. **Load-Deformation**: Crawford-Kulak model
   - $R = R_{ult}(1 - e^{-\mu\Delta/\Delta_{max}})^\lambda$
   - $\mu = 10$, $\lambda = 0.55$, $\Delta_{max} = 8.64$ mm

3. **Benefit**: Accounts for ductile redistribution; typically yields more realistic force distribution than elastic method

---

## Result Access

`ConnectionResult` provides comprehensive force and stress data:

```python
result = ConnectionResult(
    connection=connection,
    load=load,
    shear_method="elastic",
    tension_method="conservative"
)

# Force properties
result.max_shear_force      # Maximum shear force on any bolt (N)
result.min_shear_force      # Minimum shear force on any bolt (N)
result.max_axial_force      # Maximum axial force on any bolt (N)
result.min_axial_force      # Minimum axial force on any bolt (N)

# Stress properties
result.max_shear_stress     # Maximum in-plane shear stress (MPa)
result.min_shear_stress     # Minimum in-plane shear stress (MPa)
result.max_axial_stress     # Maximum out-of-plane axial stress (MPa)
result.min_axial_stress     # Minimum out-of-plane axial stress (MPa)
result.max_combined_stress  # Maximum combined stress (MPa)
result.min_combined_stress  # Minimum combined stress (MPa)

# Critical bolt info
result.bolt_results         # List of BoltResult objects (one per bolt)
result.max_shear_bolt_index # Index of bolt with maximum shear
result.max_axial_bolt_index # Index of bolt with maximum axial force

# Connection geometry
result.connection           # BoltConnection object
result.load                 # ConnectionLoad object

# Analysis methods used
result.shear_method         # "elastic" or "icr"
result.tension_method       # "conservative" or "accurate"

# ICR-specific (if shear_method="icr")
result.icr_point            # (y, z) location of instantaneous center
```

### BoltResult Object

Each bolt's force and stress is stored as a `BoltResult`:

```python
for br in result.bolt_results:
    print(f"Bolt at ({br.position[0]}, {br.position[1]})")
    
    # In-plane forces
    print(f"  Shear force = {br.shear_force:.2f} N")
    print(f"  Shear Fy = {br.shear_force_y:.2f} N")
    print(f"  Shear Fz = {br.shear_force_z:.2f} N")
    
    # Out-of-plane force
    print(f"  Axial force = {br.axial_force:.2f} N")
    
    # Stresses (calculated from forces and bolt area)
    print(f"  Shear stress = {br.shear_stress:.1f} MPa")
    print(f"  Axial stress = {br.axial_stress:.1f} MPa")
    print(f"  Combined stress = {br.combined_stress:.1f} MPa")
    print(f"  Angle = {br.angle:.1f}°")
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
- Bolts shown as circles colored by force/stress magnitude
- Applied load location marked with red ×
- **Plate boundary** shown as gray rectangle
- **Neutral axes** shown as dashed lines (blue for My bending, green for Mz bending)
  - Position calculated based on tension_method ("conservative" at mid-depth, "accurate" at d/6 from compression edge)
- ICR point shown (if ICR method used and shear mode)
- Title shows bolt count, size, and max force

### Pattern Visualization

```python
from connecty.bolt_plotter import plot_bolt_group

# Visualize bolt layout before analysis
plot_bolt_group(bolts, save_path="pattern.svg")
```

---

## Design Checks (AISC 360-22 & AS 4100)

Connecty provides **automatic design checks** for both AISC 360-22 (A325/A490) and AS 4100 (metric 8.8/10.9) bolts. Separate modules (`aisc` and `as4100`) handle each standard with dedicated check functions. Supports bearing-type and slip-critical (friction-type) connections with per-bolt utilization reporting for all limit states.

### Quick Start

```python
from connecty import BoltGroup, Plate, BoltConnection, ConnectionLoad, ConnectionResult
from connecty.bolt.checks import aisc, as4100

# Create geometry
bolts = BoltGroup.from_pattern(rows=3, cols=2, spacing_y=75, spacing_z=60, diameter=20)
plate = Plate(width=240, depth=200, thickness=12)
connection = BoltConnection(bolt_group=bolts, plate=plate, n_shear_planes=1)
load = ConnectionLoad(Fy=-100000, Fz=30000, location=(75, 150, 100))

# Run analysis
result = ConnectionResult(
    connection=connection,
    load=load,
    shear_method="elastic",
    tension_method="conservative"
)

# Define design parameters for AISC 360-22
design_aisc = aisc.BoltDesignParams(
    hole_type="standard",
    slot_orientation="perpendicular",
    threads_in_shear_plane=True,
    plate_fu=450.0,             # MPa
    plate_thickness=12.0,       # mm
    edge_distance_y=50.0,       # mm
    edge_distance_z=50.0        # mm
)

# Check using AISC 360-22
check_aisc = aisc.check_bolt_group_aisc(
    result,
    design_aisc,
    connection_type="bearing"  # "bearing" or "slip-critical"
)

# Access results
print(f"Governing utilization: {check_aisc.governing_utilization:.2f}")
print(f"Governing bolt: {check_aisc.governing_bolt_index}")
print(f"Governing limit state: {check_aisc.governing_limit_state}")

if check_aisc.governing_utilization <= 1.0:
    print("PASS")
else:
    print("FAIL")
```

### AISC 360-22 BoltDesignParams

Design parameters for AISC 360-22 checks (A325/A490 bolts):

```python
from connecty.bolt.checks import aisc

design = aisc.BoltDesignParams(
    # Hole type and orientation
    hole_type="standard",              # "standard", "oversize", "short_slotted", "long_slotted"
    slot_orientation="perpendicular",  # "perpendicular" or "parallel" (for slotted holes)
    threads_in_shear_plane=True,        # Threads in or excluded from shear plane
    
    # Slip-critical parameters (for slip-critical checks)
    slip_class="A",                    # "A" (μ=0.30) or "B" (μ=0.50)
    n_s=1,                              # Number of slip planes (typically 1 or 2)
    fillers=0,                          # Number of fillers (affects h_f factor)
    
    # Connected material properties
    plate_fu=450.0,                     # Ultimate tensile stress (MPa)
    plate_thickness=12.0,               # Plate thickness (mm)
    edge_distance_y=50.0,               # Edge distance in y-direction (mm)
    edge_distance_z=50.0,               # Edge distance in z-direction (mm)
    
    # Optional overrides
    tension_per_bolt=None,              # kN override (derives from Fx/n if None)
    n_b_tension=None,                   # Bolts carrying applied tension (for k_sc reduction)
    pretension_override=None            # kN override (uses AISC Table J3.1 if None)
)
```

### AS 4100 BoltDesignParams

Design parameters for AS 4100 / Steel Designers Handbook checks (metric 8.8/10.9 bolts):

```python
from connecty.bolt.checks import as4100

design = as4100.BoltDesignParams(
    # Hole type
    hole_type="standard",              # "standard", "oversize", "slotted"
    hole_type_factor=1.0,               # kh: 1.0 (standard), 0.85 (oversize), 0.70 (slotted)
    
    # Shear plane definition
    nn_shear_planes=1,                  # Threaded shear planes
    nx_shear_planes=0,                  # Unthreaded shear planes
    
    # Friction-type parameters (for friction-type checks)
    slip_coefficient=0.35,              # Friction coefficient μ
    n_e=1,                              # Number of shear planes (slip planes)
    prying_allowance=0.25,              # α factor for prying allowance
    
    # Connected material properties
    plate_fu=430.0,                     # Ultimate tensile stress (MPa)
    plate_fy=250.0,                     # Yield strength (MPa)
    plate_thickness=12.0,               # Plate thickness (mm)
    edge_distance=45.0,                 # Clear distance to edge (mm)
    
    # Optional
    tension_per_bolt=None,              # kN override (derives from Fx/n if None)
    use_analysis_bolt_tension_if_present=True  # Use Fx from analysis if available
)
```

### Check Functions

**AISC 360-22:**
```python
from connecty.bolt.checks import aisc

check = aisc.check_bolt_group_aisc(
    result,                          # ConnectionResult from analysis
    design,                          # aisc.BoltDesignParams
    connection_type="bearing"        # "bearing" or "slip-critical"
)
```

**AS 4100 / Steel Designers Handbook:**
```python
from connecty.bolt.checks import as4100

check = as4100.check_bolt_group_sd_handbook(
    result,                          # ConnectionResult from analysis
    design,                          # as4100.BoltDesignParams
    connection_type="bearing"        # "bearing" or "friction"
)
```

### Check Result Object

Both check functions return a result object with:

```python
check.governing_utilization     # Maximum utilization (0.0 to 1.0+)
check.governing_bolt_index      # Index of critical bolt (0-indexed)
check.governing_limit_state     # "shear", "tension", "bearing", or "slip"
check.connection_type           # "bearing" or "slip-critical"/"friction"
check.method                    # "elastic" or "icr"
check.details                   # List of BoltCheckDetail (one per bolt)
```

**Per-bolt details:**
```python
for detail in check.details:
    detail.bolt_index           # Bolt index (0-indexed)
    detail.point                # (y, z) bolt position
    detail.shear_demand         # In-plane shear force demand (kN)
    detail.tension_demand       # Out-of-plane tension force demand (kN)
    detail.shear_capacity       # Shear capacity (kN)
    detail.tension_capacity     # Tension capacity (kN)
    detail.bearing_capacity     # Bearing/tear-out capacity (kN)
    detail.slip_capacity        # Slip resistance capacity (if applicable)
    
    detail.shear_util           # Shear utilization ratio
    detail.tension_util         # Tension utilization ratio
    detail.bearing_util         # Bearing utilization ratio
    detail.slip_util            # Slip utilization (None for bearing-type)
    detail.governing_util       # Maximum utilization for this bolt
    detail.governing_limit_state # Limit state that governs for this bolt
```

### Examples

**AISC A325 - Bearing-Type**
```python
from connecty import BoltGroup, Plate, BoltConnection, ConnectionLoad, ConnectionResult
from connecty.bolt.checks import aisc

bolts = BoltGroup.from_pattern(rows=2, cols=3, spacing_y=80, spacing_z=70, diameter=20)
plate = Plate(width=240, depth=200, thickness=14)
connection = BoltConnection(bolt_group=bolts, plate=plate, n_shear_planes=1)
load = ConnectionLoad(Fy=-100000, Fz=25000, location=(40, 120, 100))

result = ConnectionResult(
    connection=connection,
    load=load,
    shear_method="elastic",
    tension_method="conservative"
)

design = aisc.BoltDesignParams(
    hole_type="standard",
    threads_in_shear_plane=True,
    plate_fu=450.0,
    plate_thickness=14.0,
    edge_distance_y=55.0,
    edge_distance_z=60.0
)

check = aisc.check_bolt_group_aisc(result, design, connection_type="bearing")
print(f"Utilization: {check.governing_utilization:.1%}")
print(f"Limit state: {check.governing_limit_state}")
```

**AISC A325 - Slip-Critical**
```python
design = aisc.BoltDesignParams(
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

check = aisc.check_bolt_group_aisc(result, design, connection_type="slip-critical")
print(f"Utilization: {check.governing_utilization:.1%}")
```

**AS 4100 Grade 8.8 - Bearing-Type**
```python
from connecty.bolt.checks import as4100

design = as4100.BoltDesignParams(
    hole_type="standard",
    nn_shear_planes=1,              # Threaded shear planes
    nx_shear_planes=0,              # Unthreaded shear planes
    plate_fu=430.0,
    plate_fy=250.0,
    plate_thickness=14.0,
    edge_distance=50.0
)

check = as4100.check_bolt_group_sd_handbook(result, design, connection_type="bearing")
print(f"Utilization: {check.governing_utilization:.1%}")
```

**AS 4100 Grade 10.9 - Friction-Type**
```python
design = as4100.BoltDesignParams(
    hole_type="standard",
    slip_coefficient=0.35,          # Friction coefficient μ
    n_e=1,                          # Number of shear planes
    plate_fu=430.0,
    plate_fy=250.0,
    plate_thickness=14.0,
    edge_distance=50.0
)

check = as4100.check_bolt_group_sd_handbook(result, design, connection_type="friction")
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
