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

# Utility functions
def modify_psd(template_path, name, date):
    # Open the PSD file
    psd = PSDImage.open(template_path)
    
    # Convert to PIL Image
    image = psd.compose()
    
    # Create drawing object
    draw = ImageDraw.Draw(image)
    
    # Load the custom font
    name_font = ImageFont.truetype("fonts/AlexBrush-Regular.ttf", size=61)
    date_font = ImageFont.truetype("fonts/AlexBrush-Regular.ttf", size=11)
    
    # Add name
    name_color = (190, 140, 75)  # RGB for #be8c4d
    draw.text((959, 655), name, font=name_font, fill=name_color)
    
    # Add date
    date_color = (79, 79, 76)  # RGB for #4f4f4c
    draw.text((739, 1048), date, font=date_font, fill=date_color)
    
    # Save modified image
    temp_path = tempfile.mktemp(suffix='.png')
    image.save(temp_path)
    
    return temp_path

def convert_to_pdf(image_path):
    # Open the image
    image = Image.open(image_path)
    
    # Convert to RGB if necessary
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Create temporary PDF file
    pdf_path = tempfile.mktemp(suffix='.pdf')
    
    # Save as PDF
    image.save(pdf_path, 'PDF', resolution=100.0)
    
    return pdf_path

def send_certificate(recipient_email, subject, body, pdf_path):
    # Email configuration
    smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    sender_email = os.getenv('SENDER_EMAIL')
    sender_password = os.getenv('SENDER_PASSWORD')
    
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
    
    # Send email
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(message)

# Main Streamlit app
def main():
    st.title("Certificate Generator & Sender")
    
    # User input form
    with st.form("certificate_form"):
        full_name = st.text_input("Full Name")
        email = st.text_input("Email Address")
        date = st.date_input("Date")
        
        submit_button = st.form_submit_button("Generate & Send Certificate")
        
        if submit_button:
            if full_name and email and date:
                try:
                    # Convert date to required format
                    formatted_date = date.strftime("%B %d, %Y")
                    
                    # Generate certificate
                    psd_path = "templates/certificate.psd"
                    modified_psd = modify_psd(psd_path, full_name, formatted_date)
                    
                    # Convert to PDF
                    pdf_path = convert_to_pdf(modified_psd)
                    
                    # Send email
                    first_name = full_name.split()[0]
                    email_subject = "Your Course Certificate"
                    email_body = f"""Dear {first_name},

Thank you for participating in our course. We are delighted to have you with us. Please find your certificate attached.

Best regards,
Your Organization Name"""
                    
                    send_certificate(email, email_subject, email_body, pdf_path)
                    
                    st.success("Certificate generated and sent successfully!")
                    
                    # Clean up temporary files
                    os.remove(modified_psd)
                    os.remove(pdf_path)
                    
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
            else:
                st.warning("Please fill in all fields.")

if __name__ == "__main__":
    main()
