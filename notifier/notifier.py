# smtpObj = smtplib.SMTP_SSL('smtp.esri.com', 465, timeout=22)
import smtplib
from email.message import EmailMessage
from datetime import datetime
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class Emailer:
    """

    Args:
      email_data (dict): A dict containing the necessary email components

        example:
        mail_dict = {
            "sender": "kgalliher@esri.com",
            "recipients": ["kgalliher@esri.com"],
            "subject": "Yo, sup",
            "body": "Body works"
        }

        mailer = notifier.Emailer(mail_dict)
        mailer.send_mail()

    """

    def __init__(self, email_data: dict):
        self.validate_message_data(email_data)
        self.timestamp = datetime.now()
        self.sender = email_data["sender"]
        self.recipients = email_data["recipients"]
        self.subject = email_data["subject"]
        self.body = email_data["body"]
        # self.smtp_server = smtplib.SMTP('SMTP2.esri.com', port=25, timeout=22)

    def validate_message_data(self, data):
        mail_keys = data.keys()
        assert "sender" in mail_keys, "Missing sender value"
        assert "recipients" in mail_keys, "Missing recipients value"
        assert "subject" in mail_keys, "Missing subject value"

    def send_mail(self):
        # msg = EmailMessage()
        msg = MIMEMultipart("alternative")
        # msg.set_content(self.body)
        msg["Subject"] = self.subject
        msg["From"] = self.sender
        msg["To"] = ", ".join(self.recipients)

        part = MIMEText(self.body, "html")
        msg.attach(part)
        try:
            smtp_server = smtplib.SMTP("SMTP2.esri.com", port=25, timeout=22)
            smtp_server.send_message(
                msg, self.sender, self.recipients,
            )
        except smtplib.SMTPException as err:
            with open("./email_error.log", "a") as f:
                f.write("COULD NOT SEND EMAIL!!!!")
            print("Unable to send email", err)
        finally:
            smtp_server.quit()


if __name__ == "__main__":
    mail_dict = {
        "sender": "kgalliher@esri.com",
        "recipients": ["kgalliher@esri.com"],
        "subject": "Yo, sup",
        "body": "<h2>Body works</h2>",
    }

    email = Emailer(mail_dict)
    email.send_mail()
