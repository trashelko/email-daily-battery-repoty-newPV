"""
Weekly battery report email functionality.
"""

import os
import pandas as pd
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import smtplib
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from emailing.credentials import EMAIL_CONFIG
from database.queries import get_active_devices, get_power_mode_statistics, get_organization_names, get_total_device_count
from data_processing.file_operations import read_df_with_metadata, get_report_filename
from data_processing.data_filters import get_new_pv_panel_devices, get_zim_c_devices, get_samskip_devices, get_hmm_devices
from data_processing.visualization import create_snapshot_chart, plot_power_stats_combined
from emailing.tracking import get_emailed_dates, update_emailed_dates
from utils import format_date_for_filename, parse_date_flexible


def generate_missing_report(date_str):
    """
    Generate a report for a specific date using the daily.py script.
    
    Args:
        date_str (str): Date in 'YYYY-MM-DD' format
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get the project root directory
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Use shell=True to properly activate the virtual environment
        # This mimics the behavior of the Automator apps
        cmd = f"""
        cd "{project_root}" && 
        source venv/bin/activate && 
        python emailing/daily.py --manual
        """
        
        # Use subprocess with shell=True and input to provide the date
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=True
        )
        
        # Send the date as input to the manual prompt
        stdout, stderr = process.communicate(input=date_str + '\n')
        
        if process.returncode == 0:
            print(f"✅ Successfully generated report for {date_str}")
            return True
        else:
            print(f"❌ Failed to generate report for {date_str}")
            print(f"Error: {stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Exception generating report for {date_str}: {str(e)}")
        return False


def find_missing_dates(emailed_dates, today_date):
    """
    Find dates between the last emailed date and today that need reports.
    
    Args:
        emailed_dates (list): List of already emailed date strings
        today_date (datetime): Today's date
        
    Returns:
        list: List of missing date strings in 'YYYY-MM-DD' format
    """
    if not emailed_dates:
        # If no emails sent yet, start from 7 days ago
        start_date = today_date - timedelta(days=7)
    else:
        # Find the most recent emailed date (handle both formats)
        last_emailed_str = max(emailed_dates, key=lambda x: parse_date_flexible(x))
        last_emailed = parse_date_flexible(last_emailed_str)
        start_date = last_emailed + timedelta(days=1)
    
    missing_dates = []
    current_date = start_date
    
    while current_date <= today_date:
        # Check if report already exists for this date
        date_str = current_date.strftime("%Y-%m-%d")
        date_file = format_date_for_filename(current_date)
        
        # Check for both regular and SMBs versions
        regular_path = get_report_filename(date_str, True)  # DebugSMBs
        smbs_path = get_report_filename(date_str, False)    # SMBs
        
        if not os.path.exists(regular_path) and not os.path.exists(smbs_path):
            missing_dates.append(date_str)
            print(f"📅 Missing report for {date_str}")
        else:
            print(f"✅ Report exists for {date_str}")
            
        current_date += timedelta(days=1)
    
    return missing_dates


def email_weekly_report(use_emailed_dates_tracking=False, debug_mode=False):
    """
    Send weekly report with reports from the last 7 days.
    Optionally can use emailed_dates.txt tracking (deprecated).
    
    Args:
        use_emailed_dates_tracking (bool): If True, use old tracking system based on emailed_dates.txt.
                                          If False (default), send last 7 days from today.
        debug_mode (bool): If True, send only to rashel. If False, send to all recipients.
    """
    print("🔄 Starting weekly report process...")
    
    # Get current date
    today = datetime.now()
    
    if use_emailed_dates_tracking:
        # OLD MODE: Use emailed_dates.txt tracking (deprecated)
        emailed_dates = get_emailed_dates()
        print(f"📅 Today's date: {format_date_for_filename(today)}")
        print(f"📧 Last emailed dates: {emailed_dates[-5:] if len(emailed_dates) > 5 else emailed_dates}")
        
        # Find missing dates that need report generation
        missing_dates = find_missing_dates(emailed_dates, today)
    else:
        # NEW MODE: Last 7 days from today
        print(f"📅 Today's date: {format_date_for_filename(today)}")
        print("📊 Using last 7 days mode (emailed_dates.txt tracking disabled)")
        
        # Get last 7 days (including today)
        date_range = []
        for i in range(7):
            date = today - timedelta(days=i)
            date_range.append(date)
        date_range.reverse()  # Oldest to newest
        
        # Check which dates need report generation
        missing_dates = []
        for date in date_range:
            date_str = date.strftime("%Y-%m-%d")
            date_file = format_date_for_filename(date)
            
            # Check for both regular and SMBs versions
            regular_path = get_report_filename(date_str, True)  # DebugSMBs
            smbs_path = get_report_filename(date_str, False)    # SMBs
            
            if not os.path.exists(regular_path) and not os.path.exists(smbs_path):
                missing_dates.append(date_str)
                print(f"📅 Missing report for {date_str}")
            else:
                print(f"✅ Report exists for {date_str}")
    
    if missing_dates:
        print(f"🔧 Generating {len(missing_dates)} missing reports...")
        successful_generations = 0
        failed_generations = 0
        failed_dates = []
        
        for date_str in missing_dates:
            if generate_missing_report(date_str):
                successful_generations += 1
            else:
                failed_generations += 1
                failed_dates.append(date_str)
                print(f"⚠️ Warning: Failed to generate report for {date_str}")
        
        print(f"📊 Generation results: {successful_generations} successful, {failed_generations} failed")
        
        # Verify that all missing reports were actually created
        still_missing = []
        for date_str in missing_dates:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            date_file = format_date_for_filename(date_obj)
            
            # Check for both regular and SMBs versions
            regular_path = get_report_filename(date_str, True)  # DebugSMBs
            smbs_path = get_report_filename(date_str, False)    # SMBs
            
            if not os.path.exists(regular_path) and not os.path.exists(smbs_path):
                still_missing.append(date_str)
        
        # If any reports are still missing after generation, abort to prevent incomplete weekly email
        if still_missing:
            print(f"❌ ERROR: {len(still_missing)} required reports are still missing after generation attempt:")
            for date_str in still_missing:
                print(f"   - {date_str}")
            print("❌ Aborting weekly email to prevent sending incomplete report.")
            print("   Please investigate and fix the report generation issues before retrying.")
            sys.exit(1)
        
        if failed_generations > 0:
            print(f"⚠️ Note: {failed_generations} reports had generation warnings, but all reports now exist.")
    else:
        print("✅ All reports are up to date")
    
    # Now proceed with the weekly email logic
    if use_emailed_dates_tracking:
        # OLD MODE: Filter by emailed_dates
        files = [f for f in os.listdir("latest_batt_reports") if f.startswith("latest_batt_") and f.endswith(".csv")]
        report_dates = [f.replace("latest_batt_", "").replace(".csv", "") for f in files]
        # Remove _smbs suffix if present and sort by date
        report_dates = [date.replace("_smbs", "").replace("_debug", "") for date in report_dates]
        report_dates = sorted(report_dates, key=lambda x: parse_date_flexible(x))
        
        emailed_dates = get_emailed_dates()
        new_dates = [date for date in report_dates if date not in emailed_dates]
    else:
        # NEW MODE: Last 7 days (reuse date_range from above)
        # Get last 7 days (including today)
        date_range = []
        for i in range(7):
            date = today - timedelta(days=i)
            date_range.append(date)
        date_range.reverse()  # Oldest to newest
        
        new_dates = []
        for date in date_range:
            # Use consistent format (no leading zero) to match daily.py chart naming
            date_file = format_date_for_filename(date)
            date_str = date.strftime("%Y-%m-%d")
            # Check if report exists (prefer SMBs, fallback to DebugSMBs)
            smbs_path = get_report_filename(date_str, False)  # SMBs database
            regular_path = get_report_filename(date_str, True)  # DebugSMBs
            
            if os.path.exists(smbs_path) or os.path.exists(regular_path):
                new_dates.append(date_file)
        
        new_dates = sorted(new_dates, key=lambda x: parse_date_flexible(x))

    print(f"🆕 Dates to email: {new_dates}")

    if not new_dates:
        print("No reports to send.")
        sys.exit(0)  # Success - no reports is a valid state
    
    # Verify all new_dates have corresponding CSV files before proceeding
    missing_csv_files = []
    for date in new_dates:
        date_obj = datetime.strptime(date, "%d%b%y")
        date_iso = date_obj.strftime("%Y-%m-%d")
        path_csv = get_report_filename(date_iso, False)  # SMBs database
        
        if not os.path.exists(path_csv):
            missing_csv_files.append((date, path_csv))
    
    if missing_csv_files:
        print(f"❌ ERROR: {len(missing_csv_files)} CSV files are missing for dates that should be included:")
        for date, path in missing_csv_files:
            print(f"   - {date}: {path}")
        print("❌ Aborting weekly email to prevent sending incomplete report.")
        sys.exit(1)
    
    # Determine recipients based on debug mode
    if debug_mode:
        # Debug mode: send only to first recipient (rashel)
        recipients = [EMAIL_CONFIG['recipients'][0]]
        print(f"🐛 Debug mode: Sending to {recipients[0]} only")
    else:
        # Normal mode: send to all recipients from EMAIL_CONFIG
        recipients = EMAIL_CONFIG['recipients']
        print(f"📧 Normal mode: Sending to {len(recipients)} recipients")
    
    email = MIMEMultipart()
    email['From'] = EMAIL_CONFIG['sender']
    email['To'] = ', '.join(recipients)
    email['Subject'] = f"Weekly Battery Report - {len(new_dates)} Reports"

    # Helper function to get power mode counts
    def get_power_mode_text(counts):
        critical = counts.get('Critical', 0)
        low = counts.get('Low', 0)
        medium = counts.get('Medium', 0)
        return f"Critical: {critical}, Low: {low}, Medium: {medium}"

    # Query active devices (weekly reports use SMBs database)
    # Query all active devices once, then filter in Python (can't include large lists in SQL)
    active_device_ids = None
    try:
        active_devices_df, _ = get_active_devices()
        # Get set of active device IDs (DeviceID only - filtering done in Python)
        active_device_ids = set(active_devices_df['DeviceID'].dropna().tolist())
        print(f"✅ Found {len(active_device_ids)} active devices")
    except Exception as e:
        print(f"⚠️ Warning: Could not query active devices: {e}")
        print("   Continuing without active device filtering")
        active_device_ids = None
    
    # Collect data for all dates first
    all_dates_data = {}
    read_errors = []
    
    for date in new_dates:
        # Convert date from flexible format to %Y-%m-%d format for get_report_filename
        date_obj = parse_date_flexible(date)
        date_iso = date_obj.strftime("%Y-%m-%d")
        
        # Read existing CSV data (no generation needed)
        path_csv = get_report_filename(date_iso, False)  # SMBs database
        print(f"📁 Reading CSV for {date}: {path_csv}")
        
        if not os.path.exists(path_csv):
            read_errors.append((date, f"CSV file not found: {path_csv}"))
            continue
        
        try:
            latest_batt, _ = read_df_with_metadata(path_csv)
            
            # Get section data (filtered by active devices if available)
            new_pv_devices = get_new_pv_panel_devices(latest_batt, active_device_ids)
            zim_c_devices = get_zim_c_devices(latest_batt, active_device_ids)
            samskip_devices = get_samskip_devices(latest_batt, active_device_ids)
            hmm_devices = get_hmm_devices(latest_batt, active_device_ids)
            
            # Store data for this date
            all_dates_data[date] = {
                'new_pv': new_pv_devices,
                'zim_c': zim_c_devices,
                'samskip': samskip_devices,
                'hmm': hmm_devices
            }
        except Exception as e:
            read_errors.append((date, f"Error reading CSV: {str(e)}"))
            continue
    
    # If any CSV files failed to read, abort to prevent incomplete weekly email
    if read_errors:
        print(f"❌ ERROR: Failed to read {len(read_errors)} CSV files:")
        for date, error_msg in read_errors:
            print(f"   - {date}: {error_msg}")
        print("❌ Aborting weekly email to prevent sending incomplete report.")
        sys.exit(1)
    
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
    
    # Section 4: HMM Devices chart
    hmm_chart_path = f"latest_batt_reports/charts/hmm_devices_{latest_date}.png"
    if os.path.exists(hmm_chart_path):
        chart_paths['hmm'] = hmm_chart_path
        print(f"📊 Using existing HMM chart: {hmm_chart_path}")
    else:
        print(f"⚠️ HMM chart not found: {hmm_chart_path}")
    
    # Attach images
    for section, chart_path in chart_paths.items():
        with open(chart_path, 'rb') as f:
            img_data = f.read()
        img_part = MIMEImage(img_data)
        img_part.add_header('Content-ID', f'<{section}_chart>')
        email.attach(img_part)
    
    # Build HTML content with 4 sections
    new_pv_chart_html = '<img src="cid:new_pv_chart" style="display:block;"><br>' if 'new_pv' in chart_paths else ''
    zim_c_chart_html = '<img src="cid:zim_c_chart" style="display:block;"><br>' if 'zim_c' in chart_paths else ''
    samskip_chart_html = '<img src="cid:samskip_chart" style="display:block;"><br>' if 'samskip' in chart_paths else ''
    hmm_chart_html = '<img src="cid:hmm_chart" style="display:block;"><br>' if 'hmm' in chart_paths else ''
    
    print(f"🔍 Chart HTML variables:")
    print(f"  new_pv_chart_html: {repr(new_pv_chart_html)}")
    print(f"  zim_c_chart_html: {repr(zim_c_chart_html)}")
    print(f"  samskip_chart_html: {repr(samskip_chart_html)}")
    print(f"  hmm_chart_html: {repr(hmm_chart_html)}")
    print(f"  chart_paths keys: {list(chart_paths.keys())}")
    
    html_content = f"""
    <html>
        <body>
            <h2>Weekly Battery Report - {len(new_dates)} Reports</h2>
            <p><strong>Reports included:</strong> {', '.join([parse_date_flexible(d).strftime('%-d %b') for d in new_dates])}</p>
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
            {new_pv_chart_html}
            <h4>Power Mode Counts by Date:</h4>
    """
    
    # Add power mode counts for each date for New PV Panel
    for date in new_dates:
        formatted_date = parse_date_flexible(date).strftime('%-d %B %Y')
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
                {'<li><strong>Device status = Active</strong> (filtered from AssetsView)</li>' if active_device_ids is not None else ''}
            </ul>
            {zim_c_chart_html}
            <h4>Power Mode Counts by Date:</h4>
    """
    
    # Add power mode counts for each date for ZIM C Devices
    for date in new_dates:
        formatted_date = parse_date_flexible(date).strftime('%-d %B %Y')
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
                {'<li><strong>Device status = Active</strong> (filtered from AssetsView)</li>' if active_device_ids is not None else ''}
            </ul>
            {samskip_chart_html}
            <h4>Power Mode Counts by Date:</h4>
    """
    
    # Add power mode counts for each date for Samskip Devices
    for date in new_dates:
        formatted_date = parse_date_flexible(date).strftime('%-d %B %Y')
        samskip_counts = all_dates_data[date]['samskip']['PowerMode'].value_counts().to_dict() if len(all_dates_data[date]['samskip']) > 0 else {}
        html_content += f"            <p><strong>{formatted_date}:</strong> {get_power_mode_text(samskip_counts)}</p>\n"
    
    html_content += f"""
            <br><br>
            
            <h3>Section 4: HMM Devices</h3>
            <p><strong>Devices included in the statistics below:</strong></p>
            <ul>
                <li><strong>CustomerName = HMM</strong></li>
                <li>paired</li>
                <li>Only include reports from the last 12 weeks</li>
                {'<li><strong>Device status = Active</strong> (filtered from AssetsView)</li>' if active_device_ids is not None else ''}
            </ul>
            {hmm_chart_html}
            <h4>Power Mode Counts by Date:</h4>
    """
    
    # Add power mode counts for each date for HMM Devices
    for date in new_dates:
        formatted_date = parse_date_flexible(date).strftime('%-d %B %Y')
        hmm_counts = all_dates_data[date]['hmm']['PowerMode'].value_counts().to_dict() if len(all_dates_data[date]['hmm']) > 0 else {}
        html_content += f"            <p><strong>{formatted_date}:</strong> {get_power_mode_text(hmm_counts)}</p>\n"
    
    # Get fleet-wide power mode statistics (filtered to specific organization IDs)
    print("📊 Querying fleet-wide power mode statistics...")
    try:
        # Filter to specific organization IDs
        target_org_ids = [18, 54, 90, 31, 89, 69, 91, 51]
        
        fleet_stats_df, stats_query_time = get_power_mode_statistics(organization_ids=target_org_ids, exclude_asset_group_id=None)
        print(f"✅ Fleet statistics query completed in {int(stats_query_time)} seconds")
        
        # Get organization names and device count
        org_names_df, org_names_query_time = get_organization_names(target_org_ids)
        print(f"✅ Organization names query completed in {int(org_names_query_time)} seconds")
        
        device_count, device_count_query_time = get_total_device_count(target_org_ids)
        print(f"✅ Device count query completed in {int(device_count_query_time)} seconds")
        
        if len(fleet_stats_df) > 0 and fleet_stats_df['TotalYears'].iloc[0] > 0:
            # Ensure charts directory exists
            charts_dir = "latest_batt_reports/charts"
            os.makedirs(charts_dir, exist_ok=True)
            
            # Generate combined chart for fleet-wide stats
            fleet_chart_path = f"{charts_dir}/fleet_power_stats_{latest_date}.png"
            plot_power_stats_combined(fleet_stats_df, list_name="Fleet-Wide (Selected Organizations)", path_save=fleet_chart_path)
            print(f"📊 Fleet statistics chart saved: {fleet_chart_path}")
            
            # Attach fleet chart image
            if os.path.exists(fleet_chart_path):
                with open(fleet_chart_path, 'rb') as f:
                    img_data = f.read()
                img_part = MIMEImage(img_data)
                img_part.add_header('Content-ID', '<fleet_stats_chart>')
                email.attach(img_part)
                # Display image smaller in email (600px width, maintain aspect ratio)
                fleet_chart_html = '<img src="cid:fleet_stats_chart" style="display:block; max-width:600px; width:100%; height:auto;"><br>'
            else:
                fleet_chart_html = ''
            
            # Build organization names list
            org_names_list = []
            if len(org_names_df) > 0:
                for _, row in org_names_df.iterrows():
                    org_names_list.append(f"{row['OrgName']} ({row['DevicesCount']} devices)")
                org_names_html = '<li>' + '</li><li>'.join(org_names_list) + '</li>'
            else:
                org_names_html = '<li>No organizations found</li>'
            
            # Add fleet statistics section to HTML
            total_years = fleet_stats_df['TotalYears'].iloc[0]
            high_pct = fleet_stats_df['HighPercent'].iloc[0]
            medium_pct = fleet_stats_df['MediumPercent'].iloc[0]
            low_pct = fleet_stats_df['LowPercent'].iloc[0]
            critical_pct = fleet_stats_df['CriticalPercent'].iloc[0]
            
            html_content += f"""
            <br><br>
            <hr style="border: 2px solid #333; margin: 30px 0;">
            <br>
            
            <h2>Fleet-Wide Power Mode Statistics</h2>
            <p><strong>Selected Organizations</strong></p>
            <ul>
                <li><strong>Organizations included:</strong>
                    <ul>
                        {org_names_html}
                    </ul>
                </li>
                <li><strong>Total number of devices:</strong> {device_count}</li>
                <li>Statistics calculated from historical battery data (SMBs database)</li>
                <li>Shows percentage of operational time spent in each power mode</li>
            </ul>
            {fleet_chart_html}
        </body>
    </html>
    """
        else:
            print("⚠️ No fleet statistics data available (TotalYears = 0)")
            html_content += """
        </body>
    </html>
    """
    except Exception as e:
        print(f"⚠️ Warning: Could not generate fleet statistics: {e}")
        import traceback
        traceback.print_exc()
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
    
    # Update log of emailed dates (only if more than 1 recipient)
    num_recipients = len(recipients)
    if num_recipients > 1:
        update_emailed_dates(new_dates)
        print(f"📝 Updated emailed_dates.txt (multiple recipients: {num_recipients})")
    else:
        print(f"📝 Skipped emailed_dates.txt update (single recipient: {num_recipients})")
    
    print(f"✅ Weekly email sent successfully")
    print(f"📊 Reports included: {', '.join(new_dates)}")
    print(f"📈 Total reports: {len(new_dates)}")
    sys.exit(0)  # Success

if __name__ == "__main__":
    try:
        # Check for --use-tracking flag to use old emailed_dates.txt system
        use_tracking = "--use-tracking" in sys.argv or "--track" in sys.argv
        
        # Check for --debug flag to send only to rashel
        debug_mode = "--debug" in sys.argv or "-d" in sys.argv
        
        if use_tracking:
            print("⚠️ Using deprecated emailed_dates.txt tracking mode")
        
        if debug_mode:
            print("🐛 Running in debug mode (sending to rashel only)")
        
        email_weekly_report(use_emailed_dates_tracking=use_tracking, debug_mode=debug_mode)
    except Exception as e:
        print(f"❌ Fatal error in weekly report: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
