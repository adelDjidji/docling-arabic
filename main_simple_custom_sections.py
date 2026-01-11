from fastapi import FastAPI, UploadFile, File
import tempfile, os
import PyPDF2
from io import BytesIO
import re
from typing import List, Dict

app = FastAPI()

def detect_sections_in_text(text: str) -> List[Dict]:
    """Detect sections in text using heading patterns"""
    sections = []
    
    # Common heading patterns
    heading_patterns = [
    # =========================
    # Numbered sections
    # =========================
    r'^\d+\s*[-–—\.]\s*.+$',          # 1 - عنوان
    r'^\d+\.\d+\s+.+$',               # 1.1 عنوان
    r'^\d+\s+[\)\]]\s*.+$',            # 1) عنوان
    r'^\(\d+\)\s*.+$',                # (1) عنوان

    # =========================
    # Common Arabic section words
    # =========================
    r'^(?:الوحدة|النشاظ|الموضوع|القسم|الجزء)\s+(?:\d+|[أ-ي]+)\s*[:\-–—]?\s*.+$',
    r'^(?:المقدمة|التمهيد|الخاتمة|الملخص|النتائج|التوصيات)\s*[:\-–—]?\s*$',

    # =========================
    # Article / clause style (legal texts)
    # =========================
    r'^(?:المادة)\s+(?:\d+|[أ-ي]+)\s*[:\-–—]?\s*.+$',

    # =========================
    # Quran / religious structure
    # =========================
    r'^(?:سورة)\s+[أ-ي]+\s*$',
    r'^(?:الآية)\s+\d+\s*$',

    # =========================
    # Bold / short standalone lines
    # =========================
    r'^[\u0600-\u06FF\s]{3,40}$',       # Short Arabic-only line
]

    
    lines = text.split('\n')
    current_section = "Document"
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if line matches any heading pattern
        is_heading = False
        for pattern in heading_patterns:
            if re.match(pattern, line, re.MULTILINE):
                current_section = line
                is_heading = True
                break
        
        if not is_heading and line:
            sections.append({
                "text": line,
                "section": current_section
            })
    
    return sections

def extract_text_with_enhanced_pypdf2(pdf_content: bytes) -> List[Dict]:
    """Extract text with section detection"""
    text_by_page = []
    
    try:
        pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_content))
        
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text = page.extract_text()
            
            if text.strip():
                # Detect sections in this page's text
                sections = detect_sections_in_text(text)
                
                for section_data in sections:
                    text_by_page.append({
                        "page": page_num + 1,
                        "text": section_data["text"],
                        "section": section_data["section"]
                    })
        
        return text_by_page
    except Exception as e:
        print(f"Enhanced PyPDF2 extraction error: {e}")
        return None

def chunk_text_with_sections(text_pages: List[Dict], chunk_size: int = 600, overlap: int = 100) -> List[Dict]:
    """Chunk text while preserving section information"""
    chunks = []
    
    # Group by section first
    current_chunk = ""
    current_section = None
    current_page = 1
    chunk_words = []
    
    for item in text_pages:
        text = item["text"]
        section = item["section"]
        page = item["page"]
        
        words = text.split()
        
        # If section changes, force a new chunk
        if section != current_section and current_chunk:
            if chunk_words:
                chunk_text = " ".join(chunk_words)
                chunks.append({
                    "text": chunk_text,
                    "meta": {
                        "page": current_page,
                        "section": current_section
                    }
                })
            chunk_words = []
            current_chunk = ""
        
        current_section = section
        current_page = page
        
        # Add words to current chunk
        for word in words:
            chunk_words.append(word)
            
            # Check if we've reached chunk size
            if len(chunk_words) >= chunk_size:
                chunk_text = " ".join(chunk_words[:chunk_size])
                chunks.append({
                    "text": chunk_text,
                    "meta": {
                        "page": page,
                        "section": section
                    }
                })
                
                # Keep overlap for next chunk
                if overlap > 0:
                    chunk_words = chunk_words[chunk_size - overlap:]
                else:
                    chunk_words = []
    
    # Add remaining words
    if chunk_words:
        chunk_text = " ".join(chunk_words)
        chunks.append({
            "text": chunk_text,
            "meta": {
                "page": current_page,
                "section": current_section
            }
        })
    
    return chunks

@app.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    content = await file.read()
    
    # Extract text with enhanced section detection
    text_pages = extract_text_with_enhanced_pypdf2(content)
    
    if text_pages:
        chunks = chunk_text_with_sections(text_pages)
        
        return {
            "success": True,
            "chunks": chunks,
            "method": "enhanced_pypdf2",
            "total_chunks": len(chunks)
        }
    
    return {
        "success": False,
        "error": "Could not extract text from PDF"
    }