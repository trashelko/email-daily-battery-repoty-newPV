"""
Data filtering functions for processing of battery data.
"""

import pandas as pd
from battery_analysis import is_6000

def filter_df_for_newPV(latest_batt):
    """
    Filter DataFrame to include only new PV devices and 6000+ series devices.
    
    Args:
        latest_batt (pandas.DataFrame): Battery data DataFrame
        
    Returns:
        list: List of DeviceIDs that match the filtering criteria
    """
    df = latest_batt

    # Import list of new panel IDs
    csv_filename = "ZIM-New Panel (Mila).csv"
    path_newPV_mila = csv_filename
    newPV_mila = pd.read_csv(path_newPV_mila)
    IDs_newPV_mila = list(newPV_mila['DeviceID'])

    # Define filtering conditions
    cond_inList = (df['DeviceID'].isin(IDs_newPV_mila))
    cond_6000 = (df['DeviceID'].apply(is_6000))
    cond_paired = (df['DeviceID'] != df['DeviceName'])
    cond_lastSeen = abs(pd.Timestamp.today() - df['EventTimeUTC']) <= pd.Timedelta(weeks=12)

    # Apply filters: (newPV OR 6000+) AND paired AND seen recently
    df_filtered = df[(cond_inList | cond_6000) & cond_paired & cond_lastSeen]

    return list(df_filtered['DeviceID'])

def get_LOW_latest_batt(latest_batt):
    """
    Filter DataFrame to get devices with low battery power modes.
    
    Args:
        latest_batt (pandas.DataFrame): Battery data DataFrame
        
    Returns:
        pandas.DataFrame: Filtered DataFrame with low battery devices
    """
    df = latest_batt
    IDs_newPV = filter_df_for_newPV(latest_batt)
    
    # Define power mode conditions
    cond_powerMode = (df['PowerMode'].isin(['Critical', 'Low', 'Medium']))
    cond_newPV = (df['DeviceID'].isin(IDs_newPV))
    
    # Apply filters: newPV devices AND low power mode
    latest_batt_LOW = df[cond_newPV & cond_powerMode]

    return latest_batt_LOW
