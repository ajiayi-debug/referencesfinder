import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import certifi

message = Mail(
    from_email='referencefind66@gmail.com',
    to_emails='jiayi.ang@frieslandcampina.com',
    subject='Sending with Twilio SendGrid is Fun',
    html_content='<strong>and easy to do anywhere, even with Python</strong>'
)

try:
    sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'), ca_certs=certifi.where())
    response = sg.send(message)
    print(response.status_code)
    print(response.body)
    print(response.headers)
except Exception as e:
    print(f"Error: {e}")
