from database.credentials import EMAIL_CONFIG
from battery_status_today_report import (read_df_with_metadata,get_LOW_latest_batt)

import pandas as pd
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import smtplib
import os

def get_emailed_dates():
    path_emailed_dates = "emailed_dates.txt"
    with open(path_emailed_dates, 'r') as f:
        dates = f.read().splitlines()
    return sorted(dates, key=lambda x: datetime.strptime(x, "%d%b"))

def update_emailed_dates(new_dates):
    path_emailed_dates = "emailed_dates.txt"
    with open(path_emailed_dates, 'a') as f:
        for date in new_dates:
            f.write(date + '\n')

def email_weekly_report():
    files = [f for f in os.listdir("latest_batt_reports") if f.startswith("latest_batt_") and f.endswith(".csv")]
    report_dates = [f.replace("latest_batt_", "").replace(".csv", "") for f in files]
    report_dates = sorted(report_dates, key=lambda x: datetime.strptime(x, "%d%b"))

    emailed_dates = get_emailed_dates()
    new_dates = [date for date in report_dates if date not in emailed_dates]

    if not new_dates:
        print("No new reports to send.")
        return
    
    email = MIMEMultipart()
    email['From'] = EMAIL_CONFIG['sender']
    email['To'] = ', '.join(EMAIL_CONFIG['recipients'])
    email['Subject'] = "Last Several Battery Reports of ZIM's New PV Trackers"

    html_content = """
    <html>
        <body>
    """
    
    for date in new_dates:
        path_csv = f"latest_batt_reports/latest_batt_{date}.csv"
        path_chart = f"latest_batt_reports/charts/snapshot_{date}.png"
        
        latest_batt, _ = read_df_with_metadata(path_csv)
        latest_batt_LOW = get_LOW_latest_batt(latest_batt)
        latest_batt_LOW = latest_batt_LOW.drop(['PayloadData', 'index'], axis=1, errors='ignore')
        latest_batt_LOW.sort_values(by='Voltage', inplace=True)
        
        # Attach image
        if os.path.exists(path_chart):
            with open(path_chart, 'rb') as f:
                img_data = f.read()
            img_part = MIMEImage(img_data)
            img_part.add_header('Content-ID', f'<chart_{date}>')
            email.attach(img_part)
            img_html = f'<img src="cid:chart_{date}" style="display:inline;margin-right:20px;">'
        else:
            img_html = ""
            
        # Append to HTML content
        html_content += f"""
            <h3>{' '.join([date[:-3], date[-3:]])}</h3>
            <div style="display: flex; align-items: center; gap: 20px;">
                {img_html}
                {latest_batt_LOW.to_html(index=False)}
            </div><br>
        """
    
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
    print(f"Emailed reports for: {', '.join(new_dates)}")

if __name__ == "__main__":
    email_weekly_report()