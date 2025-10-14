"""
Daily battery report generation logic.
"""

import pandas as pd
import os
from data_processing.visualization import create_snapshot_chart
from data_processing.parsing import process_debug_smbs_data, process_smbs_data
from database.queries import get_latest_batt, get_latest_voltage
from data_processing.file_operations import save_df_with_metadata, read_df_with_metadata, get_report_filename
from data_processing.data_filters import get_new_pv_panel_devices
from utils import prompt_for_date

def generate_battery_snapshot_report(manual_mode=False, use_old_query=False, specific_date=None):
    """
    Generate battery snapshot report for a specific date or latest data.
    
    Args:
        manual_mode (bool): If True and no specific_date, prompt user for date
        use_old_query (bool): If True, use original query implementation
        specific_date (str): Date in 'YYYY-MM-DD' format, or None for latest
        
    Returns:
        str: Report date string (e.g., "15 Jan")
    """
    if manual_mode and specific_date is None:
        specific_date = prompt_for_date()

    # Generate report date string
    if specific_date:
        date_obj = pd.to_datetime(specific_date, format="%Y-%m-%d")
        report_date = date_obj.strftime('%-d%b%y')
    else:
        report_date = pd.Timestamp.today().strftime('%-d%b%y')
    
    # Define file paths
    path_csv = get_report_filename(specific_date, use_old_query)

    # Check if we already have a report for this date
    if os.path.exists(path_csv):
        print(f"Loading existing report for {report_date}")
        latest_batt, _ = read_df_with_metadata(path_csv)
    else:
        # Choose query implementation based on flag
        if use_old_query:
            print(f"Generating new report for {report_date} using DebugSMBs database")
            latest_batt, query_time = get_latest_batt(specific_date)
            latest_batt = process_debug_smbs_data(latest_batt)
        else:
            print(f"Generating new report for {report_date} using SMBs database")
            latest_batt, query_time = get_latest_voltage(specific_date)
            latest_batt = process_smbs_data(latest_batt)
        
        save_df_with_metadata(latest_batt, query_time, path_csv)
    
    # Generate chart
    new_pv_devices = get_new_pv_panel_devices(latest_batt)
    IDs_newPV = list(new_pv_devices['DeviceID'])
    path_save_chart = f"latest_batt_reports/charts/snapshot_{report_date}.png"
    create_snapshot_chart(latest_batt, IDs_newPV, report_date, paired=True, list_name="NewPV & 6000+ Series", path_save=path_save_chart)

    return report_date

def test_main():
    """
    Test function to verify database connection and data retrieval.
    """
    from database.queries import get_test_query
    
    path_csv = "latest_batt_reports/latest_batt_reports/test_report.csv"

    if os.path.exists(path_csv):
        test_df, query_time = read_df_with_metadata(path_csv)
        print(query_time, 's')
    else:
        test_df, query_time = get_test_query()
        save_df_with_metadata(test_df, query_time, path_csv)
