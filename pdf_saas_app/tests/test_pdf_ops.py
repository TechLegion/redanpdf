# Tests for PDF operations will be implemented here. 

from fastapi.testclient import TestClient
from app.main import app
import os

client = TestClient(app)

def get_token():
    email = "pdfuser@example.com"
    password = "pdfpassword"
    client.post("/api/v1/auth/register", json={"email": email, "password": password})
    login_response = client.post("/api/v1/auth/token", data={"username": email, "password": password})
    return login_response.json()["access_token"]

def test_upload_list_delete_pdf():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    sample_pdf_path = "sample.pdf"
    if not os.path.exists(sample_pdf_path):
        # Create a simple PDF file for testing
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(sample_pdf_path)
        c.drawString(100, 750, "Hello, PDF!")
        c.save()
    with open(sample_pdf_path, "rb") as f:
        files = {"file": ("sample.pdf", f, "application/pdf")}
        upload_response = client.post("/api/v1/documents/upload", files=files, headers=headers)
        assert upload_response.status_code == 200
        doc_id = upload_response.json()["id"]
    # List documents
    list_response = client.get("/api/v1/documents/list", headers=headers)
    assert list_response.status_code == 200
    docs = list_response.json()
    assert any(doc["id"] == doc_id for doc in docs)
    # Delete document
    delete_response = client.delete(f"/api/v1/documents/{doc_id}", headers=headers)
    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "Document deleted successfully"
    # Clean up test PDF
    if os.path.exists(sample_pdf_path):
        os.remove(sample_pdf_path) 

def test_edit_text_on_page():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    sample_pdf_path = "sample.pdf"
    if not os.path.exists(sample_pdf_path):
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(sample_pdf_path)
        c.drawString(100, 750, "Hello, PDF!")
        c.save()
    with open(sample_pdf_path, "rb") as f:
        files = {"file": ("sample.pdf", f, "application/pdf")}
        upload_response = client.post("/pdfs/upload", files=files, headers=headers)
        assert upload_response.status_code == 200
        pdf_id = upload_response.json()["id"]
    # Edit text
    resp = client.post(f"/pdfs/{pdf_id}/edit_text", params={"page_number": 0, "old_text": "Hello, PDF!", "new_text": "Hi, PDF!"}, headers=headers)
    assert resp.status_code == 200
    assert "output_path" in resp.json()

def test_add_text_to_page():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    sample_pdf_path = "sample.pdf"
    if not os.path.exists(sample_pdf_path):
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(sample_pdf_path)
        c.drawString(100, 750, "Hello, PDF!")
        c.save()
    with open(sample_pdf_path, "rb") as f:
        files = {"file": ("sample.pdf", f, "application/pdf")}
        upload_response = client.post("/pdfs/upload", files=files, headers=headers)
        assert upload_response.status_code == 200
        pdf_id = upload_response.json()["id"]
    # Add text
    resp = client.post(f"/pdfs/{pdf_id}/add_text", params={"page_number": 0, "text": "Added Text", "x": 100, "y": 700, "font_size": 14}, headers=headers)
    assert resp.status_code == 200
    assert "output_path" in resp.json()

def test_add_image_to_page():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    sample_pdf_path = "sample.pdf"
    image_path = "test_image.png"
    if not os.path.exists(sample_pdf_path):
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(sample_pdf_path)
        c.drawString(100, 750, "Hello, PDF!")
        c.save()
    if not os.path.exists(image_path):
        from PIL import Image
        img = Image.new('RGB', (50, 50), color = 'red')
        img.save(image_path)
    with open(sample_pdf_path, "rb") as f:
        files = {"file": ("sample.pdf", f, "application/pdf")}
        upload_response = client.post("/pdfs/upload", files=files, headers=headers)
        assert upload_response.status_code == 200
        pdf_id = upload_response.json()["id"]
    # Add image
    resp = client.post(f"/pdfs/{pdf_id}/add_image", params={"page_number": 0, "image_path": image_path, "x": 120, "y": 650, "width": 50, "height": 50}, headers=headers)
    assert resp.status_code == 200
    assert "output_path" in resp.json()

def test_remove_images_from_page():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    sample_pdf_path = "sample.pdf"
    if not os.path.exists(sample_pdf_path):
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(sample_pdf_path)
        c.drawString(100, 750, "Hello, PDF!")
        c.save()
    with open(sample_pdf_path, "rb") as f:
        files = {"file": ("sample.pdf", f, "application/pdf")}
        upload_response = client.post("/pdfs/upload", files=files, headers=headers)
        assert upload_response.status_code == 200
        pdf_id = upload_response.json()["id"]
    # Remove images
    resp = client.post(f"/pdfs/{pdf_id}/remove_images", params={"page_number": 0}, headers=headers)
    assert resp.status_code == 200
    assert "output_path" in resp.json()

def test_annotate_page():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    sample_pdf_path = "sample.pdf"
    if not os.path.exists(sample_pdf_path):
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(sample_pdf_path)
        c.drawString(100, 750, "Hello, PDF!")
        c.save()
    with open(sample_pdf_path, "rb") as f:
        files = {"file": ("sample.pdf", f, "application/pdf")}
        upload_response = client.post("/pdfs/upload", files=files, headers=headers)
        assert upload_response.status_code == 200
        pdf_id = upload_response.json()["id"]
    # Annotate (highlight)
    data = {"rects": [[100, 740, 200, 760]]}
    resp = client.post(f"/pdfs/{pdf_id}/annotate", params={"page_number": 0, "annotation_type": "highlight", "data": str(data)}, headers=headers)
    assert resp.status_code == 200
    assert "output_path" in resp.json()

def test_reorder_pages():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    sample_pdf_path = "sample.pdf"
    if not os.path.exists(sample_pdf_path):
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(sample_pdf_path)
        c.drawString(100, 750, "Hello, PDF!")
        c.showPage()
        c.drawString(100, 750, "Second Page!")
        c.save()
    with open(sample_pdf_path, "rb") as f:
        files = {"file": ("sample.pdf", f, "application/pdf")}
        upload_response = client.post("/pdfs/upload", files=files, headers=headers)
        assert upload_response.status_code == 200
        pdf_id = upload_response.json()["id"]
    # Reorder pages (swap page 0 and 1)
    resp = client.post(f"/pdfs/{pdf_id}/reorder_pages", json={"new_order": [1, 0]}, headers=headers)
    assert resp.status_code == 200
    assert "output_path" in resp.json() 