import pandas as pd
import pyodbc
import time
import warnings
from datetime import datetime
from .credentials import DB_DebugSMBs_CONFIG, DB_SMBs_CONFIG

# Suppress pandas warning about pyodbc connections (works fine, just not officially tested)
warnings.filterwarnings('ignore', message='.*pandas only supports SQLAlchemy.*', category=UserWarning)

def get_db_connection(config=None):
    """
    Create and return a database connection.
    
    Args:
        config (dict, optional): Database configuration. If None, uses DebugSMBs_CONFIG.
    
    Returns:
        pyodbc.Connection: Database connection object
    """
    if config is None:
        config = DB_DebugSMBs_CONFIG
    
    return pyodbc.connect(
        f'DRIVER={{ODBC Driver 17 for SQL Server}};'
        f'SERVER={config["server"]};'
        f'DATABASE={config["database"]};'
        f'UID={config["username"]};'
        f'PWD={config["password"]};'
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

    # Build date filter if specific_date is provided
    date_filter = ""
    if specific_date:
        date_obj = datetime.strptime(specific_date, "%Y-%m-%d")
        noon_datetime = date_obj.replace(hour=12, minute=0, second=0)
        target_datetime = noon_datetime.strftime("%Y-%m-%d %H:%M:%S")
        date_filter = f"AND EventTimeUTC <= '{target_datetime}'"
    
    # Get the latest data for each device, looking back 4 months
    query_latest_batt = f"""
        WITH LatestBursts AS (
            SELECT
                [DeviceID],
                [DeviceName],
                [EventTimeUTC],
                [PayloadData],
                ROW_NUMBER() OVER (PARTITION BY [DeviceID] ORDER BY [EventTimeUTC] DESC) AS rn
            FROM [dbo].[Bursts]
            WHERE 1=1
                AND CustomerName = 'Zim'
                AND FPort = 1
                AND DeviceID LIKE 'A0%'
                AND PayloadData LIKE '%Battery Level%'
                AND PayloadData NOT LIKE '%Battery Level 0%'
                AND EventTimeUTC >= DATEADD(MONTH, -4, {'GETUTCDATE()' if specific_date is None else f"CAST('{specific_date}' AS DATETIME)"})
                {date_filter}
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
    SMBs DATABASE QUERY: Get latest battery voltage data from SMBs database.
    This will be the new implementation using SMBs database and BatteryInfo table.
    
    Args:
        specific_date (str, optional): Date in 'YYYY-MM-DD' format. If None, gets latest data.
    
    Returns:
        tuple: (DataFrame, query_time_seconds)
    """
    conn = get_db_connection(DB_SMBs_CONFIG)
    
    # Build date filter if specific_date is provided
    date_filter = ""
    if specific_date:
        target_datetime = pd.to_datetime(specific_date).strftime('%Y-%m-%d %H:%M:%S')
        date_filter = f"AND b.EventTime <= '{target_datetime}'"
    
    query_latest_voltage = f"""
        WITH LatestReport AS (
        SELECT
            b.[ID] AS ReportID
            ,b.[OrganizationId]
            ,o.Name AS CustomerName
            ,b.[AssetId]
            ,a.DeviceName AS DeviceID
            ,a.Name AS DeviceName
            ,b.[EventTime] AS EventTimeUTC
            ,b.[Voltage]
            ,ROW_NUMBER() OVER (PARTITION BY b.AssetID ORDER BY b.[EventTime] DESC, b.ID DESC) AS rn
        FROM [dbo].[BatteryInfo] AS b
        LEFT JOIN [dbo].[Assets] AS a ON b.AssetId = a.ID
        LEFT JOIN [dbo].[Organizations] AS o ON b.OrganizationId = o.ID
        WHERE b.[Voltage] > 2
        {date_filter}
        )
        SELECT 
            ReportID
            ,OrganizationId
            ,CustomerName
            ,AssetId
            ,DeviceID
            ,DeviceName
            ,EventTimeUTC
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

def get_active_devices(device_type="hoopoSense Solar"):
    """
    Query active devices from AssetsView table.
    
    Args:
        device_type (str): Device type to filter by. Default is "hoopoSense Solar".
    
    Returns:
        tuple: (DataFrame with active devices, query_time_seconds)
    """
    conn = get_db_connection(DB_SMBs_CONFIG)
    
    query_active_devices = f"""
    SELECT 
        [AssetId],
        [DeviceName] AS DeviceID,
        [AssetName] AS DeviceName,
        [OrganizationId],
        [OrgName],
        [DeviceType],
        [DeviceStatus]
    FROM [dbo].[AssetsView]
    WHERE DeviceType = '{device_type}'
        AND DeviceStatus = 'Active'
    ORDER BY [OrgName], [DeviceName]
    """
    
    start_time = time.time()
    active_devices_df = pd.read_sql(query_active_devices, conn)
    conn.close()
    query_time = time.time() - start_time
    
    return active_devices_df, query_time

def get_power_mode_statistics(organization_id=None, exclude_asset_group_id=None, device_type="hoopoSense Solar"):
    """
    Get power mode statistics (total years and percentages) for devices.
    
    Args:
        organization_id (int, optional): Filter by OrganizationId. If None, includes all active devices.
        exclude_asset_group_id (int, optional): Exclude devices from this AssetGroupId. If None, no exclusion.
        device_type (str): Device type to filter by. Default is "hoopoSense Solar".
    
    Returns:
        tuple: (DataFrame with statistics, query_time_seconds)
    """
    conn = get_db_connection(DB_SMBs_CONFIG)
    
    # Build organization filter
    org_filter = ""
    if organization_id is not None:
        org_filter = f"AND BI.OrganizationId = {organization_id}"
    
    # Build asset group exclusion filter
    asset_group_filter = ""
    if exclude_asset_group_id is not None:
        asset_group_filter = f"""
        AND BI.AssetId IN (
            SELECT ID FROM [dbo].[Assets] 
            WHERE OrganizationId = {organization_id if organization_id is not None else 'BI.OrganizationId'} 
            AND AssetGroupId != {exclude_asset_group_id}
        )
        """
    
    query = f"""
    WITH PowerModeSegments AS (
        SELECT 
            BI.AssetId,
            BI.EventTime,
            BI.Voltage,
            CASE 
                WHEN BI.Voltage >= 3.3 THEN 'High'
                WHEN BI.Voltage >= 3.22 THEN 'Medium' 
                WHEN BI.Voltage >= 3.18 THEN 'Low'
                ELSE 'Critical'
            END as PowerMode,
            LEAD(BI.EventTime) OVER (PARTITION BY BI.AssetId ORDER BY BI.EventTime) as NextTime
        FROM [dbo].[BatteryInfo] AS BI
        WHERE 1=1
        {org_filter}
        -- FILTER: Active devices only
        AND BI.AssetId IN (
            SELECT AssetId FROM dbo.AssetsView 
            WHERE DeviceStatus = 'Active' AND DeviceType = '{device_type}'
        )
        {asset_group_filter}
    ),
    DurationCalculation AS (
        SELECT 
            AssetId,
            PowerMode,
            -- Calculate duration in hours (much smaller numbers)
            CASE 
                WHEN NextTime IS NOT NULL 
                THEN CAST(DATEDIFF(minute, EventTime, NextTime) AS FLOAT) / 60.0
                ELSE 0 
            END as DurationHours
        FROM PowerModeSegments
        WHERE NextTime IS NOT NULL  -- Exclude last reading per device
    )
    SELECT 
        -- Convert to years at the end
        CAST(ROUND(SUM(DurationHours) / (365.0 * 24), 0) AS INT) as TotalYears,
        
        CASE 
            WHEN SUM(DurationHours) > 0 
            THEN ROUND(SUM(CASE WHEN PowerMode = 'High' THEN DurationHours ELSE 0 END) * 100.0 / SUM(DurationHours), 2)
            ELSE 0.00
        END as HighPercent,
        
        CASE 
            WHEN SUM(DurationHours) > 0 
            THEN ROUND(SUM(CASE WHEN PowerMode = 'Medium' THEN DurationHours ELSE 0 END) * 100.0 / SUM(DurationHours), 2)
            ELSE 0.00 
        END as MediumPercent,
        
        CASE 
            WHEN SUM(DurationHours) > 0 
            THEN ROUND(SUM(CASE WHEN PowerMode = 'Low' THEN DurationHours ELSE 0 END) * 100.0 / SUM(DurationHours), 2)
            ELSE 0.00
        END as LowPercent,
        
        CASE 
            WHEN SUM(DurationHours) > 0 
            THEN ROUND(SUM(CASE WHEN PowerMode = 'Critical' THEN DurationHours ELSE 0 END) * 100.0 / SUM(DurationHours), 2)
            ELSE 0.00
        END as CriticalPercent
        
    FROM DurationCalculation
    """
    
    start_time = time.time()
    stats_df = pd.read_sql(query, conn)
    conn.close()
    query_time = time.time() - start_time
    
    return stats_df, query_time

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
