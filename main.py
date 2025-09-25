"""
Main entry point for battery status reporting.
This file now serves as a simple interface to the modular components.
"""

import sys
from reports.daily_report import generate_battery_snapshot_report

if __name__ == "__main__":
    # Check if --manual flag is present
    manual_mode = "--manual" in sys.argv
    generate_battery_snapshot_report(manual_mode)