"""
Daily battery report email functionality.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.credentials import EMAIL_CONFIG
from reports.daily_report import generate_battery_snapshot_report
from data_processing.file_operations import read_df_with_metadata
from data_processing.data_filters import get_LOW_latest_batt
from utils import prompt_for_date

import pandas as pd
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import smtplib

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
    path_save_chart = f"latest_batt_reports/charts/snapshot_{report_date.replace(' ', '')}.png"
    path_csv = f"latest_batt_reports/latest_batt_{report_date.replace(' ', '')}.csv"

    # Read the generated data
    latest_batt, query_time = read_df_with_metadata(path_csv)
    latest_batt_LOW = get_LOW_latest_batt(latest_batt)
    latest_batt_LOW = latest_batt_LOW.drop(['PayloadData', 'index'], axis=1, errors='ignore')
    latest_batt_LOW.sort_values(by='Voltage', inplace=True)
    
    # Email content
    msg = f"Query took {int(query_time)} seconds"
    query_type = "Original Query" if use_old_query else "Optimized Query"
    
    # Create email
    email = MIMEMultipart()
    email['From'] = EMAIL_CONFIG['sender']
    email['To'] = EMAIL_CONFIG['recipients'][0]
    email['Subject'] = f"Daily Battery Report of ZIM's New PV Trackers - {query_type}"

    # Add image
    with open(path_save_chart, 'rb') as f:
        img_data = f.read()
    img_part = MIMEImage(img_data)
    img_part.add_header('Content-ID', '<chart>')
    email.attach(img_part)
    
    # Add HTML content
    html = f"""
    <html>
        <body>
            <h3>Battery Report - {query_type}</h3>
            <img src="cid:chart" style="display:block;"><br><br>
            <p><strong>Performance:</strong> {msg}</p>
            <p><strong>Report Date:</strong> {report_date}</p>
            <p><strong>Specific Date:</strong> {specific_date if specific_date else 'Latest available'}</p>
            <br>
            <h4>Low Battery Devices (Voltage < 3.6V):</h4>
            {latest_batt_LOW.to_html(index=False)}
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

if __name__ == "__main__":
    # Parse command line arguments
    manual_mode = "--manual" in sys.argv
    use_old_query = "--old" in sys.argv
    
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Usage: python email/daily.py [options]")
        print("Options:")
        print("  --manual    Prompt for specific date")
        print("  --old       Use original query implementation")
        print("  --help, -h  Show this help message")
        print()
        print("Examples:")
        print("  python email/daily.py                    # Latest data, optimized query")
        print("  python email/daily.py --old              # Latest data, original query")
        print("  python email/daily.py --manual           # Specific date, optimized query")
        print("  python email/daily.py --manual --old     # Specific date, original query")
        sys.exit(0)
    
    email_daily_report(manual_mode, use_old_query)
