import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from psd_tools import PSDImage
import os
from datetime import datetime

# Configure Streamlit page
st.set_page_config(page_title="Certificate Generator")

def find_text_layer_positions(psd):
    """Find the position of text layers in the PSD"""
    name_info = None
    date_info = None
    
    for layer in psd.descendants():
        if hasattr(layer, 'text'):
            # Find the name layer (Hawkar Ali Abdulhaq)
            if "Hawkar Ali Abdulhaq" in layer.text:
                name_info = {
                    'bbox': layer.bbox,
                    'text': layer.text
                }
            # Find the date layer
            elif "DATE" in layer.text.upper():
                date_info = {
                    'bbox': layer.bbox,
                    'text': layer.text
                }
    
    return name_info, date_info

def modify_psd(name, date, template_path="template.psd"):
    """Modify PSD template with participant details"""
    try:
        # Open PSD file
        psd = PSDImage.open(template_path)
        
        # Convert to PIL Image
        image = psd.compose()
        draw = ImageDraw.Draw(image)
        
        # Get layer positions
        name_info, date_info = find_text_layer_positions(psd)
        
        if name_info:
            # Set up font (using default for now, you can specify your font path)
            try:
                # Try to load Arial font
                font = ImageFont.truetype("arial.ttf", 60)
            except:
                try:
                    # Try to load DejaVu font (common on Linux)
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", 60)
                except:
                    # Fallback to default font
                    font = ImageFont.load_default()
                    st.warning("Using default font - for better results, please install Arial font")
            
            # Calculate center position
            bbox = name_info['bbox']
            x = (bbox[2] + bbox[0]) // 2
            y = (bbox[3] + bbox[1]) // 2
            
            # Calculate text size for centering
            text_bbox = draw.textbbox((0, 0), name, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            # Gold color similar to original
            gold_color = (218, 165, 32)
            
            # Draw name
            draw.text(
                (x - text_width//2, y - text_height//2),
                name,
                font=font,
                fill=gold_color
            )
        
        if date_info:
            try:
                font = ImageFont.truetype("arial.ttf", 40)
            except:
                font = ImageFont.load_default()
            
            bbox = date_info['bbox']
            x = (bbox[2] + bbox[0]) // 2
            y = (bbox[3] + bbox[1]) // 2
            
            text_bbox = draw.textbbox((0, 0), date, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            draw.text(
                (x - text_width//2, y - text_height//2),
                date,
                font=font,
                fill='black'
            )
        
        return image
    
    except Exception as e:
        st.error(f"Error modifying PSD: {str(e)}")
        raise

def main():
    st.title("Certificate Generator")
    
    # File uploader for PSD template
    uploaded_psd = st.file_uploader("Upload PSD template", type=['psd'])
    if uploaded_psd:
        with open("template.psd", "wb") as f:
            f.write(uploaded_psd.getbuffer())
        st.success("PSD template uploaded!")
    
    # Certificate generation form
    with st.form("certificate_form"):
        name = st.text_input("Participant's Name")
        date = st.date_input("Certificate Date")
        email = st.text_input("Email Address")
        submit = st.form_submit_button("Generate Certificate")
    
    if submit and name and email:
        try:
            # Generate certificate
            certificate = modify_psd(
                name, 
                date.strftime("%B %d, %Y")
            )
            
            # Save as PDF
            pdf_path = f"{name.replace(' ', '_')}_certificate.pdf"
            certificate.save(pdf_path, "PDF", resolution=300)
            
            # Show preview
            st.image(certificate, caption="Generated Certificate Preview")
            
            # Show download button
            with open(pdf_path, "rb") as file:
                st.download_button(
                    label="Download Certificate",
                    data=file,
                    file_name=pdf_path,
                    mime="application/pdf"
                )
            
            st.success("Certificate generated successfully!")
            
            # Clean up
            os.remove(pdf_path)
            
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
