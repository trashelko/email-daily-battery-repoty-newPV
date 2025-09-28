"""
Main entry point for battery status reporting.
This file now serves as a simple interface to the modular components.
"""

import sys
from reports.create_report_on_date import generate_battery_snapshot_report

if __name__ == "__main__":
    # Parse command line arguments
    manual_mode = "--manual" in sys.argv
    use_old_query = "--old" in sys.argv
    
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Usage: python main.py [options]")
        print("Options:")
        print("  --manual    Prompt for specific date")
        print("  --old       Use DebugSMBs database query")
        print("  --help, -h  Show this help message")
        print()
        print("Examples:")
        print("  python main.py                    # Latest data, SMBs database")
        print("  python main.py --old              # Latest data, DebugSMBs database")
        print("  python main.py --manual           # Specific date, SMBs database")
        print("  python main.py --manual --old     # Specific date, DebugSMBs database")
        print()
        print("Note: SMBs database is now the default (faster).")
        print("      Use --old flag for DebugSMBs database.")
        sys.exit(0)
    
    # Use the query method based on the flag (SMBs by default, DebugSMBs with --old)
    generate_battery_snapshot_report(manual_mode, use_old_query)