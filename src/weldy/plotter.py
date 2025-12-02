"""
Weld stress visualization.

Plots section geometry with weld lines colored by stress intensity.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Optional, List, Tuple
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.path import Path
from matplotlib.patches import PathPatch, FancyArrowPatch
import matplotlib.colors as mcolors

if TYPE_CHECKING:
    from .section import WeldedSection
    from .stress import WeldStressResult, PointStress
    from .force import Force
    from .weld import WeldSegment

# Plot configuration
_DEFAULT_CMAP = "coolwarm"
_DEFAULT_WELD_LINEWIDTH = 4.0
_SECTION_ALPHA = 0.3
_SECTION_EDGE_COLOR = "black"
_SECTION_FACE_COLOR = "silver"


def _contour_to_path(contour) -> Optional[Path]:
    """
    Convert a sectiony Contour to matplotlib Path.
    Adapted from sectiony.plotter.
    """
    from sectiony.geometry import Line, Arc, CubicBezier
    import math
    
    if not contour.segments:
        return None
    
    vertices = []
    codes = []
    
    # Get start point
    first_segment = contour.segments[0]
    if isinstance(first_segment, Line):
        start_point = first_segment.start
    elif isinstance(first_segment, Arc):
        cy, cz = first_segment.center
        y = cy + first_segment.radius * math.sin(first_segment.start_angle)
        z = cz + first_segment.radius * math.cos(first_segment.start_angle)
        start_point = (y, z)
    elif isinstance(first_segment, CubicBezier):
        start_point = first_segment.p0
    else:
        start_point = (0, 0)
    
    # Convert (y, z) to plot coords (z, y) - z horizontal, y vertical
    vertices.append((start_point[1], start_point[0]))
    codes.append(Path.MOVETO)
    
    for segment in contour.segments:
        if isinstance(segment, Line):
            vertices.append((segment.end[1], segment.end[0]))
            codes.append(Path.LINETO)
            
        elif isinstance(segment, Arc):
            beziers = segment.to_beziers()
            for bez in beziers:
                vertices.append((bez.p1[1], bez.p1[0]))
                codes.append(Path.CURVE4)
                vertices.append((bez.p2[1], bez.p2[0]))
                codes.append(Path.CURVE4)
                vertices.append((bez.p3[1], bez.p3[0]))
                codes.append(Path.CURVE4)
                
        elif isinstance(segment, CubicBezier):
            vertices.append((segment.p1[1], segment.p1[0]))
            codes.append(Path.CURVE4)
            vertices.append((segment.p2[1], segment.p2[0]))
            codes.append(Path.CURVE4)
            vertices.append((segment.p3[1], segment.p3[0]))
            codes.append(Path.CURVE4)
    
    codes.append(Path.CLOSEPOLY)
    vertices.append(vertices[0])
    
    return Path(vertices, codes)


def _shape_to_path(shape) -> Optional[Path]:
    """Convert a sectiony Shape to matplotlib Path."""
    if hasattr(shape, '_contour') and shape._contour and shape._contour.segments:
        return _contour_to_path(shape._contour)
    
    if not shape.points or len(shape.points) < 3:
        return None
    
    vertices = [(p[1], p[0]) for p in shape.points]  # (y,z) to (z,y)
    vertices.append(vertices[0])
    codes = [Path.MOVETO] + [Path.LINETO] * (len(shape.points) - 1) + [Path.CLOSEPOLY]
    
    return Path(vertices, codes)


def _draw_section_geometry(
    ax: plt.Axes, 
    welded_section: WeldedSection
) -> Tuple[float, float, float, float]:
    """
    Draw the section geometry as background.
    
    Returns:
        Bounds as (y_min, y_max, z_min, z_max)
    """
    geometry = welded_section.section.geometry
    
    if geometry is None or not geometry.shapes:
        return (0, 1, 0, 1)
    
    solids = [s for s in geometry.shapes if not s.hollow]
    hollows = [s for s in geometry.shapes if s.hollow]
    
    all_y = []
    all_z = []
    
    # Draw solids
    for shape in solids:
        path = _shape_to_path(shape)
        if path is None:
            continue
        
        for p in shape.points:
            all_y.append(p[0])
            all_z.append(p[1])
        
        patch = PathPatch(
            path, 
            facecolor=_SECTION_FACE_COLOR, 
            edgecolor=_SECTION_EDGE_COLOR,
            alpha=_SECTION_ALPHA, 
            linewidth=1.0
        )
        ax.add_patch(patch)
    
    # Draw hollows
    for shape in hollows:
        path = _shape_to_path(shape)
        if path is None:
            continue
        
        for p in shape.points:
            all_y.append(p[0])
            all_z.append(p[1])
        
        patch = PathPatch(
            path, 
            facecolor='white', 
            edgecolor=_SECTION_EDGE_COLOR,
            linestyle='--', 
            alpha=1.0, 
            linewidth=1.0
        )
        ax.add_patch(patch)
    
    if all_y and all_z:
        return (min(all_y), max(all_y), min(all_z), max(all_z))
    return (0, 1, 0, 1)


def _create_weld_line_collection(
    stress_result: WeldStressResult,
    cmap: str,
    linewidth: float
) -> Tuple[LineCollection, float, float]:
    """
    Create a LineCollection of weld segments colored by stress.
    
    Returns:
        (LineCollection, stress_min, stress_max)
    """
    # Group points by segment
    segment_points: dict[tuple[int, int, int], List[PointStress]] = {}
    
    for ps in stress_result.point_stresses:
        seg_key = (ps.segment.contour_index, ps.segment.segment_index, id(ps.segment))
        if seg_key not in segment_points:
            segment_points[seg_key] = []
        segment_points[seg_key].append(ps)
    
    # Create line segments with colors
    segments = []
    colors = []
    
    all_stresses = [ps.stress for ps in stress_result.point_stresses]
    if not all_stresses:
        return LineCollection([]), 0, 0

    stress_min = min(all_stresses)
    stress_max = max(all_stresses)
    if abs(stress_max - stress_min) < 1e-9:
        stress_max = stress_min + 1.0
    for seg_idx, points in segment_points.items():
        # Sort by position along segment (already ordered from discretize)
        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i + 1]
            
            # Line segment in (z, y) plot coordinates
            seg = [
                (p1.z, p1.y),
                (p2.z, p2.y)
            ]
            segments.append(seg)
            
            # Color by average stress of the two endpoints
            avg_stress = (p1.stress + p2.stress) / 2
            colors.append(avg_stress)
    
    # Create LineCollection
    norm = mcolors.Normalize(vmin=stress_min, vmax=stress_max, clip=True)
    lc = LineCollection(
        segments,
        cmap=cmap,
        norm=norm,
        linewidth=linewidth,
        capstyle='round',
        joinstyle='round'
    )
    lc.set_array(np.array(colors))
    
    return lc, stress_min, stress_max


def _draw_force_arrow(
    ax: plt.Axes,
    force: Force,
    bounds: Tuple[float, float, float, float],
    scale: float = 0.15
) -> None:
    """
    Draw an arrow representing the applied force.
    
    Args:
        ax: Axes to draw on
        force: Applied force
        bounds: (y_min, y_max, z_min, z_max)
        scale: Arrow length as fraction of section size
    """
    y_min, y_max, z_min, z_max = bounds
    size = max(y_max - y_min, z_max - z_min)
    arrow_len = size * scale
    
    # Force location in plot coordinates (z, y)
    loc_z = force.z_loc
    loc_y = force.y_loc
    
    # Draw shear force arrow (Fy, Fz)
    total_shear = force.shear_magnitude
    if total_shear > 1e-9:
        # Normalize direction
        dy = force.Fy / total_shear * arrow_len
        dz = force.Fz / total_shear * arrow_len
        
        arrow = FancyArrowPatch(
            (loc_z - dz, loc_y - dy),
            (loc_z, loc_y),
            arrowstyle='->,head_length=8,head_width=5',
            color='red',
            linewidth=2,
            mutation_scale=1,
            zorder=10
        )
        ax.add_patch(arrow)
    
    # Draw force application point
    ax.plot(loc_z, loc_y, 'ro', markersize=6, zorder=11)
    
    # Add label
    label_parts = []
    if abs(force.Fy) > 1e-9:
        label_parts.append(f"Fy={force.Fy:.0f}")
    if abs(force.Fz) > 1e-9:
        label_parts.append(f"Fz={force.Fz:.0f}")
    if abs(force.Fx) > 1e-9:
        label_parts.append(f"Fx={force.Fx:.0f}")
    if abs(force.Mx) > 1e-9:
        label_parts.append(f"Mx={force.Mx:.0f}")
    
    if label_parts:
        label = ", ".join(label_parts)
        ax.annotate(
            label,
            (loc_z, loc_y),
            xytext=(5, 5),
            textcoords='offset points',
            fontsize=8,
            color='red',
            zorder=12
        )


def plot_weld_stress(
    welded_section: WeldedSection,
    stress_result: WeldStressResult,
    force: Force,
    ax: Optional[plt.Axes] = None,
    show: bool = True,
    cmap: str = _DEFAULT_CMAP,
    weld_linewidth: float = _DEFAULT_WELD_LINEWIDTH,
    show_force: bool = True,
    save_path: Optional[str] = None
) -> Optional[plt.Axes]:
    """
    Plot section with weld stress distribution.
    
    Args:
        welded_section: The WeldedSection object
        stress_result: Calculated WeldStressResult
        force: Applied force (for arrow display)
        ax: Matplotlib axes (creates new if None)
        show: Whether to display the plot
        cmap: Colormap name for stress visualization
        weld_linewidth: Width of weld stress lines
        show_force: Whether to show force arrow
        save_path: Path to save figure (.svg recommended)
        
    Returns:
        The axes object
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 8))
    else:
        fig = ax.get_figure()
    
    # Draw section geometry as background
    bounds = _draw_section_geometry(ax, welded_section)
    y_min, y_max, z_min, z_max = bounds
    
    # Create and add weld stress line collection
    lc, stress_min, stress_max = _create_weld_line_collection(
        stress_result, cmap, weld_linewidth
    )
    ax.add_collection(lc)
    
    # Add colorbar
    # Create a ScalarMappable for the colorbar with actual stress values
    sm = plt.cm.ScalarMappable(
        cmap=cmap,
        norm=mcolors.Normalize(vmin=stress_min, vmax=stress_max)
    )
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, label='Stress (force/area)')
    
    # Draw force arrow if requested
    if show_force:
        _draw_force_arrow(ax, force, bounds)
    
    # Set limits with padding
    dy = y_max - y_min
    dz = z_max - z_min
    if dy == 0:
        dy = 1.0
    if dz == 0:
        dz = 1.0
    
    padding = max(dy, dz) * 0.15
    ax.set_xlim(z_min - padding, z_max + padding)
    ax.set_ylim(y_min - padding, y_max + padding)
    
    # Configure axes
    ax.set_aspect('equal')
    ax.set_xlabel('z')
    ax.set_ylabel('y', rotation=0)
    ax.set_title(f'Weld Stress: {welded_section.name}\nMax: {stress_max:.2f}, Min: {stress_min:.2f}')
    ax.grid(True, linestyle=':', alpha=0.5)
    
    # Save if path provided
    if save_path is not None:
        # Ensure .svg extension
        if not save_path.endswith('.svg'):
            save_path = save_path + '.svg'
        fig.savefig(save_path, format='svg', bbox_inches='tight')
    
    if show:
        plt.show()
    
    return ax


def plot_weld_stress_components(
    welded_section: WeldedSection,
    stress_result: WeldStressResult,
    force: Force,
    show: bool = True,
    save_path: Optional[str] = None
) -> plt.Figure:
    """
    Plot multiple stress component views.
    
    Creates a 2x2 grid showing:
    - Top left: Resultant stress
    - Top right: Shear stress (in-plane)
    - Bottom left: Axial stress
    - Bottom right: Torsion stress
    
    Args:
        welded_section: The WeldedSection
        stress_result: Calculated stress result
        force: Applied force
        show: Whether to display
        save_path: Path to save (.svg)
        
    Returns:
        The Figure object
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    fig.suptitle(f'Weld Stress Analysis: {welded_section.name}', fontsize=14)
    
    # Component extractors
    def get_resultant(ps):
        return ps.stress
    
    def get_shear(ps):
        return ps.components.shear_resultant
    
    def get_axial(ps):
        return abs(ps.components.total_axial)
    
    def get_torsion(ps):
        return (ps.components.f_torsion_y**2 + ps.components.f_torsion_z**2)**0.5
    
    components = [
        (axes[0, 0], "Resultant Stress", get_resultant, "coolwarm"),
        (axes[0, 1], "In-Plane Shear", get_shear, "viridis"),
        (axes[1, 0], "Axial Stress", get_axial, "RdBu_r"),
        (axes[1, 1], "Torsional Stress", get_torsion, "plasma"),
    ]
    
    for ax, title, extractor, cmap in components:
        # Draw section
        _draw_section_geometry(ax, welded_section)
        
        # Extract stresses using custom extractor
        stresses = [extractor(ps) for ps in stress_result.point_stresses]
        
        if stresses:
            stress_min = min(stresses)
            stress_max = max(stresses)
            stress_range = stress_max - stress_min
            if stress_range < 1e-12:
                stress_range = 1.0
                stress_min = stress_max - 0.5
        else:
            stress_min, stress_max, stress_range = 0, 1, 1
        
        # Create line segments
        segment_points: dict[int, List] = {}
        for i, ps in enumerate(stress_result.point_stresses):
            seg_idx = ps.segment.segment_index
            if seg_idx not in segment_points:
                segment_points[seg_idx] = []
            segment_points[seg_idx].append((ps, stresses[i]))
        
        segments = []
        colors = []
        
        for seg_idx, points in segment_points.items():
            for i in range(len(points) - 1):
                ps1, s1 = points[i]
                ps2, s2 = points[i + 1]
                
                seg = [(ps1.z, ps1.y), (ps2.z, ps2.y)]
                segments.append(seg)
                
                avg_stress = (s1 + s2) / 2
                norm = (avg_stress - stress_min) / stress_range
                colors.append(norm)
        
        if segments:
            lc = LineCollection(segments, cmap=cmap, linewidth=4)
            lc.set_array(np.array(colors))
            ax.add_collection(lc)
            
            # Colorbar
            sm = plt.cm.ScalarMappable(
                cmap=cmap,
                norm=mcolors.Normalize(vmin=stress_min, vmax=stress_max)
            )
            sm.set_array([])
            plt.colorbar(sm, ax=ax)
        
        ax.set_aspect('equal')
        ax.set_title(f'{title}\nMax: {stress_max:.2f}')
        ax.set_xlabel('z')
        ax.set_ylabel('y', rotation=0)
        ax.grid(True, linestyle=':', alpha=0.5)
    
    plt.tight_layout()
    
    if save_path is not None:
        if not save_path.endswith('.svg'):
            save_path = save_path + '.svg'
        fig.savefig(save_path, format='svg', bbox_inches='tight')
    
    if show:
        plt.show()
    
    return fig

