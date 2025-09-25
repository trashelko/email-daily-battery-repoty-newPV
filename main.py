"""
Main entry point for battery status reporting.
This file now serves as a simple interface to the modular components.
"""

import sys
from reports.daily_report import generate_battery_snapshot_report

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
        print("  python main.py                    # Latest data, DebugSMBs database")
        print("  python main.py --old              # Latest data, DebugSMBs database")
        print("  python main.py --manual           # Specific date, DebugSMBs database")
        print("  python main.py --manual --old     # Specific date, DebugSMBs database")
        print()
        print("Note: Currently only DebugSMBs database is implemented.")
        print("      SMBs database implementation coming soon.")
        sys.exit(0)
    
    # For now, always use old query since new SMBs implementation is not ready
    generate_battery_snapshot_report(manual_mode, True)