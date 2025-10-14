"""
Email tracking functionality for battery reports.
Manages which reports have been sent via email.
"""

from datetime import datetime

def get_emailed_dates():
    """
    Get list of dates that have already been emailed.
    
    Returns:
        list: Sorted list of dates that have been emailed
    """
    path_emailed_dates = "emailed_dates.txt"
    try:
        with open(path_emailed_dates, 'r') as f:
            dates = f.read().splitlines()
        return sorted(dates, key=lambda x: datetime.strptime(x, "%d%b%y"))
    except FileNotFoundError:
        return []

def update_emailed_dates(new_dates):
    """
    Add new dates to the emailed dates tracking file.
    
    Args:
        new_dates (list): List of date strings to add
    """
    path_emailed_dates = "emailed_dates.txt"
    with open(path_emailed_dates, 'a') as f:
        for date in new_dates:
            f.write(date + '\n')
