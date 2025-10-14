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

## Key Notes

Note 2. **credentials_template.py** DOES NOT contain any actual credentials -- this is a dummy-file with the set up of access info to db and to emails. In code (and on my machine) I have **credentials.py** -- this contains the real stuff.
  The code is set up such that if .csv file of current date exists -- it won't try accesing the database and just use the CSV-file. So if report of _today_ exists -- this should work without database access.

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
  * creates and sends an email with all new reports (new reports are from dates not mentioned in **emailed_dates.txt**
