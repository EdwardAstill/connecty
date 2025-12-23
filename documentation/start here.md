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

## Quick Links

- **[Bolt Analysis & Checks](bolt/)**: Force distribution and AISC checks
- **[Weld Analysis](weld/)**: Stress calculation methods
- **[User Guide](general/user%20guide.md)**: Detailed workflow examples
- **[AISC 360-22](general/standards/AISC%20360-22.md)**: Standards reference

