import streamlit as st
from PIL import Image, ImageFont, ImageDraw
from psd_tools import PSDImage
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

# Configure Streamlit page
st.set_page_config(page_title="Certificate Generator", layout="wide")

# Constants - Updated paths to match your structure
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

def create_certificate(name, date, template_path=TEMPLATE_PATH):
    """Create certificate by converting PSD to PIL Image and adding text"""
    try:
        # Open PSD and convert to PIL Image
        psd = PSDImage.open(template_path)
        image = psd.compose()
        
        # Convert to RGB mode if not already
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Create a drawing object
        draw = ImageDraw.Draw(image)
        
        # Load fonts with adjusted sizes
        name_font = load_font(size=60)  # Adjust size as needed
        date_font = load_font(size=40)  # Adjust size as needed
        
        if name_font and date_font:
            # Get image dimensions
            width, height = image.size
            
            # Calculate text sizes for centering
            name_bbox = draw.textbbox((0, 0), name, font=name_font)
            name_width = name_bbox[2] - name_bbox[0]
            name_height = name_bbox[3] - name_bbox[1]
            
            date_bbox = draw.textbbox((0, 0), date, font=date_font)
            date_width = date_bbox[2] - date_bbox[0]
            date_height = date_bbox[3] - date_bbox[1]
            
            # Calculate positions
            name_x = width * 0.5 - name_width / 2
            name_y = height * 0.5 - name_height / 2
            
            date_x = width * 0.5 - date_width / 2
            date_y = height * 0.7 - date_height / 2
            
            # Add text to image
            draw.text((name_x, name_y), name, font=name_font, fill=CERTIFICATE_COLOR)
            draw.text((date_x, date_y), date, font=date_font, fill=CERTIFICATE_COLOR)
            
            return image
        return None
    except Exception as e:
        st.error(f"Error creating certificate: {str(e)}")
        return None

def save_pdf(image, output_path):
    """Save PIL Image as PDF"""
    try:
        image.save(output_path, 'PDF', resolution=300.0)
        return True
    except Exception as e:
        st.error(f"Error saving PDF: {str(e)}")
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
    missing_assets = []
    if not os.path.exists(FONT_PATH):
        missing_assets.append(f"Font file not found at {FONT_PATH}")
    if not os.path.exists(TEMPLATE_PATH):
        missing_assets.append(f"Template file not found at {TEMPLATE_PATH}")
    
    if missing_assets:
        for error in missing_assets:
            st.error(error)
        return False
    return True

def main():
    st.title("Certificate Generator")

    # Check assets
    if not check_assets():
        st.write("Please make sure your files are in the correct locations:")
        st.code("""
certificate-generator/
├── fonts/
│   └── AlexBrush-Regular.ttf
├── template.psd
├── app.py
└── .streamlit/
    └── secrets.toml
        """)
        st.stop()

    # Show template preview
    if os.path.exists(TEMPLATE_PATH):
        psd = PSDImage.open(TEMPLATE_PATH)
        preview = psd.compose()
        st.image(preview, caption="Certificate Template", use_column_width=True)

    # User input form
    with st.form("certificate_form"):
        name = st.text_input("Participant's Name")
        date = st.date_input("Date")
        email = st.text_input("Email Address")
        
        # Add position adjustment sliders
        st.write("Adjust text positions (optional):")
        col1, col2 = st.columns(2)
        with col1:
            name_y_pos = st.slider("Name Y Position", 0.3, 0.7, 0.5, 0.01)
        with col2:
            date_y_pos = st.slider("Date Y Position", 0.5, 0.9, 0.7, 0.01)
        
        submit = st.form_submit_button("Generate Certificate")

    if submit and name and email:
        try:
            # Create temp directory if it doesn't exist
            os.makedirs('temp', exist_ok=True)

            # Generate certificate
            certificate_image = create_certificate(name, date.strftime("%B %d, %Y"))
            
            if certificate_image:
                # Show preview
                st.image(certificate_image, caption="Generated Certificate Preview", use_column_width=True)
                
                # Save as PDF
                pdf_path = f"temp/{name.replace(' ', '_')}_certificate.pdf"
                if save_pdf(certificate_image, pdf_path):
                    # Send email
                    if send_email(email, name, pdf_path):
                        st.success("Certificate generated and sent successfully!")
                    
                    # Clean up
                    os.remove(pdf_path)

        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.error("Please check that your template.psd is properly formatted and try again.")

if __name__ == "__main__":
    main()
