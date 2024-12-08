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

def modify_psd(participant_name, date, template_path="template.psd"):
    """Modify PSD template with participant details"""
    try:
        psd = PSDImage.open(template_path)
        
        # Find and modify text layers
        for layer in psd.descendants():
            if hasattr(layer, 'text'):
                # Check for name layer - contains the example name
                if "Hawkar Ali Abdulhaq" in layer.text:
                    layer.text = participant_name
                # Check for date field
                elif layer.name.lower() == 'date' or 'date' in layer.text.lower():
                    layer.text = date
        
        return psd
    except Exception as e:
        st.error(f"Error modifying PSD: {str(e)}")
        raise

def convert_to_pdf(psd, output_path):
    """Convert PSD to PDF"""
    try:
        # Convert PSD to PIL Image
        image = psd.compose()
        # Save as PDF
        image.save(output_path, 'PDF', resolution=300.0)
    except Exception as e:
        st.error(f"Error converting to PDF: {str(e)}")
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
        msg['Subject'] = "Your Code for Impact Certificate"

        # Email body
        body = f"""Dear {recipient_name},

Thank you for participating in the Comprehensive Python Training with Hawkar. 
Please find your certificate of appreciation attached.

Best regards,
Code for Impact Team"""
        
        msg.attach(MIMEText(body, 'plain'))

        # Attach PDF
        with open(pdf_path, 'rb') as f:
            pdf_attachment = MIMEApplication(f.read(), _subtype='pdf')
            pdf_attachment.add_header('Content-Disposition', 'attachment', 
                                    filename=f'Certificate_{recipient_name.replace(" ", "_")}.pdf')
            msg.attach(pdf_attachment)

        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
    except Exception as e:
        st.error(f"Error sending email: {str(e)}")
        raise

def main():
    st.title("Code for Impact - Certificate Generator")
    st.write("Generate and send certificates for course participants")

    # Add file uploader for PSD template if not exists
    if not os.path.exists("template.psd"):
        st.warning("No template.psd found. Please upload your certificate template.")
        uploaded_file = st.file_uploader("Upload PSD template", type=['psd'])
        if uploaded_file is not None:
            with open("template.psd", "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success("Template uploaded successfully!")

    # User input form
    with st.form("certificate_form"):
        name = st.text_input("Participant's Name")
        date = st.date_input("Certificate Date")
        email = st.text_input("Participant's Email Address")
        submit = st.form_submit_button("Generate & Send Certificate")

    if submit and name and email:
        try:
            with st.spinner("Generating certificate and sending email..."):
                # Create temp directory if it doesn't exist
                os.makedirs('temp', exist_ok=True)

                # Format date as needed for certificate
                formatted_date = date.strftime("%B %d, %Y")
                
                # Modify PSD
                psd = modify_psd(name, formatted_date)
                
                # Generate PDF
                pdf_path = f"temp/{name.replace(' ', '_')}_certificate.pdf"
                convert_to_pdf(psd, pdf_path)

                # Send email
                send_email(email, name, pdf_path)

                st.success("✅ Certificate generated and sent successfully!")
                
                # Optional: Show preview
                with open(pdf_path, "rb") as pdf_file:
                    st.download_button(
                        label="Download Certificate",
                        data=pdf_file,
                        file_name=f"Certificate_{name.replace(' ', '_')}.pdf",
                        mime="application/pdf"
                    )

                # Clean up
                os.remove(pdf_path)

        except Exception as e:
            st.error("❌ Failed to generate and send certificate")
            st.error(f"Error details: {str(e)}")

if __name__ == "__main__":
    main()
