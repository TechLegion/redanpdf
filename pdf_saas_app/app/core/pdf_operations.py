import os
import fitz  # PyMuPDF
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from pdf2image import convert_from_path
import io
import tempfile
from typing import List, Tuple, Optional
from PIL import Image
import pytesseract

class PDFProcessor:
    def extract_text(self, file_path: str) -> str:
        """
        Extract text from a PDF file, using OCR for image-only pages.
        """
        try:
            text = ""
            with fitz.open(file_path) as doc:
                for page in doc:
                    page_text = page.get_text()
                    if not page_text.strip():
                        # If no text, do OCR
                        pix = page.get_pixmap()
                        img = Image.open(io.BytesIO(pix.tobytes()))
                        page_text = pytesseract.image_to_string(img)
                    text += page_text
            return text
        except Exception as e:
            raise Exception(f"Error extracting text from PDF: {str(e)}")

    def merge_pdfs(self, pdf_paths: List[str], output_path: str) -> str:
        """
        Merge multiple PDFs into a single PDF
        """
        try:
            writer = PdfWriter()
            for pdf_path in pdf_paths:
                reader = PdfReader(pdf_path)
                for page in reader.pages:
                    writer.add_page(page)
            
            with open(output_path, "wb") as output_file:
                writer.write(output_file)
            return output_path
        except Exception as e:
            raise Exception(f"Error merging PDFs: {str(e)}")

    def split_pdf(self, file_path: str, output_dir: str) -> List[str]:
        """
        Split a PDF into individual pages
        """
        try:
            reader = PdfReader(file_path)
            output_paths = []
            
            for i, page in enumerate(reader.pages):
                writer = PdfWriter()
                writer.add_page(page)
                output_path = os.path.join(output_dir, f"page_{i+1}.pdf")
                
                with open(output_path, "wb") as output_file:
                    writer.write(output_file)
                output_paths.append(output_path)
            
            return output_paths
        except Exception as e:
            raise Exception(f"Error splitting PDF: {str(e)}")

    def compress_pdf(self, file_path: str, output_path: str, quality: int = 90) -> str:
        """
        Compress a PDF file (lower quality = higher compression)
        """
        try:
            # Convert PDF to images
            images = convert_from_path(file_path, dpi=72)
            
            # Create a new PDF from compressed images
            output_pdf = PdfWriter()
            
            for img in images:
                img_byte_array = io.BytesIO()
                img.save(img_byte_array, format='JPEG', quality=quality)
                img_byte_array.seek(0)
                
                # Create temporary PDF from image
                temp_pdf_path = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False).name
                c = canvas.Canvas(temp_pdf_path, pagesize=letter)
                c.drawImage(img_byte_array, 0, 0, width=letter[0], height=letter[1])
                c.save()
                
                # Add page to output PDF
                reader = PdfReader(temp_pdf_path)
                output_pdf.add_page(reader.pages[0])
                os.unlink(temp_pdf_path)
            
            # Save the compressed PDF
            with open(output_path, "wb") as output_file:
                output_pdf.write(output_file)
            
            return output_path
        except Exception as e:
            raise Exception(f"Error compressing PDF: {str(e)}")

    def add_watermark(self, file_path: str, watermark_text: str, output_path: str) -> str:
        """
        Add a text watermark to each page of a PDF
        """
        try:
            # Create watermark PDF
            watermark_pdf = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False).name
            c = canvas.Canvas(watermark_pdf, pagesize=letter)
            c.setFont("Helvetica", 60)
            c.setFillColorRGB(0.5, 0.5, 0.5, 0.3)  # Gray, semi-transparent
            c.saveState()
            c.translate(letter[0]/2, letter[1]/2)
            c.rotate(45)
            c.drawCentredString(0, 0, watermark_text)
            c.restoreState()
            c.save()
            
            # Open the input PDF
            reader = PdfReader(file_path)
            watermark_reader = PdfReader(watermark_pdf)
            watermark_page = watermark_reader.pages[0]
            
            # Create output PDF
            writer = PdfWriter()
            
            # Add watermark to each page
            for page in reader.pages:
                page.merge_page(watermark_page)
                writer.add_page(page)
            
            # Save the watermarked PDF
            with open(output_path, "wb") as output_file:
                writer.write(output_file)
            
            # Clean up
            os.unlink(watermark_pdf)
            
            return output_path
        except Exception as e:
            raise Exception(f"Error adding watermark to PDF: {str(e)}")

    def convert_to_images(self, file_path: str, output_dir: str, dpi: int = 200) -> List[str]:
        """
        Convert a PDF to a series of images
        """
        try:
            images = convert_from_path(file_path, dpi=dpi)
            image_paths = []
            
            for i, img in enumerate(images):
                img_path = os.path.join(output_dir, f"page_{i+1}.png")
                img.save(img_path, "PNG")
                image_paths.append(img_path)
            
            return image_paths
        except Exception as e:
            raise Exception(f"Error converting PDF to images: {str(e)}")

    def count_pages(self, file_path: str) -> int:
        """
        Count the number of pages in a PDF
        """
        try:
            with fitz.open(file_path) as doc:
                return len(doc)
        except Exception as e:
            raise Exception(f"Error counting PDF pages: {str(e)}")

    def rotate_pages(self, file_path: str, output_path: str, rotation: int, page_numbers: Optional[List[int]] = None) -> str:
        """
        Rotate specific pages or all pages of a PDF
        """
        try:
            reader = PdfReader(file_path)
            writer = PdfWriter()
            
            for i, page in enumerate(reader.pages):
                if page_numbers is None or (i + 1) in page_numbers:
                    page.rotate((page.rotation + rotation) % 360)
                writer.add_page(page)

            with open(output_path, "wb") as output_file:
                writer.write(output_file)

            return output_path
        except Exception as e:
            raise Exception(f"Error rotating PDF pages: {str(e)}")