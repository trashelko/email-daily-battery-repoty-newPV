import pandas as pd
import pyodbc
import time
from datetime import datetime
from .credentials import DB_DebugSMBs_CONFIG

def get_db_connection():
    """
    Create and return a database connection.
    
    Returns:
        pyodbc.Connection: Database connection object
    """
    return pyodbc.connect(
        f'DRIVER={{ODBC Driver 17 for SQL Server}};'
        f'SERVER={DB_DebugSMBs_CONFIG["server"]};'
        f'DATABASE={DB_DebugSMBs_CONFIG["database"]};'
        f'UID={DB_DebugSMBs_CONFIG["username"]};'
        f'PWD={DB_DebugSMBs_CONFIG["password"]};'
        'Encrypt=yes;'
        'TrustServerCertificate=yes;'
    )

def get_test_query():
    """
    Test query to verify database connection and get sample data.
    
    Returns:
        tuple: (DataFrame, query_time_seconds)
    """
    conn = get_db_connection()
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
    Get the latest battery status using the original query implementation.
    
    Args:
        specific_date (str, optional): Date in 'YYYY-MM-DD' format. If None, gets latest data.
    
    Returns:
        tuple: (DataFrame, query_time_seconds)
    """
    conn = get_db_connection()

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

def get_latest_voltage(specific_date=None):
    """
    NEW OPTIMIZED QUERY: Get latest battery voltage data using optimized query.
    This is the new fast implementation using BatteryInfo table.
    
    Args:
        specific_date (str, optional): Date in 'YYYY-MM-DD' format. If None, gets latest data.
    
    Returns:
        tuple: (DataFrame, query_time_seconds)
    """
    conn = get_db_connection()
    
    # Build date filter if specific_date is provided
    date_filter = ""
    if specific_date:
        target_datetime = pd.to_datetime(specific_date).strftime('%Y-%m-%d %H:%M:%S')
        date_filter = f"AND b.EventTime <= '{target_datetime}'"
    
    query_latest_voltage = f"""
        WITH LatestReport AS (
        SELECT
            b.[ID]
            ,b.[OrganizationId]
            ,o.Name AS OrganizationName
            ,b.[AssetId]
            ,a.DeviceName AS DeviceID
            ,b.[EventTime]
            ,b.[Voltage]
            ,ROW_NUMBER() OVER (PARTITION BY b.AssetID ORDER BY b.[EventTime],b.ID DESC) AS rn
        FROM [dbo].[BatteryInfo] AS b
        LEFT JOIN [dbo].[Assets] AS a ON b.AssetId = a.ID
        LEFT JOIN [dbo].[Organizations] AS o ON b.OrganizationId = o.ID
        WHERE 1=1
        {date_filter}
        )
        SELECT 
            ID
            ,OrganizationId
            ,OrganizationName
            ,AssetId
            ,DeviceID
            ,EventTime
            ,Voltage
        FROM LatestReport
        WHERE rn = 1
        ORDER BY DeviceID;
        """
    
    start_time = time.time()
    latest_voltage_df = pd.read_sql(query_latest_voltage, conn)
    conn.close()
    query_time = time.time() - start_time
    
    return latest_voltage_df, query_time

def get_latest_batt_old():
    """
    OLD VERSION: Get latest battery status using the original implementation.
    This is kept for backward compatibility and comparison.
    
    Returns:
        tuple: (DataFrame, query_time_seconds)
    """
    conn = get_db_connection()
    
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
