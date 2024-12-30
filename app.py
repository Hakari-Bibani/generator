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
import github
from github import Github
import io
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from .env if available
load_dotenv()

# Initialize session states
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

def load_existing_records():
    """Load existing certificate records from GitHub"""
    try:
        github_token = st.secrets.get("github_token") or os.getenv("GITHUB_TOKEN")
        repo_name = st.secrets.get("github_repo") or os.getenv("GITHUB_REPO")
        
        if not github_token or not repo_name:
            logger.error("GitHub configuration missing")
            return []
        
        g = Github(github_token)
        repo = g.get_repo(repo_name)
        
        try:
            # Try to get existing CSV file
            file_content = repo.get_contents("certificates/records.csv")
            content = file_content.decoded_content.decode()
            
            # Read CSV content into DataFrame
            df = pd.read_csv(io.StringIO(content))
            
            # Convert DataFrame to list of dictionaries
            records = df.to_dict('records')
            logger.info(f"Loaded {len(records)} existing records from GitHub")
            return records
        except github.GithubException as e:
            logger.warning(f"No existing records found: {str(e)}")
            return []
            
    except Exception as e:
        logger.error(f"Error loading existing records: {str(e)}")
        return []

def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets.get("password", "default_password"):
            st.session_state.authenticated = True
            del st.session_state["password"]  # Don't store password
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
    """Get email configuration from secrets or environment variables."""
    # Try to get from Streamlit secrets first
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

def generate_serial_number():
    """Generate a serial number in format PY-YYYY-XXXX considering existing records"""
    current_year = datetime.now().year
    
    # Get the last serial number from all records (including GitHub)
    last_number = 0
    
    # Check session state certificates
    all_certificates = st.session_state.certificates
    
    if all_certificates:
        # Extract all serial numbers
        serial_numbers = [cert['serial'] for cert in all_certificates]
        # Find the highest number
        for serial in serial_numbers:
            try:
                number = int(serial.split('-')[-1])
                last_number = max(last_number, number)
            except ValueError:
                continue
    
    new_number = str(last_number + 1).zfill(4)
    logger.info(f"Generated new serial number: PY-{current_year}-{new_number}")
    return f"PY-{current_year}-{new_number}"

def save_to_github(data):
    """Save certificate data to GitHub as CSV, preserving existing records"""
    try:
        github_token = st.secrets.get("github_token") or os.getenv("GITHUB_TOKEN")
        repo_name = st.secrets.get("github_repo") or os.getenv("GITHUB_REPO")
        
        if not github_token or not repo_name:
            raise ValueError("GitHub configuration missing")
            
        g = Github(github_token)
        repo = g.get_repo(repo_name)
        
        # Prepare CSV data
        df = pd.DataFrame(data)
        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_content = csv_buffer.getvalue()
        
        # File path in repository
        file_path = "certificates/records.csv"
        
        try:
            # Try to get existing file
            existing_file = repo.get_contents(file_path)
            # Update existing file
            repo.update_file(
                file_path,
                f"Update certificates record - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                csv_content,
                existing_file.sha
            )
            logger.info("Successfully updated existing records in GitHub")
        except github.GithubException:
            # Create new file if it doesn't exist
            repo.create_file(
                file_path,
                f"Create certificates record - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                csv_content
            )
            logger.info("Created new records file in GitHub")
            
        return True
    except Exception as e:
        logger.error(f"Error saving to GitHub: {str(e)}")
        return False

def modify_psd(template_path, name, date, serial_number):
    """Modify PSD template with name, date, and serial number."""
    try:
        # Open the PSD file
        psd = PSDImage.open(template_path)
        
        # Convert to PIL Image
        image = psd.compose()
        image = image.resize((1714, 1205), Image.Resampling.LANCZOS)
        
        # Create drawing object
        draw = ImageDraw.Draw(image)
        
        try:
            name_font = ImageFont.truetype("fonts/Pristina Regular.ttf", size=75)
            date_font = ImageFont.truetype("fonts/Arial-Bold.ttf", size=18)
            serial_font = ImageFont.truetype("fonts/Arial-Bold.ttf", size=16)
        except OSError as e:
            logger.error(f"Font loading error: {str(e)}")
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
        draw.text((660, 1038), date, font=date_font, fill=date_color)
        
        # Add serial number
        serial_color = (79, 79, 76)
        serial_bbox = draw.textbbox((0, 0), serial_number, font=serial_font)
        serial_width = serial_bbox[2] - serial_bbox[0]
        serial_x = 1714 - serial_width - 40
        serial_y = 1150
        draw.text((serial_x, serial_y), serial_number, font=serial_font, fill=serial_color)
        
        # Save modified image
        temp_path = tempfile.mktemp(suffix='.png')
        image.save(temp_path, quality=100, dpi=(300, 300))
        
        logger.info(f"Successfully modified certificate for {name}")
        return temp_path
    except Exception as e:
        logger.error(f"Error modifying PSD: {str(e)}")
        raise

def convert_to_pdf(image_path):
    """Convert image to PDF."""
    try:
        # Open the image
        image = Image.open(image_path)
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Create temporary PDF file
        pdf_path = tempfile.mktemp(suffix='.pdf')
        
        # Save as PDF
        image.save(
            pdf_path, 
            'PDF', 
            resolution=300.0,
            quality=100,
            optimize=False
        )
        logger.info("Successfully converted image to PDF")
        return pdf_path
    except Exception as e:
        logger.error(f"Error converting to PDF: {str(e)}")
        raise

def send_certificate(recipient_email, subject, body, pdf_path):
    """Send certificate via email."""
    config = get_email_config()
    
    if not all(config.values()):
        raise ValueError("Missing email configuration")
    
    try:
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
        
        # Send email
        with smtplib.SMTP(config['server'], config['port']) as server:
            server.starttls()
            server.login(config['email'], config['password'])
            server.send_message(message)
            logger.info(f"Successfully sent certificate to {recipient_email}")
            st.success("Email sent successfully!")
            
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP authentication error: {str(e)}")
        raise Exception(
            "Email authentication failed. Please check:\n"
            "1. App Password configuration\n"
            "2. 2-Step Verification status\n"
            "3. Correct password in secrets"
        )
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Email sending error: {str(e)}")
        raise

def main():
    if not check_password():
        st.stop()
    
    # Initialize certificates in session state with existing records
    if 'certificates' not in st.session_state:
        existing_records = load_existing_records()
        st.session_state.certificates = existing_records
    
    st.title("Certificate Generator & Sender")
    
    # Sidebar with certificate history
    st.sidebar.title("Configuration Status")
    config = get_email_config()
    st.sidebar.write("Email Configuration:")
    st.sidebar.text(f"SMTP Server: {config['server']}")
    st.sidebar.text(f"SMTP Port: {config['port']}")
    st.sidebar.text(f"Sender Email: {config['email']}")
    st.sidebar.text(f"Password Set: {'✓' if config['password'] else '✗'}")
    
    # Display certificate history
    st.sidebar.title("Certificate History")
    st.sidebar.write(f"Total Certificates Generated: {len(st.session_state.certificates)}")
    
    if st.session_state.certificates:
        for i, cert in enumerate(st.session_state.certificates, 1):
            st.sidebar.write(f"""
            **Certificate {i}:**
            - **Serial:** {cert['serial']}  
            - **Name:** {cert['name']}  
            - **Email:** {cert['email']}  
            - **Date:** {cert['date']}  
            ---
            """)
    
    # User input form
    with st.form("certificate_form"):
        full_name = st.text_input("Full Name")
        email = st.text_input("Email Address")
        date = st.date_input("Date")
        
        submit_button = st.form_submit_button("Generate & Send Certificate")
        
        if submit_button and full_name and email and date:
            try:
                # Generate serial number
                serial_number = generate_serial_number()
                
                # Format date
                formatted_date = date.strftime("%B %d, %Y")
                
                # Generate certificate
                modified_psd = modify_psd("templates/certificate.psd", full_name, formatted_date, serial_number)
                pdf_path = convert_to_pdf(modified_psd)
                
                # Preview
                st.image(modified_psd, caption="Certificate Preview", use_column_width=True)
                
                # Send email
                first_name = full_name.split()[0]
                email_subject = "Your Course Certificate"
                email_body = f"""Dear {first_name},

Please accept our sincere congratulations on successfully completing the Comprehensive Python Training course. 
Your dedication and hard work have been commendable. We are delighted to present you with your certificate (Serial: {serial_number}), attached herewith.

We wish you all the best in your future endeavors."""
                
                send_certificate(email, email_subject, email_body, pdf_path)
                
                # Store certificate data
                certificate_data = {
                    'serial': serial_number,
                    'name': full_name,
                    'email': email,
                    'date': formatted_date
                }
                st.session_state.certificates.append(certificate_data)
                
                # Save to GitHub
                if save_to_github(st.session_state.certificates):
                    st.success("Certificate data saved to GitHub successfully!")
                
                # Clean up temporary files
                os.remove(modified_psd)
                os.remove(pdf_path)
                
                # Refresh the page
                st.experimental_rerun()
                
            except Exception as e:
                st.error(str(e))
                logger.error(f"Error in certificate generation process: {str(e)}")
        elif submit_button:
            st.warning("Please fill in all fields.")
    
    # Logout button
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.experimental_rerun()

if __name__ == "__main__":
    main()
