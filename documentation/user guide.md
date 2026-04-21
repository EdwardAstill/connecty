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
from connecty import BoltConnection, BoltLayout, BoltParams, Load, Plate

layout = BoltLayout(points=[(0.0, 0.0), (0.0, 3.0)])  # inches
bolt = BoltParams(diameter=0.75, grade="A325")
plate = Plate(corner_a=(-5.0, -5.0), corner_b=(5.0, 5.0), thickness=0.5, fu=65.0, fy=50.0)
connection = BoltConnection(layout=layout, bolt=bolt, plate=plate, n_shear_planes=1)

load = Load(Fy=-100.0, location=(0.0, 4.0, 0.0))  # 100 kip, 4" eccentric
result = connection.analyze(load, shear_method="elastic", tension_method="conservative")
```

### Geometry First

Connecty separates geometry from analysis from capacity checks:

- `BoltLayout` — positions only (no material)
- `BoltParams` — bolt size and grade (required for AISC stress lookups)
- `Plate` — plate geometry and material
- `BoltConnection` — assembles the above; analysis produces forces, not utilizations
- `WeldParams` — weld type and geometry only; electrode strength is provided at check time

Design capacity (allowable stress, resistance factors, code combinations) is your responsibility. Connecty gives you the force/stress demand.

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
from connecty import BoltConnection, BoltLayout, BoltParams, Load, Plate

# 1. Define bolt layout (positions only)
layout = BoltLayout.from_pattern(rows=3, cols=2, spacing_y=75, spacing_z=60)

# 2. Define bolt parameters (size + grade)
bolt = BoltParams(diameter=20.0, grade="A325")

# 3. Define plate geometry
plate = Plate.from_dimensions(width=200.0, height=300.0, thickness=12.0, fu=450.0, fy=350.0)

# 4. Create connection
connection = BoltConnection(layout=layout, bolt=bolt, plate=plate, n_shear_planes=1)

# 5. Apply load
load = Load(Fy=-100_000.0, location=(0.0, 0.0, 75.0))

# 6. Analyze
result = connection.analyze(load, shear_method="elastic", tension_method="conservative")

# 7. Access results
forces = result.to_bolt_forces()
max_shear = max(bf.shear for bf in forces)
print(f"Max shear force: {max_shear:.1f} N")

# 8. Visualize
result.plot_shear(save_path="bolts_shear.svg")
result.plot_tension(save_path="bolts_tension.svg")
```

### Creating Bolt Layouts

`BoltLayout` defines positions. `BoltParams` defines the bolt itself.

**Option A: Explicit Positions**

```python
from connecty import BoltLayout, BoltParams

layout = BoltLayout(points=[(0.0, 0.0), (0.0, 75.0), (0.0, 150.0)])  # (y, z) per bolt
bolt = BoltParams(diameter=20.0, grade="A325")
```

**Option B: Rectangular Grid**

```python
layout = BoltLayout.from_pattern(
    rows=3, cols=2, spacing_y=75, spacing_z=60
)
```

**Option C: Circular Pattern**

```python
layout = BoltLayout.from_circular(n=8, radius=100, center=(0.0, 0.0))
```

### Force Calculation

```python
# Elastic method (direct + torsional superposition)
result = connection.analyze(load, shear_method="elastic", tension_method="conservative")

# ICR method (more economical for eccentric shear)
result = connection.analyze(load, shear_method="icr", tension_method="conservative")

# Tension methods:
#   "conservative" — neutral axis at bolt group centroid
#   "accurate"     — d/6 neutral axis approximation
result = connection.analyze(load, shear_method="elastic", tension_method="accurate")
```

### Force Results

```python
# Raw forces dict (per bolt)
forces_dict = result.bolt_forces  # {"Fx": [...], "Fy": [...], "Fz": [...]}

# Per-bolt BoltForceResult objects
for bf in result.to_bolt_forces():
    print(f"  Fx (tension) = {bf.Fx:.2f} N")
    print(f"  Fy           = {bf.Fy:.2f} N")
    print(f"  Fz           = {bf.Fz:.2f} N")
    print(f"  Shear result = {bf.shear:.2f} N")

# ICR point (ICR method only)
if result.icr_point:
    print(f"ICR: {result.icr_point}")

print(result.shear_method)   # "elastic" or "icr"
print(result.tension_method) # "conservative" or "accurate"
```

### Plotting

```python
result.plot_shear(save_path="bolts_shear.svg")
result.plot_tension(save_path="bolts_tension.svg")
```

---

## 5. Design Checks

Connecty provides automatic design checks for **bolts** and **fillet welds** (AISC 360-22, LRFD). Manual allowable-stress checks remain available when you want full control.

### Bolt Design Check (Automatic AISC 360-22)

Connecty checks A325 and A490 bolts for bearing-type and slip-critical connections.

```python
from connecty import BoltConnection, BoltLayout, BoltParams, Load, Plate

layout = BoltLayout.from_pattern(rows=3, cols=2, spacing_y=75, spacing_z=60)
bolt = BoltParams(diameter=20.0, grade="A325")
plate = Plate.from_dimensions(width=240.0, height=300.0, thickness=12.0, fu=450.0, fy=350.0)
connection = BoltConnection(layout=layout, bolt=bolt, plate=plate, n_shear_planes=1)

load = Load(Fy=-100_000.0, Fz=30_000.0, location=(0.0, 75.0, 100.0))
result = connection.analyze(load, shear_method="elastic", tension_method="conservative")

# Bearing-type check
check = result.check(standard="aisc", connection_type="bearing")

# Results are a dict; utilizations are per-bolt lists
for i, (shear_u, gov) in enumerate(zip(check["shear"], check["governing"])):
    print(f"Bolt {i+1}: shear U={shear_u:.3f}  governing={gov}")

# Max utilization per limit state across all bolts
print(f"Max shear U:    {max(check['shear']):.3f}")
print(f"Max bearing U:  {max(check['bearing']):.3f}")
print(f"Max combined U: {max(check['combined']):.3f}")
```

**Key Features:**
- AISC J3.6/J3.7 — shear, tension, and combined interaction per bolt
- AISC J3.10 — bearing and tear-out per bolt
- AISC J3.8/J3.9 — group-level slip resistance (slip-critical only)

**Connection types:**

```python
# Bearing-type
check = result.check(standard="aisc", connection_type="bearing")

# Slip-critical (group-level slip in check["slip"])
check = result.check(standard="aisc", connection_type="slip_critical")
print(f"Slip group U: {check['slip'][0]:.3f}")

# Slip-critical with filler plates (affects h_f factor)
check = result.check(standard="aisc", connection_type="slip_critical", fillers=1)
```

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
from connecty import BoltConnection, BoltLayout, BoltParams, Load, Plate

layout = BoltLayout.from_pattern(rows=4, cols=2, spacing_y=100, spacing_z=75)
bolt = BoltParams(diameter=20.0, grade="A325")
plate = Plate.from_dimensions(width=200.0, height=400.0, thickness=12.0, fu=450.0, fy=350.0)
connection = BoltConnection(layout=layout, bolt=bolt, plate=plate, n_shear_planes=1)

load = Load(Fy=-100_000.0, location=(0.0, 0.0, 150.0))  # eccentric in z

elastic = connection.analyze(load, shear_method="elastic", tension_method="conservative")
icr = connection.analyze(load, shear_method="icr", tension_method="conservative")

elastic_max = max(bf.shear for bf in elastic.to_bolt_forces())
icr_max = max(bf.shear for bf in icr.to_bolt_forces())

print(f"Elastic max: {elastic_max:.1f} N")
print(f"ICR max:     {icr_max:.1f} N")
print(f"ICR saves:   {(1 - icr_max / elastic_max) * 100:.0f}%")
```

See also: `examples/bolt.py`

### Example 2: Bolt Check (Bearing vs. Slip-Critical)

```python
from connecty import BoltConnection, BoltLayout, BoltParams, Load, Plate

layout = BoltLayout.from_pattern(rows=2, cols=3, spacing_y=80, spacing_z=70)
bolt = BoltParams(diameter=20.0, grade="A325")
plate = Plate.from_dimensions(width=280.0, height=180.0, thickness=14.0, fu=450.0, fy=350.0)
connection = BoltConnection(layout=layout, bolt=bolt, plate=plate, n_shear_planes=1)
load = Load(Fy=-100_000.0, Fz=25_000.0, location=(0.0, 40.0, 120.0))

result = connection.analyze(load, shear_method="elastic", tension_method="conservative")

# Bearing-type check — per-bolt utilizations
bearing = result.check(standard="aisc", connection_type="bearing")
print(f"Bearing max shear U: {max(bearing['shear']):.3f}")
print(f"Bearing max bearing U: {max(bearing['bearing']):.3f}")

# Slip-critical check — group-level slip
slip = result.check(standard="aisc", connection_type="slip_critical")
print(f"Slip group U: {slip['slip'][0]:.3f}")
```

See also: `examples/bolt.py`

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
| `BoltLayout` | Bolt positions (y, z) |
| `BoltParams` | Bolt size, grade, and derived AISC properties |
| `BoltGroup` | Internal bolt group (created by `BoltConnection`) |
| `Plate` | Plate geometry and material |
| `BoltConnection` | Assembles layout + params + plate; runs analysis |
| `LoadedBoltConnection` | Analysis result — distributed forces per bolt |
| `BoltForceResult` | Force result for a single bolt |

### Key Methods

**Weld Analysis:**
```python
connection = WeldConnection.from_dxf("path.dxf", parameters=params, base_metal=base_metal)
result = connection.analyze(load, method="elastic")
result.plot(save_path="weld.svg")
check = result.check(standard="aisc")
```

**Bolt Analysis:**
```python
layout = BoltLayout.from_pattern(rows=3, cols=2, spacing_y=100, spacing_z=75)
bolt = BoltParams(diameter=20.0, grade="A325")
plate = Plate.from_dimensions(width=200.0, height=300.0, thickness=12.0, fu=450.0, fy=350.0)
connection = BoltConnection(layout=layout, bolt=bolt, plate=plate, n_shear_planes=1)
result = connection.analyze(load, shear_method="elastic", tension_method="conservative")
result.plot_shear(save_path="bolts.svg")
check = result.check(standard="aisc", connection_type="bearing")
```

---

## 8. References & Standards

- **AISC 360-22**: Specification for Structural Steel Buildings
- **AWS D1.1**: Structural Welding Code – Steel
- **Crawford-Kulak Model**: Used for ICR bolt force-deformation curves
- **Instantaneous Center of Rotation (ICR)**: Per AISC Manual Part 7 & 8

All methods follow AISC provisions for force/stress calculation. Design checks (capacity, factors, combinations) are your responsibility according to your project requirements.
