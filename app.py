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
import requests
import json
from datetime import datetime

# Load environment variables
load_dotenv()

# Initialize session states
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'certificate_count' not in st.session_state:
    st.session_state.certificate_count = 0
if 'certificates_data' not in st.session_state:
    st.session_state.certificates_data = []

def generate_serial_number():
    """Generate a unique serial number"""
    current_year = datetime.now().year
    count = st.session_state.certificate_count + 1
    serial_number = f"PY{current_year}-{count:04d}"
    st.session_state.certificate_count = count
    return serial_number

def save_to_gist(data):
    """Save data to GitHub Gist"""
    gist_token = st.secrets["gist_token"]
    gist_id = st.secrets["gist_id"]
    
    headers = {
        'Authorization': f'token {gist_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    # Convert data to CSV string
    df = pd.DataFrame(data)
    csv_content = df.to_csv(index=False)
    
    # Prepare the payload
    payload = {
        "files": {
            "certificates.csv": {
                "content": csv_content
            }
        }
    }
    
    # Update the gist
    response = requests.patch(
        f'https://api.github.com/gists/{gist_id}',
        headers=headers,
        data=json.dumps(payload)
    )
    
    return response.status_code == 200

def load_from_gist():
    """Load data from GitHub Gist"""
    gist_token = st.secrets["gist_token"]
    gist_id = st.secrets["gist_id"]
    
    headers = {
        'Authorization': f'token {gist_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    response = requests.get(
        f'https://api.github.com/gists/{gist_id}',
        headers=headers
    )
    
    if response.status_code == 200:
        gist_data = response.json()
        csv_content = gist_data['files']['certificates.csv']['content']
        df = pd.read_csv(pd.StringIO(csv_content))
        return df.to_dict('records')
    return []

def modify_psd(template_path, name, date, serial_number):
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
        serial_font = ImageFont.truetype("fonts/Arial-Bold.ttf", size=14)
    except OSError:
        st.error("Font files not found!")
        raise
    
    # Add name
    name_color = (190, 140, 45)
    name_bbox = draw.textbbox((0, 0), name, font=name_font)
    name_width = name_bbox[2] - name_bbox[0]
    name_x = 959 - (name_width / 2)
    draw.text((name_x, 618), name, font=name_font, fill=name_color)
    
    # Add date
    date_color = (79, 79, 76)
    draw.text((660, 1038), date, font=date_font, fill=date_color)
    
    # Add serial number at bottom right
    serial_color = (79, 79, 76)
    serial_bbox = draw.textbbox((0, 0), serial_number, font=serial_font)
    serial_width = serial_bbox[2] - serial_bbox[0]
    draw.text((1614 - serial_width - 20, 1165), serial_number, font=serial_font, fill=serial_color)
    
    # Save image
    temp_path = tempfile.mktemp(suffix='.png')
    image.save(temp_path, quality=100, dpi=(300, 300))
    
    return temp_path

[Previous functions remain the same: check_password, get_email_config, convert_to_pdf, send_certificate]

def main():
    if not check_password():
        st.stop()
    
    # Load existing data
    if not st.session_state.certificates_data:
        st.session_state.certificates_data = load_from_gist()
        st.session_state.certificate_count = len(st.session_state.certificates_data)
    
    st.title("Certificate Generator & Sender")
    
    # Sidebar
    st.sidebar.title("Configuration Status")
    st.sidebar.write("Email Configuration:")
    config = get_email_config()
    st.sidebar.text(f"SMTP Server: {config['server']}")
    st.sidebar.text(f"SMTP Port: {config['port']}")
    st.sidebar.text(f"Sender Email: {config['email']}")
    st.sidebar.text(f"Password Set: {'✓' if config['password'] else '✗'}")
    
    # Display certificates data in sidebar
    st.sidebar.title("Certificates Issued")
    st.sidebar.text(f"Total Certificates: {st.session_state.certificate_count}")
    if st.session_state.certificates_data:
        st.sidebar.write("Recent Certificates:")
        for cert in st.session_state.certificates_data[-5:]:  # Show last 5 certificates
            st.sidebar.text(f"Serial: {cert['serial']}")
            st.sidebar.text(f"Name: {cert['name']}")
            st.sidebar.text("---")
    
    # Logout button
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.experimental_rerun()
    
    # Main form
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
                st.image(modified_psd, caption=f"Certificate Preview - Serial: {serial_number}", use_column_width=True)
                
                # Send email
                email_subject = "Your Course Certificate"
                email_body = f"""Dear {full_name.split()[0]},

Please accept our sincere congratulations on successfully completing the Comprehensive Python Training course. 
Your dedication and hard work have been commendable. We are delighted to present you with your certificate, attached herewith.
Certificate Serial Number: {serial_number}

We wish you all the best in your future endeavors."""
                
                send_certificate(email, email_subject, email_body, pdf_path)
                
                # Save record
                new_record = {
                    'serial': serial_number,
                    'name': full_name,
                    'email': email,
                    'date': formatted_date,
                    'issued_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                st.session_state.certificates_data.append(new_record)
                save_to_gist(st.session_state.certificates_data)
                
                # Cleanup
                os.remove(modified_psd)
                os.remove(pdf_path)
                
            except Exception as e:
                st.error(str(e))
        elif submit_button:
            st.warning("Please fill in all fields.")

if __name__ == "__main__":
    main()
