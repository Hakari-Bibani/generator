import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from psd_tools import PSDImage
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# Configure Streamlit page
st.set_page_config(page_title="Certificate Generator", layout="wide")

def create_certificate(participant_name, date, template_path="template.psd"):
    """Create certificate using PIL"""
    try:
        # Open PSD and convert to PIL Image
        psd = PSDImage.open(template_path)
        template = psd.compose()
        
        # Create a drawing object
        draw = ImageDraw.Draw(template)
        
        # Load a font similar to your template (you'll need to provide the font file)
        try:
            name_font = ImageFont.truetype("arial.ttf", 60)  # Adjust size as needed
            date_font = ImageFont.truetype("arial.ttf", 30)  # Adjust size as needed
        except:
            # Fallback to default font if custom font not available
            name_font = ImageFont.load_default()
            date_font = ImageFont.load_default()
            st.warning("Custom font not found. Using default font.")
        
        # Get template size
        W, H = template.size
        
        # Calculate text sizes and positions
        # Name position (adjust these values based on your template)
        name_bbox = draw.textbbox((0, 0), participant_name, font=name_font)
        name_w = name_bbox[2] - name_bbox[0]
        name_h = name_bbox[3] - name_bbox[1]
        name_x = (W - name_w) / 2
        name_y = H * 0.45  # Adjust this value to position the name correctly
        
        # Date position (adjust these values based on your template)
        date_bbox = draw.textbbox((0, 0), date, font=date_font)
        date_w = date_bbox[2] - date_bbox[0]
        date_x = W * 0.25  # Adjust this value for date position
        date_y = H * 0.85  # Adjust this value for date position
        
        # Draw text on image
        draw.text((name_x, name_y), participant_name, fill="goldenrod", font=name_font)
        draw.text((date_x, date_y), date, fill="black", font=date_font)
        
        return template
        
    except Exception as e:
        st.error(f"Error creating certificate: {str(e)}")
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
    
    # Add font file uploader
    font_file = st.file_uploader("Upload font file (optional)", type=['ttf', 'otf'])
    if font_file is not None:
        with open("custom_font.ttf", "wb") as f:
            f.write(font_file.getbuffer())
        st.success("Font uploaded successfully!")

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
                
                # Create certificate
                certificate = create_certificate(name, formatted_date)
                
                # Save as PDF
                pdf_path = f"temp/{name.replace(' ', '_')}_certificate.pdf"
                certificate.save(pdf_path, "PDF", resolution=300)

                # Send email
                send_email(email, name, pdf_path)

                st.success("✅ Certificate generated and sent successfully!")
                
                # Optional: Show preview
                st.image(certificate, caption="Certificate Preview", use_column_width=True)
                
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
