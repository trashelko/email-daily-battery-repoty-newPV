I have no fucking clue if this will work for you.

Note 1. daily battery report ZIMs newPV.app -- was a short app which runs the script -- don't know if i saved correctly but it is not required to runs this, only to email it daily.

Note 2. **credentials_template.py** DOES NOT contain any actual credentials -- this is a dummy-file with access info to db abd to emails. In code I have **credentials.py** -- this contained real stuff.
  However, the code is set up such that is .csv file of current date exists -- it won't try accesing the database and just use the CSV-file. So _today_ this should work.

All files:

* battery_analysis.py
  * functions which clean and set up correctly the data
  * function which creates the chart
  
* battery_status_today_report.py
  * fuctions which run queries (test and real)
  * funcitons which save and read data in required format
  * filter data for the list of devices of interest
  * function which creates report including snapshot_chart
 
* email_report.py
  * creates and send the email
