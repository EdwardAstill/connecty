## New API (refined spec)

### Goals
- **Consistent model**: `Connection` + `Load` → `Result` → `CheckResult`
- **Unit-agnostic**: Connecty never assumes a unit system. Outputs are in the same derived units as inputs.
  - If inputs are force + length, then stresses are in (force / length²).
  - If you input stresses, you get forces back in (stress · length²).
- **Bolts are 2D** (planar bolt layouts only).
- **Plate is bolt-only** and is used for:
  - out-of-plane effects (tension / prying / whatever out-of-plane model is supported)
  - bearing checks
  - tear-out / block shear style checks (as implemented)

---

## Shared

### `Load`
Single load object used by both bolts and welds.

- **Fields**: `Fx, Fy, Fz, Mx, My, Mz: float`, `location: tuple[float, float, float]`
- **Method**: `equivalent_at(location) -> Load`
  - Returns an equivalent load at the new location (forces unchanged; moments transferred).

---

## Bolts

### `BoltLayout` (formerly `BoltGroup` / `BoltPlacement`)
Geometry/layout only. **2D only**.

- **Fields**:
  - `points: list[tuple[float, float]]`  # (y, z)
- **Notes**:
  - No diameter here.

### `BoltParams`
Bolt properties + size.

- **Fields**:
  - `grade: str | None`
  - `diameter: float`
  - `fy: float | None`  # derived from grade if not specified
  - `fu: float | None`  # derived from grade if not specified

### `Plate` (bolt-only)
As-is, but used only in bolt checks/models that need out-of-plane + bearing + tear-out.

### `BoltConnection`
- **Fields**:
  - `layout: BoltLayout`
  - `bolt: BoltParams`
  - `plate: Plate | None`
  - `n_shear_planes: int`
- **Method**:
  - `analyze(load: Load, *, shear_method: Literal["elastic","icr"], tension_method: Literal["conservative","accurate"]) -> BoltResult`

### `BoltResult`
- **Fields**:
  - `connection: BoltConnection`
  - `load: Load`
  - `shear_method: Literal["elastic","icr"]`
  - `tension_method: Literal["conservative","accurate"]`
- **Method**:
  - `check(...)` (same concept as current; attaches to result)

---

## Welds

### `WeldParams`
Defines weld type/size and strength source.

- **Fields**:
  - `type: Literal["fillet","cjp","pjp","plug","slot"]`
  - `leg: float | None`
  - `throat: float | None`  # derived if needed/possible
  - `electrode: str | None`
  - `F_EXX: float | None`  # if not provided, derive from electrode (if given)

### `WeldConnection` (formerly “Weld”)
- **Fields**:
  - `params: WeldParams`
  - `path: Geometry/Path object` (contours need not be closed)
  - `base_metal: WeldBaseMetal | None` (only if checks require it)
  - flags like `is_double_fillet`, `is_rect_hss_end_connection` (as currently supported)
- **Method**:
  - `analyze(load: Load, *, method: Literal["elastic","icr"], discretization: int = 200) -> WeldResult`

### `WeldResult`
- **Fields**:
  - `connection: WeldConnection`
  - `load: Load`
  - `method: Literal["elastic","icr"]`
- **Method**:
  - `check(...)` (same concept as current; attaches to result)

---

## Checks (both bolts and welds)
- Checks attach to `BoltResult` / `WeldResult`.
- Output structure stays aligned with current approach:
  - `details: list[...]`
  - `governing_utilization`
  - `governing_limit_state`