This document defines the bolt design checks implemented in `connecty` and the assumptions used to map analysis outputs (per-bolt forces) into code-based utilisations.

All checks are **unit agnostic**: use any consistent set of units (e.g. mm, N, N·mm).

## Current API

```python
from connecty import BoltConnection, BoltGroup, Plate, Load

bg = BoltGroup.from_pattern(rows=3, cols=2, spacing_y=75, spacing_z=60, diameter=20, grade="A325")
plate = Plate.from_dimensions(width=250, height=160, center=(0, 0), thickness=12, fu=450, fy=350)
conn = BoltConnection(bolt_group=bg, plate=plate, n_shear_planes=1)

load = Load(Fy=-120_000, Fz=25_000, location=(0, 40, 80))
res = conn.analyze(load, shear_method="elastic", tension_method="accurate")

check = res.check(standard="aisc", connection_type="bearing")
print(check.governing_utilization)
print(check.info)  # includes method + per-bolt details + intermediate calc terms
```

---

# AISC 360-22 (LRFD)

## Scope / assumptions

- Bolt grades supported by the AISC implementation: **A325**, **A490**
- Per-bolt demands come from bolt-group analysis:
  - $V_u = \sqrt{F_y^2 + F_z^2}$
  - $T_u = \max(F_x, 0)$ (**compression is ignored** for bolt tension rupture checks)
- $n_s$ = **number of shear planes** (and, for slip-critical joints, **number of slip planes**)
  - In `connecty`, if `n_s` is not provided, it defaults to `BoltConnection.n_shear_planes`.

## Tables used by `connecty` (AISC excerpt)

### Table J3.1 (kN) — Minimum pretension (excerpt)
| Bolt Size (mm) | Group 120 (A325) | Group 150 (A490) |
|---|---:|---:|
| M12 | 49 | 72 |
| M16 | 91 | 114 |
| M20 | 142 | 179 |
| M22 | 176 | 221 |
| M24 | 205 | 257 |
| M27 | 267 | 334 |
| M30 | 326 | 408 |
| M36 | 475 | 595 |

### Table J3.2 — Nominal stresses (MPa)
| Grade | $F_{nt}$ | $F_{nv}$ (threads **included**) | $F_{nv}$ (threads **excluded**) |
|---|---:|---:|---:|
| A325 | 620 | 370 | 470 |
| A490 | 780 | 470 | 580 |

### Table J3.3 — Standard hole diameters (mm) (excerpt)
| Bolt Diameter | Standard | Oversize | Short-slot width | Long-slot width |
|---|---:|---:|---:|---:|
| M12 | 14 | 16 | 14 | 14 |
| M16 | 18 | 20 | 18 | 18 |
| M20 | 22 | 24 | 22 | 22 |
| M22 | 24 | 28 | 24 | 24 |
| M24 | 27 | 30 | 27 | 27 |
| M27 | 30 | 35 | 30 | 30 |
| M30 | 33 | 38 | 33 | 33 |

## Strength checks implemented

### 1) Shear rupture — J3.6

- $\phi = 0.75$
- $A_b = \pi d^2/4$
- Nominal: $R_{n,V} = F_{nv} A_b n_s$
- Design: $\phi R_{n,V}$

### 2) Tension rupture (with shear interaction) — J3.6 / J3.7

- $\phi = 0.75$
- Base nominal: $R_{n,T} = F_{nt} A_b$
- If combined shear–tension applies, `connecty` uses:

$$
F'_{nt} = \min\!\left(F_{nt},\ 1.3F_{nt} - \frac{F_{nt}}{\phi F_{nv}} f_{rv}\right),\quad F'_{nt}\ge 0
$$

where the **per-plane** bolt shear stress is:

$$
f_{rv} = \frac{V_u}{A_b n_s}
$$

and then:

$$
\phi R'_{n,T} = \phi F'_{nt} A_b
$$

### 3) Bearing / tearout of connected material — J3.10

- $\phi = 0.75$
- Standard hole bearing / tearout (deformation at bolt hole considered):

$$
R_{n,\text{bearing}} = 2.4 d t F_u,\quad
R_{n,\text{tearout}} = 1.2 l_c t F_u,\quad
R_n = \min(R_{n,\text{bearing}}, R_{n,\text{tearout}})
$$

`connecty` computes $l_c$ as the **minimum clear edge distance** from the **hole edge** to any plate edge (conservative):

$$
l_c = \min\left(|y-y_\text{edge}| - d_h/2,\ |z-z_\text{edge}| - d_h/2\right)
$$

**Note on edge distance definition**

AISC 360-22 defines the clear distance $l_c$ in the **direction of the applied force**.  
For simplicity and conservatism, `connecty` instead uses the **minimum clear distance from the hole edge to any plate edge**, regardless of force direction.

This approach may result in lower reported bearing or tear-out capacities compared to hand calculations that consider force direction explicitly.

**Software Note:** Because `connecty` uses the minimum clear distance to **any** edge, the reported utilization may be significantly higher than a manual check if the shear force is directed away from the closest edge. Users should verify the force direction if bearing or tear-out governs the design.

### 4) Slip resistance (slip-critical joints) — J3.8 / J3.9

When `connection_type="slip-critical"`, `connecty` evaluates slip in addition to the bearing-type limit states:

$$
\phi_{\text{slip}} R_{n,\text{slip}}
= \phi_{\text{slip}}\,\mu\,D_u\,h_f\,T_b\,n_s\,k_{sc}
$$

with:
- $D_u = 1.13$
- $h_f = 1.0$ for 0–1 filler, $h_f = 0.85$ for $\ge 2$ fillers
- $\mu$ from slip class (A: 0.30, B: 0.50)
- $\phi_{\text{slip}}$ depends on hole type / slot orientation:
  - standard: 1.00
  - oversize: 0.85
  - short-slotted: 1.00 (perpendicular), 0.85 (parallel)
  - long-slotted: 0.70

and:

$$
k_{sc} = \max\left(0,\ 1 - \frac{T_u}{D_u T_b}\right)
$$

where $T_u$ is the **per-bolt** tension demand for that bolt (from the bolt-group analysis output).

## Utilisations reported by `connecty`

For each bolt:
- Shear: $U_V = V_u / (\phi R_{n,V})$
- Tension: $U_T = T_u / (\phi R'_{n,T})$
- Bearing/tearout: $U_\text{bear} = V_u / (\phi R_n)$
- Slip (if applicable): $U_\text{slip} = V_u / (\phi_{\text{slip}} R_{n,\text{slip}})$

The governing utilisation is the maximum across applicable limit states.

---

# AS 4100 / Steel Designers Handbook (7th Ed.)

## Scope / assumptions

- Bolt grades supported by the AS 4100 implementation: **8.8**, **10.9**
- Per-bolt demands come from bolt-group analysis:
  - $V^* = \sqrt{F_y^2 + F_z^2}$
  - $N_t^* = \max(F_x, 0)$
- Optional prying allowance (approximate):
  - `connecty` applies:
    $$
    N_{t,\text{design}}^* = (1+\alpha)\,N_t^*
    $$
    for $N_t^*>0$, where $\alpha$ = `prying_allowance` (default 0.25).

  - This is a **simplified, handbook-based approximation** (e.g. Steel Designers Handbook) and does **not** represent a full prying force calculation per AS 4100 Clause 9.1.2.2.

  - **Warning:** The 0.25 prying factor is a simplified approximation. For connections with thin, flexible end plates, prying forces can exceed this estimate. Users are responsible for validating this factor per AS 4100 Clause 9.1.2.2 for specific geometries.

  - Users may override or disable this factor where a more detailed prying analysis is required.

## Strength checks implemented

### 1) Bolt shear capacity

$$
V_f = 0.62\,k_r\,f_{uf}\left(n_n A_c + n_x A_o\right)
$$

and `connecty` applies:

$$
\phi V_f,\quad \phi = 0.8
$$

Inputs:
- `reduction_factor_kr` = $k_r$
- `nn_shear_planes` = $n_n$, `nx_shear_planes` = $n_x$
- $A_c, A_o$ from grade tables (threaded core and shank areas)

### 2) Bolt tension capacity

$$
N_{tf} = A_s f_{uf},\quad \phi N_{tf},\ \phi = 0.8
$$

$A_s$ from grade tables (tensile stress area).

### 3) Combined shear + tension interaction

`connecty` reports an interaction utilisation:

$$
U_\text{int} =
\left(\frac{V^*}{\phi V_f}\right)^2
+
\left(\frac{N_{t,\text{design}}^*}{\phi N_{tf}}\right)^2
$$

The AS 4100 interaction requirement is $U_\text{int} \le 1.0$.

### 4) Bearing / tear-out of connected material

`connecty` implements:

$$
V_b = 3.2\,t_p\,d_f\,f_{up},\quad
V_p = a_e\,t_p\,f_{up}
$$

and uses the design capacity:

$$
0.9\,\min(V_b, V_p)
$$

where:

- $a_e$ = **minimum clear distance from the edge of the bolt hole to the adjacent plate edge**, in accordance with AS 4100:2020 Clause 9.3.2.4
- $a_e$ is computed as:

$$
a_e = \min(\text{edge\_clear}) - \frac{d_h}{2}
$$

This definition aligns with the Standard and avoids unconservative overestimation of tear-out capacity.

### 5) Friction (slip resistance)

When `connection_type="friction"`, `connecty` uses:

$$
\phi V_{sf} = 0.7\,\mu\,n_e\,T_b\,k_h
$$

where:
- $\mu$ is `slip_coefficient`
- $n_e$ is number of friction interfaces (`n_e`)
- $T_b$ is bolt pretension from internal tables (or `pretension_override`)
- $k_h$ is `hole_type_factor`

# Code Deviations and Conservative Assumptions

The following intentional deviations and simplifications are applied in `connecty` for robustness, clarity, and software practicality:

## General
- All checks are performed on a **per-bolt basis**, which may be conservative where codes permit force redistribution.
- Bolt compression is ignored in tension rupture checks.

## AISC 360-22
- Bearing and tear-out edge distance $l_c$ is taken as the **minimum clear distance to any plate edge**, rather than the force-direction-specific distance defined in the Standard.
- Slip resistance is evaluated per bolt using resultant shear demand.

## AS 4100
- Prying forces are approximated using a fixed multiplier rather than an explicit flexibility-based calculation.
- Tear-out edge distance $a_e$ is taken from the **edge of the hole**, consistent with Clause 9.3.2.4.

These choices are conservative unless otherwise noted and are documented to ensure transparent interpretation of reported utilisations.