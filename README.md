# ZIM NewPV Battery Report System

## Overview
This system generates daily battery reports for ZIM shipping containers with NewPV panels and for two customer fleets: ZIM (C-series) and Samskip.

## Running Daily Reports

### For Today's Data (Automatic, set to auto-run on 11.30am daily)
```bash
python emailing/daily.py
```

### For a Previous Day (Manual Mode)
```bash
python emailing/daily.py --manual
```
This will prompt you to enter a date in YYYY-MM-DD format (e.g., 2025-01-15).

### Database Options
- **Default (Recommended)**: Uses SMBs database (faster)
- **Legacy**: Use `--old` flag for DebugSMBs database

Examples:
```bash
# Previous day with SMBs database (default)
python emailing/daily.py --manual

# Previous day with DebugSMBs database
python emailing/daily.py --manual --old

# Today with DebugSMBs database
python emailing/daily.py --old
```

### Help
```bash
python emailing/daily.py --help
```

## Running Weekly Reports

### Default Mode (Last 7 Days)
```bash
python emailing/weekly.py
```
Sends an email with reports from the last 7 days (including today) to all recipients configured in `emailing/credentials.py`. This is the default behavior.

### Debug Mode (Single Recipient)
```bash
python emailing/weekly.py --debug
# or
python emailing/weekly.py -d
```
Sends the weekly report to only the first recipient (rashel) from the recipients list. Useful for testing before sending to all recipients.

### Using Email Tracking (Deprecated)
```bash
python emailing/weekly.py --use-tracking
# or
python emailing/weekly.py --track
```
Uses the old tracking system based on `emailed_dates.txt` to send only new reports that haven't been emailed yet.

### Combined Modes
You can combine flags:
```bash
# Debug mode with tracking
python emailing/weekly.py --debug --use-tracking
```

### Weekly Report Contents
The weekly report includes:
1. **Section 1: New PV Panel** - Devices from Mila's list and ZIM devices with specific criteria
2. **Section 2: ZIM C-Series Devices** - ZIM devices with DeviceID starting with 'C'
3. **Section 3: Samskip Devices** - All Samskip devices
4. **Section 4: HMM Devices** - All HMM devices
5. **Fleet-Wide Power Mode Statistics** - Statistics for selected organizations (IDs: 18, 54, 90, 31, 89, 69, 91, 51) including:
   - Organization names and device counts
   - Total number of devices
   - Power mode percentages (High, Medium, Low, Critical)

**Note:** The `emailed_dates.txt` file is only updated automatically when there are multiple recipients (>1). For single recipient emails (debug mode), the file is not updated.

## Key Notes

### Credentials
**credentials_template.py** files DO NOT contain any actual credentials -- these are dummy files with the setup structure for database and email access. 

The actual credential files are:
- `database/credentials.py` - Contains database connection credentials (DB_DebugSMBs_CONFIG and DB_SMBs_CONFIG)
- `emailing/credentials.py` - Contains email configuration (EMAIL_CONFIG with sender, password, and recipients list)

Both credential files are in `.gitignore` and should not be committed to the repository.

**Note:** The code is set up such that if a .csv file of the current date exists, it won't try accessing the database and will just use the CSV file. So if a report for _today_ exists, this should work without database access.

All files:

* **battery_analysis.py**
  * functions which clean and set up correctly the data
  * function which creates the snapshot_chart
  
* **battery_status_today_report.py**
  * fuctions which run queries (test and real)
  * funcitons which save and read data in required format
  * filter data for the list of devices of interest
  * function which creates report including snapshot_chart
 
* **email_report.py**
  * creates and send the email

* **email_weekly_report.py**
  * creates and sends an email with reports from the last 7 days (default)
  * Optionally can use `--use-tracking` flag to use old tracking system based on **emailed_dates.txt**
