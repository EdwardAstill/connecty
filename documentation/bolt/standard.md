Assumptions to apply to stardards (that help create this section)

Bolts are only o grade A325 or A490

# AISC 360-22


## Checking step
We need to calculate the nominal shear strength and nominal tension strength of each bolt based on its properties (diameter, grade, hole type, etc).

**API usage (bearing or slip-critical)**

```
from connecty import BoltGroup, BoltDesignParams, Load

bolts = BoltGroup.from_pattern(rows=2, cols=2, spacing_y=75, spacing_z=60, diameter=20)
force = Load(Fy=-120000, Fz=25000, location=(0, 40, 80))

design = BoltDesignParams(
    grade="A325",
    hole_type="standard",
    slot_orientation="perpendicular",
    threads_in_shear_plane=True,
    slip_class="A",
    n_s=2,
    fillers=0,
    plate_fu=450.0,
    plate_thickness=10.0,
    edge_distance_y=45.0,
    edge_distance_z=50.0,
)

check = bolts.check_aisc(force, design=design, method="elastic", connection_type="bearing")
print(check.governing_utilization)
print(check.info)  # dict of all per-bolt results
```


Report back the bolt with the highest utilisation.
Actually it would be good to have a table where th eshear force, tension force, and utilisation for each bolt and each check is reported back in a table perhaps.

ASIC proveds us with load factors and nominal strengths for different bolt types and grades.

Mostly will only be using A325 (Group 120) and A490 (Group 150) bolts.

#### Important tables
Table J3.1 (kN) - Minimum pretension
| Bolt Size (mm) | Group 120 | Group 150 |
|----------------|-----------|-----------|
| M12            | 49        | 72        |
| M16            | 91        | 114       |
| M20            | 142       | 179       |
| M22            | 176       | 221       |
| M24            | 205       | 257       |
| M27            | 267       | 334       |
| M30            | 326       | 408       |
| M36            | 475       | 595       |

Table J3.2 Nominal stresses
| Description of Fasteners          | Nominal Tensile Stress F<sub>nt</sub>, ksi (MPa)[a][b] | Threads Not Excluded from Shear Planes — (N)[e] | Threads Excluded from Shear Planes — (X) |
|----------------------------------|----------------------------------------------------------|--------------------------------------------------|------------------------------------------|
| Group 120 (e.g., A325)           | 90 (620)                                                 | 54 (370)                                         | 68 (470)                                 |
| Group 150 (e.g., A490)           | 113 (780)                                                | 68 (470)                                         | 84 (580)                                 |

Table J3.3 nominal hole dimenstions

| Bolt Diameter | Standard (Dia.) | Oversize (Dia.) | Short-Slot (Width × Length) | Long-Slot (Width × Length) |
|---------------|------------------|------------------|-------------------------------|-----------------------------|
| M12           | 14               | 16               | 14 × 18                       | 14 × 30                     |
| M16           | 18               | 20               | 18 × 22                       | 18 × 40                     |
| M20           | 22               | 24               | 22 × 26                       | 22 × 50                     |
| M22           | 24               | 28               | 24 × 30                       | 24 × 55                     |
| M24           | 27[a]            | 30               | 27 × 32                       | 27 × 60                     |
| M27           | 30               | 35               | 30 × 37                       | 30 × 67                     |
| M30           | 33               | 38               | 33 × 40                       | 33 × 75                     |
| ≥ M36         | d + 3            | d + 8            | (d + 3) × (d + 10)            | (d + 3) × 2.5d              |


### Bolt Strength Checks
#### **A. Universal Checks (Required for ALL Bolts)**
Every bolt must be checked for **Shear Rupture**, **Tension Rupture**, and **Bearing/Tearout** at the bolt holes.

**1. Tensile and Shear Strength (Section J3.6)**
* **$\phi = 0.75$ (LRFD)** 
* **Tensile Strength:** $R_n = F_{nt} A_b$ 
* **Shear Strength:** $R_n = F_{nv} A_b$     

* *Note:* Use $F_{nv}$ from Table J3.2 depending on if threads are included (N) or excluded (X) from the shear plane.

**2. Bearing and Tearout Strength (Section J3.10)**
* **$\phi = 0.75$ (LRFD)** 
* This checks the steel plate/connected material, not just the bolt. It is often the governing failure mode.
* **$R_n$ is the lesser of Bearing or Tearout**.
* **Standard Holes:**
    * **Bearing:** $R_n = 2.4 d t F_u$ (if deformation is a consideration).
    * **Tearout:** $R_n = 1.2 l_c t F_u$ (if deformation is a consideration).
    * Where $l_c$ is the clear distance between the edge of the hole and the edge of the material.

---

#### **B. Bearing-Type Connections (Combined Forces)**
If the bolt is in a bearing connection subject to **both** Shear ($f_{rv}$) and Tension ($f_{rt}$):

**Combined Tension and Shear (Section J3.7)**
* **$\phi = 0.75$ (LRFD)** 
* You must calculate a **modified nominal tensile stress** ($F'_{nt}$):
    $$F'_{nt} = 1.3 F_{nt} - \frac{F_{nt}}{\phi F_{nv}} f_{rv} \le F_{nt}$$

* **Check:** The available tensile strength is $R_n = F'_{nt} A_b$.


#### **C. Slip-Critical Connections (Serviceability/Slip Prevention)**
These connections must be designed to prevent slip **AND** for the limit states of bearing-type connections (Shear/Tension/Bearing from Parts A & B above).

**1. Nominal Slip Resistance (Combined J3.8 & J3.9)**
The available slip resistance shall be determined by applying the resistance factor $\phi$ to the nominal strength $R_n$:

$$\text{Design Strength} = \phi R_n$$

**Nominal Strength Formula:**
$$R_n = \mu D_u h_f T_b n_s k_{sc}$$

**Resistance Factors ($\phi$):**
* **$\phi = 1.00$**: Standard holes and short-slotted holes perpendicular to load.
* **$\phi = 0.85$**: Oversized holes and short-slotted holes parallel to load.
* **$\phi = 0.70$**: Long-slotted holes.

**Variable Definitions:**
* **$\mu$**: Mean slip coefficient (0.30 for Class A, 0.50 for Class B).
* **$D_u$**: 1.13 (multiplier for mean installed pretension).
* **$h_f$**: Factor for fillers (1.0 for one filler; 0.85 for $\ge$ 2 fillers).
* **$T_b$**: Minimum fastener pretension from Table J3.1.
* **$n_s$**: Number of slip planes.
* **$k_{sc}$**: Reduction factor for combined tension and shear.
$$ k_{sc} = 1 - \dfrac{T_u}{D_u T_b n_b} \ge 0$$
        
$n_b$: Number of bolts carrying the applied tension.



## **Utilisation Reporting**

Each bolt is evaluated for all applicable limit states based on its connection type. Two categories are considered:

1. **Bearing-type bolts** (connection transmits load through bolt bearing and shear)
2. **Slip-critical bolts** (connection relies on friction to limit slip, but still requires bearing limit-state checks)

The reported utilisation values quantify the demand-to-capacity ratio for each limit state.

---

### **1. Bearing-Type Bolts**

For bolts designed as bearing connections, the following limit states are checked:

##### **1.1 Shear Rupture**

$$
U_V = \frac{V_u}{\phi R_{n,V}}
$$
where $R_{n,V} = F_{nv} A_b$.

#### **1.2 Tension Rupture**

If no significant shear interaction:
$$
U_T = \frac{T_u}{\phi R_{n,T}}
$$
Otherwise, when combined shear–tension interaction applies:
$$
R_{n,T}' = F'_{nt} A_b,\qquad
U_T = \frac{T_u}{\phi R'_{n,T}}
$$

#### **1.3 Bearing / Tear-Out of Connected Material**

$$
U_{\text{bear}} = \frac{V_u}{\phi R_{n,\text{bearing/tearout}}}
$$
The controlling resistance is the minimum of the calculated bearing and tear-out resistances per J3.11.

#### **1.4 Governing Utilisation**

$$
U_{\text{governing}} = \max \left( U_V,; U_T,; U_{\text{bear}} \right)
$$

---

### **2. Slip-Critical Bolts**

Slip-critical bolts require two sets of checks:

1. **Slip resistance at the faying surface**
2. **Bearing-type limit states after slip** (same as Section 1)

#### **2.1 Slip Resistance**

$$
U_{\text{slip}} = \frac{V_u}{\phi_{\text{slip}} R_{n,\text{slip}}}
$$
with
$$
R_{n,\text{slip}} = \mu D_u h_f T_b n_s k_{sc}
$$

The resistance factor $\phi_{\text{slip}}$ depends on hole type and load direction.

#### **2.2 Bearing-Type Strength After Slip**

Even for slip-critical bolts, the Specification requires the bolt to still satisfy the bearing limit states after slip occurs.
These utilisations are calculated exactly as in Section 1:

* $U_V$ (shear rupture)
* $U_T$ or interaction-based tension rupture
* $U_{\text{bear}}$ (bearing/tear-out)

#### **2.3 Governing Utilisation**

$$
U_{\text{governing}} = \max \left( U_{\text{slip}},; U_V,; U_T,; U_{\text{bear}} \right)
$$

---

### **3. Reporting Format**

For each bolt (or bolt group), the following values are reported in tabular form:

| Bolt ID | Connection Type | Shear Demand ($V_u$) | Tension Demand ($T_u$) | $U_V$ | $U_T$ | $U_{\text{bear}}$ | $U_{\text{slip}}$* | Governing Utilisation |
| ------- | --------------- | ------------------ | -------------------- | ----- | ----- | ----------------- | ------------------ | --------------------- |

*Only reported for slip-critical bolts; otherwise left blank or marked “–”.

---

### **4. Identification of Critical Bolt**

After completing all checks, the bolt with the **highest governing utilisation** is identified and flagged for design review or adjustment.


# Steel Designers Handbook 7th Edition

Below is a **Steel Designers Handbook–style section** that mirrors the structure, tone, and intent of your AISC section, but is aligned with **AS 4100 / Steel Designers Handbook (7th Ed.)** practice for **checks and reporting**.
It is written as a *design-method subsection* you can drop straight into your document.

---

Below is a **clean, corrected, and tightened rewrite** of your section.
I’ve kept your structure and intent, but:

* Fixed notation and formatting (AS 4100–style)
* Removed ambiguity about demands vs capacities
* Clarified serviceability vs strength intent
* Ensured utilisation definitions are consistent and unambiguous
* Made the language read like a **code commentary / handbook extract**, not API notes

This version is something you could reasonably include in a calculation methodology, design basis, or software documentation.

---

# AS 4100 — Steel Designers Handbook (7th Edition)

## Bolt Strength Checks and Reporting

This section defines the **verification and reporting procedure** for bolts and bolt groups in accordance with **AS 4100**, as interpreted and applied in the *Steel Designers Handbook (7th Edition)*.

The procedure applies to **high-strength structural bolts** in standard building connections and is valid for both **single bolts** and **bolt groups** subject to **in-plane** and/or **out-of-plane** actions.

---

## 1. Scope and Assumptions

The following assumptions are consistent with AS 4100 and the Steel Designers Handbook:

* Bolts are **high-strength structural bolts** (e.g. Property Class 8.8 or 10.9, or equivalent).
* Bolts are installed and tightened in accordance with the nominated **bolting category**:

  * Bearing-type (/S)
  * Tensioned bearing (/TB)
  * Friction-type (/TF)
* Connected plate elements are assumed **rigid at bolt locations** for the purpose of force distribution.
* Bolt group actions may be determined using **elastic superposition** or **instantaneous centre of rotation (ICR)** analysis.
* **Strength verification is performed on the most heavily loaded bolt(s)** in the group.
* **Prying action is not included** in the basic force analysis and must be accounted for separately where applicable.

---

## 2. Bolt-Level Design Actions

From bolt-group analysis (elastic or ICR), determine for each bolt ( i ):

* Design shear force:
  [
  V_i^*
  ]
* Design tensile force:
  [
  N_{ti}^*
  ]

For bolt groups:

* The **critical bolt** is defined as the bolt with the **maximum governing utilisation**.
* In many practical cases, this corresponds to the bolt **farthest from the centre of rotation** or neutral axis.

---

## 3. Strength Limit State Checks (AS 4100)

### 3.1 Bolt Shear Capacity

The **nominal bolt shear capacity** depends on whether the shear plane passes through threaded or unthreaded regions:

[
V_f
===

0.62,k_r f_{uf}
\left(
n_n A_c + n_x A_o
\right)
]

where:

* ( f_{uf} ) = minimum tensile strength of bolt material
* ( A_c ) = core (thread-root) area
* ( A_o ) = shank area
* ( n_n, n_x ) = number of shear planes through threaded and unthreaded regions
* ( k_r ) = reduction factor for long bolt lines

**Design requirement:**
[
V_i^* \le \phi V_f
\qquad \text{with } \phi = 0.8
]

---

### 3.2 Bolt Tension Capacity

The **nominal tensile capacity** of a bolt is:

[
N_{tf} = A_s f_{uf}
]

where ( A_s ) is the tensile stress area of the bolt.

**Design requirement:**
[
N_{ti}^* \le \phi N_{tf}
\qquad \text{with } \phi = 0.8
]

---

### 3.3 Combined Shear and Tension Interaction

Bolts subject to **simultaneous shear and tension** must satisfy the AS 4100 interaction requirement:

[
\left(
\frac{V_i^*}{\phi V_f}
\right)^2
+
\left(
\frac{N_{ti}^*}{\phi N_{tf}}
\right)^2
\le 1.0
]

This interaction governs the design of bolts in:

* Out-of-plane loaded bolt groups
* Eccentrically loaded connections
* Beam–column end-plate connections

---

### 3.4 Bearing and Tear-Out of Connected Material

Bolt design must also consider the **capacity of the connected plies**, which frequently governs.

#### (a) Bearing (Ply Crushing)

[
V_b = 3.2, t_p d_f f_{up}
]

#### (b) Tear-Out

[
V_p = a_e t_p f_{up}
]

where:

* ( t_p ) = plate thickness
* ( d_f ) = bolt diameter
* ( a_e ) = edge distance in the direction of load
* ( f_{up} ) = tensile strength of plate material

**Design requirements:**
[
V_i^* \le \phi V_b
\quad \text{and} \quad
V_i^* \le \phi V_p
\qquad \text{with } \phi = 0.9
]

The **governing ply capacity** is the lesser of bearing or tear-out.

---

## 4. Serviceability Limit State

### (Friction-Type /TF Bolts Only)

For friction-type connections where slip must be prevented, the **nominal slip resistance** is:

[
V_{sf} = \mu n_e N_{ti} k_h
]

where:

* ( \mu ) = friction coefficient
* ( n_e ) = number of shear planes
* ( N_{ti} ) = installed bolt pretension
* ( k_h ) = hole-type factor

**Design requirement:**
[
V_i^* \le \phi V_{sf}
\qquad \phi = 0.7
]

Even for friction-type connections, **all strength limit state checks in Section 3 must also be satisfied**.

---

## 5. Prying Action Allowance

AS 4100 does not explicitly model prying action.
The Steel Designers Handbook recommends allowing for increased bolt tension where prying is likely.

A practical allowance is:

[
N_{ti,\text{design}}
====================

(1+\alpha),N_{ti}^*
\qquad
\alpha = 0.20\text{–}0.33
]

Prying action may be minimised by:

* Increasing bolt spacing (≥ 90 mm)
* Increasing end-plate thickness (≥ (1.25d))
* Providing end-plate stiffeners

---

## 6. Utilisation Calculations

For each bolt ( i ), the following utilisation ratios are evaluated.

### 6.1 Individual Utilisations

* **Shear utilisation**
  [
  U_{V,i} = \frac{V_i^*}{\phi V_f}
  ]

* **Tension utilisation**
  [
  U_{T,i} = \frac{N_{ti}^*}{\phi N_{tf}}
  ]

* **Bearing / tear-out utilisation**
  [
  U_{\text{bear},i}
  =================

  \frac{V_i^*}{\phi \min(V_b, V_p)}
  ]

* **Shear–tension interaction utilisation**
  [
  U_{\text{int},i}
  ================

  \left(
  \frac{V_i^*}{\phi V_f}
  \right)^2
  +
  \left(
  \frac{N_{ti}^*}{\phi N_{tf}}
  \right)^2
  ]

---

### 6.2 Governing Utilisation

[
U_{\text{governing},i}
======================

\max
\left(
U_{V,i},
U_{T,i},
U_{\text{bear},i},
U_{\text{int},i}
\right)
]

---

## 7. Reporting Format

Results are reported **per bolt**, with the governing bolt clearly identified.

| Bolt ID | (V_i^*) | (N_{ti}^*) | (U_V) | (U_T) | (U_{\text{bear}}) | (U_{\text{int}}) | Governing Utilisation |
| ------- | ------- | ---------- | ----- | ----- | ----------------- | ---------------- | --------------------- |

---

## 8. Identification of Critical Bolt

The bolt with the **maximum governing utilisation** is designated the **critical bolt** and controls:

* Bolt size and grade
* Number of bolts
* Plate thickness and detailing

This approach is consistent with Steel Designers Handbook guidance that **verification of the most heavily loaded bolt is sufficient to confirm the adequacy of the bolt group**.

---

If you want next, I can:

* Strip this down into a **formal “Design Basis” appendix**
* Align clause references **line-by-line to AS 4100**
* Or translate this directly into **software-ready pseudocode** that matches your `connecty` API exactly




