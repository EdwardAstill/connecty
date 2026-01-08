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

### `BoltLayout`
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

- **Fields**:
  - `corner_a: tuple[float, float]` (top-left / bottom-right coordinates)
  - `corner_b: tuple[float, float]`
  - `thickness: float`
  - `fu: float`
  - `fy: float | None`
  - `hole_type: Literal["standard", "oversize", "short-slot", "long-slot"]` (default "standard")
  - `hole_orientation: float | None` (angle in degrees, default None)
  - `surface_class: Literal["A", "B"] | None` (default None)
  - `slip_coefficient: float | None` (derived from surface_class if None)



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
  - `bolt_forces: Dict[str, list[float]]`
  - `shear_method: Literal["elastic","icr"]`
  - `tension_method: Literal["conservative","accurate"]`

  Bolt forces should look like this:
  {"Fx": [float, float, float, ...], "Fy": [float, float, float, ...], "Fz": [float, float, float, ...]}
  where the list index corresponds to the bolt index.
  
- **Method**:
  - `check_aisc(...)` -> `Dict`
  - `check_as4100(...)` -> `Dict`

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

### `WeldConnection`
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
  - `check_aisc(...)` -> `Dict`
  - `check_as4100(...)` -> `Dict`

---

