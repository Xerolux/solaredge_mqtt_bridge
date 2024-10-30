
import smtplib
from email.message import EmailMessage
import logging

logger = logging.getLogger("MailService")

class MailService:
    def __init__(self, smtp_server, sender_email, recipient_email, password):
        self.smtp_server = smtp_server
        self.sender_email = sender_email
        self.recipient_email = recipient_email
        self.password = password

    def send_report(self, report_content):
        msg = EmailMessage()
        msg.set_content(report_content)
        msg["Subject"] = "Daily Energy Usage Report"
        msg["From"] = self.sender_email
        msg["To"] = self.recipient_email

        with smtplib.SMTP(self.smtp_server) as server:
            server.login(self.sender_email, self.password)
            server.send_message(msg)
        logger.info("Report email sent to %s", self.recipient_email)
