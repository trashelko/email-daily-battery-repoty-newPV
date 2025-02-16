Note 1. daily battery report ZIMs newPV.app -- is a short app which runs the script -- practically, it is not required to runs this, only to email it daily.

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
