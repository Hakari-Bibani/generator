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

# Initialize session state for authentication
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

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

def modify_psd(template_path, name, date):
    # Open the PSD file
    psd = PSDImage.open(template_path)
    
    # Convert to PIL Image with specific dimensions
    image = psd.compose()
    image = image.resize((1714, 1205), Image.Resampling.LANCZOS)  # Using LANCZOS for better quality resize
    
    # Create drawing object
    draw = ImageDraw.Draw(image)
    
    try:
        # Load the custom fonts
        name_font = ImageFont.truetype("fonts/Pristina Regular.ttf", size=75)
        date_font = ImageFont.truetype("fonts/Arial-Bold.ttf", size=18)
    except OSError:
        st.error("""Font files not found. Please ensure you have:
        1. fonts/Pristina Regular.ttf
        2. fonts/Arial-Bold.ttf
        in your fonts directory.""")
        raise
    
    # Add name with Pristina Regular font - Moved higher
    name_color = (190, 140, 45)  # RGB for #be8c4d
    # Calculate text size for centering
    name_bbox = draw.textbbox((0, 0), name, font=name_font)
    name_width = name_bbox[2] - name_bbox[0]
    name_x = 959 - (name_width / 2)  # Center horizontally around x: 958.79
    name_y = 618
    draw.text((name_x, name_y), name, font=name_font, fill=name_color)
    
    # Add date with Arial Bold font - Moved left
    date_color = (79, 79, 76)  # RGB for #4f4f4c
    date_x = 660
    date_y = 1038 
    draw.text((date_x, 1038), date, font=date_font, fill=date_color)
    
    # Save modified image in high quality
    temp_path = tempfile.mktemp(suffix='.png')
    image.save(temp_path, quality=100, dpi=(300, 300))  # Maximum quality PNG
    
    return temp_path

def convert_to_pdf(image_path):
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
        optimize=False  # Disable optimization to maintain quality
    )
    return pdf_path

def send_certificate(recipient_email, subject, body, pdf_path):
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
    if not check_password():
        st.stop()  # Do not continue if not authenticated
    
    # Your existing main application code starts here
    st.title("Certificate Generator & Sender")
    
    # Show configuration status
    config = get_email_config()
    st.sidebar.title("Configuration Status")
    st.sidebar.write("Email Configuration:")
    st.sidebar.text(f"SMTP Server: {config['server']}")
    st.sidebar.text(f"SMTP Port: {config['port']}")
    st.sidebar.text(f"Sender Email: {config['email']}")
    st.sidebar.text(f"Password Set: {'✓' if config['password'] else '✗'}")
    
    # Add logout button in sidebar
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
                try:
                    # Convert date to required format
                    formatted_date = date.strftime("%B %d, %Y")
                    
                    # Generate certificate
                    psd_path = "templates/certificate.psd"
                    modified_psd = modify_psd(psd_path, full_name, formatted_date)
                    
                    # Convert to PDF
                    pdf_path = convert_to_pdf(modified_psd)
                    
                    # Preview before sending
                    st.image(modified_psd, caption="Certificate Preview", use_column_width=True)
                    
                    # Send email
                    first_name = full_name.split()[0]
                    email_subject = "Your Course Certificate"
                    email_body = f"""Dear {first_name},

Please accept our sincere congratulations on successfully completing the Comprehensive Python Training course. 
Your dedication and hard work have been commendable. We are delighted to present you with your certificate, attached herewith.
We wish you all the best in your future endeavors."""
                    
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
