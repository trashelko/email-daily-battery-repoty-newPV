"""
Email tracking functionality for battery reports.
Manages which reports have been sent via email.
"""

from datetime import datetime
from utils import parse_date_flexible

def get_emailed_dates():
    """
    Get list of dates that have already been emailed.
    Handles both formats: with leading zero (05Jan26) and without (5Jan26).
    
    Returns:
        list: Sorted list of dates that have been emailed
    """
    path_emailed_dates = "emailed_dates.txt"
    try:
        with open(path_emailed_dates, 'r') as f:
            dates = [line.strip() for line in f.read().splitlines() if line.strip()]
        return sorted(dates, key=lambda x: parse_date_flexible(x))
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
