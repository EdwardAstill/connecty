"""
High-level helpers that pair sectiony sections with weld definitions.

The WeldedSection API mirrors the documentation and testing examples:
- Enumerate geometry segments from a sectiony.Section
- Assign weld parameters to specific segments or entire contours
- Build a Weld object (WeldGroup) and compute stresses quickly
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple
import math

from sectiony import Section
from sectiony.geometry import (
    Geometry,
    Contour,
    Segment,
    Line,
    Arc,
    CubicBezier,
)

from .weld import Weld, WeldParams, WeldProperties
from ..common.load import Load

Point = Tuple[float, float]


def _segment_points(segment: Segment, resolution: int = 64) -> List[Point]:
    """Sample points along a segment with a consistent resolution."""
    points = segment.discretize(resolution=resolution)
    if not points:
        raise ValueError("Segment discretization returned no points")
    return points


def _segment_length(segment: Segment) -> float:
    """Approximate segment length from discretized points."""
    points = _segment_points(segment, resolution=64)
    length = 0.0
    for i in range(len(points) - 1):
        dy = points[i + 1][0] - points[i][0]
        dz = points[i + 1][1] - points[i][1]
        length += math.hypot(dy, dz)
    return length


def _clone_segment(segment: Segment) -> Segment:
    """Create a shallow copy of a geometry segment."""
    if isinstance(segment, Line):
        return Line(start=segment.start, end=segment.end)
    if isinstance(segment, Arc):
        return Arc(
            center=segment.center,
            radius=segment.radius,
            start_angle=segment.start_angle,
            end_angle=segment.end_angle,
        )
    if isinstance(segment, CubicBezier):
        return CubicBezier(
            p0=segment.p0,
            p1=segment.p1,
            p2=segment.p2,
            p3=segment.p3,
        )
    raise TypeError(f"Unsupported segment type: {type(segment)!r}")


@dataclass
class WeldSegment:
    """
    Metadata for a section segment available for welding.
    """
    index: int
    contour_index: int
    segment_index: int
    hollow: bool
    segment: Segment
    length: float
    start: Point
    end: Point

    @property
    def type(self) -> str:
        return type(self.segment).__name__

    def to_dict(self) -> Dict[str, object]:
        """
        Dictionary describing the segment (for CLI/debug output).
        """
        return {
            "index": self.index,
            "contour_index": self.contour_index,
            "segment_index": self.segment_index,
            "type": self.type,
            "length": self.length,
            "start": self.start,
            "end": self.end,
            "hollow": self.hollow,
        }


@dataclass
class WeldGroup:
    """
    Combination of selected segments, parameters, and the generated Weld.
    """
    weld: Weld
    segments: List[WeldSegment]
    parameters: WeldParams

    @property
    def properties(self) -> WeldProperties:
        return self.weld._calculate_properties()


class WeldedSection:
    """
    Convenience wrapper that maps section geometry to weld segments.
    """

    def __init__(self, section: Section):
        if section.geometry is None:
            raise ValueError("Section must include geometry for welding operations")
        self.section = section
        self._segments = self._extract_segments(section)
        self._assignments: Dict[int, WeldParams] = {}
        self.weld_group: WeldGroup | None = None

    @staticmethod
    def _extract_segments(section: Section) -> List[WeldSegment]:
        segments: List[WeldSegment] = []
        index = 0
        for contour_idx, contour in enumerate(section.geometry.contours):
            for seg_idx, segment in enumerate(contour.segments):
                points = _segment_points(segment, resolution=32)
                start = points[0]
                end = points[-1]
                length = _segment_length(segment)
                segments.append(WeldSegment(
                    index=index,
                    contour_index=contour_idx,
                    segment_index=seg_idx,
                    hollow=contour.hollow,
                    segment=segment,
                    length=length,
                    start=start,
                    end=end,
                ))
                index += 1
        return segments

    @property
    def segments(self) -> List[WeldSegment]:
        return list(self._segments)

    def get_segment_info(
        self,
        contour_index: int | None = None,
        include_hollows: bool = False
    ) -> List[Dict[str, object]]:
        """
        Return metadata dictionaries for available segments.
        """
        info: List[Dict[str, object]] = []
        for seg in self._segments:
            if contour_index is not None and seg.contour_index != contour_index:
                continue
            if not include_hollows and seg.hollow:
                continue
            info.append(seg.to_dict())
        return info

    def add_weld(self, segment_index: int, parameters: WeldParams) -> None:
        """
        Assign weld parameters to a specific segment.
        """
        if segment_index < 0 or segment_index >= len(self._segments):
            raise IndexError(f"Segment index {segment_index} is out of range")
        self._assignments[segment_index] = parameters
        self.weld_group = None

    def add_welds(
        self,
        segment_indices: Sequence[int],
        parameters: WeldParams
    ) -> None:
        for idx in segment_indices:
            self.add_weld(int(idx), parameters)

    def weld_all_segments(
        self,
        parameters: WeldParams,
        contour_index: int | None = None,
        include_hollows: bool = False
    ) -> None:
        """
        Assign weld parameters to every segment (optionally filtering by contour).
        """
        for seg in self._segments:
            if contour_index is not None and seg.contour_index != contour_index:
                continue
            if not include_hollows and seg.hollow:
                continue
            self._assignments[seg.index] = parameters
        self.weld_group = None

    def clear_welds(self) -> None:
        """Remove all weld assignments."""
        self._assignments.clear()
        self.weld_group = None

    def calculate_properties(self) -> WeldGroup:
        """
        Build the Weld object for the assigned segments and cache its properties.
        """
        if not self._assignments:
            raise ValueError("No weld segments have been assigned")
        if self.weld_group is not None:
            return self.weld_group

        active_segments = [
            seg for seg in self._segments
            if seg.index in self._assignments
        ]
        if not active_segments:
            raise ValueError("Selected weld segments list is empty")

        parameters = self._resolve_parameters(active_segments)
        geometry = self._build_geometry(active_segments)
        weld = Weld(geometry=geometry, parameters=parameters, section=self.section)

        self.weld_group = WeldGroup(
            weld=weld,
            segments=active_segments,
            parameters=parameters,
        )
        return self.weld_group

    def _resolve_parameters(self, segments: List[WeldSegment]) -> WeldParams:
        """
        Ensure all selected segments use identical parameters.
        """
        first_index = segments[0].index
        reference = self._assignments[first_index]
        for seg in segments[1:]:
            assigned = self._assignments[seg.index]
            if assigned != reference:
                raise ValueError("All weld segments must share identical parameters")
        return reference

    def _build_geometry(self, segments: List[WeldSegment]) -> Geometry:
        contour_segments: Dict[int, List[Segment]] = {}
        contour_hollows: Dict[int, bool] = {}
        for seg in segments:
            cloned = _clone_segment(seg.segment)
            if seg.contour_index not in contour_segments:
                contour_segments[seg.contour_index] = [cloned]
                contour_hollows[seg.contour_index] = seg.hollow
            else:
                contour_segments[seg.contour_index].append(cloned)
        contours: List[Contour] = []
        for idx in sorted(contour_segments):
            contours.append(Contour(
                segments=contour_segments[idx],
                hollow=contour_hollows[idx],
            ))
        return Geometry(contours=contours)

    def calculate_weld_stress(
        self,
        load: Load,
        method: str = "elastic",
        discretization: int = 200
    ):
        """
        Run the weld stress analysis for the current assignments.
        
        Returns a LoadedWeld object with calculated results.
        """
        from .loaded_weld import LoadedWeld
        
        weld_group = self.calculate_properties()
        return LoadedWeld(weld_group.weld, load, method=method, discretization=discretization)

    def plot_weld_stress(
        self,
        load: Load,
        method: str = "elastic",
        discretization: int = 200,
        cmap: str = "coolwarm",
        weld_linewidth: float = 5.0,
        section: bool = True,
        show_force: bool = True,
        colorbar: bool = True,
        ax=None,
        show: bool = True,
        save_path: str | None = None
    ):
        """
        Convenience wrapper around LoadedWeld.plot with weld-specific defaults.
        """
        loaded = self.calculate_weld_stress(
            load=load,
            method=method,
            discretization=discretization,
        )
        return loaded.plot(
            section=section,
            cmap=cmap,
            weld_linewidth=weld_linewidth,
            show=show,
            save_path=save_path,
        )

