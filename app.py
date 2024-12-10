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

# Template constants
TEMPLATE_WIDTH = 1714
TEMPLATE_HEIGHT = 1205

def check_file_exists(file_path, file_type="file"):
    """Check if file exists and is readable"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"{file_type} not found: {file_path}")
    if not os.access(file_path, os.R_OK):
        raise PermissionError(f"Cannot read {file_type}: {file_path}")
    return file_path

def debug_file_info(file_path):
    """Print debug information about a file"""
    try:
        size = os.path.getsize(file_path)
        st.write(f"File path: {file_path}")
        st.write(f"File size: {size} bytes")
        st.write(f"File exists: {os.path.exists(file_path)}")
        st.write(f"File is readable: {os.access(file_path, os.R_OK)}")
        return True
    except Exception as e:
        st.error(f"Error checking file: {str(e)}")
        return False

def modify_psd(template_path, name, date):
    """Modify PSD template with name and date"""
    try:
        # Debug information
        st.write("Checking template file...")
        if not debug_file_info(template_path):
            return None
            
        # Try to open the PSD file
        st.write("Opening PSD file...")
        psd = PSDImage.open(template_path)
        
        # Convert to PIL Image and ensure correct dimensions
        st.write("Converting to PIL Image...")
        image = psd.compose()
        image = image.resize((TEMPLATE_WIDTH, TEMPLATE_HEIGHT), Image.Resampling.LANCZOS)
        
        # Create drawing object
        draw = ImageDraw.Draw(image)
        
        # Try to use default fonts if custom fonts are not available
        try:
            st.write("Loading fonts...")
            try:
                name_font = ImageFont.truetype("fonts/Pristina-Regular.ttf", size=61)
            except:
                st.warning("Pristina font not found, using default font...")
                name_font = ImageFont.load_default()
                
            try:
                date_font = ImageFont.truetype("fonts/Arial-Bold.ttf", size=11)
            except:
                st.warning("Arial Bold font not found, using default font...")
                date_font = ImageFont.load_default()
        
        except Exception as e:
            st.error(f"Font error: {str(e)}")
            st.warning("Using default font...")
            name_font = ImageFont.load_default()
            date_font = ImageFont.load_default()
        
        # Add name with specified parameters
        name_color = (190, 140, 75)  # RGB for #be8c4d
        draw.text((959, 655), name, font=name_font, fill=name_color)
        
        # Add date with specified parameters
        date_color = (79, 79, 76)  # RGB for #4f4f4c
        draw.text((739, 1048), date, font=date_font, fill=date_color)
        
        # Save modified image
        st.write("Saving modified image...")
        temp_path = tempfile.mktemp(suffix='.png')
        image.save(temp_path)
        
        return temp_path
        
    except Exception as e:
        st.error(f"Error in modify_psd: {str(e)}")
        st.write("Full error details:")
        st.write(e)
        return None

def main():
    """Main Streamlit application"""
    st.title("Certificate Generator & Sender")
    
    # Show current working directory and files
    st.write("Current working directory:", os.getcwd())
    st.write("Files in current directory:", os.listdir())
    if os.path.exists("templates"):
        st.write("Files in templates directory:", os.listdir("templates"))
    
    # User input form
    with st.form("certificate_form"):
        full_name = st.text_input("Full Name")
        email = st.text_input("Email Address")
        date = st.date_input("Date")
        
        submit_button = st.form_submit_button("Generate & Send Certificate")
        
        if submit_button:
            if full_name and email and date:
                try:
                    # Convert date to required format
                    formatted_date = date.strftime("%B %d, %Y")
                    
                    # Generate certificate
                    psd_path = os.path.join("templates", "certificate.psd")
                    st.write(f"Looking for template at: {psd_path}")
                    
                    modified_psd = modify_psd(psd_path, full_name, formatted_date)
                    if modified_psd is None:
                        st.error("Failed to modify certificate template")
                        return
                        
                    # Rest of your code...
                    
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
            else:
                st.warning("Please fill in all fields.")

if __name__ == "__main__":
    main()
