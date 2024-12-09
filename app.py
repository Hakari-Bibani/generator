import streamlit as st
from PIL import Image, ImageDraw, ImageFont
from psd_tools import PSDImage
import os
from datetime import datetime

# Configure Streamlit page
st.set_page_config(page_title="Certificate Generator")

def modify_psd(name, date, template_path="template.psd"):
    """Modify PSD template with participant details"""
    try:
        # Open PSD file
        psd = PSDImage.open(template_path)
        
        # Convert to PIL Image
        image = psd.compose()
        draw = ImageDraw.Draw(image)
        
        # Find the layer containing "Hawkar Ali Abdulhaq"
        for layer in psd.descendants():
            if hasattr(layer, 'text') and "Hawkar Ali Abdulhaq" in layer.text:
                # Get layer properties
                bbox = layer.bbox
                try:
                    # Try to get original font size and color
                    font_size = layer.text_data.get('fontSize', 60)
                    color_data = layer.text_data.get('color', {})
                    # Convert color values from 0-1 to 0-255 range
                    color = (
                        int(color_data.get('red', 0.85) * 255),  # Golden color values
                        int(color_data.get('green', 0.65) * 255),
                        int(color_data.get('blue', 0.13) * 255)
                    )
                except:
                    font_size = 60
                    color = (218, 165, 32)  # Default gold color
                
                # Try to use a similar font, or default to Arial
                try:
                    font = ImageFont.truetype("arial.ttf", int(font_size))
                except:
                    try:
                        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", int(font_size))
                    except:
                        font = ImageFont.load_default()
                        st.warning("Using default font - install Arial or DejaVu Serif for better results")

                # Calculate center position of original text
                x = (bbox[2] + bbox[0]) // 2
                y = (bbox[3] + bbox[1]) // 2
                
                # Calculate text dimensions for centering
                text_bbox = draw.textbbox((0, 0), name, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                
                # Draw new name centered at the same position
                draw.text(
                    (x - text_width//2, y - text_height//2),
                    name,
                    font=font,
                    fill=color
                )
                
                st.info("Name replaced successfully!")
                break
        
        # Find and replace date if needed
        # This assumes there's a text layer containing "DATE" or similar
        for layer in psd.descendants():
            if hasattr(layer, 'text') and ("DATE" in layer.text.upper() or layer.name.upper() == "DATE"):
                bbox = layer.bbox
                x = (bbox[2] + bbox[0]) // 2
                y = (bbox[3] + bbox[1]) // 2
                
                try:
                    font = ImageFont.truetype("arial.ttf", 40)
                except:
                    font = ImageFont.load_default()
                
                text_bbox = draw.textbbox((0, 0), date, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                
                draw.text(
                    (x - text_width//2, y - text_height//2),
                    date,
                    font=font,
                    fill='black'
                )
                break
        
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
