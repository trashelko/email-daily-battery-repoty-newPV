"""
Data filtering functions for processing of battery data.
"""

import pandas as pd
from .parsing import is_6000

def get_LOW_latest_batt(latest_batt):
    """
    Filter DataFrame to get devices with low battery power modes.
    
    Args:
        latest_batt (pandas.DataFrame): Battery data DataFrame
        
    Returns:
        pandas.DataFrame: Filtered DataFrame with low battery devices
    """
    df = latest_batt
    new_pv_devices = get_new_pv_panel_devices(latest_batt)
    IDs_newPV = list(new_pv_devices['DeviceID'])
    
    # Define power mode conditions
    cond_powerMode = (df['PowerMode'].isin(['Critical', 'Low', 'Medium']))
    cond_newPV = (df['DeviceID'].isin(IDs_newPV))
    
    # Apply filters: newPV devices AND low power mode
    latest_batt_LOW = df[cond_newPV & cond_powerMode]

    return latest_batt_LOW


def get_new_pv_panel_devices(latest_batt):
    """
    Filter DataFrame for Section 1: New PV Panel devices.
    Includes devices from Mila's list + CustomerName=ZIM with DeviceID starting with 'A0' and 6000+ in remaining numbers.
    
    Args:
        latest_batt (pandas.DataFrame): Battery data DataFrame
        
    Returns:
        pandas.DataFrame: Filtered DataFrame with New PV Panel devices
    """
    df = latest_batt
    df = df.dropna(subset=['DeviceID', 'DeviceName'])
    
    # Import list of new panel IDs from Mila's CSV
    csv_filename = "ZIM-New Panel (Mila).csv"
    path_newPV_mila = csv_filename
    newPV_mila = pd.read_csv(path_newPV_mila)
    IDs_newPV_mila = list(newPV_mila['DeviceID'])
    
    # Define filtering conditions
    cond_mila_list = df['DeviceID'].isin(IDs_newPV_mila)
    cond_a0_6000 = (df['DeviceID'].str.startswith('A0')) & (df['DeviceID'].apply(is_6000))
    cond_zim = df['CustomerName'].str.lower() == 'zim'
    cond_paired = df['DeviceID'] != df['DeviceName']
    cond_lastSeen = abs(pd.Timestamp.today() - df['EventTimeUTC']) <= pd.Timedelta(weeks=12)
    
    # Apply filters: (Mila list OR ZIM A0 6000+) AND paired AND seen recently
    df_filtered = df[(cond_mila_list | cond_a0_6000) & cond_zim & cond_paired & cond_lastSeen]
    
    return df_filtered

def get_zim_c_devices(latest_batt):
    """
    Filter DataFrame for Section 2: ZIM devices starting with 'C'.
    
    Args:
        latest_batt (pandas.DataFrame): Battery data DataFrame
        
    Returns:
        pandas.DataFrame: Filtered DataFrame with ZIM C devices
    """
    df = latest_batt
    df = df.dropna(subset=['DeviceID', 'DeviceName'])
    
    # Define filtering conditions
    cond_zim = df['CustomerName'].str.lower() == 'zim'
    cond_c_devices = df['DeviceID'].str.startswith('C')
    cond_paired = df['DeviceID'] != df['DeviceName']
    cond_lastSeen = abs(pd.Timestamp.today() - df['EventTimeUTC']) <= pd.Timedelta(weeks=12)
    
    # Apply filters: ZIM AND C devices AND paired AND seen recently
    df_filtered = df[cond_zim & cond_c_devices & cond_paired & cond_lastSeen]
    
    return df_filtered

def get_samskip_devices(latest_batt):
    """
    Filter DataFrame for Section 3: samskip devices.
    
    Args:
        latest_batt (pandas.DataFrame): Battery data DataFrame
        
    Returns:
        pandas.DataFrame: Filtered DataFrame with samskip devices
    """
    df = latest_batt
    df = df.dropna(subset=['DeviceID', 'DeviceName'])
    
    # Define filtering conditions
    cond_samskip = df['CustomerName'].str.lower() == 'samskip'
    cond_paired = df['DeviceID'] != df['DeviceName']
    cond_lastSeen = abs(pd.Timestamp.today() - df['EventTimeUTC']) <= pd.Timedelta(weeks=12)
    
    # Apply filters: samskip AND paired AND seen recently
    df_filtered = df[cond_samskip & cond_paired & cond_lastSeen]
    
    return df_filtered
