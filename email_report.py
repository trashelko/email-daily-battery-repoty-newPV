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
import sys

def email_report(manual_mode=False):
    specific_date = None
    if manual_mode:
        specific_date = prompt_for_date()
    #     date_obj = pd.to_datetime(specific_date, format="%Y-%m-%d")
    #     report_date = date_obj.strftime('%-d %b')
    # else:
    #     report_date = pd.Timestamp.today().strftime('%-d %b')

    report_date = generate_battery_snapshot_report(manual_mode, specific_date)
    
    path_save_chart = f"latest_batt_reports/charts/snapshot_{report_date.replace(' ', '')}.png"
    path_csv = f"latest_batt_reports/latest_batt_{report_date.replace(' ', '')}.csv"

    latest_batt, query_time = read_df_with_metadata(path_csv)
    latest_batt_LOW = get_LOW_latest_batt(latest_batt)
    latest_batt_LOW = latest_batt_LOW.drop(['PayloadData', 'index'], axis=1, errors='ignore')
    latest_batt_LOW.sort_values(by='Voltage',inplace=True)
    msg = f"Query took {int(query_time)} seconds"
    
    email = MIMEMultipart()
    email['From'] = EMAIL_CONFIG['sender']
    email['To'] = EMAIL_CONFIG['recipients'][0]
    email['Subject'] = f"Daily Battery Report of ZIM's New PV Trackers"

    # Add image
    with open(path_save_chart, 'rb') as f:
        img_data = f.read()
    img_part = MIMEImage(img_data)
    img_part.add_header('Content-ID', '<chart>')
    email.attach(img_part)
    
    # Add text, image and df as HTML table
    html = f"""
    <html>
        <body>
            <img src="cid:chart" style="display:block;"><br><br>
            {msg}<br><br>
            {latest_batt_LOW.drop(['PayloadData', 'index'], axis=1, errors='ignore').to_html(index=False)}
        </body>
    </html>
    """
    html_part = MIMEText(html, 'html')
    email.attach(html_part)

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login(EMAIL_CONFIG['sender'], EMAIL_CONFIG['password'])
        server.send_message(email)

if __name__ == "__main__":
   manual_mode = "--manual" in sys.argv
   email_report(manual_mode)