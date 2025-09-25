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
        print("  --old       Use original query implementation")
        print("  --help, -h  Show this help message")
        print()
        print("Examples:")
        print("  python main.py                    # Latest data, optimized query")
        print("  python main.py --old              # Latest data, original query")
        print("  python main.py --manual           # Specific date, optimized query")
        print("  python main.py --manual --old     # Specific date, original query")
        sys.exit(0)
    
    generate_battery_snapshot_report(manual_mode, use_old_query)