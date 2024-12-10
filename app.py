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

# Load environment variables from .env if available
load_dotenv()

# Template constants
TEMPLATE_WIDTH = 1714
TEMPLATE_HEIGHT = 1205

def check_font_file(font_path):
    """Check if font file exists"""
    if not os.path.exists(font_path):
        raise FileNotFoundError(f"Font file not found: {font_path}")
    return font_path

def modify_psd(template_path, name, date):
    """Modify PSD template with name and date"""
    # Open the PSD file
    psd = PSDImage.open(template_path)
    
    # Convert to PIL Image and ensure correct dimensions
    image = psd.compose()
    image = image.resize((TEMPLATE_WIDTH, TEMPLATE_HEIGHT), Image.Resampling.LANCZOS)
    
    # Create drawing object
    draw = ImageDraw.Draw(image)
    
    try:
        # Load the custom fonts
        name_font = ImageFont.truetype(check_font_file("fonts/Pristina-Regular.ttf"), size=61)
        date_font = ImageFont.truetype(check_font_file("fonts/Arial-Bold.ttf"), size=11)
    except FileNotFoundError:
        st.error("Required fonts not found. Please make sure both Pristina Regular and Arial Bold fonts are in the fonts folder.")
        raise
    
    # Add name with specified parameters
    name_color = (190, 140, 75)  # RGB for #be8c4d
    # Calculate text size for centering if needed
    name_bbox = draw.textbbox((0, 0), name, font=name_font)
    name_width = name_bbox[2] - name_bbox[0]
    # Use the original x, y coordinates
    draw.text((959, 655), name, font=name_font, fill=name_color)
    
    # Add date with specified parameters
    date_color = (79, 79, 76)  # RGB for #4f4f4c
    draw.text((739, 1048), date, font=date_font, fill=date_color)
    
    # Save modified image
    temp_path = tempfile.mktemp(suffix='.png')
    image.save(temp_path)
    
    return temp_path

def convert_to_pdf(image_path):
    """Convert image to PDF"""
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

def get_email_config():
    """Get email configuration from either Streamlit secrets or environment variables"""
    # Try to get from Streamlit secrets first (TOML format)
    if hasattr(st, 'secrets') and 'smtp' in st.secrets:
        return {
            'server': st.secrets.smtp.server,
            'port': st.secrets.smtp.port,
            'email': st.secrets.smtp.email,
            'password': st.secrets.smtp.password
        }
    # Fall back to environment variables
    else:
        return {
            'server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            'port': int(os.getenv('SMTP_PORT', '587')),
            'email': os.getenv('SENDER_EMAIL'),
            'password': os.getenv('SENDER_PASSWORD')
        }

def send_certificate(recipient_email, subject, body, pdf_path):
    """Send certificate via email"""
    # Get email configuration
    config = get_email_config()
    
    if not all(config.values()):
        raise ValueError("Missing email configuration. Please check your secrets or environment variables.")
    
    # Create message
    message = MIMEMultipart()
    message['From'] = config['email']
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
        # Send email
        with smtplib.SMTP(config['server'], config['port']) as server:
            server.starttls()
            server.login(config['email'], config['password'])
            server.send_message(message)
            st.success("Email sent successfully!")
            
    except smtplib.SMTPAuthenticationError:
        raise Exception(
            "Email authentication failed. Please ensure:\n"
            "1. You're using an App Password (not your regular password)\n"
            "2. 2-Step Verification is enabled on your Google Account\n"
            "3. The App Password is correctly copied to your secrets"
        )
    except smtplib.SMTPException as e:
        raise Exception(f"SMTP error occurred: {str(e)}")
    except Exception as e:
        raise Exception(f"An unexpected error occurred: {str(e)}")

def main():
    """Main Streamlit application"""
    st.title("Certificate Generator & Sender")
    
    # Show configuration status
    config = get_email_config()
    st.sidebar.title("Configuration Status")
    st.sidebar.write("Email Configuration:")
    st.sidebar.text(f"SMTP Server: {config['server']}")
    st.sidebar.text(f"SMTP Port: {config['port']}")
    st.sidebar.text(f"Sender Email: {config['email']}")
    st.sidebar.text(f"Password Set: {'✓' if config['password'] else '✗'}")
    
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
                    if not os.path.exists(psd_path):
                        st.error(f"Template file not found: {psd_path}")
                        return
                        
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
                    
                    # Clean up temporary files
                    os.remove(modified_psd)
                    os.remove(pdf_path)
                    
                except Exception as e:
                    st.error(str(e))
            else:
                st.warning("Please fill in all fields.")

if __name__ == "__main__":
    main()
