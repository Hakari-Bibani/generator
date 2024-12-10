import streamlit as st
import os
import sys
from datetime import datetime

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.psd_handler import modify_psd
from utils.pdf_converter import convert_to_pdf
from utils.email_sender import send_certificate

def main():
    st.title("Certificate Generator & Sender")
    
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
                    modified_psd = modify_psd(psd_path, full_name, formatted_date)
                    
                    # Convert to PDF
                    pdf_path = convert_to_pdf(modified_psd)
                    
                    # Send email
                    first_name = full_name.split()[0]
                    email_subject = "Your Course Certificate"
                    email_body = f"""Dear {first_name},

Thank you for participating in our course. We are delighted to have you with us. Please find your certificate attached.

Best regards,
Your Organization Name"""
                    
                    send_certificate(email, email_subject, email_body, pdf_path)
                    
                    st.success("Certificate generated and sent successfully!")
                    
                    # Clean up temporary files
                    os.remove(modified_psd)
                    os.remove(pdf_path)
                    
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
            else:
                st.warning("Please fill in all fields.")

if __name__ == "__main__":
    main()
