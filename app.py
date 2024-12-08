import streamlit as st
from PIL import Image, ImageFont
from psd_tools import PSDImage
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import pdf2image
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Configure Streamlit page
st.set_page_config(page_title="Certificate Generator", layout="wide")

def get_font_info(psd_layer):
    """Extract font information from a PSD text layer"""
    try:
        font_info = {
            'font': psd_layer.resource_dict['FontSet'][0].get('Name', 'Unknown'),
            'size': psd_layer.text_data.get('fontSize', 12),
            'color': psd_layer.text_data.get('color', {'red': 0, 'green': 0, 'blue': 0})
        }
        logging.info(f"Font info extracted: {font_info}")
        return font_info
    except Exception as e:
        logging.error(f"Error getting font info: {e}")
        return None

def modify_psd(name, date, template_path="template.psd"):
    """Modify PSD template with participant details"""
    try:
        psd = PSDImage.open(template_path)
        
        # Find the name and date layers
        name_layer = None
        date_layer = None
        
        for layer in psd.descendants():
            if hasattr(layer, 'text'):
                # Log layer information for debugging
                logging.info(f"Layer name: {layer.name}, Text: {layer.text}")
                
                # Look for the layer containing the example name
                if "Hawkar Ali Abdulhaq" in layer.text:
                    name_layer = layer
                    # Get font information
                    font_info = get_font_info(layer)
                    if font_info:
                        st.info(f"Name font used: {font_info['font']}")
                
                # Look for the date layer
                if layer.name.lower() == 'date' or 'date' in layer.text.lower():
                    date_layer = layer
        
        if name_layer:
            name_layer.text = name
        else:
            st.warning("Name layer not found. Please check the PSD structure.")
            
        if date_layer:
            date_layer.text = date
        else:
            st.warning("Date layer not found. Please check the PSD structure.")
            
        return psd
    except Exception as e:
        logging.error(f"Error in modify_psd: {e}")
        raise

def convert_to_pdf(psd, output_path):
    """Convert PSD to PDF"""
    try:
        # Convert PSD to PIL Image
        image = psd.compose()
        # Save as PDF
        image.save(output_path, 'PDF', resolution=300.0)
        
        # Verify the PDF was created
        if not os.path.exists(output_path):
            raise Exception("PDF file was not created")
            
        return True
    except Exception as e:
        logging.error(f"Error in convert_to_pdf: {e}")
        raise

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
Please find your certificate of completion attached.

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
        logging.error(f"Error in send_email: {e}")
        raise

def main():
    st.title("Certificate Generator")
    st.write("Generate certificates for Python Training participants")

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
        name = st.text_input("Participant's Name")
        date = st.date_input("Certificate Date")
        email = st.text_input("Email Address")
        submit = st.form_submit_button("Generate Certificate")

    if submit and name and email:
        try:
            with st.spinner("Generating certificate..."):
                # Create temp directory if it doesn't exist
                os.makedirs('temp', exist_ok=True)

                # Modify PSD
                psd = modify_psd(name, date.strftime("%B %d, %Y"))
                
                # Generate PDF
                pdf_path = f"temp/{name.replace(' ', '_')}_certificate.pdf"
                if convert_to_pdf(psd, pdf_path):
                    st.success("Certificate generated successfully!")
                    
                    # Preview the generated certificate
                    with open(pdf_path, "rb") as file:
                        st.download_button(
                            label="Download Certificate",
                            data=file,
                            file_name=f"{name}_Certificate.pdf",
                            mime="application/pdf"
                        )
                    
                    # Send email if secrets are configured
                    try:
                        if send_email(email, name, pdf_path):
                            st.success("Certificate sent successfully to your email!")
                    except Exception as e:
                        st.error("Email configuration not set up. Please configure email settings in secrets.toml")
                        logging.error(f"Email error: {e}")

                # Clean up
                os.remove(pdf_path)

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            logging.error(f"Main error: {e}")

if __name__ == "__main__":
    main()
