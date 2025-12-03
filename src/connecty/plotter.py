"""
Plotting functions for weld stress visualization.

Provides plotting methods called by StressResult.plot().
"""
from __future__ import annotations
from typing import List, TYPE_CHECKING
import math
import numpy as np

if TYPE_CHECKING:
    from .stress import StressResult

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.collections import LineCollection


def plot_stress_result(
    result: StressResult,
    section: bool = True,
    force: bool = True,
    colorbar: bool = True,
    cmap: str = "coolwarm",
    weld_linewidth: float = 5.0,
    ax: plt.Axes | None = None,
    show: bool = True,
    save_path: str | None = None
) -> plt.Axes:
    """
    Plot stress distribution along the weld.
    
    Args:
        result: StressResult from stress calculation
        section: Show section outline (if weld has section reference)
        force: Show force arrow at application point
        colorbar: Show stress colorbar
        cmap: Matplotlib colormap name
        weld_linewidth: Width of weld lines
        ax: Matplotlib axes (creates new if None)
        show: Display the plot
        save_path: Path to save figure (.svg recommended)
        
    Returns:
        Matplotlib axes
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 8))
    else:
        fig = ax.figure
    
    weld = result.weld
    
    # Plot section outline if available and requested
    if section and weld.section is not None:
        _plot_section_outline(ax, weld.section)
    
    # Collect weld segments for colored line plotting
    _plot_weld_stress(ax, result, cmap, weld_linewidth)
    
    # Add colorbar
    if colorbar and result.point_stresses:
        stress_min = result.min
        stress_max = result.max
        
        norm = mcolors.Normalize(vmin=stress_min, vmax=stress_max)
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        
        cbar = fig.colorbar(sm, ax=ax, shrink=0.8, aspect=30)
        cbar.set_label('Stress (MPa)', fontsize=10)
    
    # Plot force arrow
    if force:
        _plot_force_arrow(ax, result.force, weld)
    
    # Plot ICR point if available
    if result.icr_point is not None:
        ax.plot(result.icr_point[1], result.icr_point[0], 'ko', 
                markersize=8, label='ICR')
        ax.legend(loc='upper right')
    
    # Formatting
    ax.set_aspect('equal')
    ax.set_xlabel('z', fontsize=11)
    ax.set_ylabel('y', fontsize=11)
    ax.grid(True, alpha=0.3)
    
    # Title with key info
    title = f"Weld Stress ({result.method.upper()} method)"
    if result.point_stresses:
        title += f"\nMax: {result.max:.1f} MPa | Util: {result.utilization():.0%}"
    ax.set_title(title, fontsize=12)
    
    plt.tight_layout()
    
    # Save if requested
    if save_path:
        if not save_path.endswith('.svg'):
            save_path += '.svg'
        fig.savefig(save_path, format='svg', bbox_inches='tight')
        print(f"Saved: {save_path}")
    
    if show:
        plt.show()
    
    return ax


def _plot_section_outline(ax: plt.Axes, section) -> None:
    """Plot section geometry outline."""
    if section.geometry is None:
        return
    
    for contour in section.geometry.contours:
        points = []
        for segment in contour.segments:
            seg_points = segment.discretize(resolution=50)
            points.extend(seg_points)
        
        if points:
            # Close the contour
            points.append(points[0])
            y_coords = [p[0] for p in points]
            z_coords = [p[1] for p in points]
            
            fill_color = 'lightgray' if not contour.hollow else 'white'
            edge_color = 'gray'
            
            ax.fill(z_coords, y_coords, color=fill_color, alpha=0.3)
            ax.plot(z_coords, y_coords, color=edge_color, linewidth=1.0, linestyle='-')


def _plot_weld_stress(
    ax: plt.Axes,
    result: StressResult,
    cmap: str,
    linewidth: float
) -> None:
    """Plot weld path colored by stress."""
    if not result.point_stresses:
        return
    
    weld = result.weld
    stress_min = result.min
    stress_max = result.max
    
    # Normalize stresses
    if stress_max - stress_min > 1e-12:
        norm = mcolors.Normalize(vmin=stress_min, vmax=stress_max)
    else:
        norm = mcolors.Normalize(vmin=0, vmax=max(stress_max, 1))
    
    colormap = plt.get_cmap(cmap)
    
    # Group points by contour/segment for proper line plotting
    for contour in weld.geometry.contours:
        for segment in contour.segments:
            seg_points = segment.discretize(resolution=100)
            
            if len(seg_points) < 2:
                continue
            
            # Find stresses for points on this segment
            seg_stresses = []
            for sp in seg_points:
                # Find nearest point stress
                min_dist = float('inf')
                nearest_stress = 0.0
                for ps in result.point_stresses:
                    dist = math.hypot(ps.y - sp[0], ps.z - sp[1])
                    if dist < min_dist:
                        min_dist = dist
                        nearest_stress = ps.stress
                seg_stresses.append(nearest_stress)
            
            # Create line segments
            points = np.array([[p[1], p[0]] for p in seg_points])  # (z, y) for plotting
            segments = np.array([points[:-1], points[1:]]).transpose(1, 0, 2)
            
            # Color by average stress of each segment
            colors = []
            for i in range(len(seg_stresses) - 1):
                avg_stress = (seg_stresses[i] + seg_stresses[i + 1]) / 2
                colors.append(colormap(norm(avg_stress)))
            
            lc = LineCollection(segments, colors=colors, linewidths=linewidth)
            ax.add_collection(lc)
    
    # Update axis limits
    all_y = [ps.y for ps in result.point_stresses]
    all_z = [ps.z for ps in result.point_stresses]
    
    if all_y and all_z:
        margin = max(max(all_y) - min(all_y), max(all_z) - min(all_z)) * 0.2
        ax.set_xlim(min(all_z) - margin, max(all_z) + margin)
        ax.set_ylim(min(all_y) - margin, max(all_y) + margin)


def _plot_force_arrow(ax: plt.Axes, force, weld) -> None:
    """Plot force application point and add legend."""
    y_loc, z_loc = force.location
    
    # Plot application point (red 'x')
    ax.plot(z_loc, y_loc, 'rx', markersize=10, markeredgewidth=2, 
            label='Force Location')
            
    # Build legend text
    labels = []
    
    # Forces
    if abs(force.Fx) > 1e-3:
        labels.append(f"Fx = {force.Fx/1000:.1f} kN")
    if abs(force.Fy) > 1e-3:
        labels.append(f"Fy = {force.Fy/1000:.1f} kN")
    if abs(force.Fz) > 1e-3:
        labels.append(f"Fz = {force.Fz/1000:.1f} kN")
        
    # Moments (Mx is torsion, My/Mz are bending)
    # If applied at origin (0,0), force eccentricity is zero so only applied moment matters.
    # If not at origin, forces create moment too, but legend just shows APPLIED loads.
    is_at_origin = abs(y_loc) < 1e-6 and abs(z_loc) < 1e-6
    
    # Include moments if they exist OR if we're at the origin (as requested)
    if abs(force.Mx) > 1e-3 or (is_at_origin and (abs(force.Fy) > 1e-3 or abs(force.Fz) > 1e-3)):
        labels.append(f"Mx = {force.Mx/1e6:.1f} kNm")
    if abs(force.My) > 1e-3:
        labels.append(f"My = {force.My/1e6:.1f} kNm")
    if abs(force.Mz) > 1e-3:
        labels.append(f"Mz = {force.Mz/1e6:.1f} kNm")
        
    # Add a custom legend entry for the loads
    if labels:
        text = "\n".join(labels)
        # Create a dummy handle for the legend text
        from matplotlib.lines import Line2D
        dummy_lines = [Line2D([0], [0], color='red', linestyle='None', marker='x')]
        ax.legend(dummy_lines, [text], loc='upper left', 
                 title="Applied Loads", framealpha=0.9)


def plot_stress_components(
    result: StressResult,
    components: List[str],
    layout: str = "grid",
    **kwargs
) -> plt.Figure:
    """
    Plot individual stress components.
    
    Args:
        result: StressResult from calculation
        components: Which components to plot
        layout: "grid" or "row"
        **kwargs: Passed to individual plots
    """
    n = len(components)
    
    if layout == "grid":
        cols = min(2, n)
        rows = math.ceil(n / cols)
    else:
        cols = n
        rows = 1
    
    fig, axes = plt.subplots(rows, cols, figsize=(5 * cols, 4 * rows))
    
    if n == 1:
        axes = [axes]
    else:
        axes = axes.flatten()
    
    component_map = {
        "direct": ("Direct Shear", lambda c: c.shear_resultant),
        "moment": ("Moment Shear", lambda c: math.hypot(c.f_moment_y, c.f_moment_z)),
        "axial": ("Axial", lambda c: abs(c.f_axial)),
        "bending": ("Bending", lambda c: abs(c.f_bending)),
        "total": ("Total", lambda c: c.resultant),
    }
    
    for i, comp in enumerate(components):
        if comp not in component_map:
            continue
        
        title, stress_fn = component_map[comp]
        
        # Create modified point stresses with single component
        ax = axes[i]
        
        # Simple scatter plot for components
        y_coords = [ps.y for ps in result.point_stresses]
        z_coords = [ps.z for ps in result.point_stresses]
        stresses = [stress_fn(ps.components) for ps in result.point_stresses]
        
        sc = ax.scatter(z_coords, y_coords, c=stresses, cmap='coolwarm', s=10)
        fig.colorbar(sc, ax=ax, shrink=0.8)
        
        ax.set_aspect('equal')
        ax.set_title(f'{title} Stress')
        ax.set_xlabel('z')
        ax.set_ylabel('y')
        ax.grid(True, alpha=0.3)
    
    # Hide unused axes
    for i in range(len(components), len(axes)):
        axes[i].set_visible(False)
    
    plt.tight_layout()
    plt.show()
    
    return fig
