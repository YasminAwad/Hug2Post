# services/pdf_service.py
import PyPDF2
from pathlib import Path

async def extract_text(pdf_path: Path) -> str:
    """Extract text from PDF file"""
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
    except Exception as e:
        print(f"Error extracting text from {pdf_path}: {str(e)}")
    return text

def retrieve_prompt(file_name: str) -> str:
    with open("app/prompts/" + file_name, "r") as f:
        return f.read()