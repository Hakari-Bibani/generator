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

# Load environment variables from .env if available
load_dotenv()

# Initialize session states
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if 'certificates' not in st.session_state:
    st.session_state.certificates = []

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
        # First run, show input for password.
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
    """Generate a serial number in format PY-YYYY-XXXX"""
    current_year = datetime.now().year
    
    # Get the last serial number from session state
    last_number = 0
    if st.session_state.certificates:
        last_serial = st.session_state.certificates[-1]['serial']
        try:
            last_number = int(last_serial.split('-')[-1])
        except ValueError:
            pass
    
    new_number = str(last_number + 1).zfill(4)
    return f"PY-{current_year}-{new_number}"

def save_to_github(data):
    """Save certificate data to GitHub as CSV"""
    try:
        # Get GitHub token from secrets or environment
        github_token = st.secrets.get("github_token") or os.getenv("GITHUB_TOKEN")
        if not github_token:
            raise ValueError("GitHub token not found in configuration")
            
        repo_name = st.secrets.get("github_repo") or os.getenv("GITHUB_REPO")
        if not repo_name:
            raise ValueError("GitHub repository name not found in configuration")
        
        # Initialize GitHub
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
        except github.GithubException:
            # Create new file if it doesn't exist
            repo.create_file(
                file_path,
                f"Create certificates record - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                csv_content
            )
            
        return True
    except Exception as e:
        st.error(f"Error saving to GitHub: {str(e)}")
        return False

def modify_psd(template_path, name, date, serial_number):
    """Modify PSD template with name, date, and serial number."""
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
    except OSError:
        st.error("Font files not found. Please check your fonts directory.")
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
    
    # Add serial number at bottom right
    serial_color = (79, 79, 76)
    serial_bbox = draw.textbbox((0, 0), serial_number, font=serial_font)
    serial_width = serial_bbox[2] - serial_bbox[0]
    serial_x = 1714 - serial_width - 40  # 40 pixels from right edge
    serial_y = 1150  # 55 pixels from bottom
    draw.text((serial_x, serial_y), serial_number, font=serial_font, fill=serial_color)
    
    # Save modified image
    temp_path = tempfile.mktemp(suffix='.png')
    image.save(temp_path, quality=100, dpi=(300, 300))
    
    return temp_path

def convert_to_pdf(image_path):
    """Convert image to PDF."""
    # Open the image
    image = Image.open(image_path)
    
    # Convert to RGB if necessary
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Create temporary PDF file
    pdf_path = tempfile.mktemp(suffix='.pdf')
    
    # Save as PDF with maximum quality
    image.save(
        pdf_path, 
        'PDF', 
        resolution=300.0,
        quality=100,
        optimize=False
    )
    return pdf_path

def send_certificate(recipient_email, subject, body, pdf_path):
    """Send certificate via email."""
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
