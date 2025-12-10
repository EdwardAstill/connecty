"""
Plotting functions for weld stress visualization.

Provides plotting methods called by StressResult.plot().
"""
from __future__ import annotations
from typing import List, TYPE_CHECKING, Any, Sequence
import math
import numpy as np

if TYPE_CHECKING:
    from .weld_stress import LoadedWeldResult
    from .loaded_weld import LoadedWeld
    from .weld import Weld

import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D


def plot_loaded_weld(
    loaded: LoadedWeld,
    section: bool = True,
    force: bool = True,
    colorbar: bool = True,
    cmap: str = "coolwarm",
    weld_linewidth: float = 5.0,
    ax: plt.Axes | None = None,
    show: bool = True,
    save_path: str | None = None,
    info: bool = True,
    legend: bool = False,
) -> plt.Axes:
    """
    Plot stress distribution for a LoadedWeld.
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 8))
    else:
        fig = ax.figure
    
    # Delegate to internal plotter
    _plot_single_loaded_weld(
        ax, 
        loaded, 
        section=section, 
        force=force, 
        colorbar=colorbar,
        cmap=cmap, 
        weld_linewidth=weld_linewidth,
        info=info,
        legend=legend
    )
    
    plt.tight_layout()
    
    if save_path:
        if not save_path.endswith('.svg'):
            save_path += '.svg'
        fig.savefig(save_path, format='svg', bbox_inches='tight')
        print(f"Saved: {save_path}")
    
    if show:
        plt.show()
    
    return ax


def plot_loaded_weld_comparison(
    loaded_list: Sequence[LoadedWeld],
    section: bool = True,
    force: bool = True,
    colorbar: bool = True,
    cmap: str = "coolwarm",
    weld_linewidth: float = 5.0,
    show: bool = True,
    save_path: str | None = None,
    info: bool = True,
    legend: bool = False,
) -> plt.Figure:
    """
    Plot multiple LoadedWeld results with a shared colorbar.
    """
    n = len(loaded_list)
    if n == 0:
        raise ValueError("No loaded welds to plot")

    y_coords: list[float] = []
    z_coords: list[float] = []
    for loaded in loaded_list:
        if not loaded.point_stresses:
            continue
        y_coords.extend(ps.y for ps in loaded.point_stresses)
        z_coords.extend(ps.z for ps in loaded.point_stresses)

    y_range = max(y_coords) - min(y_coords) if y_coords else 0.0
    z_range = max(z_coords) - min(z_coords) if z_coords else 0.0

    stack_vertically = z_range >= y_range

    if stack_vertically:
        fig, axes = plt.subplots(n, 1, figsize=(10, 5 * n))
        fig.subplots_adjust(hspace=0.2)
    else:
        fig, axes = plt.subplots(1, n, figsize=(6 * n, 10))
        fig.subplots_adjust(wspace=0.2)

    if isinstance(axes, np.ndarray):
        axes_list = list(axes.flatten())
    else:
        axes_list = [axes]
        
    # Calculate global min/max for shared color scale
    global_min = min(loaded.min for loaded in loaded_list)
    global_max = max(loaded.max for loaded in loaded_list)
    
    # Plot each result
    for i, (loaded, ax) in enumerate(zip(loaded_list, axes_list)):
        _plot_single_loaded_weld(
            ax,
            loaded,
            section=section,
            force=force,
            colorbar=False,
            cmap=cmap,
            weld_linewidth=weld_linewidth,
            info=info,
            legend=legend,
            vmin=global_min,
            vmax=global_max
        )
        
    # Add shared colorbar
    if colorbar:
        fig.subplots_adjust(right=0.85)
        cbar_ax = fig.add_axes([0.90, 0.15, 0.02, 0.7])
        
        norm = mcolors.Normalize(vmin=global_min, vmax=global_max)
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        
        cbar = fig.colorbar(sm, cax=cbar_ax)
        cbar.set_label('Stress (MPa)', fontsize=12)
        
    if save_path:
        if not save_path.endswith('.svg'):
            save_path += '.svg'
        fig.savefig(save_path, format='svg', bbox_inches='tight')
        print(f"Saved: {save_path}")
        
    if show:
        plt.show()
        
    return fig


def _plot_single_loaded_weld(
    ax: plt.Axes,
    loaded: LoadedWeld,
    section: bool = True,
    force: bool = True,
    colorbar: bool = True,
    cmap: str = "coolwarm",
    weld_linewidth: float = 5.0,
    info: bool = True,
    legend: bool = False,
    vmin: float | None = None,
    vmax: float | None = None
) -> None:
    """Internal helper to plot a single LoadedWeld onto an axes."""
    weld = loaded.weld
    
    # Plot section outline if available and requested
    if section and weld.section is not None:
        _plot_section_outline(ax, weld.section)
    
    # Plot weld stress
    _plot_loaded_weld_stress(ax, loaded, cmap, weld_linewidth, vmin, vmax)
    
    # Add colorbar if requested
    if colorbar and loaded.point_stresses:
        stress_min = vmin if vmin is not None else loaded.min
        stress_max = vmax if vmax is not None else loaded.max
        
        norm = mcolors.Normalize(vmin=stress_min, vmax=stress_max)
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        
        cbar = ax.figure.colorbar(sm, ax=ax, shrink=0.8, aspect=30)
        cbar.set_label('Stress (MPa)', fontsize=10)
    
    # Plot force arrow and centroid
    if force:
        _plot_force_arrow(ax, loaded.load, weld, legend=legend)
    
    # Plot ICR point if available
    if loaded.icr_point is not None:
        icr_y, icr_z = loaded.icr_point[0], loaded.icr_point[1]
        ax.plot(icr_z, icr_y, 'ko', markersize=8)
        
        ax.annotate('ICR', 
                    xy=(icr_z, icr_y), 
                    xytext=(10, 10), 
                    textcoords='offset points',
                    fontsize=9,
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8, edgecolor='black'))
    
    # Formatting
    ax.set_aspect('equal')
    ax.set_xlabel('z', fontsize=11)
    ax.set_ylabel('y', fontsize=11)
    
    # Title with key info
    title = f"Weld Stress ({loaded.method.upper()} method)"
    if info and loaded.point_stresses:
        title += f"\nMax Stress: {loaded.max:.1f} MPa"
    ax.set_title(title, fontsize=12)


def _plot_loaded_weld_stress(
    ax: plt.Axes,
    loaded: LoadedWeld,
    cmap: str,
    linewidth: float,
    vmin: float | None = None,
    vmax: float | None = None
) -> None:
    """Plot weld path colored by stress."""
    if not loaded.point_stresses:
        return
    
    weld = loaded.weld
    stress_min = vmin if vmin is not None else loaded.min
    stress_max = vmax if vmax is not None else loaded.max
    
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
                for ps in loaded.point_stresses:
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
    all_y = [ps.y for ps in loaded.point_stresses]
    all_z = [ps.z for ps in loaded.point_stresses]
    
    if all_y and all_z:
        margin = max(max(all_y) - min(all_y), max(all_z) - min(all_z)) * 0.2
        ax.set_xlim(min(all_z) - margin, max(all_z) + margin)
        ax.set_ylim(min(all_y) - margin, max(all_y) + margin)


import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D


def plot_stress_result(
    result: LoadedWeldResult,
    section: bool = True,
    force: bool = True,
    colorbar: bool = True,
    cmap: str = "coolwarm",
    weld_linewidth: float = 5.0,
    ax: plt.Axes | None = None,
    show: bool = True,
    save_path: str | None = None,
    info: bool = True,
    legend: bool = False,
) -> plt.Axes:
    """
    Plot stress distribution along the weld.
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 8))
    else:
        fig = ax.figure
    
    # Delegate to internal plotter
    _plot_single_weld_result(
        ax, 
        result, 
        section=section, 
        force=force, 
        colorbar=colorbar,
        cmap=cmap, 
        weld_linewidth=weld_linewidth,
        info=info,
        legend=legend
    )
    
    plt.tight_layout()
    
    if save_path:
        if not save_path.endswith('.svg'):
            save_path += '.svg'
        fig.savefig(save_path, format='svg', bbox_inches='tight')
        print(f"Saved: {save_path}")
    
    if show:
        plt.show()
    
    return ax


def plot_stress_comparison(
    results: Sequence[LoadedWeldResult],
    section: bool = True,
    force: bool = True,
    colorbar: bool = True,
    cmap: str = "coolwarm",
    weld_linewidth: float = 5.0,
    show: bool = True,
    save_path: str | None = None,
    info: bool = True,
    legend: bool = False,
) -> plt.Figure:
    """
    Plot multiple stress results with a shared colorbar.
    
    Layout toggles between vertical stacks for wide welds and horizontal stacks
    for tall welds to keep the view balanced. The colorbar remains shared on the
    right-hand side regardless of stacking.
    
    Args:
        results: List of StressResult objects to compare
        section, force, colorbar, cmap, weld_linewidth, show, save_path, info, legend:
            Same as plot_stress_result
            
    Returns:
        Matplotlib Figure
    """
    n = len(results)
    if n == 0:
        raise ValueError("No results to plot")

    y_coords: list[float] = []
    z_coords: list[float] = []
    for result in results:
        if not result.point_stresses:
            continue
        y_coords.extend(ps.y for ps in result.point_stresses)
        z_coords.extend(ps.z for ps in result.point_stresses)

    y_range = max(y_coords) - min(y_coords) if y_coords else 0.0
    z_range = max(z_coords) - min(z_coords) if z_coords else 0.0

    stack_vertically = z_range >= y_range

    if stack_vertically:
        fig, axes = plt.subplots(n, 1, figsize=(10, 5 * n))
        fig.subplots_adjust(hspace=0.2)
    else:
        fig, axes = plt.subplots(1, n, figsize=(6 * n, 10))
        fig.subplots_adjust(wspace=0.2)

    if isinstance(axes, np.ndarray):
        axes_list = list(axes.flatten())
    else:
        axes_list = [axes]
        
    # Calculate global min/max for shared color scale
    global_min = min(r.min for r in results)
    global_max = max(r.max for r in results)
    
    # Plot each result
    for i, (result, ax) in enumerate(zip(results, axes_list)):
        _plot_single_weld_result(
            ax,
            result,
            section=section,
            force=force,
            colorbar=False, # We'll add a shared one
            cmap=cmap,
            weld_linewidth=weld_linewidth,
            info=info,
            legend=legend,
            vmin=global_min,
            vmax=global_max
        )
        
    # Add shared colorbar
    if colorbar:
        # Create a new axes for the colorbar on the right side
        fig.subplots_adjust(right=0.85)
        cbar_ax = fig.add_axes([0.90, 0.15, 0.02, 0.7])
        
        norm = mcolors.Normalize(vmin=global_min, vmax=global_max)
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        
        cbar = fig.colorbar(sm, cax=cbar_ax)
        cbar.set_label('Stress (MPa)', fontsize=12)
        
    if save_path:
        if not save_path.endswith('.svg'):
            save_path += '.svg'
        fig.savefig(save_path, format='svg', bbox_inches='tight')
        print(f"Saved: {save_path}")
        
    if show:
        plt.show()
        
    return fig


def _plot_single_weld_result(
    ax: plt.Axes,
    result: LoadedWeldResult,
    section: bool = True,
    force: bool = True,
    colorbar: bool = True,
    cmap: str = "coolwarm",
    weld_linewidth: float = 5.0,
    info: bool = True,
    legend: bool = False,
    vmin: float | None = None,
    vmax: float | None = None
) -> None:
    """Internal helper to plot a single result onto an axes."""
    weld = result.loaded_weld.weld
    
    # Plot section outline if available and requested
    if section and weld.section is not None:
        _plot_section_outline(ax, weld.section)
    
    # Collect weld segments for colored line plotting
    _plot_weld_stress(ax, result, cmap, weld_linewidth, vmin, vmax)
    
    # Add colorbar if requested (for single plots)
    if colorbar and result.point_stresses:
        stress_min = vmin if vmin is not None else result.min
        stress_max = vmax if vmax is not None else result.max
        
        norm = mcolors.Normalize(vmin=stress_min, vmax=stress_max)
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        
        cbar = ax.figure.colorbar(sm, ax=ax, shrink=0.8, aspect=30)
        cbar.set_label('Stress (MPa)', fontsize=10)
    
    # Plot force arrow and centroid
    if force:
        _plot_force_arrow(ax, result.loaded_weld.load, weld, legend=legend)
    
    # Plot ICR point if available
    if result.icr_point is not None:
        icr_y, icr_z = result.icr_point[0], result.icr_point[1]
        ax.plot(icr_z, icr_y, 'ko', markersize=8)
        
        # Always label ICR point with annotation
        ax.annotate('ICR', 
                    xy=(icr_z, icr_y), 
                    xytext=(10, 10), 
                    textcoords='offset points',
                    fontsize=9,
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8, edgecolor='black'))
    
    # Formatting
    ax.set_aspect('equal')
    ax.set_xlabel('z', fontsize=11)
    ax.set_ylabel('y', fontsize=11)
    
    # Title with key info
    title = f"Weld Stress ({result.method.upper()} method)"
    if info and result.point_stresses:
        title += f"\nMax Stress: {result.max:.1f} MPa"
    ax.set_title(title, fontsize=12)


def plot_weld_geometry(
    weld: Weld,
    section: bool = True,
    weld_linewidth: float = 2.0,
    color: str = 'black',
    ax: plt.Axes | None = None,
    show: bool = True,
    save_path: str | None = None
) -> plt.Axes:
    """
    Plot weld geometry without stress results.
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 8))
    else:
        fig = ax.figure
        
    # Plot section outline
    if section and weld.section is not None:
        _plot_section_outline(ax, weld.section)
        
    # Plot weld path
    for contour in weld.geometry.contours:
        for segment in contour.segments:
            points = segment.discretize(resolution=100)
            y = [p[0] for p in points]
            z = [p[1] for p in points]
            ax.plot(z, y, color=color, linewidth=weld_linewidth)
            
    ax.set_aspect('equal')
    ax.set_xlabel('z')
    ax.set_ylabel('y')
    ax.set_title('Weld Geometry')
    
    if save_path:
        fig.savefig(save_path, bbox_inches='tight')
        
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
    result: LoadedWeldResult,
    cmap: str,
    linewidth: float,
    vmin: float | None = None,
    vmax: float | None = None
) -> None:
    """Plot weld path colored by stress."""
    if not result.point_stresses:
        return
    
    weld = result.loaded_weld.weld
    stress_min = vmin if vmin is not None else result.min
    stress_max = vmax if vmax is not None else result.max
    
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


def _plot_force_arrow(ax: plt.Axes, force, weld, legend: bool = False) -> None:
    """
    Plot force application point and weld centroid with text labels on plot.
    When legend=True, also show a legend with applied load values.
    """
    x_loc, y_loc, z_loc = force.location
    weld_cy = weld.Cy
    weld_cz = weld.Cz
    
    # Plot force application point (red 'x')
    ax.plot(z_loc, y_loc, 'rx', markersize=10, markeredgewidth=2)
    
    # Plot weld centroid (open green circle)
    ax.plot(weld_cz, weld_cy, 'o', markersize=8, markeredgewidth=2,
            markerfacecolor='none', markeredgecolor='green')
    
    # Always add text annotations for points
    # Calculate label offsets based on position
    def get_x_offset(z: float) -> int:
        return -70 if z > 0 else 10
    
    # Check if points are vertically close (similar y values)
    vertically_close = abs(y_loc - weld_cy) < 50
    
    if vertically_close:
        # If vertically close, put higher point's label above, lower point's label below
        if y_loc >= weld_cy:
            force_y_offset = 15
            centroid_y_offset = -15
        else:
            force_y_offset = -15
            centroid_y_offset = 15
    else:
        force_y_offset = -15 if y_loc > 0 else 10
        centroid_y_offset = -15 if weld_cy > 0 else 10
    
    force_offset = (get_x_offset(z_loc), force_y_offset)
    centroid_offset = (get_x_offset(weld_cz), centroid_y_offset)
    
    # Label force application point
    ax.annotate('Force Location', 
                xy=(z_loc, y_loc), 
                xytext=force_offset, 
                textcoords='offset points',
                fontsize=9,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8, edgecolor='red'))
    
    # Label weld centroid
    ax.annotate('Weld Centroid', 
                xy=(weld_cz, weld_cy), 
                xytext=centroid_offset, 
                textcoords='offset points',
                fontsize=9,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8, edgecolor='green'))
    
    # Add legend with applied loads if requested
    if legend:
        labels = []
        
        # Forces
        if abs(force.Fx) > 1e-3:
            labels.append(f"Fx = {force.Fx/1000:.1f} kN")
        if abs(force.Fy) > 1e-3:
            labels.append(f"Fy = {force.Fy/1000:.1f} kN")
        if abs(force.Fz) > 1e-3:
            labels.append(f"Fz = {force.Fz/1000:.1f} kN")
            
        # Moments
        if abs(force.Mx) > 1e-3:
            labels.append(f"Mx = {force.Mx/1e6:.1f} kNm")
        if abs(force.My) > 1e-3:
            labels.append(f"My = {force.My/1e6:.1f} kNm")
        if abs(force.Mz) > 1e-3:
            labels.append(f"Mz = {force.Mz/1e6:.1f} kNm")
            
        if labels:
            text = "\n".join(labels)
            dummy_handle = Line2D([0], [0], color='red', linestyle='None', marker='x')
            ax.legend([dummy_handle], [text], loc='upper left', 
                     title="Applied Loads", framealpha=0.9)


def plot_stress_components(
    result: LoadedWeldResult,
    components: List[str],
    layout: str = "grid",
    **kwargs: Any
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
