"""
WeldedSection class - extends sectiony Section with weld analysis capabilities.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, TYPE_CHECKING, Optional
import matplotlib.pyplot as plt

from sectiony import Section

from .weld import WeldParameters, WeldSegment, WeldGroup
from .force import Force
from .stress import WeldStressResult, calculate_weld_stress

if TYPE_CHECKING:
    pass


@dataclass
class WeldedSection:
    """
    A section with welded edges for stress analysis.
    
    Wraps a sectiony Section and adds weld analysis capabilities.
    
    Attributes:
        section: The underlying sectiony Section object
        weld_group: WeldGroup containing all welded segments
    """
    section: Section
    weld_group: WeldGroup = field(default_factory=WeldGroup)
    _initialized: bool = field(default=False, repr=False)
    
    def __post_init__(self) -> None:
        """Bind weld group to section if segments exist."""
        if self.weld_group.weld_segments:
            self._bind_and_calculate()
    
    def _bind_and_calculate(self) -> None:
        """Bind weld segments to section and calculate properties."""
        self.weld_group.bind_to_section(self.section)
        self.weld_group.calculate_properties()
        self._initialized = True
    
    @property
    def name(self) -> str:
        """Section name."""
        return self.section.name
    
    @property
    def geometry(self):
        """Section geometry."""
        return self.section.geometry
    
    def add_weld(
        self, 
        segment_index: int, 
        parameters: WeldParameters,
        contour_index: int = 0
    ) -> WeldSegment:
        """
        Add a weld to a specific segment of the section.
        
        Args:
            segment_index: Index of segment in the contour
            parameters: WeldParameters for this weld
            contour_index: Index of contour (0 = outer, 1+ = inner)
            
        Returns:
            The created WeldSegment
        """
        segment = WeldSegment(
            segment_index=segment_index,
            parameters=parameters,
            contour_index=contour_index
        )
        
        # Bind immediately to validate
        segment.bind_to_section(self.section)
        
        self.weld_group.add_segment(segment)
        self._initialized = False  # Need to recalculate
        
        return segment
    
    def add_welds(
        self,
        segment_indices: List[int],
        parameters: WeldParameters,
        contour_index: int = 0
    ) -> List[WeldSegment]:
        """
        Add welds to multiple segments with the same parameters.
        
        Args:
            segment_indices: List of segment indices to weld
            parameters: WeldParameters for all welds
            contour_index: Index of contour
            
        Returns:
            List of created WeldSegments
        """
        segments = []
        for idx in segment_indices:
            segment = self.add_weld(idx, parameters, contour_index)
            segments.append(segment)
        return segments
    
    def weld_all_segments(
        self,
        parameters: WeldParameters,
        contour_index: int = 0
    ) -> List[WeldSegment]:
        """
        Add welds to all segments of a contour.
        
        Args:
            parameters: WeldParameters for all welds
            contour_index: Index of contour to weld
            
        Returns:
            List of created WeldSegments
        """
        if self.section.geometry is None:
            raise ValueError("Section has no geometry")
        
        if not self.section.geometry.contours:
            raise ValueError("Section has no contours")
        
        if contour_index >= len(self.section.geometry.contours):
            raise ValueError(f"Contour index {contour_index} out of range")
        
        contour = self.section.geometry.contours[contour_index]
        indices = list(range(len(contour.segments)))
        
        return self.add_welds(indices, parameters, contour_index)
    
    def calculate_properties(self) -> None:
        """
        Calculate weld group properties.
        
        Must be called after adding all welds and before stress calculation.
        """
        if not self.weld_group.weld_segments:
            raise ValueError("No welds defined - add welds first")
        
        self._bind_and_calculate()
    
    def calculate_weld_stress(
        self, 
        force: Force,
        discretization: int = 50
    ) -> WeldStressResult:
        """
        Calculate stress distribution along all welds.
        
        Args:
            force: Applied force
            discretization: Points per segment for evaluation
            
        Returns:
            WeldStressResult with stress at all points
        """
        if not self._initialized:
            self.calculate_properties()
        
        return calculate_weld_stress(
            self.weld_group, 
            force, 
            discretization
        )
    
    def plot(
        self, 
        ax: Optional[plt.Axes] = None, 
        show: bool = True
    ) -> Optional[plt.Axes]:
        """
        Plot the section geometry (delegates to sectiony).
        
        Args:
            ax: Matplotlib axes
            show: Whether to display
            
        Returns:
            The axes
        """
        return self.section.plot(ax=ax, show=show)
    
    def plot_weld_stress(
        self,
        force: Force,
        ax: Optional[plt.Axes] = None,
        show: bool = True,
        cmap: str = "coolwarm",
        discretization: int = 50,
        weld_linewidth: float = 4.0,
        show_force: bool = True,
        save_path: Optional[str] = None
    ) -> Optional[plt.Axes]:
        """
        Plot section with weld stress distribution shown as colored lines.
        
        Args:
            force: Applied force
            ax: Matplotlib axes (creates new if None)
            show: Whether to display the plot
            cmap: Colormap for stress visualization
            discretization: Points per segment
            weld_linewidth: Width of weld lines
            show_force: Whether to show force arrow
            save_path: Path to save figure (as .svg if extension not specified)
            
        Returns:
            The axes object
        """
        from .plotter import plot_weld_stress
        
        # Calculate stress
        result = self.calculate_weld_stress(force, discretization)
        
        return plot_weld_stress(
            welded_section=self,
            stress_result=result,
            force=force,
            ax=ax,
            show=show,
            cmap=cmap,
            weld_linewidth=weld_linewidth,
            show_force=show_force,
            save_path=save_path
        )
    
    def get_segment_info(self, contour_index: int = 0) -> List[dict]:
        """
        Get information about all segments in a contour.
        
        Useful for determining which segment indices to weld.
        
        Args:
            contour_index: Index of contour
            
        Returns:
            List of dicts with segment info
        """
        if self.section.geometry is None:
            return []
        
        if not self.section.geometry.contours:
            return []
        
        if contour_index >= len(self.section.geometry.contours):
            return []
        
        contour = self.section.geometry.contours[contour_index]
        info = []
        
        from sectiony.geometry import Line, Arc, CubicBezier
        
        for i, seg in enumerate(contour.segments):
            seg_info = {"index": i, "type": type(seg).__name__}
            
            if isinstance(seg, Line):
                seg_info["start"] = seg.start
                seg_info["end"] = seg.end
            elif isinstance(seg, Arc):
                seg_info["center"] = seg.center
                seg_info["radius"] = seg.radius
            elif isinstance(seg, CubicBezier):
                seg_info["p0"] = seg.p0
                seg_info["p3"] = seg.p3
            
            info.append(seg_info)
        
        return info
    
    def __repr__(self) -> str:
        n_welds = len(self.weld_group.weld_segments)
        return f"WeldedSection(section={self.section.name!r}, welds={n_welds})"


def create_welded_section(
    section: Section,
    segment_indices: List[int],
    weld_params: WeldParameters,
    contour_index: int = 0
) -> WeldedSection:
    """
    Convenience function to create a WeldedSection with welds.
    
    Args:
        section: sectiony Section
        segment_indices: Indices of segments to weld
        weld_params: WeldParameters for all welds
        contour_index: Contour index
        
    Returns:
        Configured WeldedSection
    """
    welded = WeldedSection(section=section)
    welded.add_welds(segment_indices, weld_params, contour_index)
    welded.calculate_properties()
    return welded

