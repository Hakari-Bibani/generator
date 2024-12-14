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
    """
    Validates email format.
    Returns (is_valid, message)
    """
    # Remove any whitespace
    email = email.strip()
    
    # Basic email pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if ' ' in email:
        return False, "Email address cannot contain spaces"
    
    if not re.match(pattern, email):
        return False, "Invalid email format"
    
    return True, "Valid email"

def check_password():
    """Returns `True` if the user had the correct password."""
    def password_entered():
        """Checks whether a password entered by the user is correct."""
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

def ensure_data_directory():
    """Ensure data directory and CSV file exist"""
    try:
        # Create directory if it doesn't exist
        os.makedirs('participants_data', exist_ok=True)
        
        # Create CSV file if it doesn't exist
        csv_path = 'participants_data/certificates_data.csv'
        if not os.path.exists(csv_path):
            initial_df = pd.DataFrame(columns=['Number', 'Date', 'Name', 'Email', 'Serial Number'])
            initial_df.to_csv(csv_path, index=False)
        
        return True
    except Exception as e:
        st.error(f"Error setting up data directory: {str(e)}")
        return False

def get_next_serial_number():
    ensure_data_directory()
    try:
        # Try to read existing CSV file
        csv_path = 'participants_data/certificates_data.csv'
        df = pd.read_csv(csv_path)
        last_number = len(df) + 1
        
        # Generate serial number
        current_year = datetime.now().year
        return f"PY{current_year}-{last_number:04d}"
    except Exception as e:
        st.error(f"Error generating serial number: {str(e)}")
        return f"PY{datetime.now().year}-{datetime.now().timestamp():.0f}"

def save_participant_data(name, email, serial_number, date, number):
    """Save participant data to CSV file"""
    ensure_data_directory()
    try:
        # Prepare new data
        new_data = {
            'Number': number,
            'Date': date,
            'Name': name,
            'Email': email,
            'Serial Number': serial_number
        }
        
        csv_path = 'participants_data/certificates_data.csv'
        
        # Read existing or create new DataFrame
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
        else:
            df = pd.DataFrame([new_data])
        
        # Save to CSV
        df.to_csv(csv_path, index=False)
        
        # Save backup
        backup_path = 'participants_data/certificates_backup.csv'
        df.to_csv(backup_path, index=False)
        
        return True
    except Exception as e:
        st.error(f"Error saving participant data: {str(e)}")
        return False

def display_participants():
    """Display participants from CSV in sidebar"""
    ensure_data_directory()
    try:
        csv_path = 'participants_data/certificates_data.csv'
        df = pd.read_csv(csv_path)
        
        if len(df) > 0:
            # Display total number of certificates
            st.sidebar.metric("Total Certificates", len(df))
            
            st.sidebar.title("Recent Certificates")
            
            # Display recent certificates with all information
            st.sidebar.dataframe(
                df[['Number', 'Name', 'Email', 'Serial Number', 'Date']].tail(10),
                hide_index=True,
                column_config={
                    'Number': 'No.',
                    'Name': 'Participant Name',
                    'Email': 'Email Address',
                    'Serial Number': 'Serial No.',
                    'Date': 'Issue Date'
                }
            )
            
            # Add download button
            csv = df.to_csv(index=False)
            st.sidebar.download_button(
                "Download Complete List",
                csv,
                "certificates_data.csv",
                "text/csv",
                key='download-csv'
            )
            
            # Display statistics
            st.sidebar.title("Statistics")
            today_date = datetime.now().strftime('%B %d, %Y')
            certificates_today = len(df[df['Date'] == today_date])
            st.sidebar.text(f"Certificates Today: {certificates_today}")
            st.sidebar.text(f"Latest Serial: {df['Serial Number'].iloc[-1]}")
        else:
            st.sidebar.write("No certificates generated yet")
            
    except Exception as e:
        st.sidebar.write("Ready to generate certificates!")

[Previous functions remain the same: modify_psd, convert_to_pdf, send_certificate]

def main():
    if not check_password():
        st.stop()
    
    st.title("Certificate Generator & Sender")
    
    # Ensure data directory exists
    ensure_data_directory()
    
    # Show configuration status
    config = get_email_config()
    st.sidebar.title("Configuration Status")
    st.sidebar.write("Email Configuration:")
    st.sidebar.text(f"SMTP Server: {config['server']}")
    st.sidebar.text(f"SMTP Port: {config['port']}")
    st.sidebar.text(f"Sender Email: {config['email']}")
    st.sidebar.text(f"Password Set: {'✓' if config['password'] else '✗'}")
    
    # Display participants
    display_participants()
    
    # Add logout button
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.experimental_rerun()
    
    # User input form
    with st.form("certificate_form"):
        full_name = st.text_input("Full Name")
        email = st.text_input("Email Address")
        date = st.date_input("Date")
        
        submit_button = st.form_submit_button("Generate & Send Certificate")
        
        if submit_button:
            if full_name and email and date:
                # Validate email first
                is_valid, message = validate_email(email)
                if not is_valid:
                    st.error(f"Email Error: {message}")
                else:
                    try:
                        # Get current number
                        csv_path = 'participants_data/certificates_data.csv'
                        df = pd.read_csv(csv_path)
                        current_number = len(df) + 1
                        
                        # Generate serial number
                        serial_number = get_next_serial_number()
                        
                        # Format date
                        formatted_date = date.strftime("%B %d, %Y")
                        
                        # Generate certificate
                        psd_path = "templates/certificate.psd"
                        modified_psd = modify_psd(psd_path, full_name, formatted_date, serial_number)
                        
                        # Convert to PDF
                        pdf_path = convert_to_pdf(modified_psd)
                        
                        # Preview certificate
                        st.image(modified_psd, caption=f"Certificate Preview - {serial_number}", use_column_width=True)
                        
                        # Send email
                        first_name = full_name.split()[0]
                        email_subject = "Your Course Certificate"
                        email_body = f"""Dear {first_name},

Please accept our sincere congratulations on successfully completing the Comprehensive Python Training course. 
Your dedication and hard work have been commendable. We are delighted to present you with your certificate, attached herewith.

Certificate Serial Number: {serial_number}

We wish you all the best in your future endeavors."""
                        
                        # Clean email address
                        clean_email = email.strip()
                        send_certificate(clean_email, email_subject, email_body, pdf_path)
                        
                        # Save participant data with number
                        if save_participant_data(full_name, clean_email, serial_number, formatted_date, current_number):
                            st.success(f"Certificate generated and sent successfully! Serial Number: {serial_number}")
                        
                        # Clean up temporary files
                        os.remove(modified_psd)
                        os.remove(pdf_path)
                        
                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")
            else:
                st.warning("Please fill in all fields.")

if __name__ == "__main__":
    main()
