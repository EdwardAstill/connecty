"""User-facing weld analysis object (connection + load + convenience methods)."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..common.load import Load
from .geometry import WeldConnection, WeldMethod
from .loaded_weld import LoadedWeld
from .weld import Weld


@dataclass
class LoadedWeldConnection:
    """A `WeldConnection` subjected to a `Load`, with calculated weld stresses."""

    connection: WeldConnection
    load: Load
    method: WeldMethod = "elastic"
    discretization: int = 200

    _analysis: LoadedWeld = field(init=False, repr=False)

    def __post_init__(self) -> None:
        # Match electrode by default for analysis inputs (conservative and cancels in scaling)
        F_EXX = float(self.connection.base_metal.fu)

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

    def check(self, **kwargs):
        from .checks import check_weld_group

        return check_weld_group(self, **kwargs)


