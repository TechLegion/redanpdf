# Tests for PDF operations will be implemented here. 

from fastapi.testclient import TestClient
from pdf_saas_app.app.main import app
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