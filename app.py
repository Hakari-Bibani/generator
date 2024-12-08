import streamlit as st
from PIL import Image
import psd_tools
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import pdf2image
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

# Configure Streamlit page
st.set_page_config(page_title="Certificate Generator", layout="wide")

def get_google_drive_service():
    """Initialize Google Drive service"""
    creds = None
    # Get credentials from streamlit secrets
    if 'google' in st.secrets:
        creds = Credentials.from_authorized_user_info(
            st.secrets['google'],
            ['https://www.googleapis.com/auth/drive.readonly']
        )
    return build('drive', 'v3', credentials=creds)

def download_template_from_drive(file_id):
    """Download PSD template from Google Drive"""
    service = get_google_drive_service()
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    fh.seek(0)
    return fh

def modify_psd(name, date, template_content):
    """Modify PSD template with participant details"""
    psd = psd_tools.PsdImage.open(template_content)
    # Assuming text layers are named 'name' and 'date' in PSD
    for layer in psd:
        if layer.name == 'name':
            layer.text = name
        elif layer.name == 'date':
            layer.text = date
    return psd

def convert_to_pdf(psd, output_path):
    """Convert PSD to PDF"""
    image = psd.compose()
    image.save(output_path, 'PDF')

def send_email(recipient_email, recipient_name, pdf_path):
    """Send email with PDF certificate"""
    sender_email = st.secrets["email"]["sender"]
    sender_password = st.secrets["email"]["password"]
    smtp_server = st.secrets["email"]["smtp_server"]
    smtp_port = st.secrets["email"]["smtp_port"]

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = "Your Course Certificate"

    body = f"""Dear {recipient_name},

Thank you for participating in our course. We are delighted to have you with us. 
Please find your certificate attached.

Best regards,
Your Organization Name"""
    
    msg.attach(MIMEText(body, 'plain'))

    with open(pdf_path, 'rb') as f:
        pdf_attachment = MIMEApplication(f.read(), _subtype='pdf')
        pdf_attachment.add_header('Content-Disposition', 'attachment', filename='certificate.pdf')
        msg.attach(pdf_attachment)

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)

def main():
    st.title("Certificate Generator")

    # Get template file ID from secrets
    template_file_id = st.secrets["google"]["template_file_id"]

    # User input form
    with st.form("certificate_form"):
        name = st.text_input("Participant's Name")
        date = st.date_input("Date")
        email = st.text_input("Email Address")
        submit = st.form_submit_button("Generate Certificate")

    if submit and name and email:
        try:
            # Create temp directory if it doesn't exist
            os.makedirs('temp', exist_ok=True)

            # Download template from Google Drive
            with st.spinner("Downloading template..."):
                template_content = download_template_from_drive(template_file_id)

            # Modify PSD
            with st.spinner("Generating certificate..."):
                psd = modify_psd(name, date.strftime("%B %d, %Y"), template_content)
            
            # Generate PDF
            pdf_path = f"temp/{name.replace(' ', '_')}_certificate.pdf"
            convert_to_pdf(psd, pdf_path)

            # Send email
            with st.spinner("Sending email..."):
                send_email(email, name, pdf_path)

            st.success("Certificate generated and sent successfully!")

            # Clean up
            os.remove(pdf_path)

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
