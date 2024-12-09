import streamlit as st
from PIL import Image
from psd_tools import PSDImage
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# Configure Streamlit page
st.set_page_config(page_title="Certificate Generator", layout="wide")

def modify_psd(name, date, template_path="template.psd"):
    """Modify PSD template with participant details"""
    try:
        psd = PSDImage.open(template_path)
        
        # Find and modify the name and date layers
        for layer in psd.descendants():
            if hasattr(layer, 'text'):
                # Check for name layer - it might be identified by its content or name
                if "Hawkar Ali Abdulhaq" in layer.text or layer.name.lower() == "name":
                    layer.text = name
                    
                # Check for date layer
                elif layer.name.lower() == "date" or "DATE" in layer.text:
                    layer.text = date
        
        return psd
    except Exception as e:
        st.error(f"Error modifying PSD: {str(e)}")
        raise e

def convert_to_pdf(psd, output_path):
    """Convert PSD to PDF"""
    try:
        # Convert PSD to PIL Image
        image = psd.compose()
        # Save as PDF with high quality
        image.save(output_path, 'PDF', resolution=300.0, quality=100)
        return True
    except Exception as e:
        st.error(f"Error converting to PDF: {str(e)}")
        return False

def send_email(recipient_email, recipient_name, pdf_path):
    """Send email with PDF certificate"""
    try:
        # Get email credentials from Streamlit secrets
        sender_email = st.secrets["email"]["sender"]
        sender_password = st.secrets["email"]["password"]
        smtp_server = st.secrets["email"]["smtp_server"]
        smtp_port = st.secrets["email"]["smtp_port"]

        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = "Your Python Training Certificate"

        # Email body
        body = f"""Dear {recipient_name},

Thank you for participating in our Comprehensive Python Training course. 
We are pleased to present you with your certificate of completion.

Best regards,
Code for Impact Team"""
        
        msg.attach(MIMEText(body, 'plain'))

        # Attach PDF
        with open(pdf_path, 'rb') as f:
            pdf_attachment = MIMEApplication(f.read(), _subtype='pdf')
            pdf_attachment.add_header('Content-Disposition', 'attachment', 
                                    filename=f'{recipient_name}_Certificate.pdf')
            msg.attach(pdf_attachment)

        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            
        return True
    except Exception as e:
        st.error(f"Error sending email: {str(e)}")
        return False

def main():
    st.title("Python Training Certificate Generator")
    st.write("Generate and send certificates for course participants")

    # Add file uploader for PSD template if not exists
    if not os.path.exists("template.psd"):
        st.warning("No template.psd found. Please upload your PSD template.")
        uploaded_file = st.file_uploader("Upload PSD template", type=['psd'])
        if uploaded_file is not None:
            with open("template.psd", "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success("Template uploaded successfully!")

    # User input form
    with st.form("certificate_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Participant's Name")
        with col2:
            email = st.text_input("Email Address")
        
        date = st.date_input("Certificate Date")
        submit = st.form_submit_button("Generate & Send Certificate")

    if submit and name and email:
        try:
            # Create temp directory if it doesn't exist
            os.makedirs('temp', exist_ok=True)

            # Show processing message
            with st.spinner('Generating certificate...'):
                # Modify PSD
                psd = modify_psd(name, date.strftime("%d/%m/%Y"))
                
                # Generate PDF
                pdf_path = f"temp/{name.replace(' ', '_')}_certificate.pdf"
                if convert_to_pdf(psd, pdf_path):
                    # Send email
                    if send_email(email, name, pdf_path):
                        st.success("✅ Certificate generated and sent successfully!")
                    else:
                        st.error("Failed to send email. Please check your email settings.")

                # Clean up
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
