"""
Data visualization functions for battery reports.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from datetime import datetime
from utils import format_date_for_display

def create_snapshot_chart(latest_batt, IDs_list, report_date, paired=True, list_name='', path_save=None):
    """
    Create a snapshot chart showing battery power zones distribution.
    
    Args:
        latest_batt (pandas.DataFrame): Battery data DataFrame
        IDs_list (list): List of device IDs to include in chart
        report_date (str): Date string for the report
        paired (bool): If True, only include paired devices
        list_name (str): Name for the device list
        path_save (str, optional): Path to save the chart
        
    Returns:
        str: Path where the chart was saved
    """
    if path_save is None:
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"latest_batt_reports/charts/snapshot_{report_date}_{timestamp}.png"
        path_save = filename
    
    # Define chart styling
    order = ['Critical', 'Low', 'Medium', 'High']
    palette = {
        'High': 'tab:green',
        'Medium': 'tab:blue',
        'Low': 'tab:orange',
        'Critical': 'tab:red'
    }

    # Filter data based on pairing requirement
    if paired:
        cond_paired = (latest_batt['DeviceID'] != latest_batt['DeviceName'])
    else:
        cond_paired = latest_batt['CustomerName'].str.lower() == 'zim'
    df = latest_batt[(latest_batt['DeviceID'].isin(IDs_list)) & cond_paired]
    
    # Create the chart
    plt.figure(figsize=(4, 6))
    ax = sns.countplot(data=df, x='PowerMode', hue='PowerMode', order=order, palette=palette)
    
    # Remove legend
    try:
        ax.get_legend().remove()
    except:
        pass  # No legend to remove
    
    # Set y-axis limit to always show 0 to 100% (total number of devices)
    # This ensures that if the highest bar is less than 100%, there will be empty space above it
    ax.set_ylim(0, len(df))
    
    # Add percentage labels on bars
    # Use 2% of the y-axis range for spacing, which works well for both small and large datasets
    label_offset = len(df) * 0.005 if len(df) > 0 else 1
    for p in ax.patches:
        height = p.get_height()
        ax.text(p.get_x() + p.get_width() / 2., height + label_offset,
                f'{round(int(height)/len(df)*100,2)}%', ha="center")
    
    # Customize chart appearance
    ax = plt.gca() 
    ax.set_yticks([])
    ax.set_yticklabels([])
    
    plt.xlabel('Power Zone')
    plt.ylabel('Trackers per Power Zone')
    # Format date for display (e.g., "5 Jan 2026")
    formatted_date = format_date_for_display(report_date)
    plt.title(f"Tracker Battery Power Zones\n{list_name} ({len(df)}) devices\nSnapshot of {formatted_date}")
    
    plt.tight_layout()
    plt.savefig(path_save)
    plt.close()

    return path_save

def plot_power_pie_chart(power_stats, ax=None, show_plot=False, title=None, path_save=None):
    """
    Plot a pie chart of power modes.
    
    Args:
        power_stats: DataFrame with power mode statistics (must have columns: HighPercent, MediumPercent, LowPercent, CriticalPercent, TotalYears)
        ax: Matplotlib axis to plot on. If None, a new one will be created.
        show_plot: If True, plt.show() will be called to display the plot
        title: Optional custom title. If None, a default title will be used.
        path_save: Optional path to save the chart. If None, chart is not saved.
        
    Returns:
        fig, ax: The figure and axis with the pie chart
    """
    # Create a new figure and axis if needed
    if ax is None:
        fig, ax = plt.subplots(figsize=(5, 5))
    else:
        fig = ax.figure
    
    # Define color palette
    palette = {
        'High': 'tab:green',
        'Medium': 'tab:blue',
        'Low': 'tab:orange',
        'Critical': 'tab:red'
    }
    
    # Get data for pie chart
    labels = ['High', 'Medium', 'Low', 'Critical']
    values = [
        power_stats['HighPercent'].iloc[0] if 'HighPercent' in power_stats.columns else 0,
        power_stats['MediumPercent'].iloc[0] if 'MediumPercent' in power_stats.columns else 0,
        power_stats['LowPercent'].iloc[0] if 'LowPercent' in power_stats.columns else 0,
        power_stats['CriticalPercent'].iloc[0] if 'CriticalPercent' in power_stats.columns else 0
    ]
    colors = [palette[mode] for mode in labels]
    
    # Create the pie chart
    wedges, _ = ax.pie(
        values, 
        labels=None,  # We'll add custom labels with lines
        colors=colors,
        startangle=90,
        wedgeprops={'edgecolor': 'w', 'linewidth': 1},
        radius=1.0
    )
    
    # Define fixed positions and angled connections for each label
    label_config = {
        'High': {
            'position': [.9, -1.05], 
            'alignment': 'right',
            'connection': "angle,angleA=0,angleB=90"
        },
        'Medium': {
            'position': [.5, 1.025], 
            'alignment': 'left',
            'connection': "angle,angleA=0,angleB=90"  
        },
        'Low': {
            'position': [.3, 1.15], 
            'alignment': 'left',
            'connection': "angle,angleA=0,angleB=90"  
        },
        'Critical': {
            'position': [-.9, 1.05], 
            'alignment': 'left',
            'connection': "angle,angleA=0,angleB=90"  
        }
    }
    
    # Add custom annotations for each wedge
    for i, p in enumerate(wedges):
        ang = (p.theta2 - p.theta1)/2. + p.theta1
        x = np.cos(np.deg2rad(ang))
        y = np.sin(np.deg2rad(ang))
    
        label = labels[i]
        config = label_config[label]
    
        # Add the lines and labels with custom curved connections (smaller font for email)
        font_size = 10 if ax is not None and ax.figure.get_figwidth() < 10 else 20
        ax.annotate(f"{label}: {values[i]:.2f}%", 
                    xy=(x, y), 
                    xytext=(config['position'][0], config['position'][1]),
                    arrowprops=dict(arrowstyle="-", 
                                    connectionstyle=config['connection'],
                                    color='gray', lw=1.5),
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="gray", lw=1, alpha=0.8),
                    horizontalalignment=config['alignment'], verticalalignment="center",
                    fontsize=font_size)
    
    # Set title (smaller font for email)
    title_font_size = 12 if ax is not None and ax.figure.get_figwidth() < 10 else 28
    if title is not None:
        ax.set_title(title, fontsize=title_font_size, pad=10)
    else:
        total_years = power_stats['TotalYears'].iloc[0] if 'TotalYears' in power_stats.columns else 0
        ax.set_title(f'Pie Chart of Power Modes\nTotal Operational Time: {total_years} years', fontsize=title_font_size, pad=10)
    
    ax.axis('equal')
    
    # Save if path provided
    if path_save is not None:
        plt.tight_layout()
        plt.savefig(path_save)
        if ax is None:  # Only close if we created the figure
            plt.close()
    
    # Show the plot if requested
    if show_plot:
        plt.tight_layout()
        plt.show()
    
    return fig, ax


def plot_power_bar_chart(power_stats, ax=None, show_plot=False, title=None, fixed_scale=True, path_save=None):
    """
    Plot a bar chart of power modes.
    
    Args:
        power_stats: DataFrame with power mode statistics (must have columns: HighPercent, MediumPercent, LowPercent, CriticalPercent, TotalYears)
        ax: Matplotlib axis to plot on. If None, a new one will be created.
        show_plot: If True, plt.show() will be called to display the plot
        title: Optional custom title. If None, a default title will be used.
        fixed_scale: If True, x-axis will be fixed at 0-100% for consistent comparison
        path_save: Optional path to save the chart. If None, chart is not saved.
        
    Returns:
        fig, ax: The figure and axis with the bar chart
    """
    # Create a new figure and axis if needed
    if ax is None:
        fig, ax = plt.subplots(figsize=(14, 12))
    else:
        fig = ax.figure
    
    # Define color palette
    palette = {
        'High': 'tab:green',
        'Medium': 'tab:blue',
        'Low': 'tab:orange',
        'Critical': 'tab:red'
    }
    
    # Get data for bar chart
    modes = ['High', 'Medium', 'Low', 'Critical']
    values = [
        power_stats['HighPercent'].iloc[0] if 'HighPercent' in power_stats.columns else 0,
        power_stats['MediumPercent'].iloc[0] if 'MediumPercent' in power_stats.columns else 0,
        power_stats['LowPercent'].iloc[0] if 'LowPercent' in power_stats.columns else 0,
        power_stats['CriticalPercent'].iloc[0] if 'CriticalPercent' in power_stats.columns else 0
    ]
    colors = [palette[mode] for mode in modes]
    
    # Create horizontal bar chart
    bars = ax.barh(
        modes,
        values,
        color=colors,
        height=0.5,
        edgecolor='white',
        linewidth=1
    )
    
    # Add value labels always outside the bar
    for bar, value in zip(bars, values):
        ax.text(
            value + 2,  # More offset to ensure visibility
            bar.get_y() + bar.get_height()/2,
            f'{value:.2f}%',
            va='center',
            fontsize=20
        )
    
    # Set title
    if title is not None:
        ax.set_title(title, fontsize=28, pad=20)
    else:
        total_years = power_stats['TotalYears'].iloc[0] if 'TotalYears' in power_stats.columns else 0
        ax.set_title(f'Bar Chart of Power Modes\nTotal Operational Time: {total_years} years', fontsize=28, pad=20)
    
    ax.grid(axis='x', linestyle='--', alpha=0.7)
    
    # Set x-axis limits: fixed scale (0-100%) or dynamic
    if fixed_scale:
        ax.set_xlim(0, 110)  # Fixed scale from 0 to 100% with extra room for labels
        
        # Add more tick points for better readability
        ax.set_xticks([0, 25, 50, 75, 100])
        ax.set_xticklabels(['0%', '25%', '50%', '75%', '100%'])
    else:
        ax.set_xlim(0, max(values) * 1.3)  # Dynamic scale with extra padding for labels
    
    ax.set_xlabel("Percentage (%) of Time in Operation", fontsize=24, labelpad=20)
    ax.tick_params(axis='both', which='major', labelsize=24, width=0, length=10)
    
    # Save if path provided
    if path_save is not None:
        plt.tight_layout()
        plt.savefig(path_save)
        if ax is None:  # Only close if we created the figure
            plt.close()
    
    # Show the plot if requested
    if show_plot:
        plt.tight_layout()
        plt.show()
    
    return fig, ax


def plot_power_stats_combined(power_stats, list_name='', path_save=None):
    """
    Create a combined plot with pie chart and bar chart for power mode statistics.
    
    Args:
        power_stats: DataFrame with power mode statistics
        list_name: Name to display in the title
        path_save: Optional path to save the chart. If None, chart is not saved.
        
    Returns:
        fig: The figure with the combined plots
    """
    # Original size for quality - will be scaled down in email HTML
    H = 12
    W = H + 8
    
    # Create figure and subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(W, H), gridspec_kw={'width_ratios': [1, 1.2]})
    
    # Plot pie chart on the first subplot
    plot_power_pie_chart(power_stats, ax=ax1)
    
    # Plot bar chart on the second subplot
    plot_power_bar_chart(power_stats, ax=ax2)
    
    # Add overall title
    total_years = power_stats['TotalYears'].iloc[0] if 'TotalYears' in power_stats.columns else 0
    plt.suptitle(f"{list_name} Total Operational Time: {total_years} years", fontsize=36)
    
    # Adjust layout
    plt.tight_layout()
    plt.subplots_adjust(top=0.85, wspace=0.3)  # Increase spacing between subplots
    
    # Save if path provided
    if path_save is not None:
        plt.savefig(path_save, dpi=150, bbox_inches='tight')
        plt.close()
    
    return fig