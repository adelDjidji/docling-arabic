from fastapi import FastAPI, UploadFile, File
import tempfile, os
import torch
import PyPDF2
from io import BytesIO

app = FastAPI()

def extract_text_with_pypdf2(pdf_content):
    """Extract text using PyPDF2 as a reliable fallback"""
    text_by_page = []
    
    try:
        pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_content))
        
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text = page.extract_text()
            
            if text.strip():  # Only add if there's text
                text_by_page.append({
                    "page": page_num + 1,
                    "text": text
                })
        
        return text_by_page
    except Exception as e:
        print(f"PyPDF2 extraction error: {e}")
        return None

def chunk_text(text_pages, chunk_size=600, overlap=100):
    """Simple text chunking"""
    chunks = []
    
    for page_data in text_pages:
        text = page_data["text"]
        page_num = page_data["page"]
        
        # Simple sliding window chunking
        words = text.split()
        for i in range(0, len(words), chunk_size - overlap):
            chunk_words = words[i:i + chunk_size]
            if chunk_words:
                chunk_text = " ".join(chunk_words)
                chunks.append({
                    "text": chunk_text,
                    "meta": {
                        "page": page_num,
                        "section": None
                    }
                })
    
    return chunks

@app.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    content = await file.read()
    
    # Try PyPDF2 first (most reliable)
    text_pages = extract_text_with_pypdf2(content)
    
    if text_pages and any(page["text"].strip() for page in text_pages):
        chunks = chunk_text(text_pages)
        
        return {
            "success": True,
            "chunks": chunks,
            "method": "pypdf2",
            "total_pages": len(text_pages),
            "total_chunks": len(chunks)
        }
    
    # If PyPDF2 fails, try docling with layout disabled
    try:
        # Patch torch.xpu
        if not hasattr(torch, 'xpu'):
            torch.xpu = type('XPU', (), {
                'is_available': lambda: False,
                'device_count': lambda: 0
            })()
        
        from docling.document_converter import DocumentConverter
        from docling.chunking import HybridChunker
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(content)
            path = tmp.name
        
        try:
            # Try with layout disabled
            converter = DocumentConverter(do_layout_model=False)
            result = converter.convert(path, raises_on_error=False)
            
            if result.document:
                doc = result.document
                chunker = HybridChunker(chunk_size=600, chunk_overlap=100)
                chunks = chunker.chunk(doc)
                
                return {
                    "success": True,
                    "chunks": [
                        {
                            "text": c.text,
                            "meta": {
                                "page": c.meta.get("page"),
                                "section": c.meta.get("section")
                            }
                        }
                        for c in chunks
                    ],
                    "method": "docling_no_layout",
                    "total_chunks": len(chunks)
                }
        finally:
            if os.path.exists(path):
                os.unlink(path)
                
    except Exception as e:
        return {
            "success": False,
            "error": f"All methods failed: {str(e)}"
        }
    
    return {
        "success": False,
        "error": "Could not extract text from PDF"
    }