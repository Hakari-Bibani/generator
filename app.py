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
import pandas as pd
import re

# Load environment variables from .env if available
load_dotenv()

# Initialize session state for authentication and participants data
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

def validate_email(email):
    """Validates email format."""
    email = email.strip()
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if ' ' in email:
        return False, "Email address cannot contain spaces"
    
    if not re.match(pattern, email):
        return False, "Invalid email format"
    
    return True, "Valid email"

def check_password():
    """Returns `True` if the user had the correct password."""
    def password_entered():
        if st.session_state["password"] == st.secrets.get("password", "default_password"):
            st.session_state.authenticated = True
            del st.session_state["password"]
        else:
            st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.text_input(
            "Please enter the password", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
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

def ensure_data_directory():
    """Ensure data directory and CSV file exist with proper initialization"""
    try:
        os.makedirs('participants_data', exist_ok=True)
        csv_path = 'participants_data/certificates_data.csv'
        
        if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
            initial_df = pd.DataFrame({
                'Number': [],
                'Date': [],
                'Name': [],
                'Email': [],
                'Serial Number': []
            })
            initial_df.to_csv(csv_path, index=False, encoding='utf-8')
        
        df = pd.read_csv(csv_path)
        expected_columns = ['Number', 'Date', 'Name', 'Email', 'Serial Number']
        if not all(col in df.columns for col in expected_columns):
            initial_df = pd.DataFrame(columns=expected_columns)
            initial_df.to_csv(csv_path, index=False, encoding='utf-8')
        
        return True
    except Exception as e:
        st.error(f"Error setting up data directory: {str(e)}")
        return False

def get_next_serial_number():
    ensure_data_directory()
    try:
        csv_path = 'participants_data/certificates_data.csv'
        df = pd.read_csv(csv_path)
        last_number = len(df) if not df.empty else 0
        next_number = last_number + 1
        
        current_year = datetime.now().year
        return f"PY{current_year}-{next_number:04d}"
    except Exception as e:
        st.error(f"Error generating serial number: {str(e)}")
        return f"PY{datetime.now().year}-{datetime.now().timestamp():.0f}"

def save_participant_data(name, email, serial_number, date, number):
    ensure_data_directory()
    try:
        new_data = {
            'Number': number,
            'Date': date,
            'Name': name,
            'Email': email,
            'Serial Number': serial_number
        }
        
        csv_path = 'participants_data/certificates_data.csv'
        
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
        else:
            df = pd.DataFrame([new_data])
        
        df.to_csv(csv_path, index=False)
        backup_path = 'participants_data/certificates_backup.csv'
        df.to_csv(backup_path, index=False)
        
        return True
    except Exception as e:
        st.error(f"Error saving participant data: {str(e)}")
        return False

def modify_psd(template_path, name, date, serial_number):
    psd = PSDImage.open(template_path)
    image = psd.compose()
    image = image.resize((1714, 1205), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(image)
    
    try:
        name_font = ImageFont.truetype("fonts/Pristina Regular.ttf", size=75)
        date_font = ImageFont.truetype("fonts/Arial-Bold.ttf", size=18)
        serial_font = ImageFont.truetype("fonts/Arial-Bold.ttf", size=12)
    except OSError:
        st.error("Font files not found. Please ensure you have required fonts in the fonts directory.")
        raise
    
    # Add name
    name_color = (190, 140, 45)
    name_bbox = draw.textbbox((0, 0), name, font=name_font)
    name_width = name_bbox[2] - name_bbox[0]
    name_x = 959 - (name_width / 2)
    name_y = 618
    draw.text((name_x, name_y), name, font=name_font, fill=name_color)
    
    # Add date
    date_color = (79, 79, 76)
    date_x = 660
    draw.text((date_x, 1038), date, font=date_font, fill=date_color)
    
    # Add serial number
    serial_color = (79, 79, 76)
    serial_x = 1500
    serial_y = 1150
    draw.text((serial_x, serial_y), serial_number, font=serial_font, fill=serial_color)
    
    temp_path = tempfile.mktemp(suffix='.png')
    image.save(temp_path, quality=100, dpi=(300, 300))
    
    return temp_path

def convert_to_pdf(image_path):
    image = Image.open(image_path)
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    pdf_path = tempfile.mktemp(suffix='.pdf')
    image.save(
        pdf_path, 
        'PDF', 
        resolution=300.0,
        quality=100,
        optimize=False
    )
    return pdf_path

def send_certificate(recipient_email, subject, body, pdf_path):
    config = get_email_config()
    
    if not all(config.values()):
        raise ValueError("Missing email configuration. Please check your secrets or environment variables.")
    
    message = MIMEMultipart()
    message['From'] = config['email']
    message['To'] = recipient_email
    message['Subject'] = subject
    
    message.attach(MIMEText(body, 'plain'))
    
    with open(pdf_path, 'rb') as f:
        pdf_attachment = MIMEApplication(f.read(), _subtype='pdf')
        pdf_attachment.add_header('Content-Disposition', 'attachment', filename='certificate.pdf')
        message.attach(pdf_attachment)
    
    try:
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

def display_participants():
    ensure_data_directory()
    try:
        csv_path = 'participants_data/certificates_data.csv'
        df = pd.read_csv(csv_path)
        
        if len(df) > 0:
            st.sidebar.metric("Total Certificates", len(df))
            st.sidebar.title("Recent Certificates")
            
            st.sidebar.dataframe(
                df[['Number', 'Name', 'Email', 'Serial Number', 'Date']].tail(10),
                hide_index=True
            )
            
            csv = df.to_csv(index=False)
            st.sidebar.download_button(
                "Download Complete List",
                csv,
                "certificates_data.csv",
                "text/csv",
                key='download-csv'
            )
            
            st.sidebar.title("Statistics")
            today_date = datetime.now().strftime('%B %d, %Y')
            certificates_today = len(df[df['Date'] == today_date])
            st.sidebar.text(f"Certificates Today: {certificates_today}")
            if not df.empty:
                st.sidebar.text(f"Latest Serial: {df['Serial Number'].iloc[-1]}")
        else:
            st.sidebar.write("No certificates generated yet")
            
    except Exception as e:
        st.sidebar.write("Ready to generate certificates!")

def main():
    if not check_password():
        st.stop()
    
    st.title("Certificate Generator & Sender")
    ensure_data_directory()
    
    config = get_email_config()
    st.sidebar.title("Configuration Status")
    st.sidebar.write("Email Configuration:")
    st.sidebar.text(f"SMTP Server: {config['server']}")
    st.sidebar.text(f"SMTP Port: {config['port']}")
    st.sidebar.text(f"Sender Email: {config['email']}")
    st.sidebar.text(f"Password Set: {'✓' if config['password'] else '✗'}")
    
    display_participants()
    
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.experimental_rerun()
    
    with st.form("certificate_form"):
        full_name = st.text_input("Full Name")
        email = st.text_input("Email Address")
        date = st.date_input("Date")
        
        submit_button = st.form_submit_button("Generate & Send Certificate")
        
        if submit_button:
            if full_name and email and date:
                is_valid, message = validate_email(email)
                if not is_valid:
                    st.error(f"Email Error: {message}")
                else:
                    try:
                        csv_path = 'participants_data/certificates_data.csv'
                        df = pd.read_csv(csv_path)
                        current_number = len(df) + 1
                        
                        serial_number = get_next_serial_number()
                        formatted_date = date.strftime("%B %d, %Y")
                        
                        psd_path = "templates/certificate.psd"
                        modified_psd = modify_psd(psd_path, full_name, formatted_date, serial_number)
                        pdf_path = convert_to_pdf(modified_psd)
                        
                        st.image(modified_psd, caption=f"Certificate Preview - {serial_number}", use_column_width=True)
                        
                        first_name = full_name.split()[0]
                        email_subject = "Your Course Certificate"
                        email_body = f"""Dear {first_name},

Please accept our sincere congratulations on successfully completing the Comprehensive Python Training course. 
Your dedication and hard work have been commendable. We are delighted to present you with your certificate, attached herewith.

Certificate Serial Number: {serial_number}

We wish you all the best in your future endeavors."""
                        
                        clean_email = email.strip()
                        send_certificate(clean_email, email_subject, email_body, pdf_path)
                        
                        if save_participant_data(full_name, clean_email, serial_number, formatted_date, current_number):
                            st.success(f"Certificate generated and sent successfully! Serial Number: {serial_number}")
                        
                        os.remove(modified_psd)
                        os.remove(pdf_path)
                        
                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")
            else:
                st.warning("Please fill in all fields.")

if __name__ == "__main__":
    main()
