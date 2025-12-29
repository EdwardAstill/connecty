# Connecty User Guide

Welcome to the **Connecty** user guide. This package calculates force/stress distribution in welded and bolted connections per AISC 360. It focuses on **geometry-based analysis**—you provide geometry and loads; the tool outputs forces and stresses. Design checks (capacity, utilization) are your responsibility.

## Table of Contents

1. [Installation](#1-installation)
2. [Core Concepts](#2-core-concepts)
   - [Coordinate System](#coordinate-system)
   - [Units](#units)
   - [Philosophy: Geometry First](#geometry-first)
3. [Weld Analysis](#3-weld-analysis)
   - [Quick Start](#weld-quick-start)
   - [Creating Welds](#creating-welds)
   - [Stress Results](#stress-results)
4. [Bolt Analysis](#4-bolt-analysis)
   - [Quick Start](#bolt-quick-start)
   - [Creating Bolt Groups](#creating-bolt-groups)
   - [Force Results](#force-results)
5. [Design Checks](#5-design-checks)
6. [Examples](#6-examples)
7. [API Reference Summary](#7-api-reference-summary)
8. [References & Standards](#8-references--standards)

---

## 1. Installation

```bash
uv add connecty
# or
pip install connecty
```

It relies on **sectiony** for geometry and **matplotlib** for visualization.

---

## 2. Core Concepts

### Coordinate System

Connecty uses a consistent 2D coordinate system:

- **y-axis**: Vertical (positive up)
- **z-axis**: Horizontal (positive right)
- **x-axis**: Out of page (for torsional moments)

The cross-section of the connection lies in the **y-z plane**.

### Units

Connecty is **unit-agnostic**: you choose your unit system and maintain consistency throughout.

**Recommended Unit Systems:**

**Metric (SI):**
- Length: mm
- Force: N  
- Stress: MPa (N/mm²)
- Moment: N·mm

**US Customary:**
- Length: inches
- Force: kip
- Stress: ksi
- Moment: kip·in

**Consistency Rules:**
1. All lengths use the same unit
2. All forces use the same unit
3. All moments are force × length (consistent)
4. Stress = Force / Area (dimensionally consistent)

**Example: US Customary Units**

```python
from connecty import BoltConnection, BoltGroup, Load, Plate

bolts = BoltGroup(positions=[(0, 0), (0, 3)], diameter=0.75)
plate = Plate(corner_a=(-5.0, -5.0), corner_b=(5.0, 5.0), thickness=0.5, fu=65.0, fy=50.0)
connection = BoltConnection(bolt_group=bolts, plate=plate)

load = Load(Fy=-100.0, location=(4.0, 0.0, 0.0))  # 100 kip at 4"
result = connection.analyze(load, shear_method="elastic", tension_method="conservative")
```

### Geometry First

The philosophy: **Geometry defines the analysis**, not material properties.

- `BoltParameters` only needs diameter (for visualization and ICR force distribution shape)
- `WeldParams` only needs geometry (type, leg, throat, area)
- No electrode, grade, or capacity in the class definitions
- You provide allowable stresses/capacities separately for design checks

This separation of concerns gives you complete control over design decisions.

---

## 3. Weld Analysis

### Weld Quick Start

```python
from connecty import Weld, WeldParams, Load, LoadedWeld
from sectiony.library import rhs

# Create weld geometry from section
section = rhs(b=100, h=200, t=10, r=15)
params = WeldParams(type="fillet", leg=6.0)
weld = Weld.from_section(section, params)

# Apply load
load = Load(Fy=-100e3, location=(50, 0))

# Analyze (elastic method)
loaded = LoadedWeld(weld, load, method="elastic")

# Access results
print(f"Max stress: {loaded.max:.1f} MPa")
print(f"Mean stress: {loaded.mean:.1f} MPa")

# Visualize
loaded.plot(save_path="weld.svg")
```

### Creating Welds

**Option A: From a Section (Convenient)**

```python
from connecty import Weld, WeldParams
from sectiony.library import rhs

section = rhs(b=100, h=200, t=10, r=15)
params = WeldParams(type="fillet", leg=6.0)
weld = Weld.from_section(section, params)
```

**Option B: Custom Geometry**

```python
from connecty import Weld, WeldParams
from sectiony import Geometry, Contour, Line

# Define weld path (doesn't need to be closed)
path = Contour(segments=[
    Line(start=(0, -50), end=(0, 50))
])
weld = Weld(
    geometry=Geometry(contours=[path]),
    parameters=WeldParams(type="fillet", leg=6.0)
)
```

### WeldParams Details

```python
params = WeldParams(
    type="fillet",      # "fillet", "pjp", "cjp", "plug", "slot"
    leg=6.0,            # Fillet leg size (optional, auto-calculates throat)
    throat=None,        # Effective throat (optional)
    area=None           # Plug/slot area (optional)
)
```

For fillet welds, if you provide `leg`, `throat` is auto-calculated as $a = w \times 0.707$.

### Stress Calculation

```python
from connecty import LoadedWeld

# Elastic method (all weld types)
loaded = LoadedWeld(weld, load, method="elastic", discretization=200)

# ICR method (fillet welds only)
loaded = LoadedWeld(weld, load, method="icr", discretization=200)

# Access stress at any point
stress = loaded.at(y=50, z=25)
print(f"Components: {stress}")
print(f"Resultant: {stress.resultant:.1f} MPa")
```

### Stress Results

```python
# Properties
loaded.max              # Maximum resultant stress (MPa)
loaded.min              # Minimum resultant stress (MPa)
loaded.mean             # Average stress (MPa)
loaded.range            # max - min (MPa)
loaded.method           # "elastic" or "icr"

# Detailed access
for ps in loaded.point_stresses:
    print(f"At ({ps.y}, {ps.z}): {ps.stress:.1f} MPa")

# ICR-specific
if loaded.method == "icr":
    print(f"ICR center: {loaded.icr_point}")
    print(f"Rotation: {loaded.rotation} rad")
```

### Plotting

```python
loaded.plot(
    section=True,        # Show section geometry
    force=True,          # Show applied load
    colorbar=True,       # Show colorbar
    cmap="coolwarm",
    weld_linewidth=5,
    save_path="weld.svg"
)
```

---

## 4. Bolt Analysis

### Bolt Quick Start

```python
from connecty import BoltGroup, Plate, BoltConnection, Load

# 1. Create bolt pattern
bolts = BoltGroup.from_pattern(
    rows=3, cols=2, spacing_y=75, spacing_z=60, diameter=20
)

# 2. Define plate geometry (required for analysis)
plate = Plate(corner_a=(-100.0, -150.0), corner_b=(100.0, 150.0), thickness=12.0, fu=450.0, fy=350.0)

# 3. Create connection
connection = BoltConnection(bolt_group=bolts, plate=plate)

# 4. Apply load
load = Load(Fy=-100000, location=(75, 150, 100))

# 5. Analyze
result = connection.analyze(load, shear_method="elastic", tension_method="conservative")

# 6. Access results
print(f"Max shear force: {result.max_shear_force:.1f} N")
print(f"Max combined stress: {result.max_combined_stress:.1f} MPa")

# 7. Visualize (default: in-plane shear forces with arrows)
result.plot(save_path="bolts.svg")

# Visualize out-of-plane axial forces
# Use diverging colormap to show tension (red) vs compression (blue)
result.plot(mode="axial", cmap="RdBu_r", save_path="bolts_axial.svg")
```

### Creating Bolt Groups

**Option A: Explicit Coordinates**

```python
from connecty import BoltGroup

bolts = BoltGroup(
    positions=[(0, 0), (0, 75), (0, 150)],
    diameter=20,
    grade="A325"
)
```

**Option B: Rectangular Pattern**

```python
bolts = BoltGroup.from_pattern(
    rows=3, cols=2, spacing_y=75, spacing_z=60, diameter=20
)
```

**Option C: Circular Pattern**

```python
bolts = BoltGroup.from_circle(
    n=8, radius=100, diameter=20, center=(0, 0)
)
```

### Force Calculation

```python
# Elastic method
result = connection.analyze(load, shear_method="elastic", tension_method="conservative")

# ICR method (more accurate for eccentric loading)
result = connection.analyze(load, shear_method="icr", tension_method="conservative")
```

### Force Results

```python
# Properties
result.max_shear_force     # Maximum shear force on any bolt (N)
result.max_axial_force     # Maximum axial force on any bolt (N)
result.max_combined_stress  # Maximum combined stress (MPa)
result.icr_point           # ICR center (for icr method)
result.shear_method        # "elastic" or "icr"

# Detailed access
for bf in result.to_bolt_results():
    print(f"Bolt at ({bf.y}, {bf.z})")
    print(f"  Fy = {bf.Fy:.2f} N")
    print(f"  Fz = {bf.Fz:.2f} N")
    print(f"  Resultant = {bf.resultant:.2f} N")
```

### Plotting

```python
result.plot(
    force=True,          # Show applied load
    bolt_forces=True,    # Show reaction vectors
    colorbar=True,
    cmap="coolwarm",
    save_path="bolts.svg"
)
```

---

## 5. Design Checks

Connecty provides automatic design checks for **bolts** (AISC 360-22), and outputs-only for **welds** (you define allowable stress).

### Bolt Design Check (Automatic AISC 360-22)

Connecty automatically checks A325 and A490 bolts for bearing-type and slip-critical connections.

```python
from connecty import BoltGroup, Plate, BoltConnection, Load

# 1. Create connection
bolts = BoltGroup.from_pattern(rows=3, cols=2, spacing_y=75, spacing_z=60, diameter=20)
plate = Plate(corner_a=(-120.0, -100.0), corner_b=(120.0, 100.0), thickness=12.0, fu=450.0, fy=350.0)
connection = BoltConnection(bolt_group=bolts, plate=plate)

# 2. Define load
load = Load(Fy=-100000, Fz=30000, location=(75, 150, 100))

# 3. Analyze
result = connection.analyze(load, shear_method="elastic", tension_method="conservative")

# 4. Automatic check (bearing-type)
check = result.check(
    standard="aisc",
    connection_type="bearing",
    hole_type="standard",
    threads_in_shear_plane=True
)

# 5. Results
print(f"Utilization: {check.governing_utilization:.2f}")
print(f"Limit state: {check.governing_limit_state}")

if check.governing_utilization <= 1.0:
    print("PASS")
else:
    print("FAIL")
```

**Key Features:**
- Automatic per-bolt force distribution (elastic or ICR method)
- AISC J3.6/J3.7 (shear + tension with interaction)
- AISC J3.10 (bearing and tear-out)
- AISC J3.8–J3.9 (slip resistance for slip-critical connections)
- Per-bolt utilization for each limit state
- Identification of governing limit state and critical bolt

**Connection Types:**

```python
# Bearing-type (default)
check = result.check(connection_type="bearing")

# Slip-critical
check = result.check(connection_type="slip-critical", slip_class="A", n_s=1)
```

**Example: Slip-Critical (A325 Class B)**

```python
check = result.check(
    standard="aisc",
    connection_type="slip-critical",
    hole_type="short_slotted",
    slot_orientation="perpendicular",
    threads_in_shear_plane=False,
    slip_class="B",
    n_s=2
)
print(f"Slip-critical utilization: {check.governing_utilization:.1%}")
```

For detailed parameter documentation, see [../bolt/bolt.md](../bolt/bolt.md).

### Weld Design Check

Connecty provides automatic AISC 360-22 checks for fillet welds (with geometry-based inputs):

```python
from connecty import WeldConnection, WeldBaseMetal, WeldParams, Load

# Setup weld connection with base metal properties
base_metal = WeldBaseMetal(t=10.0, fy=350.0, fu=450.0)
params = WeldParams(type="fillet", leg=6.0)
connection = WeldConnection.from_dxf(
    "path/to/weld.dxf",
    parameters=params,
    base_metal=base_metal,
    is_double_fillet=False
)

# Analyze
load = Load(Fy=-120000, Fz=45000, location=(0, 0, 0))
result = connection.analyze(load, method="icr")

# Automatic AISC 360-22 check
check = result.check(standard="aisc")

# Results
print(f"Utilization: {check.governing_utilization:.2f}")
print(f"Limit state: {check.governing_limit_state}")

if check.governing_utilization <= 1.0:
    print("PASS")
else:
    print("FAIL")
```

**Directional strength increase (automatic by default):**

By default, Connecty automatically computes theta at the **governing location** (the point of maximum utilization) to claim the AISC k_ds directional strength benefit:

```python
# Default behavior: automatic theta computation
check = result.check(standard="aisc")
print(f"Auto theta: {check.details[0].theta_deg:.1f}°")
print(f"k_ds: {check.details[0].k_ds:.4f}")

# Conservative mode: force k_ds=1.0
check = result.check(standard="aisc", conservative_k_ds=True)
print(f"k_ds: {check.details[0].k_ds:.4f}")  # Will be 1.0
```

The automatic computation scans all points along the weld to find the one with the highest stress-to-capacity ratio ($\sigma / k_{ds}$), ensuring the true governing condition is identified even if it doesn't occur at the point of maximum absolute stress.

**Key Features:**
- AISC J2.2 (fillet weld metal strength with k_ds directional factor)
- AISC J4 (base metal fusion face shear: yielding + rupture)
- Detailing limits (max fillet size per thickness)
- Per-limit-state utilization
- Automatic theta computation at governing location

**Manual stress-based check:**

For custom checks or other weld types, you can use the stress output directly:

```python
from connecty import Weld, WeldParams, Load, LoadedWeld

# ... analyze weld ...
loaded = LoadedWeld(weld, load, method="elastic")

# Define your allowable stress
# Example: AISC 360 fillet weld
F_EXX = 483.0  # E70 electrode (MPa)
phi = 0.75     # resistance factor
allowable = phi * 0.60 * F_EXX  # ~218 MPa

# Check adequacy
utilization = loaded.max / allowable
if utilization <= 1.0:
    print(f"PASS: {utilization:.1%}")
else:
    print(f"FAIL: {utilization:.1%}")
```

---

## 6. Examples

Connecty includes comprehensive examples demonstrating analysis and checks. Run them with:

```bash
# Run all examples (welds + bolts)
python examples/run_all_examples.py

# Run bolt examples only
python examples/run_bolt_examples.py
```

**Example Organization:**

```
examples/
├── bolt analysis/       # Force distribution (elastic vs ICR)
├── bolt check/          # AISC 360-22 checks (bearing vs slip-critical)
├── bolt plotting/       # Visualization
├── weld analysis/       # Stress distribution
├── weld plotting/       # Visualization
└── common/              # Shared helpers
```

**Gallery Outputs:**

```
gallery/
├── bolt analysis/       # .txt analysis results + .svg plots
├── bolt check/          # .txt check results
├── bolt plotting/       # .svg bolt group plots
├── weld analysis/       # .txt stress results
└── weld plotting/       # .svg stress distribution plots
```

### Example 1: Eccentric Bolt Group (Elastic vs. ICR)

```python
from connecty import BoltGroup, Plate, BoltConnection, Load

# 4×2 bolt pattern
bolts = BoltGroup.from_pattern(rows=4, cols=2, spacing_y=100, spacing_z=75, diameter=20)
plate = Plate(corner_a=(-100.0, -250.0), corner_b=(100.0, 250.0), thickness=12.0, fu=450.0, fy=350.0)
connection = BoltConnection(bolt_group=bolts, plate=plate)

# Eccentric load (100 kN at edge)
load = Load(Fy=-100000, location=(150, 0, 100))

# Elastic method
elastic = connection.analyze(load, shear_method="elastic", tension_method="conservative")
print(f"Elastic: Max = {elastic.max_shear_force:.1f} N")

# ICR method (more economical)
icr = connection.analyze(load, shear_method="icr", tension_method="conservative")
print(f"ICR: Max = {icr.max_shear_force:.1f} N")

# ICR typically 15-30% more economical
savings = (1 - icr.max_shear_force / elastic.max_shear_force) * 100
print(f"ICR saves: {savings:.0f}%")
```

See also: `examples/bolt analysis/bolt_group_analysis.py`

### Example 2: Bolt Check (Bearing vs. Slip-Critical)

```python
from connecty import BoltGroup, Plate, BoltConnection, Load

# 2×3 bolt group
bolts = BoltGroup.from_pattern(rows=2, cols=3, spacing_y=80, spacing_z=70, diameter=20)
plate = Plate(corner_a=(-150.0, -125.0), corner_b=(150.0, 125.0), thickness=14.0, fu=450.0, fy=350.0)
connection = BoltConnection(bolt_group=bolts, plate=plate)
load = Load(Fy=-100000, Fz=25000, location=(40, 120, 0))

# Analyze
result = connection.analyze(load, shear_method="elastic", tension_method="conservative")

# Bearing-type check
bearing = result.check(connection_type="bearing", threads_in_shear_plane=True)
print(f"Bearing: {bearing.governing_utilization:.1%}")

# Slip-critical check (Class B)
slip = result.check(connection_type="slip-critical", slip_class="B", n_s=2)
print(f"Slip-critical: {slip.governing_utilization:.1%}")
```

See also: `examples/bolt check/bearing_vs_slip_check.py`

### Example 3: Fillet Weld with Moment

```python
from connecty import Weld, WeldParams, Load, LoadedWeld
from sectiony.library import rhs

# Section with fillet welds
section = rhs(b=100, h=200, t=10, r=15)
params = WeldParams(type="fillet", leg=6.0)
weld = Weld.from_section(section, params)

# Eccentric shear load
load = Load(Fy=-100e3, location=(50, 0))

# Elastic method
elastic = LoadedWeld(weld, load, method="elastic")
print(f"Elastic: Max = {elastic.max:.1f} MPa")

# ICR method
icr = LoadedWeld(weld, load, method="icr")
print(f"ICR: Max = {icr.max:.1f} MPa")

# Visualize both
elastic.plot(save_path="elastic.svg")
icr.plot(save_path="icr.svg")
```

See also: `examples/weld analysis/` and `examples/weld plotting/`

---

## 7. API Reference Summary

### Weld Classes

| Class | Purpose |
|-------|---------|
| `Weld` | Weld geometry + parameters |
| `WeldParams` | Weld configuration (geometry only) |
| `Load` | Load definition (forces + moments) |
| `LoadedWeld` | Weld + load (calculates stress) |
| `PointStress` | Stress at a single point |
| `StressComponents` | Detailed stress components |

### Bolt Classes

| Class | Purpose |
|-------|---------|
| `BoltGroup` | Group of bolts at specified coordinates |
| `Plate` | Plate geometry for connection backing |
| `BoltConnection` | Combines bolt group and plate |
| `Load` | Load definition (forces + moments) |
| `LoadedBoltConnection` | Analysis result (forces at each bolt) |
| `BoltResult` | Result details for a single bolt |

### Key Methods

**Weld Analysis:**
```python
weld = Weld(geometry=geom, parameters=params)
loaded = LoadedWeld(weld, load, method="elastic")
loaded.plot(save_path="weld.svg")
```

**Bolt Analysis:**
```python
bolts = BoltGroup.from_pattern(rows=3, cols=2, spacing_y=100, spacing_z=75, diameter=20)
plate = Plate(corner_a=(-100.0, -150.0), corner_b=(100.0, 150.0), thickness=12.0, fu=450.0, fy=350.0)
connection = BoltConnection(bolt_group=bolts, plate=plate)
result = connection.analyze(load, shear_method="elastic", tension_method="conservative")
result.plot(save_path="bolts.svg")
```

---

## 8. References & Standards

- **AISC 360-22**: Specification for Structural Steel Buildings
- **AWS D1.1**: Structural Welding Code – Steel
- **Crawford-Kulak Model**: Used for ICR bolt force-deformation curves
- **Instantaneous Center of Rotation (ICR)**: Per AISC Manual Part 7 & 8

All methods follow AISC provisions for force/stress calculation. Design checks (capacity, factors, combinations) are your responsibility according to your project requirements.
