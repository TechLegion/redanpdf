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
import subprocess
import time
import logging
import shutil

logger = logging.getLogger(__name__)

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
            logger.info(f"PDFProcessor.compress_pdf called with file_path: {file_path}")
            logger.info(f"file_path type: {type(file_path)}")
            logger.info(f"file_path exists: {os.path.exists(file_path)}")
            
            # Alternative compression method using PyMuPDF (fitz)
            try:
                logger.info("Attempting compression using PyMuPDF")
                with fitz.open(file_path) as doc:
                    # Create a new document
                    new_doc = fitz.open()
                    
                    for page_num in range(len(doc)):
                        page = doc.load_page(page_num)
                        
                        # Get the page as an image with reduced quality
                        mat = fitz.Matrix(1.0, 1.0)  # Scale factor
                        pix = page.get_pixmap(matrix=mat, alpha=False)
                        
                        # Convert to PIL Image for compression
                        img_data = pix.tobytes("png")
                        img = Image.open(io.BytesIO(img_data))
                        
                        # Compress the image
                        img_byte_array = io.BytesIO()
                        img.save(img_byte_array, format='JPEG', quality=quality, optimize=True)
                        img_byte_array.seek(0)
                        
                        # Create a new page with the compressed image
                        new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
                        new_page.insert_image(page.rect, stream=img_byte_array.getvalue())
                    
                    # Save the compressed PDF
                    new_doc.save(output_path, garbage=4, deflate=True)
                    new_doc.close()
                
                logger.info(f"Successfully compressed PDF using PyMuPDF")
                return output_path
                
            except Exception as e:
                logger.error(f"PyMuPDF compression failed: {str(e)}")
                logger.info("Falling back to pdf2image method")
                
                # Fallback to original method
                # Convert PDF to images
                logger.info(f"Calling convert_from_path with: {file_path}")
                try:
                    images = convert_from_path(file_path, dpi=72)
                except Exception as e2:
                    logger.error(f"Error in convert_from_path: {str(e2)}")
                    logger.error(f"Error type: {type(e2)}")
                    # Try with explicit poppler path
                    try:
                        images = convert_from_path(file_path, dpi=72, poppler_path=None)
                    except Exception as e3:
                        logger.error(f"Error with explicit poppler path: {str(e3)}")
                        raise e2
                
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

    def pdf_to_epub(self, file_path: str, output_path: str) -> str:
        """
        Convert a PDF file to EPUB format using Calibre's ebook-convert.
        """
        try:
            # On Linux (including Render), ebook-convert is in PATH
            ebook_convert = "ebook-convert"
            
            result = subprocess.run(
                [ebook_convert, file_path, output_path],
                check=True,
                capture_output=True
            )
            return output_path
        except subprocess.CalledProcessError as e:
            raise Exception(f"Error converting PDF to EPUB: {e.stderr.decode()}")
        except FileNotFoundError:
            raise Exception("Calibre's ebook-convert not found. Please install Calibre.")

    def pdf_to_jpg(self, file_path: str, output_dir: str, dpi: int = 200) -> list:
        """
        Convert a PDF to a series of JPG images (one per page).
        """
        try:
            # Check if Poppler is installed
            if os.name == 'nt':  # Windows
                poppler_paths = [
                    r"C:\Program Files\poppler\bin",
                    r"C:\Program Files (x86)\poppler\bin",
                    os.path.expanduser("~\\AppData\\Local\\Programs\\poppler\\bin"),
                    r"C:\Program Files\poppler\Release-24.08.0-0\poppler-24.08.0\Library\bin",  # Added actual path
                    r"C:\Program Files\poppler\Release-24.08.0-0\Library\bin",  # Alternative path
                    r"C:\Program Files\poppler\Library\bin"  # Generic path
                ]
                poppler_path = None
                for path in poppler_paths:
                    if os.path.exists(path):
                        poppler_path = path
                        logger.info(f"Found Poppler at: {path}")
                        break
                if not poppler_path:
                    # Try to find pdfinfo in PATH
                    try:
                        pdfinfo_path = subprocess.check_output(['where', 'pdfinfo'], text=True).strip()
                        if pdfinfo_path:
                            poppler_path = os.path.dirname(pdfinfo_path)
                            logger.info(f"Found Poppler via PATH at: {poppler_path}")
                    except Exception as e:
                        logger.error(f"Error finding pdfinfo in PATH: {str(e)}")
                        pass
                        
                if not poppler_path:
                    raise FileNotFoundError("Poppler not found. Please install Poppler and add its bin directory to PATH.")
            else:  # Linux/Mac
                poppler_path = None  # Let pdf2image find it in PATH

            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
            logger.info(f"Output directory: {output_dir}")

            # Verify input file exists and is readable
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Input PDF file not found: {file_path}")
            logger.info(f"Input file: {file_path}")

            from pdf2image import convert_from_path
            logger.info(f"Using Poppler path: {poppler_path}")
            try:
                images = convert_from_path(file_path, dpi=dpi, poppler_path=poppler_path)
                logger.info(f"Successfully converted PDF to {len(images)} images")
            except Exception as e:
                logger.error(f"Error in convert_from_path: {str(e)}")
                raise
            
            if not images:
                raise Exception("No images were generated from the PDF")
                
            image_paths = []
            for i, img in enumerate(images):
                img_path = os.path.join(output_dir, f"page_{i+1}.jpg")
                try:
                    img.save(img_path, "JPEG", quality=95)  # Higher quality JPEG
                    logger.info(f"Saved image {i+1} to {img_path}")
                    image_paths.append(img_path)
                except Exception as e:
                    logger.error(f"Error saving image {i+1}: {str(e)}")
                    raise
                
            if not image_paths:
                raise Exception("Failed to save any images")
                
            return image_paths
        except FileNotFoundError as e:
            if "Poppler" in str(e):
                logger.error("Poppler not found error")
                raise Exception("PDF to JPG conversion requires Poppler to be installed. Please install Poppler and add its bin directory to PATH.")
            logger.error(f"File not found error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in pdf_to_jpg: {str(e)}")
            raise Exception(f"Error converting PDF to JPG: {str(e)}")

    def convert_office_to_pdf(self, input_path: str, output_path: str) -> None:
        """
        Convert Office documents (Word, Excel, PowerPoint) to PDF using LibreOffice
        """
        try:
            # Check if LibreOffice is installed
            if os.name == 'nt':  # Windows
                libreoffice_paths = [
                    r"C:\Program Files\LibreOffice\program\soffice.exe",
                    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
                    os.path.expanduser("~\\AppData\\Local\\Programs\\LibreOffice\\program\\soffice.exe")
                ]
                soffice_path = None
                for path in libreoffice_paths:
                    if os.path.exists(path):
                        soffice_path = path
                        break
                if not soffice_path:
                    raise FileNotFoundError("LibreOffice not found. Please install LibreOffice to use this feature.")
            else:  # Linux/Mac
                # Check multiple possible paths for LibreOffice on Linux
                linux_paths = [
                    "/usr/bin/libreoffice",
                    "/usr/bin/soffice",
                    "/usr/lib/libreoffice/program/soffice",
                    "/opt/libreoffice/program/soffice",
                    "/snap/bin/libreoffice",
                    "/usr/local/bin/libreoffice",
                    "/usr/local/bin/soffice"
                ]
                soffice_path = None
                for path in linux_paths:
                    if os.path.exists(path):
                        soffice_path = path
                        break
                if not soffice_path:
                    # Try to find it in PATH
                    try:
                        soffice_path = subprocess.check_output(['which', 'libreoffice']).decode().strip()
                    except:
                        try:
                            soffice_path = subprocess.check_output(['which', 'soffice']).decode().strip()
                        except:
                            raise FileNotFoundError("LibreOffice not found. Please install LibreOffice to use this feature.")

            logger.info(f"Using LibreOffice at: {soffice_path}")

            # Convert paths to absolute paths
            input_path = os.path.abspath(input_path)
            output_path = os.path.abspath(output_path)
            output_dir = os.path.dirname(output_path)
            input_filename = os.path.basename(input_path)
            base_filename = os.path.splitext(input_filename)[0]

            logger.info(f"Input file: {input_path}")
            logger.info(f"Output path: {output_path}")

            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)

            # Create a temporary directory for conversion
            with tempfile.TemporaryDirectory() as temp_dir:
                logger.info(f"Created temporary directory: {temp_dir}")

                # Copy input file to temporary directory
                temp_input = os.path.join(temp_dir, input_filename)
                shutil.copy2(input_path, temp_input)
                logger.info(f"Copied input file to: {temp_input}")

                # Run LibreOffice conversion in the temporary directory
                cmd = [
                    soffice_path,
                    '--headless',
                    '--convert-to', 'pdf',
                    temp_input
                ]
                logger.info(f"Running command: {' '.join(cmd)}")

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=temp_dir  # Set working directory to temp_dir
                )

                if result.returncode != 0:
                    logger.error(f"Conversion failed with return code {result.returncode}")
                    logger.error(f"stdout: {result.stdout}")
                    logger.error(f"stderr: {result.stderr}")
                    raise Exception(f"Conversion failed: {result.stderr}")

                # Wait for file to be fully written
                time.sleep(2)

                # Get the converted file path
                converted_file = os.path.join(temp_dir, f"{base_filename}.pdf")
                logger.info(f"Looking for converted file at: {converted_file}")

                # List all files in temp directory for debugging
                logger.info(f"Files in temp directory: {os.listdir(temp_dir)}")

                if not os.path.exists(converted_file):
                    raise Exception(f"Converted file not found at: {converted_file}")

                # Copy the converted file to the desired output location
                shutil.copy2(converted_file, output_path)
                logger.info(f"Copied converted file to: {output_path}")

            # Verify the output file exists and has content
            if not os.path.exists(output_path):
                raise Exception(f"Output file not found at: {output_path}")
            
            if os.path.getsize(output_path) == 0:
                raise Exception("Output file is empty")

            logger.info("Conversion completed successfully")

        except Exception as e:
            logger.error(f"Error converting Office document to PDF: {str(e)}")
            raise Exception(f"Failed to convert document: {str(e)}")

    def edit_text_on_page(self, file_path: str, output_path: str, page_number: int, old_text: str, new_text: str) -> str:
        """
        Replace occurrences of old_text with new_text on a specific page of the PDF, trying to match the original font and size.
        """
        try:
            doc = fitz.open(file_path)
            page = doc[page_number]
            text_instances = page.search_for(old_text)
            # Try to get font info from the original text
            fontname = None
            fontsize = 12
            color = (0, 0, 0)
            blocks = page.get_text('dict')['blocks']
            for b in blocks:
                for l in b.get('lines', []):
                    for s in l.get('spans', []):
                        if old_text.strip() in s['text']:
                            fontname = s.get('font', None)
                            fontsize = s.get('size', 12)
                            color = s.get('color', 0)
                            break
            # Redact the old text
            for inst in text_instances:
                page.add_redact_annot(inst, fill=(1, 1, 1))
            page.apply_redactions()
            for inst in text_instances:
                # Add new text at the same position, try to match font/size
                try:
                    page.insert_text(
                        (inst.x0, inst.y0),
                        new_text,
                        fontsize=fontsize,
                        fontname=fontname if fontname else "helv",
                        color=color if isinstance(color, tuple) else (0, 0, 0)
                    )
                except Exception:
                    page.insert_text((inst.x0, inst.y0), new_text, fontsize=fontsize, color=(0, 0, 0))
            doc.save(output_path)
            doc.close()
            return output_path
        except Exception as e:
            raise Exception(f"Error editing text on page: {str(e)}")

    def add_text_to_page(self, file_path: str, output_path: str, page_number: int, text: str, position: tuple, font_size: int = 12) -> str:
        """
        Add new text to a specific position on a page.
        """
        try:
            doc = fitz.open(file_path)
            page = doc[page_number]
            page.insert_text(position, text, fontsize=font_size, color=(0, 0, 0))
            doc.save(output_path)
            doc.close()
            return output_path
        except Exception as e:
            raise Exception(f"Error adding text to page: {str(e)}")

    def add_image_to_page(self, file_path: str, output_path: str, page_number: int, image_path: str, position: tuple, size: tuple = None) -> str:
        """
        Add an image to a specific position on a page.
        """
        try:
            doc = fitz.open(file_path)
            page = doc[page_number]
            rect = fitz.Rect(position[0], position[1], position[0] + (size[0] if size else 100), position[1] + (size[1] if size else 100))
            page.insert_image(rect, filename=image_path)
            doc.save(output_path)
            doc.close()
            return output_path
        except Exception as e:
            raise Exception(f"Error adding image to page: {str(e)}")

    def remove_images_from_page(self, file_path: str, output_path: str, page_number: int) -> str:
        """
        Remove all images from a specific page.
        """
        try:
            doc = fitz.open(file_path)
            page = doc[page_number]
            img_list = page.get_images(full=True)
            for img in img_list:
                xref = img[0]
                page._wrapContents()
                page._deleteObject(xref)
            doc.save(output_path)
            doc.close()
            return output_path
        except Exception as e:
            raise Exception(f"Error removing images from page: {str(e)}")

    def annotate_page(self, file_path: str, output_path: str, page_number: int, annotation_type: str, data: dict) -> str:
        """
        Add an annotation (highlight, comment, drawing) to a page.
        annotation_type: 'highlight', 'comment', 'draw'
        data: parameters for the annotation
        """
        try:
            doc = fitz.open(file_path)
            page = doc[page_number]
            if annotation_type == 'highlight':
                rects = [fitz.Rect(*rect) for rect in data.get('rects', [])]
                for rect in rects:
                    page.add_highlight_annot(rect)
            elif annotation_type == 'comment':
                pos = tuple(data.get('position', (72, 72)))
                text = data.get('text', '')
                page.add_text_annot(pos, text)
            elif annotation_type == 'draw':
                points = data.get('points', [])
                if points:
                    shape = page.new_shape()
                    shape.draw_polyline(points)
                    shape.finish(color=(1, 0, 0), width=2)
                    shape.commit()
            doc.save(output_path)
            doc.close()
            return output_path
        except Exception as e:
            raise Exception(f"Error annotating page: {str(e)}")

    def reorder_pages(self, file_path: str, output_path: str, new_order: list) -> str:
        """
        Reorder the pages of a PDF according to new_order (list of page indices, 0-based).
        """
        try:
            doc = fitz.open(file_path)
            doc.select(new_order)
            doc.save(output_path)
            doc.close()
            return output_path
        except Exception as e:
            raise Exception(f"Error reordering pages: {str(e)}")