import streamlit as st 
from PIL import Image
import img2pdf
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

def modify_certificate(name, date):
  # Open the PSD template
  psd = Image.open("template.psd")
  
  # Modify the name and date layers
  # (implementation depends on PSD layer names/structure)
  # ...

  # Save modified PSD as PDF
  pdf_bytes = img2pdf.convert(psd)
  return pdf_bytes

def send_email(email, name, pdf_file):
  # Email configuration 
  smtp_server = 'smtp.gmail.com'
  smtp_port = 587
  sender_email = st.secrets["email"]
  password = st.secrets["password"]

  # Create email message
  message = MIMEMultipart()
  message['From'] = sender_email
  message['To'] = email
  message['Subject'] = "Course Certificate"
  
  body = f"""Dear {name},

  Thank you for participating in our course. We are delighted to have you with us. 
  Please find your certificate attached.

  Best regards,
  Hawkar Ali Abdulhaq"""

  message.attach(MIMEText(body, 'plain'))

  # Attach PDF 
  attachment = MIMEBase('application', 'pdf')
  attachment.set_payload(pdf_file) 
  encoders.encode_base64(attachment)
  attachment.add_header('Content-Disposition', "attachment; filename= certificate.pdf")
  message.attach(attachment)

  # Send email
  server = smtplib.SMTP(smtp_server, smtp_port)
  server.starttls()
  server.login(sender_email, password)
  server.send_message(message)
  server.quit()

# Streamlit app
st.title("Certificate Generator")

with st.form("input_form"):
  name = st.text_input("Participant Name")
  email = st.text_input("Email Address") 
  date = st.date_input("Certificate Date")

  submitted = st.form_submit_button("Generate Certificate")
  if submitted:
    pdf_bytes = modify_certificate(name, date)
    send_email(email, name, pdf_bytes)
    st.success("Certificate generated and emailed!")

if st.secrets["password"] == "":
  st.warning("Email password not set. Add it in .streamlit/secrets.toml")
