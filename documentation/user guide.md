# Connecty User Guide

Welcome to the **Connecty** user guide. This package provides structural engineering analysis for welded and bolted connections according to AISC 360 provisions.

## Table of Contents

1. [Installation](#1-installation)
2. [Core Concepts](#2-core-concepts)
    - [Coordinate System](#coordinate-system)
    - [Units](#units)
    - [Defining Forces](#defining-forces)
3. [Weld Analysis](#3-weld-analysis)
    - [Overview & Methods](#weld-overview)
    - [Workflow with Sections](#weld-workflow-sections)
    - [Custom Geometry](#weld-custom-geometry)
    - [Weld Parameters](#weld-parameters)
    - [Results & Plotting](#weld-results)
4. [Bolt Analysis](#4-bolt-analysis)
    - [Overview & Methods](#bolt-overview)
    - [Creating Bolt Groups](#creating-bolt-groups)
    - [Bolt Parameters](#bolt-parameters)
    - [Results & Plotting](#bolt-results)
5. [Complete Examples](#5-complete-examples)
6. [API Reference Summary](#6-api-reference-summary)
7. [References & Standards](#7-references--standards)
8. [Limitations](#8-limitations)

---

## 1. Installation

Connecty can be installed using `uv` or `pip`.

```bash
uv add connecty
# or
pip install connecty
```

It relies on **sectiony** for geometry definition and **matplotlib** for visualization.

---

## 2. Core Concepts

### Coordinate System

Connecty uses a consistent 2D/3D coordinate system (matching the `sectiony` package):

- **y-axis**: Vertical (positive up)
- **z-axis**: Horizontal (positive right)
- **x-axis**: Longitudinal (out of page) - *Used for torsional moments*

The cross-section of the connection lies in the **y-z plane**.

### Units

The package is **unit-agnostic for geometry and loads**, but **material properties use fixed units**. You must maintain consistency within your chosen unit system.

**Recommended Unit Systems:**

**Metric (SI):**
- Length: mm
- Force: N  
- Moment: N·mm
- Stress: MPa (N/mm²)
- Bolt pretension: kN (for bolt diameters in mm)

**US Customary:**
- Length: inches
- Force: kip (1 kip = 1000 lbf)
- Moment: kip·in
- Stress: ksi (kip/in²)
- Bolt pretension: kip (for bolt diameters in inches)

**Important Notes:**

1. **Material Property Units (Fixed):**
   - Bolt shear strengths (`BOLT_SHEAR_STRENGTH`): **MPa**
   - Bolt pretension (`BOLT_PRETENSION`): **kN** (for diameters in **mm**)
   - Electrode strengths (`ELECTRODE_STRENGTH`): **MPa**
   - ICR deformation limit: **8.64 mm**

2. **Bolt Analysis Input:**
   - Input forces should be in **N** (they are converted to kN internally)
   - Or override material properties using `BoltParameters(F_nv=..., R_n=...)` for your unit system

3. **Consistency Required:**
   - All lengths must use the same unit (mm, inches, meters, etc.)
   - All forces must use the same unit (N, kN, kip, lbf, etc.)
   - All moments must be consistent with force × length
   - Stress = Force / Area (must be dimensionally consistent)

**Example with US Customary Units:**

```python
from connecty import BoltGroup, BoltParameters, Force

# Override material properties for US units
# A325 bolt: F_nv = 54 ksi (instead of 372 MPa)
# For 3/4" bolt: area = π(0.75/2)² = 0.442 in²
# Nominal capacity: R_n = 54 ksi × 0.442 in² = 23.9 kip
params = BoltParameters(
    diameter=0.75,        # 3/4" bolt (in inches)
    grade="A325",
    F_nv=54.0,          # Override: 54 ksi (instead of MPa lookup)
    R_n=23.9            # Override: nominal capacity in kip
)

# Use kip and inches throughout
force = Force(Fy=-100.0, location=(4.0, 0.0))  # 100 kip, 4 inches
bolts = BoltGroup(positions=[(0, 0), (0, 3)], parameters=params)
result = bolts.analyze(force)
# Note: Result forces will be in the same units as R_n (kip in this case)
```

**Example with Metric Units (Default):**

```python
# Standard metric usage - no overrides needed
params = BoltParameters(diameter=20, grade="A325")  # 20mm bolt
force = Force(Fy=-100000, location=(100, 0))  # 100 kN = 100000 N, 100mm
bolts = BoltGroup.from_pattern(rows=3, cols=2, spacing_y=75, spacing_z=60, parameters=params)
result = bolts.analyze(force)  # Forces in kN
```

**For Weld Analysis:**

Weld analysis is fully unit-agnostic. Material properties can be overridden:

```python
# US Customary example
params = WeldParameters(
    weld_type="fillet",
    leg=0.25,           # 1/4" leg (in inches)
    electrode="E70",
    F_EXX=70.0          # Override: 70 ksi instead of 483 MPa
)
# Use kip and inches - stresses will be in ksi
```

### Defining Forces

The `Force` class is used for both weld and bolt analysis. It allows you to define loads in 6 degrees of freedom and specify their point of application.

```python
from connecty import Force

# Load applied at a specific location (y=100, z=50)
force = Force(
    Fy=-50000,      # 50 kN Downward shear
    Fz=20000,       # 20 kN Horizontal shear
    Fx=10000,       # 10 kN Axial tension
    Mx=5e6,         # 5 kNm Torsion
    My=0,           # Bending about y-axis
    Mz=0,           # Bending about z-axis
    location=(100, 50) # Point of application (y, z)
)
```

**Note:** If a force is applied away from the connection's centroid, Connecty automatically calculates the resulting eccentric moments.

---

## 3. Weld Analysis

### Overview & Methods <a name="weld-overview"></a>

Connecty supports various weld types and analysis methods per AISC 360 (Section J2).

| Weld Type | Analysis Methods | Strength Limit |
|-----------|------------------|----------------|
| **Fillet** | Elastic, ICR | $\phi R_n = \phi(0.60 F_{EXX}) A_w$ |
| **PJP** | Elastic | $\phi R_n = \phi(0.60 F_{EXX}) A_w$ |
| **CJP** | Base Metal Check | Base metal governs ($F_y$, $F_u$) |
| **Plug/Slot** | Elastic (Shear only) | $\phi R_n = \phi(0.60 F_{EXX}) A_w$ |

#### Analysis Methods

1.  **Elastic Method** (Default)
    -   Conservative vector superposition.
    -   Full **3D analysis** (handles $F_x, F_y, F_z, M_x, M_y, M_z$).
    -   Calculates stress at discretized points along the weld.
    -   Resultant stress $f = \sqrt{f_{axial}^2 + f_{shear,y}^2 + f_{shear,z}^2}$.

2.  **ICR Method** (Instantaneous Center of Rotation)
    -   Applicable to **Fillet Welds** only.
    -   **2D analysis only** (considers $F_y, F_z, M_x$). Out-of-plane loads are ignored.
    -   Iteratively finds the center of rotation that satisfies equilibrium.
    -   Accounts for the directional strength increase factor $(1.0 + 0.50 \sin^{1.5}\theta)$.
    -   Generally more economical for eccentrically loaded connections.

### Workflow with Sections <a name="weld-workflow-sections"></a>

The `WeldedSection` class wraps a `sectiony` section to easily apply welds to standard shapes.

```python
from sectiony.library import rhs
from connecty import WeldedSection, WeldParameters

# 1. Define the steel section
section = rhs(b=100, h=200, t=10, r=15)

# 2. Initialize the wrapper
welded = WeldedSection(section=section)

# 3. Apply welds
# You can weld all segments or specific indices
params = WeldParameters(weld_type="fillet", leg=6.0, electrode="E70")
welded.weld_all_segments(params) 

# Alternatively, weld specific segments:
welded.add_weld(segment_index=0, parameters=params)
welded.add_welds([1, 2, 3], parameters=params)

# Get segment information to identify which edges to weld
segments = welded.get_segment_info()
for seg in segments:
    print(f"Segment {seg['index']}: {seg['type']} from {seg['start']} to {seg['end']}")
```

**Using `Weld.from_section()`:**

For simpler workflows, create a weld directly from a section:

```python
from sectiony.library import rhs
from connecty import Weld, WeldParameters

section = rhs(b=100, h=200, t=10, r=15)
params = WeldParameters(weld_type="fillet", leg=6.0, electrode="E70")

# Creates weld from section's outer contour (contour_index=0)
weld = Weld.from_section(section=section, parameters=params, contour_index=0)
```

### Custom Geometry <a name="weld-custom-geometry"></a>

For arbitrary weld paths (e.g., plate connections), use the `Weld` class directly with `sectiony.Geometry`.

```python
from connecty import Weld, WeldParameters
from sectiony import Geometry, Contour, Line

# Define a vertical weld line
path = Contour(segments=[
    Line(start=(0, -50), end=(0, 50))
])

weld = Weld(
    geometry=Geometry(contours=[path]),
    parameters=WeldParameters(weld_type="fillet", leg=8.0)
)
```

### Weld Parameters <a name="weld-parameters"></a>

Use `WeldParameters` to define physical properties.

```python
params = WeldParameters(
    weld_type="fillet",  # "fillet", "pjp", "cjp", "plug", "slot"
    leg=6.0,             # Leg size (mm) -> calculates throat automatically
    throat=4.2,          # Effective throat (mm). Overrides leg if provided.
    electrode="E70",     # Electrode strength (E60, E70, E80, etc.)
    F_EXX=None,          # Override electrode strength (MPa) if needed
    phi=0.75,            # Resistance factor (AISC default)
    
    # For Plug/Slot welds:
    area=314.16,         # Plug/slot hole area (mm²)
    
    # For CJP Base Metal Checks:
    t_base=12.0,         # Base metal thickness
    F_y=345,             # Yield strength (MPa)
    F_u=450              # Ultimate strength (MPa)
)
```

**Electrode Strength Lookup:**

If `F_EXX` is not provided, it's automatically looked up from the electrode classification:

| Electrode | $F_{EXX}$ (MPa) | $F_{EXX}$ (ksi) |
|-----------|-----------------|-----------------|
| E60 | 414 | 60 |
| E70 | 483 | 70 |
| E80 | 552 | 80 |
| E90 | 621 | 90 |
| E100 | 690 | 100 |
| E110 | 759 | 110 |

**Throat Calculation:**

For fillet welds, if only `leg` is provided, throat is calculated automatically:
- **Equal leg fillet (45°):** $a = w \times 0.707$
- For unequal leg or other angles, provide `throat` directly.

### Results & Plotting <a name="weld-results"></a>

Calculate stress and visualize results using the `stress()` method.

```python
# Calculate
result = welded.calculate_weld_stress(force, method="elastic")
# OR for custom geometry:
# result = weld.stress(force, method="elastic")

# Check capacity
print(f"Max Stress: {result.max:.2f} MPa")
print(f"Capacity: {result.capacity:.2f} MPa")
print(f"Utilization: {result.utilization():.1%}")
print(f"Adequate? {result.is_adequate()}")

# Plot Resultant Stress
result.plot(
    section=True,       # Show section outline (if available)
    force=True,         # Show applied force
    save_path="weld_results.svg"
)

# Plot Specific Components (Shear, Bending, etc.)
result.plot_components(
    components=["shear_resultant", "total_axial"],
    save_path="weld_components.svg"
)
```

**Complete Result Properties:**

```python
result = weld.stress(force)

# Basic properties
result.max              # Maximum resultant stress (MPa)
result.min              # Minimum resultant stress (MPa)
result.mean             # Average stress (MPa)
result.range            # Stress range (max - min) (MPa)
result.capacity         # Design capacity φ(0.60 × F_EXX) (MPa)

# Detailed access
result.max_point        # PointStress object at max location
result.all              # List of all PointStress objects
result.icr_point        # ICR location (if ICR method used)
result.rotation         # Rotation angle (if ICR method used)

# Methods
result.utilization(allowable=None)  # max / allowable (uses capacity if None)
result.is_adequate(allowable=None)  # True if utilization ≤ 1.0
result.at(y, z)                     # StressComponents at nearest point
```

**Accessing Stress Components:**

```python
# Get stress at specific location
components = result.at(y=100, z=0)

# Individual components
components.f_direct_y   # In-plane shear from Fy (uniform)
components.f_direct_z   # In-plane shear from Fz (uniform)
components.f_moment_y   # In-plane shear from Mx (y-component)
components.f_moment_z   # In-plane shear from Mx (z-component)
components.f_axial      # Out-of-plane from Fx (uniform)
components.f_bending    # Out-of-plane from My, Mz (linear)

# Computed properties
components.total_y      # f_direct_y + f_moment_y
components.total_z      # f_direct_z + f_moment_z
components.total_axial  # f_axial + f_bending
components.shear_resultant  # √(total_y² + total_z²)
components.resultant    # √(total_axial² + shear_resultant²)

# Access at maximum stress location
pt = result.max_point
print(f"Location: ({pt.y:.1f}, {pt.z:.1f})")
print(f"Stress: {pt.stress:.1f} MPa")
print(f"Components: {pt.components}")
```

**Plotting Options:**

```python
# Plot resultant stress
result.plot(
    section=True,           # Show section outline (if available)
    force=True,             # Show force arrow at application point
    colorbar=True,         # Show stress colorbar
    cmap="coolwarm",       # Matplotlib colormap
    weld_linewidth=5.0,    # Weld line thickness
    ax=None,               # Matplotlib axes (creates new if None)
    show=True,             # Display plot
    save_path="weld.svg"   # Save to file (.svg recommended)
)

# Plot individual stress components
result.plot_components(
    components=["direct", "moment", "axial", "bending"],
    layout="grid",         # "grid" or "row"
    save_path="components.svg"
)
```

**Note:** `section=True` only has an effect if the `Weld` was created via `Weld.from_section()` or `WeldedSection`. Otherwise, only the weld path is shown.

---

## 4. Bolt Analysis

### Overview & Methods <a name="bolt-overview"></a>

Connecty analyzes bolt groups for shear, bearing, and slip resistance.

| Bolt Type | Analysis Methods | Key Variable | Strength Limit |
|-----------|------------------|--------------|----------------|
| **Bearing** | Elastic, ICR | Diameter ($d_b$) | Shear/Bearing capacity ($\phi R_n$) |
| **Slip-Critical** | Elastic, ICR | Diameter ($d_b$) | Slip resistance ($\phi R_n$) |

#### Analysis Methods

1.  **Elastic Method**
    -   **Centroid**: Calculated from bolt coordinates: $C_y = \frac{\sum y_i}{n}$, $C_z = \frac{\sum z_i}{n}$.
    -   **Polar Moment**: $I_p = \sum (y_i^2 + z_i^2)$ about centroid.
    -   **Direct Shear**: $R_{direct} = P / n$ (uniform distribution).
    -   **Torsional Shear**: $R_{torsion} = \frac{M \cdot r}{I_p}$ (perpendicular to radius, linear with distance).
    -   **Superposition**: Vector sum of direct and torsional components.
    -   Conservative assumption of rigid plate behavior.
    -   Check: $f_{resultant} \leq \phi R_n$.

2.  **ICR Method**
    -   Iterative Instantaneous Center of Rotation method.
    -   Uses Crawford-Kulak load-deformation relationship: $R = R_{ult}(1 - e^{-\mu\Delta/\Delta_{max}})^\lambda$.
    -   Parameters: $\mu = 10$, $\lambda = 0.55$, $\Delta_{max} = 8.64$ mm.
    -   Allows for redistribution of forces, typically **15-30% more economical** for eccentric loads.
    -   Finds the instantaneous center of rotation that satisfies equilibrium.

### Creating Bolt Groups <a name="creating-bolt-groups"></a>

You can create groups from patterns or explicit coordinates.

```python
from connecty import BoltGroup, BoltParameters

# Define common parameters
params = BoltParameters(diameter=20, grade="A325")

# Option A: Rectangular Pattern
bolts = BoltGroup.from_pattern(
    rows=3, 
    cols=2, 
    spacing_y=75, 
    spacing_z=60,
    parameters=params
)

# Option B: Circular Pattern
bolts = BoltGroup.from_circle(
    n=8,
    radius=100,
    center=(0, 0),
    parameters=params
)

# Option C: Manual Coordinates
bolts = BoltGroup(
    positions=[(0,0), (0,100), (100,0)],
    parameters=params
)
```

### Bolt Parameters <a name="bolt-parameters"></a>

Control the strength calculation of the bolts.

```python
params = BoltParameters(
    diameter=20,          # mm
    grade="A325",         # "A325", "A490", "8.8", "10.9"
    threads_excluded=False, # "N" (included) or "X" (excluded) condition
    shear_planes=1,       # Single or double shear
    slip_critical=False,  # If True, checks slip resistance
    slip_class="B",       # Surface class A, B, or C (for slip-critical)
    hole_type="STD"       # "STD", "OVS", "SSL", "LSL"
)
```

### Results & Plotting <a name="bolt-results"></a>

```python
# Analyze
result = bolts.analyze(force, method="icr")

# Check results
print(f"Max Bolt Force: {result.max_force:.1f} kN")
print(f"Capacity per Bolt: {result.capacity:.1f} kN")
print(f"Utilization: {result.utilization():.1%}")

# Complete Result Properties
result.max_force        # Maximum resultant force on any bolt (kN)
result.min_force        # Minimum resultant force on any bolt (kN)
result.mean             # Average bolt force (kN)
result.capacity         # Design capacity per bolt φR_n (kN)
result.critical_bolt    # BoltForce object at max location
result.critical_index   # Index of most stressed bolt
result.bolt_forces      # List of all BoltForce objects
result.icr_point        # (y, z) location of ICR (if ICR method used)

# Methods
result.utilization(capacity=None)  # max_force / capacity
result.is_adequate(capacity=None) # True if utilization ≤ 1.0

# Access individual bolt forces
for bf in result.bolt_forces:
    print(f"Bolt at ({bf.y}, {bf.z})")
    print(f"  Fy = {bf.Fy:.2f} kN")
    print(f"  Fz = {bf.Fz:.2f} kN")
    print(f"  Resultant = {bf.resultant:.2f} kN")
    print(f"  Angle = {bf.angle:.1f}°")

# Visualize
result.plot(
    force=True,          # Show applied load location
    bolt_forces=True,    # Show reaction vectors at each bolt
    colorbar=True,       # Show force magnitude colorbar
    cmap="coolwarm",     # Matplotlib colormap
    show=True,           # Display plot
    save_path="bolt_group.svg"
)

# Visualize bolt pattern before analysis
from connecty.bolt_plotter import plot_bolt_pattern
plot_bolt_pattern(bolts, save_path="pattern.svg")
```

**Plot Features:**
- Bolts shown as circles colored by force magnitude
- Reaction forces shown as arrows at each bolt
- Applied load location marked with red ×
- ICR point shown (if ICR method used)
- Title includes bolt count, size, grade, max force, and utilization

---

## 5. Complete Examples

### Example 1: Fillet Weld - Elastic Method

```python
from sectiony.library import rhs
from connecty import Weld, WeldParameters, Force

section = rhs(b=100, h=200, t=10, r=15)
params = WeldParameters(
    weld_type="fillet",
    leg=6.0,              # 6mm leg → throat auto-calculated as 4.2mm
    electrode="E70"       # F_EXX = 483 MPa
)

weld = Weld.from_section(section=section, parameters=params)
force = Force(Fy=-100e3, location=(100, 0))  # Eccentric load
result = weld.stress(force, method="elastic")

print(f"Max stress: {result.max:.1f} MPa")
print(f"Capacity: {result.capacity:.1f} MPa")  # φ(0.60 × 483) = 217 MPa
print(f"Utilization: {result.utilization():.1%}")
```

### Example 2: Fillet Weld - ICR Method

```python
# Same setup as Example 1
result_icr = weld.stress(force, method="icr")
print(f"ICR Max stress: {result_icr.max:.1f} MPa")
print(f"ICR Utilization: {result_icr.utilization():.1%}")
# ICR typically gives lower utilization due to directional strength increase
```

### Example 3: PJP Groove Weld

```python
from connecty import Weld, WeldParameters, Force
from sectiony import Geometry, Contour, Line

weld_path = Contour(segments=[Line(start=(0, -150), end=(0, 150))])
params = WeldParameters(
    weld_type="pjp",
    throat=8.0,           # Effective throat E = 8mm
    electrode="E70"
)
weld = Weld(geometry=Geometry(contours=[weld_path]), parameters=params)

force = Force(Fx=200e3, Mz=50e6)  # Tension + bending
result = weld.stress(force)  # Elastic method only for PJP
```

### Example 4: CJP Weld (Base Metal Check)

```python
params = WeldParameters(
    weld_type="cjp",
    t_base=12.0,          # 12mm plate
    F_y=345,              # Grade 345 steel yield
    F_u=450,              # Ultimate strength
    electrode="E70"
)
weld = Weld(geometry=Geometry(contours=[weld_path]), parameters=params)

force = Force(Fx=500e3)  # Tension
result = weld.stress(force, method="base_metal")
# Result is base metal utilization, not weld stress
```

### Example 5: Plug Weld

```python
from sectiony import Geometry, Contour, Arc
import math

plug_center = Contour(segments=[
    Arc(center=(0, 0), radius=10, start_angle=0, end_angle=2*math.pi)
])
params = WeldParameters(
    weld_type="plug",
    area=math.pi * 10**2,  # πr² = 314 mm²
    electrode="E70"
)
weld = Weld(geometry=Geometry(contours=[plug_center]), parameters=params)

# Plug welds resist shear only
force = Force(Fy=-15e3, Fz=10e3)
result = weld.stress(force)
```

### Example 6: Bolt Group - Eccentric Load

```python
from connecty import BoltGroup, BoltParameters, Force

params = BoltParameters(diameter=20, grade="A325")
bolts = BoltGroup.from_pattern(rows=3, cols=2, spacing_y=75, spacing_z=60, parameters=params)

force = Force(Fy=-100000, location=(75, 150))  # Eccentric load

# Elastic analysis
result_elastic = bolts.analyze(force, method="elastic")
print(f"Elastic max: {result_elastic.max_force:.1f} kN")

# ICR analysis (more economical)
result_icr = bolts.analyze(force, method="icr")
print(f"ICR max: {result_icr.max_force:.1f} kN")
print(f"ICR location: {result_icr.icr_point}")
```

---

## 6. API Reference Summary <a name="5-api-reference-summary"></a>

### Main Classes

**`Weld(geometry, parameters, section=None)`**
- `geometry`: Weld path as `sectiony.Geometry` (required)
- `parameters`: `WeldParameters` configuration
- `section`: Optional `Section` reference for plotting
- Properties: `A`, `L`, `Cy`, `Cz`, `Iy`, `Iz`, `Ip`
- Methods: `stress(force, method, discretization)` → `StressResult`
- Class methods: `from_section(section, parameters, contour_index=0)` → `Weld`

**`WeldedSection(section)`**
- `section`: `sectiony.Section` object
- Methods:
  - `weld_all_segments(params, contour_index=None, include_hollows=False)`
  - `add_weld(segment_index, parameters)`
  - `add_welds(segment_indices, parameters)`
  - `get_segment_info(contour_index=None, include_hollows=False)`
  - `calculate_weld_stress(force, method, discretization)` → `StressResult`
  - `plot_weld_stress(force, method, ...)` → Axes

**`WeldParameters`**
- `weld_type`: `"fillet" | "pjp" | "cjp" | "plug" | "slot"`
- `leg`: Fillet leg size (any length unit)
- `throat`: Effective throat (any length unit)
- `area`: Plug/slot area (any length² unit)
- `electrode`: Electrode classification (`"E70"`, etc.; lookup table uses MPa)
- `F_EXX`: Override electrode strength (any stress unit; default lookup is MPa)
- `F_y`, `F_u`: Base metal strengths (any stress unit)
- `t_base`: Base metal thickness (any length unit)
- `phi`: Resistance factor (default 0.75)
- Property: `capacity` → Design capacity φ(0.60 × F_EXX) (units match F_EXX)

**`BoltGroup(positions, parameters)`**
- `positions`: List of `(y, z)` coordinates
- `parameters`: `BoltParameters` configuration
- Properties: `n`, `Cy`, `Cz`, `Iy`, `Iz`, `Ip`
- Methods: `analyze(force, method)` → `BoltResult`
- Class methods:
  - `from_pattern(rows, cols, spacing_y, spacing_z, parameters, origin=(0,0))`
  - `from_circle(n, radius, parameters, center=(0,0), start_angle=0)`

**`BoltParameters`**
- `diameter`: Bolt diameter (any length unit; pretension lookup assumes mm)
- `grade`: `"A325" | "A490" | "8.8" | "10.9"`
- `threads_excluded`: Thread condition (`False` = N, `True` = X)
- `hole_type`: `"STD" | "OVS" | "SSL" | "LSL"`
- `shear_planes`: Number of shear planes (1 or 2)
- `slip_critical`: Use slip resistance instead of shear
- `slip_class`: Surface class `"A" | "B" | "C"` (for slip-critical)
- `phi`: Resistance factor (default 0.75)
- `F_nv`: Override nominal shear strength (any stress unit; default lookup is MPa)
- `R_n`: Override nominal capacity per bolt (any force unit; default calculation uses kN)
- Properties: `capacity` → Design capacity φR_n (units match `R_n` or default to kN)

**`Force(Fx=0, Fy=0, Fz=0, Mx=0, My=0, Mz=0, location=(0,0))`**
- `Fx`: Axial force (out-of-plane)
- `Fy`: Vertical shear (in-plane)
- `Fz`: Horizontal shear (in-plane)
- `Mx`: Torsion about x-axis
- `My`: Bending about y-axis
- `Mz`: Bending about z-axis
- `location`: Application point `(y, z)`

### Result Classes

**`StressResult`**
- Properties: `max`, `min`, `mean`, `range`, `capacity`, `max_point`, `all`, `icr_point`, `rotation`
- Methods:
  - `at(y, z)` → `StressComponents`
  - `utilization(allowable=None)` → `float`
  - `is_adequate(allowable=None)` → `bool`
  - `plot(section, force, colorbar, cmap, ...)` → Axes
  - `plot_components(components, layout, ...)` → Axes

**`BoltResult`**
- Properties: `max_force`, `min_force`, `mean`, `capacity`, `critical_bolt`, `critical_index`, `bolt_forces`, `icr_point`
- Methods:
  - `utilization(capacity=None)` → `float`
  - `is_adequate(capacity=None)` → `bool`
  - `plot(force, bolt_forces, colorbar, cmap, ...)` → Axes

**`BoltForce`**
- Properties: `point`, `y`, `z`, `Fy`, `Fz`, `resultant`, `angle`

**`PointStress`**
- Properties: `point`, `y`, `z`, `stress`, `components`

**`StressComponents`**
- Properties: `f_direct_y`, `f_direct_z`, `f_moment_y`, `f_moment_z`, `f_axial`, `f_bending`
- Computed: `total_y`, `total_z`, `total_axial`, `shear_resultant`, `resultant`

---

## 7. References & Standards

Based on **AISC 360-22** (Specification for Structural Steel Buildings):

- **Section J2**: Welds
- **Section J3**: Bolts
- **Table J2.5**: Available Strength of Welded Joints
- **Table J3.2**: Nominal Shear Strength of Bolts

Key equations:
- Fillet/PJP/Plug nominal strength: $R_n = F_{nw} \times A_{we}$
- Where $F_{nw} = 0.60 \times F_{EXX}$ (filler metal classification strength)
- Design strength: $\phi R_n$ with $\phi = 0.75$ for welds

ICR method references:
- AISC Design Guide 8: Column Base Plates
- AWS D1.1 Annex K
- Crawford-Kulak load-deformation model

---

## 8. Limitations

1. **Linear elastic analysis** - Does not model weld/bolt ductility or load redistribution (except ICR method)
2. **2D weld groups** - All welds assumed in same plane (y-z)
3. **No fatigue** - Static loading only; use other tools for fatigue assessment
4. **Simplified shear lag** - Does not account for shear lag in long connections
5. **No weld defects** - Assumes full-strength welds without defects
6. **ICR method limitations** - For welds, ICR is 2D only (ignores out-of-plane loads)
7. **Bolt bearing** - Bearing capacity checks on connected material are not included
