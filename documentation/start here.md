# Connecty - Connection Analysis & Design Checks

This module is for analyzing **welded and bolted connections** per AISC 360-22.

## Two Main Connection Types

### **1. Welds**

**Analysis:** Calculate stress distribution along fillet, PJP, CJP, plug, and slot welds  
**Check:** You define allowable stress; compare max stress to allowable

### **2. Bolts**

**Analysis:** Calculate force distribution on bolt groups using elastic or ICR methods  
**Check:** AISC 360-22 automatic checks for A325/A490 bolts (bearing-type and slip-critical)

---

## What You'll Find

### Analysis
- Force/stress calculation based on geometry and loads
- Elastic method (conservative, closed-form)
- ICR method (more accurate for eccentric loading)
- Per-bolt and per-point stress/force output

### Design Checks

**Welds:** You provide allowable stress; the tool outputs max stress for comparison

**Bolts:** Automatic AISC 360-22 checks for:
- Shear rupture (J3.6)
- Tension rupture with interaction (J3.6/J3.7)
- Bearing and tear-out (J3.10)
- Slip resistance (J3.8–J3.9) for slip-critical connections

Per-bolt utilization breakdown and governing limit state identification

---

## Quick Start - Bolt Connection

```python
from connecty import (
    BoltGroup, Plate, BoltConnection,
    ConnectionLoad, ConnectionResult
)

# 1. Define bolt group geometry
bolts = BoltGroup.from_pattern(
    rows=3, cols=2,
    spacing_y=75, spacing_z=60,
    diameter=20
)

# 2. Define plate geometry
plate = Plate(width=240, depth=200, thickness=12)

# 3. Create connection
connection = BoltConnection(
    bolt_group=bolts,
    plate=plate,
    n_shear_planes=1
)

# 4. Define applied load
load = ConnectionLoad(
    Fy=-100000,  # 100 kN downward
    location=(75, 150, 100)
)

# 5. Analyze (analysis happens automatically)
result = ConnectionResult(
    connection=connection,
    load=load,
    shear_method="elastic",
    tension_method="conservative"
)

# 6. View results
print(f"Max shear: {result.max_shear_force:.1f} N")
print(f"Max tension: {result.max_axial_force:.1f} N")
print(f"Max stress: {result.max_combined_stress:.1f} MPa")

# 7. Visualize
result.plot(save_path="analysis.svg")
```

---

## Quick Links

- **[Bolt Analysis & Checks](bolt/)**: Force distribution and AISC checks
- **[Weld Analysis](weld/)**: Stress calculation methods
- **[User Guide](general/user%20guide.md)**: Detailed workflow examples
- **[AISC 360-22](general/standards/AISC%20360-22.md)**: Standards reference

