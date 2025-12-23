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
from connecty import BoltGroup, BoltParameters, Force

# All dimensions in inches, all forces in kip
params = BoltParameters(diameter=0.75)  # 3/4" bolt
force = Force(Fy=-100.0, location=(4.0, 0.0))  # 100 kip at 4"
bolts = BoltGroup(positions=[(0, 0), (0, 3)], parameters=params)
result = bolts.analyze(force)  # Forces in kip
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
from connecty import BoltGroup, BoltParameters, Force

# Create bolt pattern
params = BoltParameters(diameter=20)
bolts = BoltGroup.from_pattern(
    rows=3, cols=2, spacing_y=75, spacing_z=60, diameter=20
)

# Apply load
force = Force(Fy=-100000, location=(75, 150))

# Analyze
result = bolts.analyze(force, method="elastic")

# Access results
print(f"Max bolt force: {result.max_force:.1f} kN")
print(f"Mean force: {result.mean:.1f} kN")

# Visualize
result.plot(save_path="bolts.svg")
```

### Creating Bolt Groups

**Option A: Explicit Coordinates**

```python
from connecty import BoltGroup, BoltParameters

params = BoltParameters(diameter=20)
bolts = BoltGroup(
    positions=[(0, 0), (0, 75), (0, 150)],
    parameters=params
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
result = bolts.analyze(force, method="elastic")

# ICR method (more accurate for eccentric loading)
result = bolts.analyze(force, method="icr")
```

### Force Results

```python
# Properties
result.max_force        # Maximum resultant force on any bolt (kN)
result.min_force        # Minimum resultant force on any bolt (kN)
result.mean             # Average bolt force (kN)
result.critical_bolt    # BoltForce at max location
result.critical_index   # Index of most loaded bolt
result.method           # "elastic" or "icr"

# Detailed access
for bf in result.bolt_forces:
    print(f"Bolt at ({bf.y}, {bf.z})")
    print(f"  Fy = {bf.Fy:.2f} kN")
    print(f"  Fz = {bf.Fz:.2f} kN")
    print(f"  Resultant = {bf.resultant:.2f} kN")

# ICR-specific
if result.method == "icr":
    print(f"ICR center: {result.icr_point}")
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

Connecty outputs **forces and stresses only**. You handle design checks.

### Bolt Design Check

```python
from connecty import BoltGroup, BoltParameters, Force

# ... analyze bolt group ...
result = bolts.analyze(force, method="elastic")

# Define your capacity (from tables, material properties, etc.)
# Example: A325 M20 bearing-type bolt
F_nv = 372.0  # MPa (nominal shear strength)
area = 314.0  # mm² (M20 area)
phi = 0.75    # resistance factor
capacity_kN = (phi * F_nv * area) / 1000

# Check adequacy
utilization = result.max_force / capacity_kN
if utilization <= 1.0:
    print(f"PASS: {utilization:.1%}")
else:
    print(f"FAIL: {utilization:.1%}")
```

### Weld Design Check

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

### Example 1: Eccentric Bolt Group

Compare elastic vs. ICR for an eccentric load:

```python
from connecty import BoltGroup, BoltParameters, Force

# 4×2 bolt pattern
params = BoltParameters(diameter=20)
bolts = BoltGroup.from_pattern(rows=4, cols=2, spacing_y=100, spacing_z=75, diameter=20)

# Eccentric load (100 kN at edge)
force = Force(Fy=-100000, location=(150, 0))

# Elastic method
elastic = bolts.analyze(force, method="elastic")
print(f"Elastic: Max = {elastic.max_force:.1f} kN")

# ICR method (more economical)
icr = bolts.analyze(force, method="icr")
print(f"ICR: Max = {icr.max_force:.1f} kN")

# ICR typically 15-30% more economical
savings = (1 - icr.max_force / elastic.max_force) * 100
print(f"ICR saves: {savings:.0f}%")
```

### Example 2: Fillet Weld with Moment

Compare elastic vs. ICR for a fillet weld with eccentric load:

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

### Example 3: Custom Design Workflow

```python
from connecty import BoltGroup, BoltParameters, Force

# Try different bolt sizes
sizes = [16, 20, 24]  # mm

for size in sizes:
    params = BoltParameters(diameter=size)
    bolts = BoltGroup.from_pattern(rows=3, cols=2, spacing_y=100, spacing_z=75, diameter=size)
    
    force = Force(Fy=-200000, location=(100, 75))
    result = bolts.analyze(force, method="icr")
    
    # Assume A325 capacity
    F_nv = 372.0  # MPa
    area = 3.14 * (size / 2) ** 2  # mm²
    capacity_kN = (0.75 * F_nv * area) / 1000
    
    util = result.max_force / capacity_kN
    print(f"M{size}: {util:.1%} utilization")
```

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
| `BoltParameters` | Bolt configuration (diameter only) |
| `Force` | Load definition |
| `BoltResult` | Analysis result (forces at each bolt) |
| `BoltForce` | Force at a single bolt |

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
result = bolts.analyze(force, method="elastic")
result.plot(save_path="bolts.svg")
```

---

## 8. References & Standards

- **AISC 360-22**: Specification for Structural Steel Buildings
- **AWS D1.1**: Structural Welding Code – Steel
- **Crawford-Kulak Model**: Used for ICR bolt force-deformation curves
- **Instantaneous Center of Rotation (ICR)**: Per AISC Manual Part 7 & 8

All methods follow AISC provisions for force/stress calculation. Design checks (capacity, factors, combinations) are your responsibility according to your project requirements.
