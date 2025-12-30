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
7. [Weld Design Checks](#weld-design-checks)
8. [Visualization](#visualization)

---

## Imports

```python
from connecty import (
    # Bolt analysis
    BoltGroup,
    Plate,
    BoltConnection,
    Load,
    LoadedBoltConnection,
    BoltResult,
    
    # Bolt design checks
    BoltCheckResult,
    BoltCheckDetail,
    
    # Weld analysis
    Weld,
    WeldParams,
    WeldBaseMetal,
    WeldConnection,
    LoadedWeld,
    LoadedWeldConnection,
    PointStress,
    StressComponents,
    WeldCheckResult,
    WeldCheckDetail,
)
```

---

## Shared Classes

### `Load`

Represents a force vector and moment vector applied at a point.

```python
class Load:
    Fx: float          # Axial force (out-of-plane, tension positive) [N]
    Fy: float          # Shear force in y-direction (vertical) [N]
    Fz: float          # Shear force in z-direction (horizontal) [N]
    Mx: float          # Torsional moment about x-axis [N·mm]
    My: float          # Bending moment about y-axis [N·mm]
    Mz: float          # Bending moment about z-axis [N·mm]
    location: tuple    # (x, y, z) application point
```

**Constructor:**
```python
# With forces only (moments calculated from eccentricity)
load = Load(Fy=-100000.0, Fz=50000.0, location=(0, 100, 150))

# With forces and moments
load = Load(
    Fx=0.0,
    Fy=-100000.0,
    Fz=50000.0,
    Mx=5000000.0,    # Applied torsion
    My=0.0,
    Mz=0.0,
    location=(0, 100, 150)
)
```

**Method:**
```python
eq_load = load.equivalent_at(location=(50, 100, 0))  # Transfer load to a new position
```

The `equivalent_at()` method transfers moments to a different position using: M_new = M_old + r × F

---

## Bolt Analysis

### `Plate`

Defines plate geometry for tension and bearing calculations.

```python
class Plate:
    corner_a: tuple[float, float]   # (y, z)
    corner_b: tuple[float, float]   # (y, z) opposite corner
    thickness: float                # Plate thickness [mm]
    fu: float = 450.0               # Ultimate tensile stress [MPa]
    fy: float = 350.0               # Yield stress [MPa]
```

**Constructor:**
```python
# Explicit corners (y, z)
plate = Plate(corner_a=(-125.0, -80.0), corner_b=(125.0, 80.0), thickness=12.0)
```

---

### `BoltGroup`

A collection of bolts defining the pattern and bolt properties.

**Constructors:**

```python
# Option A: Explicit coordinates
bolts = BoltGroup(
    positions=[(0, 0), (0, 75), (0, 150)],
    diameter=20,
    grade="A325"
)

# Option B: Rectangular pattern
bolts = BoltGroup.from_pattern(
    rows=3,
    cols=2,
    spacing_y=75,
    spacing_z=60,
    diameter=20,
    grade="A325",
    origin=(0, 0)
)
```

**Properties:**

```python
bolts.n                    # Total number of bolts
bolts.positions            # List of (y, z) coordinates
bolts.Cy, bolts.Cz         # Centroid coordinates
bolts.Ip                   # Polar moment of inertia (Σr²)
```

---

### `BoltConnection`

Combines a `BoltGroup` and `Plate` to define connection geometry.

```python
class BoltConnection:
    bolt_group: BoltGroup
    plate: Plate
    n_shear_planes: int = 1
```

**Constructor:**
```python
connection = BoltConnection(bolt_group=bolts, plate=plate, n_shear_planes=1)
```

**Method:**
```python
# Main analysis entry point
result = connection.analyze(load, shear_method="elastic", tension_method="conservative")
```

---

### `LoadedBoltConnection`

Complete analysis result for a bolt connection.

**Attributes:**

```python
result.max_shear_force     # Max in-plane shear force on any bolt
result.max_axial_force     # Max out-of-plane axial force (tension)
result.max_combined_stress  # Max combined stress sqrt(tau^2 + sigma^2)
result.icr_point           # ICR center (for icr method)
result.shear_method        # "elastic" or "icr"
```

**Methods:**

#### `check(**kwargs)`
Perform AISC 360-22 or AS 4100 design checks.

```python
check = result.check(
    standard="aisc",
    connection_type="bearing",
    hole_type="standard",
    threads_in_shear_plane=True
)
```

---

#### `to_bolt_results()`
Returns a list of `BoltResult` objects for each bolt.

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

### `BoltResult`

Force and stress at a single bolt location.

**Attributes:**

```python
# Bolt position
bf.y                       # y-coordinate of bolt
bf.z                       # z-coordinate of bolt

# Forces (3D)
bf.Fx                      # Axial force component (out-of-plane) [kN, kip, etc.]
bf.Fy                      # Shear force component in y-direction (in-plane) [kN, kip, etc.]
bf.Fz                      # Shear force component in z-direction (in-plane) [kN, kip, etc.]

# Force magnitudes
bf.shear                   # In-plane shear magnitude sqrt(Fy^2 + Fz^2) [kN, kip, etc.]
bf.axial                   # Out-of-plane axial force (signed: + = tension) [kN, kip, etc.]
bf.resultant               # Total resultant force magnitude sqrt(Fx^2 + Fy^2 + Fz^2)

# Bolt properties
bf.diameter                # Bolt diameter [mm, in]
bf.area                    # Cross-sectional area of bolt [mm^2, in^2]
bf.angle                   # In-plane force direction in degrees (atan2(Fz, Fy))

# Stresses (calculated from forces if diameter is set)
bf.shear_stress            # In-plane shear stress tau = V / (A * planes)
bf.axial_stress            # Out-of-plane axial stress sigma = Fx / A (positive = tension)
bf.combined_stress         # Combined stress sqrt(tau^2 + sigma^2)
```

**Notes:**
- Stress properties return 0.0 if diameter is not set in BoltParameters
- Shear stress calculation (in-plane): tau = sqrt(Fy^2 + Fz^2) / A
- Axial stress calculation (out-of-plane, signed): sigma = Fx / A (positive = tension, negative = compression)
- Combined stress: sqrt(tau^2 + |sigma|^2)
- For kN and mm units: stress is in MPa (N/mm^2)
- For kip and inch units: stress is in ksi
- Axial stress and combined stress properties are only available for elastic method results (ICR returns 0 for Fx)
- **Shear stress is the same for both bearing-type and slip-critical connections**
  - Bearing-type: Shear stress is the primary resistance mechanism (AISC J3.6)
  - Slip-critical: Shear stress represents post-slip capacity; primary resistance is friction (AISC J3.8-J3.9)

---

## Bolt Design Checks

### `BoltCheckResult`

Result of AISC 360-22 or AS 4100 bolt group design check.

**Attributes:**

```python
check.governing_utilization     # Maximum utilization across all bolts/limit states
check.governing_bolt_index      # Index of critical bolt (0-indexed)
check.governing_limit_state     # "shear", "tension", "bearing", "slip", or "interaction"
check.connection_type           # "bearing", "slip-critical", or "friction"
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

**Properties (calculated automatically):**

```python
weld.A                         # Throat area (area = throat × length)
weld.L                         # Total weld length
weld.Cy, weld.Cz               # Centroid coordinates
weld.Iy, weld.Iz               # Second moments of area about centroid
weld.Ip                        # Polar moment (Iy + Iz)
```

---

### Analyzing a weld

Use `LoadedWeld` to perform analysis (instantiation runs the calculation):

```python
from connecty import LoadedWeld

loaded = LoadedWeld(
    weld,
    load,
    method="elastic",
    discretization=200,
    F_EXX=483.0,        # optional: stored for utilisation plots/checks
    include_kds=True    # apply AISC directional strength factor
)
```

**Method options by weld type:**

| Weld Type | `method` | Notes |
|-----------|----------|-------|
| Fillet    | `"elastic"` | 3D vector method (Fx, Fy, Fz, Mx, My, Mz) |
| Fillet    | `"icr"` | 2D ICR (Fy, Fz, Mx only) with k_ds benefit |
| Fillet    | `"both"` | Runs elastic + icr; enables comparison plot |
| PJP / CJP / Plug / Slot | `"elastic"` | Only option |

---

### `LoadedWeld`

Pointwise stress results for a weld under load.

**Attributes:**

```python
loaded.max                     # Maximum resultant stress
loaded.max_stress              # Alias for max
loaded.min                     # Minimum resultant stress
loaded.min_stress              # Alias for min
loaded.mean                    # Average resultant stress
loaded.range                   # Stress range (max - min)
loaded.method                  # "elastic", "icr", or "both" (fillet only)
loaded.weld                    # Weld object
loaded.load                    # Load object
loaded.point_stresses          # List[PointStress] (aligned to discretization)
loaded.max_point               # PointStress at maximum stress

# ICR-only
loaded.icr_point               # (y, z) instantaneous center of rotation
loaded.rotation                # Rotation about ICR (radians)
```

**Methods:**

#### `at(y, z)`
Return `StressComponents` at the nearest discretized point.

#### `weld_metal_utilizations(F_EXX=None, phi_w=0.75, conservative_k_ds=False)`
Pointwise weld-metal utilisation per AISC fillet basis (aligned to `point_stresses`). If `F_EXX` is not passed, uses `LoadedWeld.F_EXX`; raises if neither is set.

#### `directional_factors(conservative_k_ds=False)`
Return pointwise `k_ds` values (AISC directional strength factor). If `include_kds` was False at analysis or `conservative_k_ds` is True, returns 1.0 everywhere.

#### `plot(**kwargs)`
Visualize weld and stress distribution.

```python
loaded.plot(
    section=True,          # show section outline if available
    info=True,             # show max/util info in title
    cmap="coolwarm",
    weld_linewidth=5.0,
    show=True,
    save_path="weld.svg",  # ".svg" appended if missing
    legend=False
)
```

- If `method="both"` on construction, plots elastic vs ICR side-by-side (fillet only).

#### `plot_utilization(**kwargs)`
Plot weld-metal utilisation along the weld path.

```python
loaded.plot_utilization(
    section=True,
    info=True,
    cmap="viridis",
    weld_linewidth=5.0,
    show=True,
    save_path=None,        # optional .svg
    legend=False,
    F_EXX=None,            # override electrode strength
    conservative_k_ds=False
)
```

#### `plot_directional_factor(**kwargs)`
Plot `k_ds` along the weld path (fillet only).

---

### `PointStress`

Stress at a single point on the weld.

**Attributes:**

```python
ps.point                     # (y, z) coordinates
ps.y, ps.z                   # Convenience accessors
ps.components                # StressComponents object
ps.stress                    # Resultant stress magnitude
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

## Weld Design Checks

### `WeldBaseMetal`

Base metal properties for the weaker/thinner part of the connection:

```python
WeldBaseMetal(t=10.0, fy=350.0, fu=450.0)
# t (thickness), fy (yield), fu (ultimate)
```

### `WeldConnection`

Wraps a `Weld` with base metal data and connection flags.

```python
from connecty import WeldConnection, WeldBaseMetal

connection = WeldConnection.from_geometry(
    geometry=weld.geometry,
    parameters=weld.parameters,
    base_metal=WeldBaseMetal(t=10.0, fy=350.0, fu=450.0),
    is_double_fillet=False,
    is_rect_hss_end_connection=False,
)
result = connection.analyze(load, method="icr", discretization=200)
```

- `from_geometry(...)` / `from_dxf(...)` helpers build the `Weld` for you.
- `analyze(...)` returns a `LoadedWeldConnection`.

### `LoadedWeldConnection`

Convenience wrapper over `LoadedWeld` with bolt-style API.

```python
result.max_stress          # == result.analysis.max
result.min_stress
result.mean_stress
result.max_point

result.plot(...)           # delegates to LoadedWeld.plot
result.plot_utilization(...)  # util plot
result.plot_directional_factor(...)  # k_ds plot
```

#### `check(**kwargs)`
Perform AISC 360-22 fillet weld check (LRFD):

```python
check = result.check(
    standard="aisc",
    F_EXX=None,               # default: matching electrode = base metal Fu
    enforce_max_fillet_size=True,
    conservative_k_ds=False,  # set True to force k_ds=1.0
)
```

### `WeldCheckResult` and `WeldCheckDetail`

```python
check.governing_utilization    # Governing utilisation across weld groups
check.governing_limit_state    # "weld_metal", "base_metal", or "detailing"
check.details                  # List[WeldCheckDetail]

detail.leg                     # Fillet leg (w)
detail.throat                  # Effective throat (t_e)
detail.theta_deg               # Governing theta used for k_ds (None if k_ds=1.0)
detail.k_ds                    # Directional factor used
detail.weld_util               # Weld-metal utilisation
detail.base_util               # Base-metal utilisation (if applicable)
detail.detailing_max_util      # Utilisation vs max fillet size limit (if checked)
detail.governing_util          # Governing utilisation for this weld
detail.governing_limit_state   # Governing limit state string
```

Notes:
- Fillet welds are auto-checked; other types require advanced inputs and are not auto-checked here.
- `k_ds` is automatically computed at the governing point unless disabled or HSS end-connection restriction applies.
- Electrode defaults to matching the weaker base metal (`F_EXX = fu`).

---

## Visualization

### Plotting Methods

Both bolt and weld results expose `.plot()` helpers. When `save_path` is provided, `.svg` is appended automatically; set `show=False` for headless environments.

```python
result.plot(save_path="output.svg", show=True)
```

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

### Weld Plot Parameters

`LoadedWeld.plot` (stress), `plot_utilization`, and `plot_directional_factor` accept:

- `section` — Show section outline when available
- `info` — Include summary text (max stress / utilisation / k_ds)
- `cmap` — Matplotlib colormap (`"coolwarm"`, `"viridis"`, `"plasma"`, etc.)
- `weld_linewidth` — Line weight for weld path
- `legend` — Show load legend
- `show` — Display immediately (set False for automation)
- `save_path` — Optional file path; `.svg` appended if missing
- `F_EXX` (utilisation plot) — Override electrode strength; otherwise uses `LoadedWeld.F_EXX`
- `conservative_k_ds` (utilisation/k_ds plots) — Force `k_ds = 1.0`

`LoadedWeld.plot` automatically shows the applied load; for `method="both"` it renders an elastic vs ICR comparison when applicable.

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
from connecty import BoltGroup, Plate, BoltConnection, Load

# 1. Define bolt group
bolts = BoltGroup.from_pattern(rows=3, cols=2, spacing_y=75, spacing_z=60, diameter=20)

# 2. Define plate
plate = Plate(corner_a=(-120.0, -100.0), corner_b=(120.0, 100.0), thickness=12.0, fu=450.0, fy=350.0)

# 3. Create connection
connection = BoltConnection(bolt_group=bolts, plate=plate)

# 4. Define load
load = Load(Fy=-100000, Fz=30000, location=(75, 150, 100))

# 5. Analyze (elastic method)
result = connection.analyze(load, shear_method="elastic", tension_method="conservative")
print(f"Max shear: {result.max_shear_force:.1f} N")
print(f"Max combined stress: {result.max_combined_stress:.1f} MPa")

# 6. Check adequacy
check = result.check(
    standard="aisc",
    connection_type="bearing",
    hole_type="standard",
    threads_in_shear_plane=True
)
print(f"Utilization: {check.governing_utilization:.1%}")
print(f"Limit state: {check.governing_limit_state}")

# 7. Visualize
result.plot(save_path="bolt_analysis.svg")

# 8. Export results
results_dict = check.info
```

### Complete Weld Analysis

```python
from connecty import Weld, WeldParams, Load, LoadedWeld
from sectiony.library import rhs

# Define weld
section = rhs(b=100, h=200, t=10, r=15)
weld = Weld.from_section(section, WeldParams(type="fillet", leg=6.0))

# Define load
load = Load(Fy=-100e3, location=(50, 0))

# Analyze
loaded = LoadedWeld(
    weld,
    load,
    method="elastic",
    discretization=200,
    F_EXX=483.0,          # optional storage for utilisation plots/checks
    include_kds=True,
)
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
loaded.plot_utilization(save_path="weld_util.svg", F_EXX=F_EXX)
```

### Weld Analysis + AISC Check (Fillet)

```python
from connecty import (
    Weld,
    WeldParams,
    WeldConnection,
    WeldBaseMetal,
    Load,
)
from sectiony.library import rhs

section = rhs(b=100, h=200, t=10, r=15)
weld = Weld.from_section(section, WeldParams(type="fillet", leg=6.0))
base_metal = WeldBaseMetal(t=10.0, fy=350.0, fu=450.0)

# Build connection with base metal data
connection = WeldConnection(
    weld=weld,
    base_metal=base_metal,
    is_double_fillet=False,
    is_rect_hss_end_connection=False,
)

load = Load(Fy=-120000, Fz=45000, location=(0, 0))
result = connection.analyze(load, method="icr")

check = result.check(standard="aisc")
print(f"Governing util: {check.governing_utilization:.2f}")
print(f"Limit state: {check.governing_limit_state}")
```

---

## Unit Systems

Connecty is **unit-agnostic**. Choose any consistent system:

**Metric (SI):**
```python
# All mm, N, MPa, N·mm
bolts = BoltGroup.from_pattern(rows=3, cols=2, spacing_y=75, spacing_z=60, diameter=20)
load = Load(Fy=-100000, Fz=30000, location=(75, 150))
# Results in kN, stresses in MPa
```

**US Customary:**
```python
# All inches, kip, ksi, kip·in
bolts = BoltGroup.from_pattern(rows=3, cols=2, spacing_y=3, spacing_z=2.4, diameter=0.75)
load = Load(Fy=-100, Fz=30, location=(3, 6))
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
| `ValueError` | Invalid method name | Use `"elastic"`, `"icr"`, or `"both"` (fillet only) |
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
