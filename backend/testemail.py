# import os
# from sendgrid import SendGridAPIClient
# from sendgrid.helpers.mail import Mail
# import ssl
# import certifi

# ssl._create_default_https_context = ssl._create_unverified_context

# message = Mail(
#     from_email='referencefind66@gmail.com',
#     to_emails='jiayi.ang@frieslandcampina.com',
#     subject='Sending with Twilio SendGrid is Fun',
#     html_content='<strong>and easy to do anywhere, even with Python</strong>'
# )

# try:
#     sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
#     response = sg.send(message)
#     print(response.status_code)
#     print(response.body)
#     print(response.headers)
# except Exception as e:
#     print(f"Error: {e}")
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Outlook SMTP server configuration
SMTP_SERVER = 'smtp.office365.com'
SMTP_PORT = 587

# Your Outlook email credentials
email = 'jiayi.ang@frieslandcampina.com'
password = 'JJJY#91296517'

# Email details
recipient_email = 'e0774928@u.nus.edu'
subject = 'Test Email from Python'
body = 'Hello, this is a test email sent using Python and Outlook SMTP.'

try:
    # Create the email object
    message = MIMEMultipart()
    message['From'] = email
    message['To'] = recipient_email
    message['Subject'] = subject
    message.attach(MIMEText(body, 'plain'))

    # Connect to the Outlook SMTP server
    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()  # Start TLS encryption
    server.login(email, password)
    
    # Send the email
    server.sendmail(email, recipient_email, message.as_string())
    print('Email sent successfully!')

    # Close the server connection
    server.quit()
except Exception as e:
    print(f'Error: {e}')
