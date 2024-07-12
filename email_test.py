# import smtplib
# from email.mime.multipart import MIMEMultipart
# from email.mime.text import MIMEText

# # Email configuration
# smtp_server = 'smtp.gmail.com'
# smtp_port = 587
# gmail_user = 'ohboy3947@gmail.com'
# gmail_password = 'Platform93/4'

# # Email content
# from_email = 'ohboy3947@gmail.com'
# to_email = 'saurabhiitd3@gmail.com'
# subject = 'Test Email'
# body = 'This is a test email sent from Python!'

# # Create the email
# msg = MIMEMultipart()
# msg['From'] = from_email
# msg['To'] = to_email
# msg['Subject'] = subject
# msg.attach(MIMEText(body, 'plain'))

# # Send the email
# try:
#     server = smtplib.SMTP(smtp_server, smtp_port)
#     server.starttls()  # Secure the connection
#     server.login(gmail_user, gmail_password)
#     text = msg.as_string()
#     server.sendmail(from_email, to_email, text)
#     print('Email sent successfully')
# except Exception as e:
#     print(f'Failed to send email: {e}')
# finally:
#     server.quit()

import win32com.client as win32
outlook = win32.Dispatch('outlook.application')
mail = outlook.CreateItem(0)
mail.To = 'saurabhiitd3@gmail.com'
mail.Subject = 'Message subject'
mail.Body = 'Message body'
mail.HTMLBody = '<h2>HTML Message body</h2>' #this field is optional

# To attach a file to the email (optional):
# attachment  = "Path to the attachment"
# mail.Attachments.Add(attachment)

mail.Send()