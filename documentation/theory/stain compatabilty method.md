
## Simple steps
1. Your targets are the **ratio** and **magnitude** of the moments about the origin.

2. Assume an angle $\theta$ for the Neutral Axis (NA).

3. For that $\theta$, find $c$ (NA offset) that balances the axial forces (i.e. $\sum F_z(\theta,c) \approx P_\text{target}$ within tolerance). The relative forces are proportional to **signed distance** from the NA (linear elastic assumption), so you can compute them and slide $c$ until force equilibrium is met.

4. With that balanced NA, compute internal moments about the origin. Compare the ratio $M_y/M_x$ to your target. If the ratio is off, change $\theta$ and repeat Step 3.

5. Once the ratio matches, **scale** the relative forces so the internal moment magnitude matches your target (only valid for a linear elastic model).

## In depth:

### Strain-compatibility (fiber) method for base plates with **(P\neq 0)**

You are solving for the **neutral axis orientation**, **neutral axis offset**, and a **scale factor** that converts “distance-to-NA” into actual separation/strain.

---

## 0) Inputs and conventions

* Geometry points:

  * **Bolts/anchors** at ((x_b,y_b)), tension-only, stiffness (k_b) (force/length)
  * **Bearing cells** at ((x_i,y_i)), compression-only, stiffness (k_i) (force/length)
* Target actions about the origin:
  [
  P_\text{target},\quad M_{x,\text{target}},\quad M_{y,\text{target}}
  ]
* Neutral axis definition:

  * unit normal (n=(\cos\theta,\sin\theta))
  * signed distance:
    [
    d(x,y)=n\cdot r - c=\cos\theta,x+\sin\theta,y-c
    ]
  * (d>0): tension side, (d<0): compression side

---

## 1) Unknowns you solve for

You solve **three** unknowns:

* (\theta) = NA angle
* (c) = NA offset
* (s) = **scale factor** (converts distance to “elongation/separation”)

Interpretation:
[
\delta_i = s, d_i
]
and the point force is
[
F_i = k_i,\delta_i = s,k_i,d_i
]

---

## 2) Force model with tension/compression gating

For each point, compute (d_i) and then:

* **Bolt (tension only)**:
  [
  F_b =
  \begin{cases}
  s,k_b,d_b & d_b>0\
  0 & d_b\le 0
  \end{cases}
  ]

* **Bearing cell (compression only)**:
  [
  F_i =
  \begin{cases}
  s,k_i,d_i & d_i<0 \quad(\text{negative force})\
  0 & d_i\ge 0
  \end{cases}
  ]

---

## 3) Equilibrium equations (what must match)

### Axial equilibrium

[
\sum F_i(\theta,c,s) = P_\text{target}
]

### Moment equilibrium (about the origin, consistent sign convention)

With axial forces (F_z):
[
M_x(\theta,c,s)=\sum y_i,F_i
]
[
M_y(\theta,c,s)=\sum (-x_i),F_i
]

Targets:
[
M_x(\theta,c,s)=M_{x,\text{target}},\quad
M_y(\theta,c,s)=M_{y,\text{target}}
]

---

## 4) How the **scale factor (s)** is handled properly when (P\neq0)

Key point: for a fixed ((\theta,c)), forces are **linear in (s)**, so you can solve (s) directly from axial equilibrium.

1. Compute **unit-scale** forces with (s=1):
   [
   F_i^{(1)}(\theta,c) = k_i,d_i ;;(\text{with gating})
   ]
   and:
   [
   S(\theta,c)=\sum F_i^{(1)}(\theta,c)
   ]

2. Solve scale from axial force:
   [
   s(\theta,c)=\frac{P_\text{target}}{S(\theta,c)}
   ]
   (If (S(\theta,c)\approx 0), that ((\theta,c)) can’t support the required (P).)

3. Now compute scaled moments:
   [
   M_x(\theta,c)= s(\theta,c),M_x^{(1)}(\theta,c)
   ]
   [
   M_y(\theta,c)= s(\theta,c),M_y^{(1)}(\theta,c)
   ]

So for (P\neq0), **you do not “scale at the end”**. You compute (s) **inside** the search, from (P).

---

## 5) Solution procedure (digestible version)

1. **Pick a trial (\theta)** (scan or use an optimizer).
2. **Search (c)** (bracket + bisection or 1D solver):

   * Compute (S(\theta,c)=\sum F^{(1)}) with (s=1)
   * Compute (s=P_\text{target}/S(\theta,c)) (skip if (S\approx 0))
   * Compute (M_x(\theta,c), M_y(\theta,c)) using scaled forces
3. **Check moment match**:

   * Either match both components:
     [
     M_x(\theta,c)\approx M_{x,\text{target}},\quad
     M_y(\theta,c)\approx M_{y,\text{target}}
     ]
   * Or minimize the vector error (|(M_x,M_y)-(M_{x,t},M_{y,t})|)
4. Iterate (\theta) (and (c)) until moments match within tolerance.
5. With final ((\theta,c,s)), compute **final bolt forces** and **bearing pressures** using:
   [
   F_i = s,k_i,d_i \quad \text{(with gating)}
   ]

---

## 6) Special case: (P_\text{target}=0)

If (P=0), axial equilibrium does **not** determine (s) (it would be (0/0) style). Then you can:

* find ((\theta,c)) from (\sum F^{(1)}=0) and moment **direction**, and
* set (s) from moment **magnitude** at the end:
  [
  s=\frac{|M_\text{target}|}{|M^{(1)}|}
  ]

---

If you want, I can express this as a short “implementation checklist” (what functions you need and what each returns) matching your current code structure.


---

## Recommended optimization (faster + more accurate)

The nested scan over $\theta$ and $c$ is easy to implement but can be slow and can miss solutions between step sizes.

A better approach is to solve for $(\theta, c)$ using a root-finder:

- Unknowns: $[\theta, c]$ (or $[\theta,c,s]$ if $P_\text{target}\ne 0$ and you need exact magnitudes)
- Residuals:
  - $R_1(\theta,c) = \sum F_z(\theta,c) - P_\text{target}$
  - $R_2(\theta,c) = \operatorname{wrap}\big(\operatorname{atan2}(M_y,M_x)-\operatorname{atan2}(M_{y,\text{target}},M_{x,\text{target}})\big)$

This removes the need for a coarse angle step like 1° and reduces “flip” mistakes by forcing you to make signs explicit in the residuals.

#### Inner solve for $c$: bracket + bisection (robust)

For fixed $\theta$, $\sum F_z(\theta,c)$ is typically **piecewise linear** in $c$ (active set changes when points cross the NA). A bracketed bisection on $c$ is usually more reliable than scanning a range with steps.

---

## Coordinate origin check (don’t mix origins)

When you say “moments about the origin”, ensure that the origin $(0,0)$ used for the geometry is **exactly** the point about which $M_\text{target}$ is defined (plate centroid vs load point vs column centroid). If not, shift moments/coordinates appropriately before comparing.

---
```

## Pseudo code
# ============================================================
# STRAIN COMPATIBILITY / FIBER METHOD (P != 0)
# Unknowns ultimately returned: theta, c, s
#   theta = NA angle (rad or deg, be consistent)
#   c     = NA offset
#   s     = scale factor mapping distance -> elongation: delta = s*d
# ============================================================


# -----------------------------
# DATA
# -----------------------------
# bolts: list of points with (x, y, k)   # tension-only
# cells: list of points with (x, y, k)   # compression-only
# targets: P_target, Mx_target, My_target


# -----------------------------
# FUNC: signed distance to NA
# -----------------------------
FUNC distance_to_NA(x, y, theta, c):
    # d = n·r - c, n=(cos theta, sin theta)
    RETURN cos(theta)*x + sin(theta)*y - c


# ---------------------------------------------------
# FUNC: unit-scale forces + unit-scale moments (s=1)
# ---------------------------------------------------
FUNC unit_forces_and_unit_moments(theta, c, bolts, cells):
    S    = 0      # sum of axial forces at s=1
    Mx1  = 0      # moment about x at s=1
    My1  = 0      # moment about y at s=1
    F1s  = []     # store per-point unit forces if needed

    # bolts: tension-only (d>0)
    FOR b IN bolts:
        d = distance_to_NA(b.x, b.y, theta, c)
        IF d > 0:
            F1 = b.k * d      # positive
        ELSE:
            F1 = 0
        S   += F1
        Mx1 += b.y * F1
        My1 += -b.x * F1
        APPEND (b.x, b.y, F1, "bolt") TO F1s

    # cells: compression-only (d<0)
    FOR cell IN cells:
        d = distance_to_NA(cell.x, cell.y, theta, c)
        IF d < 0:
            F1 = cell.k * d   # negative because d<0
        ELSE:
            F1 = 0
        S   += F1
        Mx1 += cell.y * F1
        My1 += -cell.x * F1
        APPEND (cell.x, cell.y, F1, "cell") TO F1s

    RETURN S, Mx1, My1, F1s


# ------------------------------------------
# FUNC: compute scale factor from axial load
# ------------------------------------------
FUNC scale_from_axial(P_target, S, tiny):
    # Axial equilibrium: sum(F) = P_target
    # But F = s * F1  => sum(F) = s * S
    IF abs(S) < tiny:
        RETURN None   # cannot determine s (NA position cannot carry P)
    RETURN P_target / S


# ---------------------------------------
# FUNC: moments after applying scale factor
# ---------------------------------------
FUNC scaled_moments(Mx1, My1, s):
    RETURN s*Mx1, s*My1


# -------------------------------------------
# FUNC: scalar error measuring moment mismatch
# -------------------------------------------
FUNC moment_error(Mx, My, Mx_target, My_target):
    # vector magnitude error
    RETURN sqrt((Mx - Mx_target)^2 + (My - My_target)^2)


# -----------------------------------------------------------
# FUNC: compute search bounds for c at a given theta (geometry)
# -----------------------------------------------------------
FUNC c_bounds(theta, bolts, cells, margin):
    # project all points onto NA normal to get a reasonable c range
    projs = []
    FOR p IN (bolts + cells):
        projs.append(cos(theta)*p.x + sin(theta)*p.y)
    c_min = min(projs) - margin
    c_max = max(projs) + margin
    RETURN c_min, c_max


# ----------------------------------------
# FUNC: coarse scan to get a good initial c
# ----------------------------------------
FUNC coarse_best_c(theta, bolts, cells, P_target, Mx_target, My_target,
                  N, c_min, c_max, tiny):
    best_c   = None
    best_err = +infinity

    FOR c IN linspace(c_min, c_max, N):
        S, Mx1, My1, _ = unit_forces_and_unit_moments(theta, c, bolts, cells)
        s = scale_from_axial(P_target, S, tiny)
        IF s IS None:
            CONTINUE

        Mx, My = scaled_moments(Mx1, My1, s)
        err = moment_error(Mx, My, Mx_target, My_target)

        IF err < best_err:
            best_err = err
            best_c = c

    RETURN best_c, best_err



# ==========================
# MAIN SOLVER
# ==========================
FUNC solve_NA_with_axial(bolts, cells, P_target, Mx_target, My_target,
                        theta_search, N, margin, tiny):

    best_solution = None
    best_error = +infinity

    FOR theta IN theta_search:

        # 1) pick c search interval from geometry
        c_min, c_max = c_bounds(theta, bolts, cells, margin)

        # 2) coarse scan for a good starting c
        c0, err0 = coarse_best_c(theta, bolts, cells,
                                 P_target, Mx_target, My_target,
                                 N, c_min, c_max, tiny)
        IF c0 IS None:
            CONTINUE

        # 3) evaluate final at (theta, c_star)
        S, Mx1, My1, F1s = unit_forces_and_unit_moments(theta, c_star, bolts, cells)
        s = scale_from_axial(P_target, S, tiny)
        IF s IS None:
            CONTINUE

        Mx, My = scaled_moments(Mx1, My1, s)
        err = moment_error(Mx, My, Mx_target, My_target)

        IF err < best_error:
            best_error = err
            best_solution = (theta, c_star, s, F1s)

    IF best_solution IS None:
        RAISE "No solution found"

    theta_sol, c_sol, s_sol, F1s = best_solution

    # 4) final forces = s * unit forces
    forces_final = []
    FOR (x, y, F1, kind) IN F1s:
        APPEND (x, y, s_sol*F1, kind) TO forces_final

    RETURN theta_sol, c_sol, s_sol, forces_final

```




