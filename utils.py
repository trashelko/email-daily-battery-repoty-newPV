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