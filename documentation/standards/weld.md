# AISC 360-22 — Weld Design Checks (LRFD)

This document defines the **AISC-based weld design checks** implemented in `connecty`, rewritten to align in structure, scope, and reporting style with the Bolt Design document.

Only **AISC 360-22** provisions are included. **Australian Standards are intentionally excluded.**

All checks are **unit agnostic**: any consistent set of units may be used (e.g. mm–N–MPa).

---

## Scope / assumptions

* Applicable standard: **AISC 360-22 (LRFD)**
* Weld types supported:

  * Fillet welds
  * Partial-joint-penetration (PJP) groove welds
  * Complete-joint-penetration (CJP) groove welds
  * Plug and slot welds
* Filler metal strength **must not exceed** base metal strength unless explicitly permitted by AISC.
* Weld group forces are obtained from elastic or ICR-based weld group analysis.
* Forces are reduced to a **single resultant demand per weld group**:

$$
R_u = \sqrt{F_x^2 + F_y^2 + F_z^2}
$$

* Strength checks are performed **per weld group**.

---

## Input simplifications and implementation approach

To keep `connecty` practical and conservative while maintaining AISC compliance, the following simplifications are applied:

### Primary scope: Fillet welds

**Fillet welds** are the default and primary weld type supported with full automatic checking.

For **PJP, CJP, plug, and slot welds**, advanced inputs are required:
- **PJP**: User must supply effective throat `t_e` (or directly `A_we`)
- **CJP**: User must supply effective base metal area `A_BM`
- **Plug/Slot**: User must supply effective area `A_we` (nominal hole/slot area)

Unless advanced inputs are provided, `connecty` will only compute utilisations for **fillet welds**.

### Electrode strength (matching filler assumption)

By default, `connecty` assumes **matching electrodes**:

$$
F_{EXX} = F_u \text{ (of the weaker/thinner connected part)}
$$

This is conservative and typical in practice. If a specified electrode is known (e.g., E70), users should override `F_{EXX}`; otherwise the default may underpredict weld metal strength but will not miss base-metal-governed limit states.

**Impact:** Since base metal fusion-face capacity is always checked for fillets, the governing limit state is automatically captured.

### Material properties: single set per weld group

Instead of tracking properties for both connected parts, `connecty` requires only the **weaker/thinner material**:

**Required inputs:**
- `t` = thickness of thinner part
- `F_y` = yield strength of weaker material
- `F_u` = tensile strength of weaker material

**Justification:** Base metal checks are conservative when tied to the weaker side, and this is the controlling failure mode.

### Fusion faces: boolean input

The number of fusion faces `n_f` is specified via a simple boolean:

- `is_double_fillet: bool`
  - `True` → `n_f = 2` (both sides of plate)
  - `False` → `n_f = 1` (single fillet line)

This is clearer than asking users to count "fusion faces."

### Total effective length (no segmentation required)

Users supply a **single total effective length**:

- $L_{weld}$ = sum of all effective weld segment lengths

Segment-by-segment geometry is **not required** for capacity checking (though it may be used for stress visualization).

### Resultant demand only

Users supply the **resultant factored demand** on the weld group:

$$
R_u = \sqrt{F_x^2 + F_y^2 + F_z^2}
$$

where $R_u$ is the **factored** resultant demand on the weld group.

Component-level directionality is not required unless the directional strength factor `k_ds` is explicitly enabled.

---

### Minimal "easy mode" input summary

For **fillet weld capacity checking**, the minimal required inputs are:

| Parameter         | Description                                      | Units  |
| ----------------- | ------------------------------------------------ | ------ |
| `w`               | Fillet leg size                                  | length |
| `L_weld`          | Total effective weld length                      | length |
| `R_u`             | Resultant factored demand                        | force  |
| `t`               | Thinner part thickness                           | length |
| `F_y`             | Weaker material yield strength                   | stress |
| `F_u`             | Weaker material tensile strength                 | stress |
| `is_double_fillet`| True if fillet on both sides of plate            | bool   |
| `F_EXX` (optional)| Electrode strength (default: `F_u`)              | stress |
| `theta` (optional)| Load angle for `k_ds` factor (default: ignore)   | degrees|

This input set enables:
- Weld metal strength check (with default matching electrode)
- Base metal fusion-face shear check (yielding + rupture)
- Maximum and minimum fillet size detailing checks

---

## AISC tables used

### Table J2.4 — Minimum fillet weld size

Minimum permitted fillet weld leg size is enforced based on the thickness of the thinner connected part.

> The weld leg size is not permitted to exceed the thickness of the thinner part joined (Section J2.2b).

### Maximum fillet weld size (detailing)

Applies to fillet welds placed along the edge of a part (common detailing limit).

For the thinner part thickness $t$, the maximum fillet weld leg size is:

$$
w_{\max} =
\begin{cases}
t, & t < 6\text{ mm}\\
t - 2\text{ mm}, & t \ge 6\text{ mm}
\end{cases}
$$

This is a **detailing limit** (not a strength calculation). `connecty` will flag any fillet weld with $w > w_{\max}$.

---

### Table J2.5 — Available strength of welded joints (excerpted logic)

Key takeaways applied in `connecty`:

* **Fillet, PJP, Plug/Slot welds**
  Weld metal strength usually governs.
* **CJP groove welds**
  Strength is controlled by **base metal**, not weld metal.
* A **resistance factor of ϕ = 0.75** is conservatively applied to most weld-controlled limit states.

---

## Weld strength checks implemented

### 1) General design strength rule

The design strength of a weld is:

$$
\phi R_n = \min(\phi_w R_{n,\text{weld}}, \, \phi_b R_{n,\text{base}})
$$

Where:

* $R_{n,\text{weld}}$ = nominal weld metal strength
* $R_{n,\text{base}}$ = nominal base metal strength
* $\phi_w$, $\phi_b$ = resistance factors (depend on weld type and limit state, as specified in subsequent sections)

Base metal strength is **always evaluated for fillet welds**. The governing limit state (weld metal or base metal) depends on relative material strengths and weld geometry.

---

## 2) Fillet welds — Section J2.2

### Effective geometry

* Effective throat:

$$
t_e = 0.707 w
$$

* Effective area:

$$
A_{we} = L_{weld} \, t_e
$$

### Nominal strength

$$
R_n = F_{nw} A_{we} k_{ds}
$$

Where:

* $F_{nw} = 0.60 F_{EXX}$
* $k_{ds}$ = directional strength factor

Directional factor:

$$
k_{ds} = 1.0 + 0.50 \sin^{1.5} \theta
$$

* $\theta$ = angle between applied force and weld axis
* If directional effects are ignored, `connecty` uses $k_{ds} = 1.0$

**Automatic theta computation (default behavior)**

By default, `connecty` automatically computes $\theta$ at the **governing location** (the point of maximum utilization, i.e., highest stress-to-capacity ratio).

The algorithm:
1. Scans all discretized points along the weld.
2. For each point $i$, calculates local stress $\sigma_i$ and angle $\theta_i$ between local force direction and tangent.
3. Calculates local directional factor $k_{ds,i} = 1.0 + 0.5 \sin^{1.5}\theta_i$.
4. Identifies the point that maximizes the ratio $\sigma_i / k_{ds,i}$.
5. Uses the $\theta$ from that governing point for the weld group check.

This ensures safety even if a point with slightly lower stress has a much less favorable load angle (lower $k_{ds}$), which could result in a higher utilization.

To disable this and use conservative $k_{ds} = 1.0$, set `conservative_k_ds=True` in the check.

**Rectangular HSS (end connection) restriction**

* If the weld is **to the end of a rectangular HSS** (cap plate / end plate type), then **force**:

$$
k_{ds} = 1.0
$$

> If end-connection geometry cannot be reliably detected, a conservative blanket rule may be applied to all rectangular HSS connections.

### Resistance factor

$$
\phi = 0.75
$$

### Base metal strength at fusion face (Section J4 via Table J2.5)

For fillet weld groups, base metal shear capacity at the fusion face is evaluated:

* Fusion-face shear area:

$$
A_{BM} = n_f \, t \, L_{weld}
$$

Where:

* $t$ = thickness of thinner connected part
* $n_f$ = number of fusion faces (1 for single fillet line, 2 for double fillet)
* $L_{weld}$ = total effective weld length; for weld groups with multiple segments, use $L_{weld} = \sum L_i$ (sum of effective segment lengths)

Base metal design shear capacity:

$$
\phi R_{n,\text{base}} = \min\left( \underbrace{1.00(0.60F_yA_{BM})}_{\text{shear yielding}}, \, \underbrace{0.75(0.60F_uA_{BM})}_{\text{shear rupture}} \right)
$$

The utilisation is:

$$
U_{base} = \frac{R_u}{\phi R_{n,\text{base}}}
$$

---

## 3) Groove welds — Section J2.1

### A) Complete-joint-penetration (CJP)

CJP welds are treated as **base metal connections**.

* **Tension (normal to weld):**

$$
\phi = 0.90, \quad R_n = F_y A_{BM}
$$

* **Shear:**

$$
\phi = 1.00, \quad R_n = 0.60 F_y A_{BM}
$$

Weld metal strength is **not checked**.

---

### B) Partial-joint-penetration (PJP)

* Effective throat determined from groove geometry (Table J2.1)

* **Tension:**

$$
\phi = 0.80, \quad R_n = 0.60 F_{EXX} A_{we}
$$

* **Shear:**

$$
\phi = 0.75, \quad R_n = 0.60 F_{EXX} A_{we}
$$

---

## 4) Plug and slot welds — Section J2.3

* Effective area = nominal area of hole or slot

$$
R_n = 0.60 F_{EXX} A_{we}
$$

* Resistance factor:

$$
\phi = 0.75
$$

---

## Utilisation reporting

For each weld group, `connecty` reports:

### Weld metal utilisation

$$
U_{weld} = \frac{R_u}{\phi R_{n,\text{weld}}}
$$

### Base metal utilisation (if applicable)

$$
U_{base} = \frac{R_u}{\phi R_{n,\text{base}}}
$$

### Governing utilisation

$$
U_{governing} = \max(U_{weld}, U_{base})
$$

The **maximum governing utilisation across all weld groups** is returned as the connection result.

---

## Reporting format

For each weld group:

| Weld ID | Type   | Throat / Size | Load Angle $\theta$ | Demand $R_u$ | $\phi R_n$ | Governing Utilisation |
| ------- | ------ | ------------- | ------------------- | ------------ | ---------- | --------------------- |
| W1      | Fillet | 6 mm          | 0°                  | 48 kN        | 120 kN     | 0.40                  |
| W2      | Fillet | 8 mm          | 90°                 | 72 kN        | 150 kN     | 0.48                  |
| W3      | CJP    | —             | —                   | 210 kN       | 225 kN     | 0.93                  |

---

## Code deviations and conservative assumptions

* Welds are checked using **resultant force magnitude**, ignoring stress component directionality unless $k_{ds}$ is enabled.
* Base metal shear at the fusion face is checked for fillet welds; the governing utilisation may be weld-controlled or base-metal-controlled.
* No redistribution of force between weld groups is permitted.

These choices are conservative and align with the philosophy used in the bolt design checks.
