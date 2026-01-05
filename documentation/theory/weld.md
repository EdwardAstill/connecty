# Weld Group Theory

## Overview
In `connecty`, weld analysis returns **stress** along the weld path (not discrete forces). The weld group lives in the $y$-$z$ plane and is discretized into small segments; stresses are computed at each segment midpoint.

## Coordinate system (matches `connecty.common.load.Load`)
- $x$: out-of-plane (axial), $+F_x$ = tension
- $y$: vertical in plane, $+F_y$ = up
- $z$: horizontal in plane, $+F_z$ = right
- $+M_x$: CCW when viewed from $+x$
- $+M_y$: causes tension on the $+z$ side
- $+M_z$: causes tension on the $+y$ side

## Weld types and supported analysis methods (`connecty`)
| Weld type (`WeldParams.type`) | Analysis methods | Key geometry input | Notes |
| --- | --- | --- | --- |
| `fillet` | `elastic`, `icr` | Leg $w$ (and throat $a=0.707w$) | ICR is AISC-preferred for planar in-plane loading |
| `pjp` | `elastic` | Effective throat $a$ | Stress-based elastic method only |
| `cjp` | `elastic` | Plate thickness $t$ (and throat/area as modeled) | In design, capacity is often governed by base metal rather than weld metal |
| `plug` / `slot` | `elastic` | Area $A$ | Uses provided area directly |

## Elastic method (stress-based, conservative)
The elastic method assumes stress is proportional to deformation and superposition applies. `connecty` computes stresses at discretized points along the weld and reports the resultant stress magnitude.

### Geometry and section properties
For line welds (fillet / PJP / CJP), define:
- $L$: total weld length
- $a$: effective throat
- $A = aL$: total effective weld area

The weld-group centroid $(C_y, C_z)$ and moments $(I_y, I_z, I_p)$ are computed about the centroid using the weld area weighting $dA=a\,ds$ (so for constant throat, it is equivalent to length weighting).

**Note on CJP welds**: For Complete Joint Penetration (CJP) welds, the effective throat $a$ is typically taken as the plate thickness $t_{\text{plate}}$. Ensure consistency in your input: the capacity of CJP welds is often governed by base-metal rather than weld-metal properties.

### Stress components (matches `connecty.weld.weld_stress.calculate_elastic_stress`)
Evaluate the applied moments about the weld centroid:

$$
(M_{x,\text{total}},M_{y,\text{total}},M_{z,\text{total}})=\texttt{Load.get\_moments\_about}(0,C_y,C_z)
$$

At a weld point $(y,z)$, define $\Delta y = y-C_y$ and $\Delta z = z-C_z$.

**In-plane (shear) stress**
- Direct shear (uniform):

$$
f_{y,\text{direct}}=\frac{F_y}{A},\qquad f_{z,\text{direct}}=\frac{F_z}{A}
$$

- Torsion about $x$ (perpendicular to the radius, linear with distance):

$$
f_{y,\text{moment}}=-\frac{M_{x,\text{total}}\Delta z}{I_p},\qquad
f_{z,\text{moment}}=-\frac{M_{x,\text{total}}\Delta y}{I_p}
$$

**Out-of-plane (normal) stress**
- Direct axial (uniform):

$$
f_{x,\text{axial}}=\frac{F_x}{A}
$$

- Bending (linear with distance):

$$
f_{x,\text{bend}}=\frac{M_{y,\text{total}}\Delta z}{I_y}+\frac{M_{z,\text{total}}\Delta y}{I_z}
$$

**Resultants**

$$
f_y=f_{y,\text{direct}}+f_{y,\text{moment}},\qquad
f_z=f_{z,\text{direct}}+f_{z,\text{moment}},\qquad
f_x=f_{x,\text{axial}}+f_{x,\text{bend}}
$$

$$
f_\text{resultant}=\sqrt{f_x^2+f_y^2+f_z^2}
$$

> **Note**: The above expressions for $f_y$, $f_z$, $f_x$ are vector components at a specific point along the weld. The peak resultant stress may not necessarily occur at the point of maximum individual component stress, although for elastic groups it typically does at the corners or extrema.

> The elastic method supports 3D loading $(F_x,F_y,F_z,M_x,M_y,M_z)$.

## Instantaneous center of rotation (ICR) method (fillet welds, in-plane only)
The ICR method uses AISC’s curved load–deformation relationship for fillet welds, and iteratively finds the instantaneous center of rotation (ICR) that satisfies equilibrium.

### Scope (important)
In `connecty`, the ICR weld solver is **only** valid for:
- `fillet` welds, and
- **planar in-plane loading only**: $F_y$, $F_z$, and torsion $M_x$

If $F_x$, $M_y$, or $M_z$ are present, `connecty` raises an error and you should use the elastic method.

### Angle definition
At each discretized weld point, define $\theta$ as the angle (degrees) between:
- the local in-plane resultant direction, and
- the local weld axis (tangent direction).

Thus $\theta=0^\circ$ is “parallel to the weld axis” and $\theta=90^\circ$ is “transverse”.

### Deformation limits (AISC; matches `connecty.common.icr_solver.aisc_weld_deformation_limits`)

$$
\Delta_m = 0.209 (\theta + 2)^{-0.32} w
$$

$$
\Delta_u = \min\left(0.17 w,\ 1.087 (\theta + 6)^{-0.65} w\right)
$$

Where $w$ is the fillet leg size.

### Stress–deformation model (AISC; matches `connecty.common.icr_solver.aisc_weld_stress`)
Directional strength factor:

$$
k_{ds}=1.0+0.5\sin^{1.5}\theta
$$

Normalized deformation:

$$
p=\frac{\Delta}{\Delta_m}
$$

Weld stress:

$$
f_w = 0.60 F_{EXX}\,k_{ds}\,[p(1.9-0.9p)]^{0.3}
$$

In `connecty`, $\Delta$ is clamped to $\Delta_u$ before computing $p$.

### Force equilibrium
For a weld segment of length $ds$ and effective throat $a$, the segment force magnitude is:

$$
R=f_w\,a\,ds
$$

For a trial ICR, let $c$ be the distance from the ICR to the segment point. The governing rotation parameter is:

$$
\lambda=\min\left(\frac{\Delta_u}{c}\right)
$$

Then:

$$
\Delta=\min(\lambda c,\Delta_u)
$$

`connecty` searches for the ICR along a line through the weld centroid perpendicular to the applied shear resultant, and iterates until the computed moment-to-shear ratio matches the applied target $M_x/P$, where $P=\sqrt{F_y^2+F_z^2}$. The final stresses are scaled so the resultant shear equilibrates the applied shear magnitude.

## Notes
- `connecty` is unit-agnostic: keep units consistent (e.g., N–mm–MPa or kN–m–MPa).
- For some AISC detailing cases (e.g., rectangular HSS end connections), `connecty` can disable the directional strength benefit ($k_{ds}=1$) via the `is_rect_hss_end_connection` flag on the connection.


