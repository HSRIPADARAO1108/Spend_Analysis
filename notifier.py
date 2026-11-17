import smtplib
import ssl
from email.message import EmailMessage
import os

def send_email(subject, body):
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", 465))  # Default to 465 (SSL)
    
    sender_email = os.environ["SMTP_USER"]
    receiver_email = os.environ["EMAIL_TO"]
    password = os.environ["SMTP_PASS"]

    msg = EmailMessage()
    msg.set_content(body)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = receiver_email

    # If using Port 465 (SMTP_SSL)
    if smtp_port == 465:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as s:
            s.set_debuglevel(1)  # Enables verbose logging to debug connection drops
            s.login(sender_email, password)
            s.send_message(msg)
    
    # If using Port 587 (STARTTLS)
    else:
        with smtplib.SMTP(smtp_server, smtp_port) as s:
            s.set_debuglevel(1)
            s.starttls(context=ssl.create_default_context())
            s.login(sender_email, password)
            s.send_message(msg)
