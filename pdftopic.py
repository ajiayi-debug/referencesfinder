import fitz  # PyMuPDF
from PIL import Image
import io

# Open the PDF file
pdf_document = fitz.open('FC-Institute-Publication-on-Lactose-intolerance_2022.pdf')

images = []

# Loop through each page
for page_number in range(len(pdf_document)):
    page = pdf_document.load_page(page_number)
    images_list = page.get_images(full=True)
    
    for img_index, img in enumerate(images_list):
        xref = img[0]
        base_image = pdf_document.extract_image(xref)
        image_bytes = base_image["image"]
        image_ext = base_image["ext"]
        
        # Load the image using PIL
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert CMYK and palette mode images to RGB
        if image.mode == "CMYK" or image.mode == "P":
            image = image.convert("RGB")
        
        images.append((image, image_ext, page_number, img_index))

# Save extracted images
for image, image_ext, page_number, img_index in images:
    image_filename = f"FC_lactose_intolerance_page_{page_number+1}_image_{img_index+1}.png"
    
    # Save the image using PIL
    image.save(image_filename)

pdf_document.close()


