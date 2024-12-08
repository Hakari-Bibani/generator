import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from psd_tools import PSDImage
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

# Configure Streamlit page
st.set_page_config(page_title="Certificate Generator", layout="wide")

def get_layer_properties(layer):
    """Extract layer properties including position and text"""
    bbox = layer.bbox
    text = layer.text
    font = layer.resource_dict.get('FontSet', [{}])[0].get('Name', 'Arial')
    font_size = layer.text_data.get('fontSize', 40)
    transform = layer.transform
    color = layer.text_data.get('color', {'red': 0, 'green': 0, 'blue': 0})
    
    return {
        'bbox': bbox,
        'text': text,
        'font': font,
        'font_size': font_size,
        'transform': transform,
        'color': color
    }

def create_certificate(name, date, template_path="template.psd"):
    """Create certificate by compositing PSD and adding text"""
    try:
        # Open PSD file
        psd = PSDImage.open(template_path)
        
        # Convert PSD to PIL Image
        image = psd.compose()
        
        # Create a drawing object
        draw = ImageDraw.Draw(image)
        
        # Find the name and date layers to get their properties
        name_layer = None
        date_layer = None
        
        for layer in psd.descendants():
            if hasattr(layer, 'text'):
                if "Hawkar Ali Abdulhaq" in layer.text:
                    name_layer = layer
                elif layer.name.lower() == 'date' or 'date' in layer.text.lower():
                    date_layer = layer
        
        # If we found the name layer, get its properties
        if name_layer:
            props = get_layer_properties(name_layer)
            # Try to use the original font, fallback to Arial
            try:
                font_size = int(props['font_size'])
                font = ImageFont.truetype(props['font'], font_size)
            except:
                st.warning(f"Original font {props['font']} not found. Using Arial.")
                font = ImageFont.load_default()
            
            # Calculate text position (center aligned)
            bbox = props['bbox']
            text_bbox = draw.textbbox((0, 0), name, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            x = bbox[0] + (bbox[2] - bbox[0] - text_width) / 2
            y = bbox[1] + (bbox[3] - bbox[1] - text_height) / 2
            
            # Draw the name
            # Convert color values to RGB tuple
            color = props['color']
            rgb_color = (
                int(color.get('red', 0) * 255),
                int(color.get('green', 0) * 255),
                int(color.get('blue', 0) * 255)
            )
            draw.text((x, y), name, font=font, fill=rgb_color)
        
        # If we found the date layer, add the date
        if date_layer:
            props = get_layer_properties(date_layer)
            try:
                font_size = int(props['font_size'])
                font = ImageFont.truetype(props['font'], font_size)
            except:
                font = ImageFont.load_default()
            
            bbox = props['bbox']
            text_bbox = draw.textbbox((0, 0), date, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            x = bbox[0] + (bbox[2] - bbox[0] - text_width) / 2
            y = bbox[1] + (bbox[3] - bbox[1] - text_height) / 2
            
            color = props['color']
            rgb_color = (
                int(color.get('red', 0) * 255),
                int(color.get('green', 0) * 255),
                int(color.get('blue', 0) * 255)
            )
            draw.text((x, y), date, font=font, fill=rgb_color)
        
        return image
    except Exception as e:
        logging.error(f"Error in create_certificate: {e}")
        raise

def send_email(recipient_email, recipient_name, pdf_path):
    """Send email with PDF certificate"""
    try:
        sender_email = st.secrets["email"]["sender"]
        sender_password = st.secrets["email"]["password"]
        smtp_server = st.secrets["email"]["smtp_server"]
        smtp_port = st.secrets["email"]["smtp_port"]

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = "Your Python Training Certificate"

        body = f"""Dear {recipient_name},

Thank you for participating in our Comprehensive Python Training course. 
Please find your certificate of completion attached.

Best regards,
Code for Impact Team"""
        
        msg.attach(MIMEText(body, 'plain'))

        with open(pdf_path, 'rb') as f:
            pdf_attachment = MIMEApplication(f.read(), _subtype='pdf')
            pdf_attachment.add_header('Content-Disposition', 'attachment', 
                                    filename=f'{recipient_name}_Certificate.pdf')
            msg.attach(pdf_attachment)

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

    if not os.path.exists("template.psd"):
        st.warning("No template.psd found. Please upload your PSD template.")
        uploaded_file = st.file_uploader("Upload PSD template", type=['psd'])
        if uploaded_file is not None:
            with open("template.psd", "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success("Template uploaded successfully!")

    with st.form("certificate_form"):
        name = st.text_input("Participant's Name")
        date = st.date_input("Certificate Date")
        email = st.text_input("Email Address")
        submit = st.form_submit_button("Generate Certificate")

    if submit and name and email:
        try:
            with st.spinner("Generating certificate..."):
                os.makedirs('temp', exist_ok=True)
                
                # Generate certificate
                certificate_image = create_certificate(name, date.strftime("%B %d, %Y"))
                
                # Save as PDF
                pdf_path = f"temp/{name.replace(' ', '_')}_certificate.pdf"
                certificate_image.save(pdf_path, 'PDF', resolution=300)
                
                # Preview and download
                st.success("Certificate generated successfully!")
                with open(pdf_path, "rb") as file:
                    st.download_button(
                        label="Download Certificate",
                        data=file,
                        file_name=f"{name}_Certificate.pdf",
                        mime="application/pdf"
                    )
                
                # Send email if configured
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
