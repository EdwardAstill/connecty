"""WeldResult: a WeldConnection subjected to a Load, with calculated weld stresses."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..common.load import Load
from .geometry import WeldConnection, WeldMethod
from .loaded_weld import LoadedWeld
from .weld import Weld


@dataclass
class WeldResult:
    """A `WeldConnection` subjected to a `Load`, with calculated weld stresses."""

    connection: WeldConnection
    load: Load
    method: WeldMethod = "elastic"
    discretization: int = 200

    _analysis: LoadedWeld = field(init=False, repr=False)

    def __post_init__(self) -> None:
        # Provide a strength scale for ICR when available (unit-agnostic).
        # - Prefer an explicit WeldParams.F_EXX if provided
        # - Else, if base metal is provided, default to matching-electrode assumption: F_EXX = Fu
        # - Else, leave None and let the analysis engine fall back
        F_EXX: float | None
        if self.connection.params.F_EXX is not None:
            F_EXX = float(self.connection.params.F_EXX)
        elif self.connection.base_metal is not None:
            F_EXX = float(self.connection.base_metal.fu)
        else:
            F_EXX = None

        # If HSS end-connection restriction applies, disable directional strength increase in ICR.
        include_kds = not bool(self.connection.is_rect_hss_end_connection)

        self._analysis = LoadedWeld(
            weld=self.connection.weld,
            load=self.load,
            method=self.method,
            discretization=self.discretization,
            F_EXX=F_EXX,
            include_kds=include_kds,
        )

    @property
    def weld(self) -> Weld:
        return self.connection.weld

    @property
    def analysis(self) -> LoadedWeld:
        """Underlying pointwise stress result (`LoadedWeld`)."""
        return self._analysis

    # --- Convenience (bolt-like) ---
    @property
    def max_stress(self) -> float:
        return float(self._analysis.max)

    @property
    def min_stress(self) -> float:
        return float(self._analysis.min)

    @property
    def mean_stress(self) -> float:
        return float(self._analysis.mean)

    @property
    def max_point(self):
        return self._analysis.max_point

    def plot(self, *args, **kwargs):
        return self._analysis.plot(*args, **kwargs)

    def plot_utilization(self, *args, **kwargs):
        return self._analysis.plot_utilization(*args, **kwargs)

    def plot_directional_factor(self, *args, **kwargs):
        return self._analysis.plot_directional_factor(*args, **kwargs)

    def check(self, **kwargs) -> dict:
        from .checks import check_weld_group

        return check_weld_group(self, **kwargs).to_dict()


