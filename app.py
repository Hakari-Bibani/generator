import streamlit as st
from PIL import Image
from psd_tools import PSDImage
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import pdf2image

# Configure Streamlit page
st.set_page_config(page_title="Certificate Generator", layout="wide")

def save_uploaded_template(uploaded_file):
    """Save uploaded template to temp directory"""
    if not os.path.exists('temp'):
        os.makedirs('temp')
    template_path = os.path.join('temp', 'template.psd')
    with open(template_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return template_path

def modify_psd(name, date, template_path):
    """Modify PSD template with participant details"""
    psd = PSDImage.open(template_path)
    for layer in psd.descendants():
        if hasattr(layer, 'text'):
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
    try:
        sender_email = st.secrets["email"]["sender"]
        sender_password = st.secrets["email"]["password"]
        smtp_server = st.secrets["email"]["smtp_server"]
        smtp_port = st.secrets["email"]["smtp_port"]
    except Exception as e:
        st.error("Email configuration is missing. Please check your secrets.toml file.")
        return False

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

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Failed to send email: {str(e)}")
        return False

def main():
    st.title("Certificate Generator")

    # Template upload section
    st.subheader("1. Upload Certificate Template")
    uploaded_file = st.file_uploader("Upload PSD template", type=['psd'])
    
    if uploaded_file is None:
        st.warning("Please upload a PSD template first")
        st.stop()
    
    template_path = save_uploaded_template(uploaded_file)
    st.success("Template uploaded successfully!")

    # User input form
    st.subheader("2. Enter Certificate Details")
    with st.form("certificate_form"):
        name = st.text_input("Participant's Name")
        date = st.date_input("Date")
        email = st.text_input("Email Address")
        submit = st.form_submit_button("Generate Certificate")

    if submit and name and email:
        try:
            # Create temp directory if it doesn't exist
            os.makedirs('temp', exist_ok=True)

            # Modify PSD
            psd = modify_psd(name, date.strftime("%B %d, %Y"), template_path)
            
            # Generate PDF
            pdf_path = f"temp/{name.replace(' ', '_')}_certificate.pdf"
            convert_to_pdf(psd, pdf_path)

            # Send email
            if send_email(email, name, pdf_path):
                st.success("Certificate generated and sent successfully!")
            
            # Cleanup
            if os.path.exists(pdf_path):
                os.remove(pdf_path)

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.error("Make sure your PSD template has text layers named 'name' and 'date'")
            st.error("If the error persists, check that the text layers are properly configured in your PSD file")

if __name__ == "__main__":
    main()
