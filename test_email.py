import smtplib
from database.credentials import EMAIL_CONFIG

sender = EMAIL_CONFIG['sender']
app_password = EMAIL_CONFIG['password']

try:
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender, app_password)
    print("✅ Login successful")
except Exception as e:
    print("❌ Login failed:", e)
