from datetime import datetime

def prompt_for_date():
    """Prompts the user to input a date in YYYY-MM-DD format."""
    current_date = datetime.now().strftime("%Y-%m-%d")
    print(f"Please enter a date in format YYYY-MM-DD (e.g., 2025-03-09) or press Enter to use today's date ({current_date})")
    
    while True:
        user_input = input("Date [YYYY-MM-DD]: ").strip()
        
        # Use current date if user just presses Enter
        if user_input == "":
            return current_date
            
        # Validate the format
        try:
            input_date = datetime.strptime(user_input, "%Y-%m-%d")
            return user_input
        except ValueError:
            print("Invalid format! Please use YYYY-MM-DD format (e.g., 2025-03-09)")

def get_current_date():
    """Returns the current date in YYYY-MM-DD format."""
    return datetime.now().strftime("%Y-%m-%d")

def format_date_for_filename(date_obj):
    """
    Format date for use in filenames and chart names (no leading zero on day).
    Matches the format used by daily.py: '%-d%b%y' (e.g., '5Jan26')
    
    Args:
        date_obj: datetime object or date object
        
    Returns:
        str: Formatted date string (e.g., '5Jan26')
    """
    try:
        # Try Unix/Mac format first (no leading zero)
        return date_obj.strftime('%-d%b%y')
    except ValueError:
        # Fallback for systems that don't support %-d (Windows)
        return f"{date_obj.day}{date_obj.strftime('%b%y')}"

def parse_date_flexible(date_str):
    """
    Parse date string that may have or not have leading zero on day.
    Handles both '5Jan26' and '05Jan26' formats.
    
    Args:
        date_str: Date string in format like '5Jan26' or '05Jan26'
        
    Returns:
        datetime: Parsed datetime object
    """
    # Try with leading zero first (more common in emailed_dates.txt)
    try:
        return datetime.strptime(date_str, "%d%b%y")
    except ValueError:
        # Try without leading zero
        try:
            return datetime.strptime(date_str, "%-d%b%y")
        except ValueError:
            # Last resort: try parsing with single digit day
            # This handles cases like '5Jan26' on systems that don't support %-d
            import re
            match = re.match(r'(\d{1,2})([A-Za-z]{3})(\d{2})', date_str)
            if match:
                day, month, year = match.groups()
                # Reconstruct with leading zero for parsing
                date_str_normalized = f"{int(day):02d}{month}{year}"
                return datetime.strptime(date_str_normalized, "%d%b%y")
            raise ValueError(f"Could not parse date: {date_str}")