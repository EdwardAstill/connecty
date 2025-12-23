# Connecty API Reference

Complete API documentation for the Connecty structural connection analysis and design check library.

---

## Table of Contents

1. [Imports](#imports)
2. [Shared Classes](#shared-classes)
3. [Bolt Analysis](#bolt-analysis)
4. [Bolt Design Checks](#bolt-design-checks)
5. [Weld Analysis](#weld-analysis)
6. [Weld Parameters](#weld-parameters)
7. [Visualization](#visualization)

---

## Imports

```python
from connecty import (
    # Bolt analysis
    BoltGroup,
    BoltParameters,
    BoltResult,
    BoltForce,
    
    # Bolt design checks (AISC 360-22)
    BoltDesignParams,
    BoltCheckResult,
    BoltCheckDetail,
    
    # Weld analysis
    Weld,
    WeldParams,
    LoadedWeld,
    WeldStress,
    
    # Shared
    Load,
)
```

---

## Shared Classes

### `Load`

Represents a concentrated force and moment applied at a point.

```python
class Load:
    Fx: float          # Axial force (out-of-plane, tension positive) [kN, kip, etc.]
    Fy: float          # Shear force in y-direction (vertical) [kN, kip, etc.]
    Fz: float          # Shear force in z-direction (horizontal) [kN, kip, etc.]
    Mx: float          # Torsional moment about x-axis [kN·mm, kip·in, etc.]
    My: float          # Bending moment about y-axis [kN·mm, kip·in, etc.]
    Mz: float          # Bending moment about z-axis [kN·mm, kip·in, etc.]
    location: tuple    # (x, y, z) application point
```

**Constructor:**
```python
# With forces only (moments calculated from eccentricity)
load = Load(Fy=-100.0, Fz=50.0, location=(0, 100, 150))

# With forces and moments
load = Load(
    Fx=0.0,
    Fy=-100.0,
    Fz=50.0,
    Mx=5000.0,    # Applied torsion
    My=0.0,
    Mz=0.0,
    location=(0, 100, 150)
)

# Alternative constructor with descriptive names
load = Load.from_components(
    axial=0.0,
    shear_y=-100.0,
    shear_z=50.0,
    torsion=5000.0,
    moment_y=0.0,
    moment_z=0.0,
    at=(0, 100, 150)
)
```

**Attributes:**
- `Fx`, `Fy`, `Fz`: Force components (positive per right-hand rule)
- `Mx`, `My`, `Mz`: Moment components (default 0.0)
- `location`: (x, y, z) coordinates where force is applied
- **Note**: For bolt analysis, moments are typically generated from force eccentricity rather than applied directly

**Methods:**
```python
force.at(x, y, z)                    # Get equivalent force/moments at a point
force.get_moments_about(x, y, z)     # Get total moments about a point
force.shear_magnitude                # √(Fy² + Fz²)
force.total_force_magnitude          # √(Fx² + Fy² + Fz²)
```

---

## Bolt Analysis

### `BoltParameters`

Defines bolt geometry for force calculations and visualization.

```python
class BoltParameters:
    diameter: float    # Bolt diameter [mm, in, etc.]
```

**Constructor:**
```python
params = BoltParameters(diameter=20)  # M20 bolt
```

**Attributes:**
- `diameter`: Bolt diameter (used for ICR load-deformation curves and visualization)

---

### `BoltGroup`

A collection of bolts with analysis methods.

**Constructors:**

```python
# Option A: Explicit coordinates
bolts = BoltGroup(
    positions=[(0, 0), (0, 75), (0, 150)],
    parameters=BoltParameters(diameter=20)
)

# Option B: Rectangular pattern
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

**Class Methods:**

#### `from_pattern(rows, cols, spacing_y, spacing_z, diameter, origin=(0, 0))`
Creates a rectangular bolt pattern.

- `rows` (int): Number of rows
- `cols` (int): Number of columns
- `spacing_y` (float): Spacing between rows [same unit as diameter]
- `spacing_z` (float): Spacing between columns [same unit as diameter]
- `diameter` (float): Bolt diameter [same unit]
- `origin` (tuple): (y, z) origin for pattern
- **Returns:** `BoltGroup`

#### `from_circle(n, radius, diameter, center=(0, 0), start_angle=0)`
Creates a circular bolt pattern.

- `n` (int): Number of bolts
- `radius` (float): Radius from center [same unit as diameter]
- `diameter` (float): Bolt diameter [same unit]
- `center` (tuple): (y, z) center point
- `start_angle` (float): Starting angle in degrees
- **Returns:** `BoltGroup`

**Instance Methods:**

#### `analyze(force, method="elastic")`
Calculate forces at each bolt.

```python
result = bolts.analyze(force, method="elastic")
# or
result = bolts.analyze(force, method="icr")
```

- `force` (`Force` or `Load`): Applied force and location
- `method` (str): `"elastic"` or `"icr"`
- **Returns:** `BoltResult`

#### `check_aisc(force, design, method="elastic", connection_type="bearing")`
Perform AISC 360-22 design check.

```python
check = bolts.check_aisc(
    force=force,
    design=design_params,
    method="elastic",
    connection_type="bearing"
)
```

- `force` (`Force` or `Load`): Applied force and location
- `design` (`BoltDesignParams`): Design parameters
- `method` (str): `"elastic"` or `"icr"`
- `connection_type` (str): `"bearing"` or `"slip-critical"`
- **Returns:** `BoltCheckResult`

**Properties:**

```python
bolts.n_bolts              # Total number of bolts
bolts.positions            # List of (y, z) coordinates
bolts.parameters           # BoltParameters instance
bolts.centroid             # (y, z) centroid of bolt group
bolts.polar_moment         # Polar moment of inertia about centroid
```

---

### `BoltResult`

Result of bolt group analysis containing forces at each bolt.

**Attributes:**

```python
result.max_force           # Maximum resultant force on any bolt [kN, kip, etc.]
result.min_force           # Minimum resultant force on any bolt
result.mean                # Average force per bolt
result.max_stress          # Maximum shear stress on any bolt (MPa, ksi)
result.min_stress          # Minimum shear stress on any bolt (MPa, ksi)
result.mean_stress         # Average shear stress across bolts (MPa, ksi)
result.critical_bolt       # BoltForce object at maximum force location
result.critical_index      # Index of bolt with maximum force
result.bolt_forces         # List of BoltForce objects (one per bolt)
result.method              # "elastic" or "icr"
```

**Notes:**
- Stress properties return 0.0 if bolt diameter is not set in BoltParameters
- Stresses are calculated from forces and bolt cross-sectional area
- Max/min properties use `.max` and `.min` as aliases for compatibility

**ICR-Specific Attributes:**

```python
result.icr_point           # (y, z) location of instantaneous center of rotation
result.icr_iteration_count # Number of iterations to converge
```

**Methods:**

#### `check_aisc(design, connection_type="bearing")`
Perform AISC 360-22 design check on analysis result.

```python
check = result.check_aisc(design, connection_type="bearing")
```

- `design` (`BoltDesignParams`): Design parameters
- `connection_type` (str): `"bearing"` or `"slip-critical"`
- **Returns:** `BoltCheckResult`

#### `plot(**kwargs)`
Visualize bolt group and force distribution.

```python
result.plot(
    mode="shear",       # "shear" (default) or "axial"
    force=True,
    bolt_forces=True,
    colorbar=True,
    cmap="coolwarm",
    show=True,
    save_path="bolts.svg"
)
```

- `mode` (str): Bolt plotting mode — `"shear"` colors by in-plane shear magnitude and shows arrows; `"axial"` colors by signed axial force (+ tension, − compression) and hides arrows. `"axial"` mode is only available for the elastic method.
- `force` (bool): Show applied load location
- `bolt_forces` (bool): Show reaction force vectors (arrows shown in `"shear"` mode only)
- `colorbar` (bool): Show force magnitude colorbar
- `cmap` (str): Matplotlib colormap (e.g., use `"RdBu_r"` for axial to show tension/compression)
- `show` (bool): Display plot immediately
- `save_path` (str): Path to save .svg file

---

### `BoltForce`

Force and stress at a single bolt location.

**Attributes:**

```python
bf.y                       # y-coordinate of bolt
bf.z                       # z-coordinate of bolt
bf.Fy                      # Force component in y-direction [kN, kip, etc.]
bf.Fz                      # Force component in z-direction
bf.diameter                # Bolt diameter [mm, in]
bf.resultant               # Resultant force magnitude (√(Fy² + Fz²))
bf.angle                   # Force direction in degrees (atan2(Fz, Fy))
bf.area                    # Cross-sectional area of bolt [mm², in²]
bf.shear_stress            # Shear stress through bolt (MPa, ksi) - τ = V/A
bf.shear_stress_y          # Shear stress from y-component only (MPa, ksi)
bf.shear_stress_z          # Shear stress from z-component only (MPa, ksi)
```

**Notes:**
- Stress properties return 0.0 if diameter is not set
- Shear stress is calculated as: τ = Force / Area
- For kN and mm units: stress is in MPa (N/mm²)
- For kip and inch units: stress is in ksi
- **Shear stress is the same for both bearing-type and slip-critical connections**
  - Bearing-type: Shear stress is the primary resistance mechanism (AISC J3.6)
  - Slip-critical: Shear stress represents post-slip capacity; primary resistance is friction (AISC J3.8-J3.9)

---

## Bolt Design Checks

### `BoltDesignParams`

Design-only inputs for AISC 360-22 bolt checks. Captures material properties and geometry not needed for analysis.

```python
design = BoltDesignParams(
    grade="A325",
    hole_type="standard",
    slot_orientation="perpendicular",
    threads_in_shear_plane=True,
    slip_class="A",
    n_s=1,
    fillers=0,
    plate_fu=450.0,
    plate_thickness=12.0,
    edge_distance_y=50.0,
    edge_distance_z=50.0,
    tension_per_bolt=None,
    n_b_tension=None,
    pretension_override=None
)
```

**Attributes:**

```python
# Grade and hole type
grade: str                      # "A325" or "A490"
hole_type: str                  # "standard", "oversize", "short_slotted", "long_slotted"
slot_orientation: str           # "perpendicular" or "parallel" (for slots)
threads_in_shear_plane: bool    # True if threads are in shear plane

# Slip-critical parameters
slip_class: str                 # "A" (μ=0.30) or "B" (μ=0.50)
n_s: int                        # Number of slip planes (1 or 2 typical)
fillers: int                    # Number of fillers (0, 1, or ≥2)

# Connected material properties
plate_fu: float                 # Ultimate tensile stress [MPa, ksi]
plate_thickness: float          # Plate thickness [mm, in]
edge_distance_y: float          # Edge distance in y-direction [mm, in]
edge_distance_z: float          # Edge distance in z-direction [mm, in]

# Optional overrides
tension_per_bolt: float | None  # Tension per bolt [kN, kip] (if None, derives from Fx/n)
n_b_tension: int | None         # Bolts carrying applied tension (for k_sc reduction)
pretension_override: float | None  # Bolt pretension [kN, kip] (if None, uses Table J3.1)
```

**Valid Parameter Combinations:**

- **Bearing-type**: Provide `plate_fu`, `plate_thickness`, at least one edge distance
- **Slip-critical**: Provide `slip_class`, `n_s`, all bearing parameters

---

### `BoltCheckResult`

Result of AISC 360-22 bolt group design check.

**Attributes:**

```python
check.governing_utilization     # Maximum utilization across all bolts/limit states
check.governing_bolt_index      # Index of critical bolt (0-indexed)
check.governing_limit_state     # "shear", "tension", "bearing", or "slip"
check.connection_type           # "bearing" or "slip-critical"
check.method                    # "elastic" or "icr"
check.details                   # List of BoltCheckDetail (one per bolt)
```

**Methods:**

#### `info` (property)
Return results as a nested dictionary for serialization.

```python
info_dict = check.info
# Structure:
# {
#     "governing_utilization": 0.68,
#     "governing_bolt_index": 2,
#     "governing_limit_state": "bearing",
#     "connection_type": "bearing",
#     "method": "elastic",
#     "bolts": [
#         {
#             "index": 0,
#             "position": {"y": 0, "z": 0},
#             "forces": {"Fy": ..., "Fz": ..., "resultant": ...},
#             "utilization": {
#                 "shear": 0.45,
#                 "tension": 0.30,
#                 "bearing": 0.68,
#                 "slip": None
#             },
#             "governing_limit_state": "bearing",
#             "governing_utilization": 0.68
#         },
#         ...
#     ]
# }
```

---

### `BoltCheckDetail`

Check results for a single bolt.

**Attributes:**

```python
detail.bolt_index                   # Bolt index (0-indexed)
detail.y                            # Bolt y-coordinate
detail.z                            # Bolt z-coordinate
detail.shear_demand                 # Shear force demand [kN, kip]
detail.tension_demand               # Tension force demand [kN, kip]
detail.shear_capacity               # Shear capacity [kN, kip]
detail.tension_capacity             # Tension capacity (with J3.7 interaction) [kN, kip]
detail.bearing_capacity             # Bearing/tear-out capacity [kN, kip]
detail.slip_capacity                # Slip resistance capacity [kN, kip] (slip-critical only)

# Utilizations (fraction of capacity)
detail.shear_util                   # Shear utilization
detail.tension_util                 # Tension utilization
detail.bearing_util                 # Bearing utilization
detail.slip_util                    # Slip utilization (None for bearing-type)
detail.governing_util               # Maximum utilization (governing limit state)
detail.governing_limit_state        # Name of governing limit state
```

---

## Weld Analysis

### `WeldParams`

Weld geometry parameters for analysis and visualization.

```python
params = WeldParams(
    type="fillet",
    leg=6.0,
    throat=None,
    area=None
)
```

**Attributes:**

```python
type: str          # "fillet", "pjp", "cjp", "plug", "slot"
leg: float         # Leg size (for fillet welds) [mm, in]
throat: float      # Throat dimension (if None, calculated from type/leg)
area: float        # Throat area (if None, calculated automatically)
```

---

### `Weld`

Weld geometry and parameters.

**Constructors:**

```python
# Option A: From a section
from sectiony.library import rhs
section = rhs(b=100, h=200, t=10, r=15)
weld = Weld.from_section(section, WeldParams(type="fillet", leg=6.0))

# Option B: Custom geometry
from sectiony import Geometry, Contour, Line
path = Contour(segments=[Line(start=(0, -50), end=(0, 50))])
weld = Weld(
    geometry=Geometry(contours=[path]),
    parameters=WeldParams(type="fillet", leg=6.0)
)
```

**Class Methods:**

#### `from_section(section, parameters)`
Create weld from a structural section (steel shape).

- `section`: sectiony Geometry object (e.g., from `sectiony.library`)
- `parameters` (`WeldParams`): Weld geometry
- **Returns:** `Weld`

**Properties:**

```python
weld.total_length              # Total weld length [mm, in]
weld.throat_area               # Effective throat area [mm², in²]
weld.centroid                  # (y, z) centroid of weld
weld.polar_moment              # Polar moment of inertia about centroid
```

**Methods:**

#### `analyze(load, method="elastic")`
Calculate stress distribution along weld.

```python
loaded = weld.analyze(load, method="elastic")
# or
loaded = weld.analyze(load, method="icr")
```

- `load` (`Force` or `Load`): Applied force and location
- `method` (str): `"elastic"` or `"icr"`
- **Returns:** `LoadedWeld`

---

### `LoadedWeld`

Stress results for a weld under load. Same as `analyze()` return value.

**Attributes:**

```python
loaded.max                     # Maximum stress at any point on weld
loaded.min                     # Minimum stress at any point on weld
loaded.mean                    # Average stress along weld
loaded.method                  # "elastic" or "icr"
loaded.weld                    # Weld object
loaded.load                    # Load object
loaded.stresses                # List of WeldStress objects (one per discretized point)
loaded.critical_stress         # WeldStress object at maximum location
loaded.critical_index          # Index of maximum stress point
```

**ICR-Specific Attributes:**

```python
loaded.icr_point               # (y, z) location of instantaneous center of rotation
```

**Methods:**

#### `plot(**kwargs)`
Visualize weld and stress distribution.

```python
loaded.plot(
    force=True,
    colorbar=True,
    cmap="RdYlGn_r",
    show=True,
    save_path="weld.svg"
)
```

- `force` (bool): Show applied load location
- `colorbar` (bool): Show stress magnitude colorbar
- `cmap` (str): Matplotlib colormap
- `show` (bool): Display plot immediately
- `save_path` (str): Path to save .svg file

---

### `WeldStress`

Stress at a single point on the weld.

**Attributes:**

```python
stress.s                       # Position along weld [0 to total_length]
stress.y                       # y-coordinate on weld
stress.z                       # z-coordinate on weld
stress.value                   # Stress magnitude [MPa, ksi]
stress.angle                   # Stress direction
```

---

## Weld Parameters

### `WeldParams` Details

**Supported Weld Types:**

| Type | Description |
|------|-------------|
| `"fillet"` | Fillet weld; `leg` is the fillet leg size |
| `"pjp"` | Partial Joint Penetration; `throat` or `leg` required |
| `"cjp"` | Complete Joint Penetration; typically `throat` = thickness |
| `"plug"` | Plug weld; `area` defines effective area |
| `"slot"` | Slot weld; `area` defines effective area |

**Throat Area Calculation:**

For fillet welds, throat area is:
$$A_{throat} = 0.707 \times \text{leg} \times \text{length}$$

For PJP/CJP, throat area is:
$$A_{throat} = \text{throat} \times \text{length}$$

For plug/slot, you provide `area` directly.

---

## Visualization

### Plotting Methods

Both `BoltResult` and `LoadedWeld` have `.plot()` methods.

**Common Parameters:**

```python
result.plot(
    force=True,              # Show applied load
    colorbar=True,           # Show magnitude colorbar
    cmap="coolwarm",         # Matplotlib colormap
    title=None,              # Custom title
    show=True,               # Display immediately
    save_path="output.svg"   # Save to file
)
```

**Available Colormaps:**

- `"coolwarm"` — Blue (low) to red (high)
- `"viridis"` — Purple to yellow (perceptually uniform)
- `"RdYlGn_r"` — Red (high) to green (low)
- `"plasma"` — Purple to yellow
- See [matplotlib colormaps](https://matplotlib.org/stable/tutorials/colors/colormaps.html) for more

### Bolt Plot Parameters

Additional parameters and behavior specific to `BoltResult.plot`:

- `mode` — `"shear"` (default) colors by in-plane shear magnitude and shows arrows; `"axial"` colors by signed axial force (+ tension, − compression) and hides arrows. `"axial"` mode is only available for elastic results (not ICR).
- Colormap tip — For `mode="axial"`, a diverging colormap like `"RdBu_r"` is recommended (red=tension, blue=compression).
- Normalization — Colors scale to the actual data range (min→max); the colormap is not forcibly centered at zero.

**Bolt Plot Features:**

- Bolts drawn as circles, colored by force magnitude
- Applied load location marked with red ×
- Force vectors shown as arrows at each bolt (shear mode only)
- ICR point shown (for ICR results; axial mode is not available)
- Title shows bolt count, size, max force

**Weld Plot Features:**

- Weld path drawn as line
- Stress distribution shown as color gradient along weld
- Applied load location marked
- Critical stress point highlighted
- ICR point shown (if ICR method used)

---

## Constants & Tables

### AISC 360-22 Data (Built-In)

**Table J3.1: Minimum Pretension (kN)**

| Bolt Size | A325 | A490 |
|-----------|------|------|
| M20       | 142  | 179  |
| M22       | 176  | 221  |
| M24       | 205  | 257  |

**Table J3.2: Nominal Stresses (MPa)**

| Grade | $F_{nt}$ | $F_{nv}$ (N) | $F_{nv}$ (X) |
|-------|----------|--------------|-------------|
| A325  | 620      | 370          | 470         |
| A490  | 780      | 470          | 580         |

Note: (N) = threads not in shear plane, (X) = threads in shear plane

### Slip-Critical Friction Coefficients

| Class | $\mu$ |
|-------|-------|
| A     | 0.30  |
| B     | 0.50  |

### Slip-Critical Phi Factors ($\phi_{slip}$)

| Hole Type | Orientation | $\phi$ |
|-----------|-------------|--------|
| Standard  | —           | 1.00   |
| Oversize  | —           | 0.85   |
| Short-slotted | ⊥ load | 1.00   |
| Short-slotted | ∥ load  | 0.85   |
| Long-slotted | Any     | 0.70   |

---

## Example Workflows

### Complete Bolt Analysis + Check

```python
from connecty import BoltGroup, BoltDesignParams, Load

# Define bolt group
bolts = BoltGroup.from_pattern(rows=3, cols=2, spacing_y=75, spacing_z=60, diameter=20)

# Define load
load = Load(Fy=-100000, Fz=30000, location=(75, 150))

# Define design parameters
design = BoltDesignParams(
    grade="A325",
    hole_type="standard",
    threads_in_shear_plane=True,
    plate_fu=450.0,
    plate_thickness=12.0,
    edge_distance_y=50.0,
    edge_distance_z=50.0
)

# Analyze (elastic method)
analysis = bolts.analyze(load, method="elastic")
print(f"Max force: {analysis.max_force:.1f} kN")
print(f"Max shear stress: {analysis.max_stress:.1f} MPa")

# Access per-bolt results
for bf in analysis.bolt_forces:
    print(f"Bolt at ({bf.y}, {bf.z}): Force={bf.resultant:.2f} kN, Stress={bf.shear_stress:.1f} MPa")

# Check adequacy
check = analysis.check_aisc(design, connection_type="bearing")
print(f"Utilization: {check.governing_utilization:.1%}")
print(f"Limit state: {check.governing_limit_state}")

# Visualize
analysis.plot(save_path="bolt_analysis.svg")

# Export results
results_dict = check.info
```

### Complete Weld Analysis

```python
from connecty import Weld, WeldParams, Load
from sectiony.library import rhs

# Define weld
section = rhs(b=100, h=200, t=10, r=15)
weld = Weld.from_section(section, WeldParams(type="fillet", leg=6.0))

# Define load
load = Load(Fy=-100e3, location=(50, 0))

# Analyze
loaded = weld.analyze(load, method="elastic")
print(f"Max stress: {loaded.max:.1f} MPa")

# Define allowable (example: E70 fillet weld)
F_EXX = 483.0  # MPa
phi = 0.75
allowable = phi * 0.60 * F_EXX  # ~218 MPa

# Check
utilization = loaded.max / allowable
print(f"Utilization: {utilization:.1%}")

# Visualize
loaded.plot(save_path="weld_analysis.svg")
```

---

## Unit Systems

Connecty is **unit-agnostic**. Choose any consistent system:

**Metric (SI):**
```python
# All mm, N, MPa, N·mm
bolts = BoltGroup.from_pattern(rows=3, cols=2, spacing_y=75, spacing_z=60, diameter=20)
force = Force(Fy=-100000, Fz=30000, location=(75, 150))
# Results in kN, stresses in MPa
```

**US Customary:**
```python
# All inches, kip, ksi, kip·in
bolts = BoltGroup.from_pattern(rows=3, cols=2, spacing_y=3, spacing_z=2.4, diameter=0.75)
force = Force(Fy=-100, Fz=30, location=(3, 6))
# Results in kip, stresses in ksi
```

**Key Rule:** Maintain dimensional consistency throughout. Length units, force units, and stress units must be compatible (stress = force / area).

---

## Error Handling

Common exceptions and causes:

| Exception | Cause | Solution |
|-----------|-------|----------|
| `ValueError` | Invalid bolt grade, hole type, or connection type | Check parameter values match allowed options |
| `ValueError` | Missing required design parameters | Provide `plate_fu`, `plate_thickness`, edge distances for bearing checks |
| `ValueError` | Invalid method name | Use `"elastic"` or `"icr"` only |
| `RuntimeError` | ICR solver did not converge | Check load location is reasonable; try elastic method |

---

## Performance Notes

**ICR Method:**
- Requires iterative solver (typically 5–15 iterations)
- Slower than elastic method but more accurate for eccentric loads
- Use for final design; elastic for quick checks

**Large Bolt Groups:**
- Performance is O(n) for n bolts
- Groups with >100 bolts should still be fast (<1 second)

**Visualization:**
- Save to `.svg` for scalable vector graphics
- Use `.show=False` for headless environments

---

## Version & Compatibility

- **Python:** 3.8+
- **Dependencies:** sectiony, matplotlib, numpy, dataclasses

---

## See Also

- [User Guide](general/user%20guide.md) — Workflow examples
- [Bolt Analysis & Checks](bolt/bolt.md) — Detailed bolt documentation
- [Weld Analysis](weld/weld.md) — Detailed weld documentation
- [AISC 360-22](general/standards/AISC%20360-22.md) — Standards reference
