"""
File Input/Output operations for battery data with metadata support.
"""

import pandas as pd
import os
from datetime import datetime

def save_df_with_metadata(df, query_time, path_csv):
    """
    Save DataFrame to CSV file with metadata header.
    
    Args:
        df (pandas.DataFrame): Data to save
        query_time (float): Query execution time in seconds
        path_csv (str): Path to save the CSV file
    """
    with open(path_csv, 'w') as f:
        f.write('### METADATA ###\n')
        f.write(f'query_time,{query_time}\n')
        f.write('### DATA ###\n')
        df.to_csv(f, index=False)

def read_df_with_metadata(path_csv):
    """
    Read DataFrame from CSV file with metadata header.
    
    Args:
        path_csv (str): Path to the CSV file
        
    Returns:
        tuple: (DataFrame, query_time_seconds)
    """
    with open(path_csv, 'r') as f:
        f.readline()  # Skip separator
        query_time = float(f.readline().split(',')[1])
        f.readline()  # Skip separator
        df = pd.read_csv(f)
    
    df['EventTimeUTC'] = pd.to_datetime(df['EventTimeUTC'])
    return df, query_time

def get_report_filename(date_str=None, use_old_query=True):
    """
    Generate standardized report filename.
    
    Args:
        date_str (str, optional): Date in 'YYYY-MM-DD' format. If None, uses today.
        use_old_query (bool): Whether using DebugSMBs (True) or SMBs (False) database
        
    Returns:
        str: Full path to the report file
    """
    if date_str:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        report_date = date_obj.strftime('%-d%b%y')
    else:
        report_date = datetime.now().strftime('%-d%b%y')
    
    # Add database indicator to filename
    db_suffix = "debug" if use_old_query else "smbs"
    filename = f"latest_batt_reports/latest_batt_{report_date}_{db_suffix}.csv"
    
    return filename