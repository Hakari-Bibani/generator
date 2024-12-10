import streamlit as st
import os
from datetime import datetime
from psd_tools import PSDImage
from PIL import Image, ImageFont, ImageDraw
import tempfile
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# [Previous functions remain the same: modify_psd and convert_to_pdf]

def send_certificate(recipient_email, subject, body, pdf_path):
    # Email configuration
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    sender_email = os.getenv('SENDER_EMAIL')
    sender_password = os.getenv('SENDER_PASSWORD')
    
    if not all([smtp_server, smtp_port, sender_email, sender_password]):
        raise ValueError("Missing email configuration. Please check your environment variables.")
    
    # Create message
    message = MIMEMultipart()
    message['From'] = sender_email
    message['To'] = recipient_email
    message['Subject'] = subject
    
    # Add body
    message.attach(MIMEText(body, 'plain'))
    
    # Attach PDF
    with open(pdf_path, 'rb') as f:
        pdf_attachment = MIMEApplication(f.read(), _subtype='pdf')
        pdf_attachment.add_header('Content-Disposition', 'attachment', filename='certificate.pdf')
        message.attach(pdf_attachment)
    
    try:
        # Send email with detailed error handling
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            # Show connection steps for debugging
            st.write("Connecting to SMTP server...")
            server.set_debuglevel(1)  # Enable debug output
            
            # Start TLS
            st.write("Starting TLS encryption...")
            server.starttls()
            
            # Login
            st.write("Attempting login...")
            server.login(sender_email, sender_password)
            
            # Send message
            st.write("Sending email...")
            server.send_message(message)
            
            st.write("Email sent successfully!")
            
    except smtplib.SMTPAuthenticationError:
        raise Exception(
            "Email authentication failed. Please ensure:\n"
            "1. You're using an App Password (not your regular password)\n"
            "2. 2-Step Verification is enabled on your Google Account\n"
            "3. The App Password is correctly copied to your environment variables"
        )
    except smtplib.SMTPException as e:
        raise Exception(f"SMTP error occurred: {str(e)}")
    except Exception as e:
        raise Exception(f"An unexpected error occurred: {str(e)}")

# Main Streamlit app
def main():
    st.title("Certificate Generator & Sender")
    
    # Add configuration status
    st.sidebar.title("Configuration Status")
    email_config = {
        "SMTP Server": os.getenv('SMTP_SERVER'),
        "SMTP Port": os.getenv('SMTP_PORT'),
        "Sender Email": os.getenv('SENDER_EMAIL'),
        "Password Set": "Yes" if os.getenv('SENDER_PASSWORD') else "No"
    }
    
    st.sidebar.write("Email Configuration:")
    for key, value in email_config.items():
        if key != "Password Set":
            st.sidebar.text(f"{key}: {value}")
        else:
            st.sidebar.text(f"{key}: {'✓' if value == 'Yes' else '✗'}")
    
    # User input form
    with st.form("certificate_form"):
        full_name = st.text_input("Full Name")
        email = st.text_input("Email Address")
        date = st.date_input("Date")
        
        submit_button = st.form_submit_button("Generate & Send Certificate")
        
        if submit_button:
            if full_name and email and date:
                try:
                    # [Rest of the code remains the same]
                    ...
                    
                except Exception as e:
                    st.error(str(e))
                    if "authentication failed" in str(e).lower():
                        st.error("Please check the sidebar for configuration status.")
            else:
                st.warning("Please fill in all fields.")

if __name__ == "__main__":
    main()
