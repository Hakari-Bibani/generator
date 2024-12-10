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

# Load environment variables from .env if available
load_dotenv()

def modify_psd(template_path, name, date):
    # Open the PSD file
    psd = PSDImage.open(template_path)
    
    # Convert to PIL Image with specific dimensions
    image = psd.compose()
    image = image.resize((1714, 1205))  # Set to exact template size
    
    # Create drawing object
    draw = ImageDraw.Draw(image)
    
    try:
        # Load the custom fonts
        name_font = ImageFont.truetype("fonts/Pristina Regular.ttf", size=61)
        date_font = ImageFont.truetype("fonts/Arial-Bold.ttf", size=11)
    except OSError:
        st.error("""Font files not found. Please ensure you have:
        1. fonts/Pristina Regular.ttf
        2. fonts/Arial-Bold.ttf
        in your fonts directory.""")
        raise
    
    # Add name with Pristina Regular font
    name_color = (190, 140, 75)  # RGB for #be8c4d
    # Calculate text size for centering
    name_bbox = draw.textbbox((0, 0), name, font=name_font)
    name_width = name_bbox[2] - name_bbox[0]
    name_x = 959 - (name_width / 2)  # Center horizontally around x: 958.79
    draw.text((name_x, 655), name, font=name_font, fill=name_color)
    
    # Add date with Arial Bold font
    date_color = (79, 79, 76)  # RGB for #4f4f4c
    draw.text((739, 1048), date, font=date_font, fill=date_color)
    
    # Save modified image
    temp_path = tempfile.mktemp(suffix='.png')
    image.save(temp_path, quality=95)  # High quality save
    
    return temp_path

def convert_to_pdf(image_path):
    # Open the image
    image = Image.open(image_path)
    
    # Convert to RGB if necessary
    if image.mode != 'RGB':
        image = image.convert('RGB')
    
    # Create temporary PDF file
    pdf_path = tempfile.mktemp(suffix='.pdf')
    
    # Save as PDF with high quality
    image.save(pdf_path, 'PDF', resolution=300.0)  # Increased resolution for better quality
    
    return pdf_path

# [Rest of the code remains the same: get_email_config(), send_certificate(), and main()]

if __name__ == "__main__":
    main()
