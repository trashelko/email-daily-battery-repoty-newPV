import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from credentials import EMAIL_CONFIG

msg = MIMEMultipart()
msg['From'] = EMAIL_CONFIG['sender']
msg['To'] = EMAIL_CONFIG['recipient']
msg['Subject'] = "Test Email"

body = "Hi, this is a test email."
msg.attach(MIMEText(body, 'plain'))

with smtplib.SMTP('smtp.gmail.com', 587) as server:
    server.starttls()
    server.login(EMAIL_CONFIG['sender'], EMAIL_CONFIG['password'])
    server.send_message(msg)