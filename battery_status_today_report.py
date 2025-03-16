from battery_analysis import (is_6000,create_snapshot_chart,get_ready_latest_batt)
from credentials import DB_CONFIG
from utils import prompt_for_date

import pandas as pd
# import matplotlib.pyplot as plt
import pyodbc
from datetime import datetime
import time
import os
import sys

# base_dir = "/Users/rasheltublin/Desktop/Hoopo/ZIM pilot/newPV battery report"

conn = pyodbc.connect(
        f'DRIVER={{ODBC Driver 17 for SQL Server}};'
        f'SERVER={DB_CONFIG["server"]};'
        f'DATABASE={DB_CONFIG["database"]};'
        f'UID={DB_CONFIG["username"]};'
        f'PWD={DB_CONFIG["password"]};'
        'Encrypt=yes;'
        'TrustServerCertificate=yes;'
    )

def get_test_query():
    query_test = """
    SELECT TOP 1000
        [DeviceID],
        [DeviceName],
        [EventTimeUTC],
        [PayloadData]
    FROM [dbo].[Bursts]
    WHERE CustomerName = 'Zim'
    ORDER BY [EventTimeUTC] DESC;
        """
    
    start_time = time.time()
    test_df = pd.read_sql(query_test, conn)
    conn.close()
    query_time = time.time() - start_time

    return test_df, query_time

def get_latest_batt(specific_date=None):
    """
    Get the latest battery status.
    """
    if specific_date is None:
        # Get the most recent data up to now, looking back 4 months
        query_latest_batt = """
            WITH LatestBursts AS (
                SELECT
                    [DeviceID],
                    [DeviceName],
                    [EventTimeUTC],
                    [PayloadData],
                    ROW_NUMBER() OVER (PARTITION BY [DeviceID] ORDER BY [EventTimeUTC] DESC) AS rn
                FROM [dbo].[Bursts]
                WHERE
                    CustomerName = 'Zim'
                    AND FPort = 1
                    AND DeviceID LIKE 'A0%'
                    AND PayloadData LIKE '%Battery Level%'
                    AND PayloadData NOT LIKE '%Battery Level 0%'
                    AND EventTimeUTC >= DATEADD(MONTH, -4, GETUTCDATE())
            )
            SELECT
                [DeviceID],
                [DeviceName],
                [EventTimeUTC],
                [PayloadData]
            FROM LatestBursts
            WHERE rn = 1
            ORDER BY [EventTimeUTC] DESC;
            """
    else:
        # Convert specific_date to datetime object for noon
        date_obj = datetime.strptime(specific_date, "%Y-%m-%d")
        noon_datetime = date_obj.replace(hour=12, minute=0, second=0)
        target_datetime = noon_datetime.strftime("%Y-%m-%d %H:%M:%S")
        
        # Get the latest data for each device up to noon on the specified date, looking back 4 months
        query_latest_batt = f"""
            WITH LatestBursts AS (
                SELECT
                    [DeviceID],
                    [DeviceName],
                    [EventTimeUTC],
                    [PayloadData],
                    ROW_NUMBER() OVER (PARTITION BY [DeviceID] ORDER BY [EventTimeUTC] DESC) AS rn
                FROM [dbo].[Bursts]
                WHERE
                    CustomerName = 'Zim'
                    AND FPort = 1
                    AND DeviceID LIKE 'A0%'
                    AND PayloadData LIKE '%Battery Level%'
                    AND PayloadData NOT LIKE '%Battery Level 0%'
                    AND EventTimeUTC <= '{target_datetime}'
                    AND EventTimeUTC >= DATEADD(MONTH, -4, CAST('{specific_date}' AS DATETIME))
            )
            SELECT
                [DeviceID],
                [DeviceName],
                [EventTimeUTC],
                [PayloadData]
            FROM LatestBursts
            WHERE rn = 1
            ORDER BY [EventTimeUTC] DESC;
            """
    
    start_time = time.time()
    latest_batt = pd.read_sql(query_latest_batt, conn)
    conn.close()
    query_time = time.time() - start_time
    
    return latest_batt, query_time

def save_df_with_metadata(df, query_time, path_csv):
   with open(path_csv, 'w') as f:
       f.write('### METADATA ###\n')
       f.write(f'query_time,{query_time}\n')
       f.write('### DATA ###\n')
       df.to_csv(f, index=False)

def read_df_with_metadata(path_csv):
    with open(path_csv, 'r') as f:
        f.readline()  # Skip separator
        query_time = float(f.readline().split(',')[1])
        f.readline()  # Skip separator
        df = pd.read_csv(f)
    
    df['EventTimeUTC'] = pd.to_datetime(df['EventTimeUTC'])
    return df, query_time

def filter_df_for_newPV(latest_batt):

    df = latest_batt

    # Import list of new panel IDs
    csv_filename = f"ZIM-New Panel (Mila).csv"
    # path_newPV_mila = os.path.join(base_dir, csv_filename)
    path_newPV_mila = csv_filename
    newPV_mila = pd.read_csv(path_newPV_mila)
    IDs_newPV_mila = list(newPV_mila['DeviceID'])

    cond_inList = (df['DeviceID'].isin(IDs_newPV_mila))
    cond_6000 = (df['DeviceID'].apply(is_6000))
    cond_paired = (df['DeviceID'] != df['DeviceName'])
    cond_lastSeen = abs(pd.Timestamp.today() - df['EventTimeUTC']) <= pd.Timedelta(weeks=12)

    df_filtered = df[(cond_inList | cond_6000) & cond_paired & cond_lastSeen]

    return list(df_filtered['DeviceID'])

def get_LOW_latest_batt(latest_batt):
    df = latest_batt
    IDs_newPV = filter_df_for_newPV(latest_batt)
    cond_powerMode = (df['PowerMode'].isin(['Critical','Low','Medium']))
    cond_newPV = (df['DeviceID'].isin(IDs_newPV))
    latest_batt_LOW = df[cond_newPV & cond_powerMode]

    return latest_batt_LOW

def generate_battery_snapshot_report(manual_mode=False, specific_date=None):
    
    if manual_mode and specific_date is None:
        specific_date = prompt_for_date()

    if specific_date:
        date_obj = pd.to_datetime(specific_date, format="%Y-%m-%d")
        report_date = date_obj.strftime('%-d %b')
    else:
        report_date = pd.Timestamp.today().strftime('%-d %b')
    
    csv_filename = f"latest_batt_reports/latest_batt_{report_date.replace(' ', '')}.csv"
    path_csv = csv_filename

    # Check if we already have a report for this date
    if os.path.exists(path_csv):
        print(f"Loading existing report for {report_date}")
        latest_batt, _ = read_df_with_metadata(path_csv)
    else:
        print(f"Generating new report for {report_date}")
        latest_batt, query_time = get_latest_batt(specific_date)
        latest_batt = get_ready_latest_batt(latest_batt)
        save_df_with_metadata(latest_batt, query_time, path_csv)
    
    IDs_newPV = filter_df_for_newPV(latest_batt)
    path_save_chart = f"latest_batt_reports/charts/snapshot_{report_date.replace(' ', '')}.png"
    create_snapshot_chart(latest_batt, IDs_newPV, report_date, paired=True, list_name="NewPV & 6000+ Series", path_save = path_save_chart)

    return report_date


if __name__ == "__main__":
    # Check if --manual flag is present
    manual_mode = "--manual" in sys.argv
    generate_battery_snapshot_report(manual_mode)





# OLD VERSIONS

def test_main():
    path_csv = "latest_batt_reports/latest_batt_reports/test_report.csv"

    if os.path.exists(path_csv):
        test_df, query_time = read_df_with_metadata(path_csv)
        print(query_time,'s')
    else:
        test_df, query_time = get_test_query()
        save_df_with_metadata(test_df, query_time, path_csv)

def get_latest_batt_old():

    query_latest_batt_old = """
        WITH LatestBursts AS (
            SELECT
                [DeviceID],
                [DeviceName],
                [EventTimeUTC],
                [PayloadData],
                ROW_NUMBER() OVER (PARTITION BY [DeviceID] ORDER BY [EventTimeUTC] DESC) AS rn
            FROM [dbo].[Bursts]
            WHERE
                CustomerName = 'Zim'
                AND FPort = 1
                AND DeviceID LIKE 'A0%'
                AND PayloadData LIKE '%Battery Level%'
                AND PayloadData NOT LIKE '%Battery Level 0%'
                -- AND DeviceID != DeviceName
        )
        SELECT
            [DeviceID],
            [DeviceName],
            [EventTimeUTC],
            [PayloadData]
        FROM LatestBursts
        WHERE rn = 1
        ORDER BY [EventTimeUTC] DESC;
        """

    query_latest_batt = """
        WITH LatestBursts AS (
            SELECT
                [DeviceID],
                [DeviceName],
                [EventTimeUTC],
                [PayloadData],
                ROW_NUMBER() OVER (PARTITION BY [DeviceID] ORDER BY [EventTimeUTC] DESC) AS rn
            FROM [dbo].[Bursts]
            WHERE
                CustomerName = 'Zim'
                AND FPort = 1
                AND DeviceID LIKE 'A0%'
                AND PayloadData LIKE '%Battery Level%'
                AND PayloadData NOT LIKE '%Battery Level 0%'
                AND EventTimeUTC >= DATEADD(MONTH, -4, GETUTCDATE())
        )
        SELECT
            [DeviceID],
            [DeviceName],
            [EventTimeUTC],
            [PayloadData]
        FROM LatestBursts
        WHERE rn = 1
        ORDER BY [EventTimeUTC] DESC;
        """
    
    start_time = time.time()
    latest_batt = pd.read_sql(query_latest_batt, conn)
    conn.close()
    query_time = time.time() - start_time
    
    return latest_batt, query_time