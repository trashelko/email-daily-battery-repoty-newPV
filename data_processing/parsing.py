"""
Data parsing and extraction functions for battery data.
"""

import pandas as pd
import numpy as np

def detect_date_format(date_series):
    """
    Detect the date format of a pandas Series.
    
    Args:
        date_series (pandas.Series): Series containing date strings
        
    Returns:
        str or None: Date format string if detected, None otherwise
    """
    for fmt in ["%Y-%m-%d %H:%M:%S.%f", '%d/%m/%Y %H:%M', '%m/%d/%Y %H:%M']:
        try:
            pd.to_datetime(date_series, format=fmt)
            return fmt
        except ValueError: 
            continue
    return None

def extract_voltage_fport1(payload_col):
    """
    Extract voltage values from payload data using vectorized operations.
    
    Args:
        payload_col (pandas.Series): Series containing payload data
        
    Returns:
        pandas.Series: Series containing extracted voltage values
    """
    return payload_col.str.extract(r'Battery Level (\d+\.\d+)', expand=False)

def extract_power_mode(payload_col):
    """
    Extract power mode from payload data.
    
    Args:
        payload_col (pandas.Series): Series containing payload data
        
    Returns:
        pandas.Series: Series containing extracted power modes
    """
    return payload_col.str.extract(r'Power mode (\w+)', expand=False).fillna('None')

def is_6000(ID):
    """
    Check if device ID belongs to 6000+ series.
    
    Args:
        ID (str): Device ID string
        
    Returns:
        bool: True if device is 6000+ series, False otherwise
    """
    if len(ID) < 4 or not ID[-4:].isdigit():
        return False
    return int(ID[-4:]) >= 6000

def get_ready_latest_batt(latest_batt):
    """
    Process battery data to extract voltage, power mode, and clean data.
    
    Args:
        latest_batt (pandas.DataFrame): Raw battery data DataFrame
        
    Returns:
        pandas.DataFrame: Processed battery data with Voltage and PowerMode columns
    """
    # Extract voltage from payload data
    latest_batt['Voltage'] = extract_voltage_fport1(latest_batt['PayloadData'])
    latest_batt['Voltage'] = pd.to_numeric(latest_batt['Voltage'], errors='coerce')
    
    # Handle non-numeric voltage values
    non_numeric_rows = latest_batt[latest_batt['Voltage'].isna()]
    if non_numeric_rows.empty:
        print('All rows have a numeric value for Voltage.')
    else:
        print("Some rows had non-numeric values for Voltage, see these in variable 'non_numeric_rows', cleaned.")
        latest_batt = latest_batt[~latest_batt['Voltage'].isna()]

    # Convert EventTimeUTC to datetime
    fmt = detect_date_format(latest_batt['EventTimeUTC'])
    latest_batt['EventTimeUTC'] = pd.to_datetime(latest_batt['EventTimeUTC'], format=fmt)
    print('EventTimeUTC is in DateTime-format.')

    # Extract and clean power mode
    crit_level = 3.18
    latest_batt['PowerMode'] = extract_power_mode(latest_batt['PayloadData'])
    
    # Handle devices with wrong/no power mode labels
    wrong_labels = list(set(latest_batt['PowerMode'].unique()) - set(['High', 'Medium', 'Low', 'Critical']))
    mask = latest_batt['PowerMode'].isin(wrong_labels)
    print(f"There are {len(latest_batt[mask])} trackers out of {len(latest_batt)} paired trackers which don't have a well-defined 'Power mode' in the payload data but instead have:")
    print(wrong_labels)

    # Assign power modes based on voltage thresholds
    conditions = [
        (latest_batt.loc[mask,'Voltage'] > 3.3),
        (latest_batt.loc[mask,'Voltage'] > 3.22) & (latest_batt.loc[mask,'Voltage'] <= 3.3),
        (latest_batt.loc[mask,'Voltage'] > crit_level) & (latest_batt.loc[mask,'Voltage'] <= 3.22),
        (latest_batt.loc[mask,'Voltage'] <= crit_level)
    ]
    modes = np.array(['High', 'Medium', 'Low', 'Critical'], dtype=str)
    
    latest_batt.loc[mask, 'PowerMode'] = np.select(conditions, modes, default='Unknown')
    
    print(f"Added 'Power mode' for the ones with wrong/no labels under the same definitions (with critical at {crit_level}).")
    
    return latest_batt
