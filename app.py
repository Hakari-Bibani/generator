import streamlit as st
import os
import csv
from datetime import datetime
from psd_tools import PSDImage
from PIL import Image, ImageFont, ImageDraw
import tempfile
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from dotenv import load_dotenv
import uuid

# Load environment variables from .env if available
load_dotenv()

# Initialize session state for authentication and certificate tracking
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'sent_certificates' not in st.session_state:
    st.session_state.sent_certificates = []

# File path for saving certificate details
CERTIFICATE_LOG = "certificate_log.csv"

# Check if CSV exists, if not create headers
def initialize_csv():
    if not os.path.exists(CERTIFICATE_LOG):
        with open(CERTIFICATE_LOG, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Number', 'Name', 'Email', 'Serial Number'])

def check_password():
    """Returns `True` if the user had the correct password."""
    def password_entered():
        if st.session_state["password"] == st.secrets.get("password", "default_password"):
            st.session_state.authenticated = True
            del st.session_state["password"]
        else:
            st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.text_input("Please enter the password", type="password", on_change=password_entered, key="password")
        return False
    return True

def get_email_config():
    if hasattr(st, 'secrets') and 'smtp' in st.secrets:
        return {
            'server': st.secrets.smtp.server,
            'port': st.secrets.smtp.port,
            'email': st.secrets.smtp.email,
            'password': st.secrets.smtp.password
        }
    else:
        return {
            'server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
            'port': int(os.getenv('SMTP_PORT', '587')),
            'email': os.getenv('SENDER_EMAIL'),
            'password': os.getenv('SENDER_PASSWORD')
        }

def generate_serial_number():
    return str(uuid.uuid4())[:8]  # Short unique serial number

def modify_psd(template_path, name, date, serial_number):
    psd = PSDImage.open(template_path)
    image = psd.compose().resize((1714, 1205), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(image)
    try:
        name_font = ImageFont.truetype("fonts/Pristina Regular.ttf", size=75)
        date_font = ImageFont.truetype("fonts/Arial-Bold.ttf", size=18)
        serial_font = ImageFont.truetype("fonts/Arial-Bold.ttf", size=15)
    except OSError:
        st.error("Font files not found. Ensure required fonts exist in the 'fonts' folder.")
        raise

    # Add name
    name_color = (190, 140, 45)
    name_bbox = draw.textbbox((0, 0), name, font=name_font)
    name_x = 959 - ((name_bbox[2] - name_bbox[0]) / 2)
    draw.text((name_x, 618), name, font=name_font, fill=name_color)

    # Add date
    date_color = (79, 79, 76)
    draw.text((660, 1038), date, font=date_font, fill=date_color)

    # Add serial number (bottom right)
    draw.text((1500, 1150), f"Serial: {serial_number}", font=serial_font, fill=(0, 0, 0))

    temp_path = tempfile.mktemp(suffix='.png')
    image.save(temp_path, quality=100, dpi=(300, 300))
    return temp_path

def convert_to_pdf(image_path):
    image = Image.open(image_path).convert('RGB')
    pdf_path = tempfile.mktemp(suffix='.pdf')
    image.save(pdf_path, 'PDF', resolution=300.0, quality=100, optimize=False)
    return pdf_path

def save_to_csv(number, name, email, serial_number):
    with open(CERTIFICATE_LOG, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([number, name, email, serial_number])

def send_certificate(recipient_email, subject, body, pdf_path):
    config = get_email_config()
    if not all(config.values()):
        raise ValueError("Missing email configuration.")
    message = MIMEMultipart()
    message['From'] = config['email']
    message['To'] = recipient_email
    message['Subject'] = subject
    message.attach(MIMEText(body, 'plain'))
    with open(pdf_path, 'rb') as f:
        attachment = MIMEApplication(f.read(), _subtype='pdf')
        attachment.add_header('Content-Disposition', 'attachment', filename='certificate.pdf')
        message.attach(attachment)
    try:
        with smtplib.SMTP(config['server'], config['port']) as server:
            server.starttls()
            server.login(config['email'], config['password'])
            server.send_message(message)
            st.success("Email sent successfully!")
    except Exception as e:
        raise Exception(f"Email error: {str(e)}")

def main():
    initialize_csv()
    if not check_password():
        st.stop()
    st.title("Certificate Generator & Sender")

    config = get_email_config()
    st.sidebar.title("Configuration Status")
    st.sidebar.text(f"SMTP Server: {config['server']}")
    st.sidebar.text(f"Sender Email: {config['email']}")

    # Display sent certificates
    st.sidebar.title("Sent Certificates")
    for cert in st.session_state.sent_certificates:
        st.sidebar.text(f"{cert['number']}. {cert['name']} ({cert['serial']})")

    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.experimental_rerun()

    # Input form
    with st.form("certificate_form"):
        full_name = st.text_input("Full Name")
        email = st.text_input("Email Address")
        date = st.date_input("Date")
        submit_button = st.form_submit_button("Generate & Send Certificate")

        if submit_button and full_name and email and date:
            try:
                serial_number = generate_serial_number()
                formatted_date = date.strftime("%B %d, %Y")
                psd_path = "templates/certificate.psd"
                modified_psd = modify_psd(psd_path, full_name, formatted_date, serial_number)
                pdf_path = convert_to_pdf(modified_psd)
                first_name = full_name.split()[0]
                email_subject = "Your Course Certificate"
                email_body = f"Dear {first_name},\n\nYour certificate is attached. Congratulations!"
                send_certificate(email, email_subject, email_body, pdf_path)

                # Save to CSV and session state
                certificate_number = len(st.session_state.sent_certificates) + 1
                save_to_csv(certificate_number, full_name, email, serial_number)
                st.session_state.sent_certificates.append({
                    'number': certificate_number,
                    'name': full_name,
                    'serial': serial_number
                })

                # Clean up
                os.remove(modified_psd)
                os.remove(pdf_path)
            except Exception as e:
                st.error(str(e))
        elif submit_button:
            st.warning("Please fill in all fields.")

if __name__ == "__main__":
    main()
