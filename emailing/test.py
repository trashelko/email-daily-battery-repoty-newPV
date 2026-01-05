"""
Email connection testing functionality.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import smtplib
from emailing.credentials import EMAIL_CONFIG

def test_email_connection():
    """
    Test email connection and credentials.
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    sender = EMAIL_CONFIG['sender']
    app_password = EMAIL_CONFIG['password']

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender, app_password)
        print("✅ Login successful")
        return True
    except Exception as e:
        print("❌ Login failed:", e)
        return False

if __name__ == "__main__":
    test_email_connection()
