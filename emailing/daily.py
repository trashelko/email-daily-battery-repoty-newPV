"""
Daily battery report email functionality.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from emailing.credentials import EMAIL_CONFIG
from database.queries import get_active_devices
from reports.create_report_on_date import generate_battery_snapshot_report
from data_processing.file_operations import read_df_with_metadata, get_report_filename
from data_processing.data_filters import get_new_pv_panel_devices, get_zim_c_devices, get_samskip_devices, get_hmm_devices
from data_processing.visualization import create_snapshot_chart
from utils import prompt_for_date

import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
import smtplib
import io

def add_table_attachment(email, table_df, table_name, report_date):
    """
    Add a table as CSV attachment to the email.
    
    Args:
        email: MIMEMultipart email object
        table_df: pandas.DataFrame to attach
        table_name: Name for the attachment
        report_date: Date string for filename
    """
    if len(table_df) == 0:
        return
    
    # Create CSV in memory
    csv_buffer = io.StringIO()
    table_df.to_csv(csv_buffer, index=False)
    csv_data = csv_buffer.getvalue().encode('utf-8')
    csv_buffer.close()
    
    # Create attachment
    attachment = MIMEBase('text', 'csv')
    attachment.set_payload(csv_data)
    encoders.encode_base64(attachment)
    attachment.add_header(
        'Content-Disposition',
        f'attachment; filename="{table_name}_{report_date}.csv"'
    )
    email.attach(attachment)

def get_table_html_with_limit(table_df, limit=30):
    """
    Get HTML representation of table with optional row limit.
    
    Args:
        table_df: pandas.DataFrame to convert to HTML
        limit: Maximum number of rows to display (None for no limit)
        
    Returns:
        tuple: (html_string, has_more_rows, total_rows)
    """
    if len(table_df) == 0:
        return '<p>No devices found below high.</p>', False, 0
    
    total_rows = len(table_df)
    
    if limit is None or total_rows <= limit:
        return table_df.to_html(index=False), False, total_rows
    
    # Show only first 'limit' rows
    limited_df = table_df.head(limit)
    html = limited_df.to_html(index=False)
    return html, True, total_rows

def email_daily_report(manual_mode=False, use_old_query=False):
    """
    Send daily battery report via email.
    
    Args:
        manual_mode (bool): If True, prompt for specific date
        use_old_query (bool): If True, use original query implementation
    """
    specific_date = None
    if manual_mode:
        specific_date = prompt_for_date()
    
    # Generate the report
    report_date = generate_battery_snapshot_report(manual_mode, use_old_query, specific_date)
    
    if not report_date:
        print("❌ Failed to generate report")
        return
    
    # File paths
    path_csv = get_report_filename(specific_date, use_old_query)

    # Read the generated data
    latest_batt, query_time = read_df_with_metadata(path_csv)
    
    # Query active devices (only for SMBs database, skip for old query)
    # Query all active devices once, then filter in Python (can't include large lists in SQL)
    active_device_ids = None
    if not use_old_query:
        try:
            active_devices_df, _ = get_active_devices()
            # Get set of active device IDs (DeviceID only - filtering done in Python)
            active_device_ids = set(active_devices_df['DeviceID'].dropna().tolist())
            print(f"✅ Found {len(active_device_ids)} active devices")
        except Exception as e:
            print(f"⚠️ Warning: Could not query active devices: {e}")
            print("   Continuing without active device filtering")
            active_device_ids = None
    
    # Get section data (filtered by active devices if available)
    new_pv_devices = get_new_pv_panel_devices(latest_batt, active_device_ids)
    new_pv_counts = new_pv_devices['PowerMode'].value_counts().to_dict() if len(new_pv_devices) > 0 else {}
    
    zim_c_devices = get_zim_c_devices(latest_batt, active_device_ids)
    zim_c_counts = zim_c_devices['PowerMode'].value_counts().to_dict() if len(zim_c_devices) > 0 else {}
    
    samskip_devices = get_samskip_devices(latest_batt, active_device_ids)
    samskip_counts = samskip_devices['PowerMode'].value_counts().to_dict() if len(samskip_devices) > 0 else {}
    
    hmm_devices = get_hmm_devices(latest_batt, active_device_ids)
    hmm_counts = hmm_devices['PowerMode'].value_counts().to_dict() if len(hmm_devices) > 0 else {}
    
    # Create section charts (only if devices exist)
    chart_paths = {}
    
    # Section 1: New PV Panel - show all power modes
    if len(new_pv_devices) > 0:
        new_pv_ids = list(new_pv_devices['DeviceID'])
        chart_paths['new_pv'] = create_snapshot_chart(
            latest_batt, 
            new_pv_ids, 
            report_date, 
            paired=True, 
            list_name="New PV Panel", 
            path_save=f"latest_batt_reports/charts/new_pv_panel_{report_date}.png"
        )
    
    # Section 2: ZIM C Devices - show all power modes
    if len(zim_c_devices) > 0:
        zim_c_ids = list(zim_c_devices['DeviceID'])
        chart_paths['zim_c'] = create_snapshot_chart(
            latest_batt, 
            zim_c_ids, 
            report_date, 
            paired=True, 
            list_name="ZIM C-series Devices", 
            path_save=f"latest_batt_reports/charts/zim_c_devices_{report_date}.png"
        )
    
    # Section 3: samskip Devices - show all power modes
    if len(samskip_devices) > 0:
        samskip_ids = list(samskip_devices['DeviceID'])
        chart_paths['samskip'] = create_snapshot_chart(
            latest_batt, 
            samskip_ids, 
            report_date, 
            paired=True,
            list_name="Samskip Devices", 
            path_save=f"latest_batt_reports/charts/samskip_devices_{report_date}.png"
        )
    
    # Section 4: HMM Devices - show all power modes
    if len(hmm_devices) > 0:
        hmm_ids = list(hmm_devices['DeviceID'])
        chart_paths['hmm'] = create_snapshot_chart(
            latest_batt, 
            hmm_ids, 
            report_date, 
            paired=True,
            list_name="HMM Devices", 
            path_save=f"latest_batt_reports/charts/hmm_devices_{report_date}.png"
        )
    
    # Prepare data for tables
    # Section 1: New PV Panel - all critical, low, medium
    new_pv_table = new_pv_devices[new_pv_devices['PowerMode'].isin(['Critical', 'Low', 'Medium'])].copy()
    new_pv_table = new_pv_table.drop(['PayloadData', 'index', 'AssetId', 'OrganizationId'], axis=1, errors='ignore')
    new_pv_table.sort_values(by='Voltage', inplace=True)
    
    # Section 2: ZIM C devices - only critical and low, but show medium count
    zim_c_table = zim_c_devices[zim_c_devices['PowerMode'].isin(['Critical', 'Low'])].copy()
    zim_c_table = zim_c_table.drop(['PayloadData', 'index', 'AssetId', 'OrganizationId'], axis=1, errors='ignore')
    zim_c_table.sort_values(by='Voltage', inplace=True)
    
    # Section 3: samskip devices - critical, low, and medium
    samskip_table = samskip_devices[samskip_devices['PowerMode'].isin(['Critical', 'Low', 'Medium'])].copy()
    samskip_table = samskip_table.drop(['PayloadData', 'index', 'AssetId', 'OrganizationId'], axis=1, errors='ignore')
    samskip_table.sort_values(by='Voltage', inplace=True)
    
    # Section 4: HMM devices - critical, low, and medium
    hmm_table = hmm_devices[hmm_devices['PowerMode'].isin(['Critical', 'Low', 'Medium'])].copy()
    hmm_table = hmm_table.drop(['PayloadData', 'index', 'AssetId', 'OrganizationId'], axis=1, errors='ignore')
    hmm_table.sort_values(by='Voltage', inplace=True)
    
    # Get HTML representations with row limits
    new_pv_html, new_pv_has_more, new_pv_total = get_table_html_with_limit(new_pv_table, 30)
    zim_c_html, zim_c_has_more, zim_c_total = get_table_html_with_limit(zim_c_table, 30)
    samskip_html, samskip_has_more, samskip_total = get_table_html_with_limit(samskip_table, 30)
    hmm_html, hmm_has_more, hmm_total = get_table_html_with_limit(hmm_table, 30)
    
    # Email content
    msg = f"Query took {int(query_time)} seconds"
    query_type = "DebugSMBs Database" if use_old_query else "SMBs Database"
    
    # Create email
    email = MIMEMultipart()
    email['From'] = EMAIL_CONFIG['sender']
    email['To'] = EMAIL_CONFIG['recipients'][0]
    
    # Format date for subject (e.g., "13 October")
    formatted_date = pd.to_datetime(report_date, format='%d%b%y').strftime('%-d %B')
    email['Subject'] = f"Daily Battery Report - {formatted_date}"

    # Add images (only for sections with data)
    for section, chart_path in chart_paths.items():
        with open(chart_path, 'rb') as f:
            img_data = f.read()
        img_part = MIMEImage(img_data)
        img_part.add_header('Content-ID', f'<{section}_chart>')
        email.attach(img_part)
    
    # Add CSV attachments for tables with more than 30 rows
    if new_pv_has_more:
        add_table_attachment(email, new_pv_table, "new_pv_panel_devices", report_date)
    if zim_c_has_more:
        add_table_attachment(email, zim_c_table, "zim_c_devices", report_date)
    if samskip_has_more:
        add_table_attachment(email, samskip_table, "samskip_devices", report_date)
    if hmm_has_more:
        add_table_attachment(email, hmm_table, "hmm_devices", report_date)
    
    # Helper function to get power mode counts
    def get_power_mode_text(counts):
        critical = counts.get('Critical', 0)
        low = counts.get('Low', 0)
        medium = counts.get('Medium', 0)
        return f"Critical: {critical}, Low: {low}, Medium: {medium}"
    
    # Add HTML content
    html = f"""
    <html>
        <body>
            <h2>Daily Battery Report - {query_type}</h2>
            <p><strong>Performance:</strong> {msg}</p>
            <br>
            
            <h3>Section 1: New PV Panel</h3>
            <p><strong>Devices included in the statistics below:</strong></p>
            <ul>
                <li>Devices from Mila's list</li>
                <li><strong>CustomerName = ZIM</strong> which are
                    <ul>
                        <li>paired</strong></li>
                        <li>DeviceID starting with <strong>'A0'</strong></li>
                        <li>DeviceID is 6000-series or higher</li>
                    </ul>
                </li>
                <li>Only include reports from the last 12 weeks</li>
                {'<li><strong>Device status = Active</strong> (filtered from AssetsView)</li>' if active_device_ids is not None else ''}
            </ul>
            <p><strong>Power Mode Counts:</strong> {get_power_mode_text(new_pv_counts)}</p>
            {'<img src="cid:new_pv_chart" style="display:block;"><br>' if 'new_pv' in chart_paths else ''}
            <h4>Critical, Low & Medium Battery Devices ({new_pv_total} devices):</h4>
            {f'<p><em>Showing first 30 of {new_pv_total} devices. Full data attached as CSV.</em></p>' if new_pv_has_more else ''}
            {new_pv_html}
            <br><br>
            
            <h3>Section 2: ZIM C-Series Devices</h3>
            <p><strong>Devices included in the statistics below:</strong></p>
            <ul>
                <li><strong>CustomerName = ZIM</strong> which are
                    <ul>
                        <li>paired</strong></li>
                        <li>DeviceID starting with <strong>'C'</strong></li>
                    </ul>
                </li>
                <li>Only include reports from the last 12 weeks</li>
                {'<li><strong>Device status = Active</strong> (filtered from AssetsView)</li>' if active_device_ids is not None else ''}
            </ul>
            <p><strong>Power Mode Counts:</strong> {get_power_mode_text(zim_c_counts)}</p>
            {'<img src="cid:zim_c_chart" style="display:block;"><br>' if 'zim_c' in chart_paths else ''}
            <h4>Critical & Low Battery Devices ({zim_c_total} devices):</h4>
            {f'<p><em>Showing first 30 of {zim_c_total} devices. Full data attached as CSV.</em></p>' if zim_c_has_more else ''}
            {zim_c_html}
            <br><br>
            
            <h3>Section 3: Samskip Devices</h3>
            <p><strong>Devices included in the statistics below:</strong></p>
            <ul>
                <li><strong>CustomerName = Samskip</strong></li>
                <li>paired</li>
                <li>Only include reports from the last 12 weeks</li>
                {'<li><strong>Device status = Active</strong> (filtered from AssetsView)</li>' if active_device_ids is not None else ''}
            </ul>
            <p><strong>Power Mode Counts:</strong> {get_power_mode_text(samskip_counts)}</p>
            {'<img src="cid:samskip_chart" style="display:block;"><br>' if 'samskip' in chart_paths else ''}
            <h4>Critical, Low & Medium Battery Devices ({samskip_total} devices):</h4>
            {f'<p><em>Showing first 30 of {samskip_total} devices. Full data attached as CSV.</em></p>' if samskip_has_more else ''}
            {samskip_html}
            <br><br>
            
            <h3>Section 4: HMM Devices</h3>
            <p><strong>Devices included in the statistics below:</strong></p>
            <ul>
                <li><strong>CustomerName = HMM</strong></li>
                <li>paired</li>
                <li>Only include reports from the last 12 weeks</li>
                {'<li><strong>Device status = Active</strong> (filtered from AssetsView)</li>' if active_device_ids is not None else ''}
            </ul>
            <p><strong>Power Mode Counts:</strong> {get_power_mode_text(hmm_counts)}</p>
            {'<img src="cid:hmm_chart" style="display:block;"><br>' if 'hmm' in chart_paths else ''}
            <h4>Critical, Low & Medium Battery Devices ({hmm_total} devices):</h4>
            {f'<p><em>Showing first 30 of {hmm_total} devices. Full data attached as CSV.</em></p>' if hmm_has_more else ''}
            {hmm_html}
        </body>
    </html>
    """
    html_part = MIMEText(html, 'html')
    email.attach(html_part)

    # Send email
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(EMAIL_CONFIG['sender'], EMAIL_CONFIG['password'])
        server.send_message(email)
    
    print(f"✅ Email sent successfully using {query_type}")
    print(f"📊 Report date: {report_date}")
    print(f"⚡ Query time: {int(query_time)} seconds")
    print(f"📈 Sections generated:")
    print(f"   - New PV Panel: {len(new_pv_devices)} devices - {get_power_mode_text(new_pv_counts)}")
    print(f"   - ZIM C-Series Devices: {len(zim_c_devices)} devices - {get_power_mode_text(zim_c_counts)}")
    print(f"   - Samskip Devices: {len(samskip_devices)} devices - {get_power_mode_text(samskip_counts)}")
    print(f"   - HMM Devices: {len(hmm_devices)} devices - {get_power_mode_text(hmm_counts)}")
    print(f"📊 Charts attached: {len(chart_paths)} out of 4 sections")
    
    # Show attachment information
    attachments = []
    if new_pv_has_more:
        attachments.append(f"new_pv_panel_devices_{report_date}.csv ({new_pv_total} rows)")
    if zim_c_has_more:
        attachments.append(f"zim_c_devices_{report_date}.csv ({zim_c_total} rows)")
    if samskip_has_more:
        attachments.append(f"samskip_devices_{report_date}.csv ({samskip_total} rows)")
    if hmm_has_more:
        attachments.append(f"hmm_devices_{report_date}.csv ({hmm_total} rows)")
    
    if attachments:
        print(f"📎 CSV attachments: {', '.join(attachments)}")
    else:
        print("📎 No CSV attachments (all tables ≤ 30 rows)")

if __name__ == "__main__":
    # Parse command line arguments
    manual_mode = "--manual" in sys.argv
    use_old_query = "--old" in sys.argv
    
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Usage: python emailing/daily.py [options]")
        print("Options:")
        print("  --manual    Prompt for specific date")
        print("  --old       Use DebugSMBs database (current implementation)")
        print("  --help, -h  Show this help message")
        print()
        print("Examples:")
        print("  python emailing/daily.py                    # Latest data, SMBs database")
        print("  python emailing/daily.py --old              # Latest data, DebugSMBs database")
        print("  python emailing/daily.py --manual           # Specific date, SMBs database")
        print("  python emailing/daily.py --manual --old     # Specific date, DebugSMBs database")
        print()
        print("Note: SMBs database is now the default (faster).")
        print("      Use --old flag for DebugSMBs database.")
        sys.exit(0)
    
    # Use the query method based on the flag (SMBs by default, DebugSMBs with --old)
    email_daily_report(manual_mode, use_old_query)
