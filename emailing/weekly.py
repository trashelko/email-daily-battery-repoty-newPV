"""
Weekly battery report email functionality.
"""

import os
import pandas as pd
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import smtplib

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.credentials import EMAIL_CONFIG
from data_processing.file_operations import read_df_with_metadata, get_report_filename
from data_processing.data_filters import get_new_pv_panel_devices, get_zim_c_devices, get_samskip_devices
from data_processing.visualization import create_snapshot_chart
from emailing.tracking import get_emailed_dates, update_emailed_dates


def email_weekly_report():
    """
    Send weekly report with all new reports that haven't been emailed yet.
    """
    files = [f for f in os.listdir("latest_batt_reports") if f.startswith("latest_batt_") and f.endswith(".csv")]
    report_dates = [f.replace("latest_batt_", "").replace(".csv", "") for f in files]
    # Remove _smbs suffix if present and sort by date
    report_dates = [date.replace("_smbs", "") for date in report_dates]
    report_dates = sorted(report_dates, key=lambda x: datetime.strptime(x, "%d%b%y"))

    emailed_dates = get_emailed_dates()
    new_dates = [date for date in report_dates if date not in emailed_dates]

    print(f"🆕 New dates to email: {new_dates}")

    if not new_dates:
        print("No new reports to send.")
        return
    
    email = MIMEMultipart()
    email['From'] = EMAIL_CONFIG['sender']
    email['To'] = ', '.join(EMAIL_CONFIG['recipients'])
    # email['To'] = EMAIL_CONFIG['recipients'][0]
    email['Subject'] = f"Weekly Battery Report - {len(new_dates)} Reports"

    # Helper function to get power mode counts
    def get_power_mode_text(counts):
        critical = counts.get('Critical', 0)
        low = counts.get('Low', 0)
        medium = counts.get('Medium', 0)
        return f"Critical: {critical}, Low: {low}, Medium: {medium}"

    # Collect data for all dates first
    all_dates_data = {}
    
    for date in new_dates:
        # Convert date from %d%b%y format to %Y-%m-%d format for get_report_filename
        date_obj = datetime.strptime(date, "%d%b%y")
        date_iso = date_obj.strftime("%Y-%m-%d")
        
        # Read existing CSV data (no generation needed)
        path_csv = get_report_filename(date_iso, False)  # SMBs database
        print(f"📁 Reading CSV for {date}: {path_csv}")
        
        if not os.path.exists(path_csv):
            print(f"❌ CSV file not found for {date}: {path_csv}")
            continue
            
        latest_batt, _ = read_df_with_metadata(path_csv)
        
        # Get section data (same as daily email)
        new_pv_devices = get_new_pv_panel_devices(latest_batt)
        zim_c_devices = get_zim_c_devices(latest_batt)
        samskip_devices = get_samskip_devices(latest_batt)
        
        # Store data for this date
        all_dates_data[date] = {
            'new_pv': new_pv_devices,
            'zim_c': zim_c_devices,
            'samskip': samskip_devices
        }
    
    # Use existing charts (no generation needed)
    latest_date = new_dates[-1]  # Use the most recent date for charts
    chart_paths = {}
    
    # Section 1: New PV Panel chart
    new_pv_chart_path = f"latest_batt_reports/charts/new_pv_panel_{latest_date}.png"
    if os.path.exists(new_pv_chart_path):
        chart_paths['new_pv'] = new_pv_chart_path
        print(f"📊 Using existing New PV Panel chart: {new_pv_chart_path}")
    else:
        print(f"⚠️ New PV Panel chart not found: {new_pv_chart_path}")
    
    # Section 2: ZIM C Devices chart
    zim_c_chart_path = f"latest_batt_reports/charts/zim_c_devices_{latest_date}.png"
    if os.path.exists(zim_c_chart_path):
        chart_paths['zim_c'] = zim_c_chart_path
        print(f"📊 Using existing ZIM C chart: {zim_c_chart_path}")
    else:
        print(f"⚠️ ZIM C chart not found: {zim_c_chart_path}")
    
    # Section 3: Samskip Devices chart
    samskip_chart_path = f"latest_batt_reports/charts/samskip_devices_{latest_date}.png"
    if os.path.exists(samskip_chart_path):
        chart_paths['samskip'] = samskip_chart_path
        print(f"📊 Using existing Samskip chart: {samskip_chart_path}")
    else:
        print(f"⚠️ Samskip chart not found: {samskip_chart_path}")
    
    # Attach images
    for section, chart_path in chart_paths.items():
        with open(chart_path, 'rb') as f:
            img_data = f.read()
        img_part = MIMEImage(img_data)
        img_part.add_header('Content-ID', f'<{section}_chart>')
        email.attach(img_part)
    
    # Build HTML content with 3 sections
    new_pv_chart_html = '<img src="cid:new_pv_chart" style="display:block;"><br>' if 'new_pv' in chart_paths else ''
    zim_c_chart_html = '<img src="cid:zim_c_chart" style="display:block;"><br>' if 'zim_c' in chart_paths else ''
    samskip_chart_html = '<img src="cid:samskip_chart" style="display:block;"><br>' if 'samskip' in chart_paths else ''
    
    print(f"🔍 Chart HTML variables:")
    print(f"  new_pv_chart_html: {repr(new_pv_chart_html)}")
    print(f"  zim_c_chart_html: {repr(zim_c_chart_html)}")
    print(f"  samskip_chart_html: {repr(samskip_chart_html)}")
    print(f"  chart_paths keys: {list(chart_paths.keys())}")
    
    html_content = f"""
    <html>
        <body>
            <h2>Weekly Battery Report - {len(new_dates)} Reports</h2>
            <p><strong>Reports included:</strong> {', '.join(pd.to_datetime(new_dates, format='%d%b%y').strftime('%-d %b'))}</p>
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
            </ul>
            {new_pv_chart_html}
            <h4>Power Mode Counts by Date:</h4>
    """
    
    # Add power mode counts for each date for New PV Panel
    for date in new_dates:
        formatted_date = pd.to_datetime(date, format='%d%b%y').strftime('%-d %B %Y')
        new_pv_counts = all_dates_data[date]['new_pv']['PowerMode'].value_counts().to_dict() if len(all_dates_data[date]['new_pv']) > 0 else {}
        html_content += f"            <p><strong>{formatted_date}:</strong> {get_power_mode_text(new_pv_counts)}</p>\n"
    
    html_content += f"""
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
            </ul>
            {zim_c_chart_html}
            <h4>Power Mode Counts by Date:</h4>
    """
    
    # Add power mode counts for each date for ZIM C Devices
    for date in new_dates:
        formatted_date = pd.to_datetime(date, format='%d%b%y').strftime('%-d %B %Y')
        zim_c_counts = all_dates_data[date]['zim_c']['PowerMode'].value_counts().to_dict() if len(all_dates_data[date]['zim_c']) > 0 else {}
        html_content += f"            <p><strong>{formatted_date}:</strong> {get_power_mode_text(zim_c_counts)}</p>\n"
    
    html_content += f"""
            <br><br>
            
            <h3>Section 3: Samskip Devices</h3>
            <p><strong>Devices included in the statistics below:</strong></p>
            <ul>
                <li><strong>CustomerName = Samskip</strong></li>
                <li>paired</li>
                <li>Only include reports from the last 12 weeks</li>
            </ul>
            {samskip_chart_html}
            <h4>Power Mode Counts by Date:</h4>
    """
    
    # Add power mode counts for each date for Samskip Devices
    for date in new_dates:
        formatted_date = pd.to_datetime(date, format='%d%b%y').strftime('%-d %B %Y')
        samskip_counts = all_dates_data[date]['samskip']['PowerMode'].value_counts().to_dict() if len(all_dates_data[date]['samskip']) > 0 else {}
        html_content += f"            <p><strong>{formatted_date}:</strong> {get_power_mode_text(samskip_counts)}</p>\n"
    
    html_content += """
        </body>
    </html>
    """
    
    html_part = MIMEText(html_content, 'html')
    email.attach(html_part)
    
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(EMAIL_CONFIG['sender'], EMAIL_CONFIG['password'])
        server.send_message(email)
    
    # Update log of emailed dates
    update_emailed_dates(new_dates)
    print(f"✅ Weekly email sent successfully")
    print(f"📊 Reports included: {', '.join(new_dates)}")
    print(f"📈 Total reports: {len(new_dates)}")

if __name__ == "__main__":
    email_weekly_report()
