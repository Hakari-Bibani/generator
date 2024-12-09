import streamlit as st
from PIL import Image, ImageFont, ImageDraw
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

# Constants
FONT_PATH = "fonts/AlexBrush-Regular.ttf"
TEMPLATE_PATH = "template.psd"
CERTIFICATE_COLOR = (198, 194, 177)  # RGB color for text

def load_font(size=60):
    """Load the custom font with specified size"""
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except Exception as e:
        st.error(f"Error loading font: {str(e)}")
        return None

def modify_psd(name, date, template_path=TEMPLATE_PATH):
    """Modify PSD template with participant details"""
    try:
        psd = PSDImage.open(template_path)
        image = psd.compose()
        
        # Convert to PIL Image for custom font rendering
        draw = ImageDraw.Draw(image)
        
        # Load fonts
        name_font = load_font(size=60)  # Larger size for name
        date_font = load_font(size=40)  # Smaller size for date
        
        if name_font and date_font:
            # Get image dimensions
            width, height = image.size
            
            # Calculate text positions (adjust these values based on your template)
            name_position = (width * 0.5, height * 0.5)  # Center of image
            date_position = (width * 0.5, height * 0.7)  # Below name
            
            # Get text sizes for centering
            name_bbox = draw.textbbox((0, 0), name, font=name_font)
            name_width = name_bbox[2] - name_bbox[0]
            name_height = name_bbox[3] - name_bbox[1]
            
            date_bbox = draw.textbbox((0, 0), date, font=date_font)
            date_width = date_bbox[2] - date_bbox[0]
            date_height = date_bbox[3] - date_bbox[1]
            
            # Draw text centered
            draw.text((name_position[0] - name_width/2, name_position[1] - name_height/2), 
                     name, font=name_font, fill=CERTIFICATE_COLOR)
            draw.text((date_position[0] - date_width/2, date_position[1] - date_height/2), 
                     date, font=date_font, fill=CERTIFICATE_COLOR)
            
        return image
    except Exception as e:
        st.error(f"Error modifying PSD: {str(e)}")
        return None

def convert_to_pdf(image, output_path):
    """Convert PIL Image to PDF"""
    try:
        image.save(output_path, 'PDF', resolution=300.0)
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
        msg['Subject'] = "Your Course Certificate"

        # Email body
        body = f"""Dear {recipient_name},

Thank you for participating in our course. We are delighted to have you with us. 
Please find your certificate attached.

Best regards,
Your Organization Name"""
        
        msg.attach(MIMEText(body, 'plain'))

        # Attach PDF
        with open(pdf_path, 'rb') as f:
            pdf_attachment = MIMEApplication(f.read(), _subtype='pdf')
            pdf_attachment.add_header('Content-Disposition', 'attachment', filename='certificate.pdf')
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

def check_assets():
    """Check if required assets exist"""
    if not os.path.exists(FONT_PATH):
        st.error(f"Font file not found at {FONT_PATH}")
        return False
    if not os.path.exists(TEMPLATE_PATH):
        st.error(f"Template file not found at {TEMPLATE_PATH}")
        return False
    return True

def main():
    st.title("Certificate Generator")

    # Check assets
    if not check_assets():
        st.stop()

    # Preview current template
    if os.path.exists(TEMPLATE_PATH):
        psd = PSDImage.open(TEMPLATE_PATH)
        preview = psd.compose()
        st.image(preview, caption="Current Template Preview", use_column_width=True)

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

            # Modify PSD and convert to image
            modified_image = modify_psd(name, date.strftime("%B %d, %Y"))
            
            if modified_image:
                # Generate PDF
                pdf_path = f"temp/{name.replace(' ', '_')}_certificate.pdf"
                if convert_to_pdf(modified_image, pdf_path):
                    # Preview generated certificate
                    st.image(modified_image, caption="Generated Certificate Preview", use_column_width=True)
                    
                    # Send email
                    if send_email(email, name, pdf_path):
                        st.success("Certificate generated and sent successfully!")
                    
                    # Clean up
                    os.remove(pdf_path)

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
