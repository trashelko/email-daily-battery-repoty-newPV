"""
Data visualization functions for battery reports.
"""

import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

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
    label_offset = len(df) * 0.007 if len(df) > 0 else 1
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
    plt.title(f"Tracker Battery Power Zones\n{list_name} ({len(df)}) devices\nSnapshot of {report_date}")
    
    plt.tight_layout()
    plt.savefig(path_save)
    plt.close()

    return path_save