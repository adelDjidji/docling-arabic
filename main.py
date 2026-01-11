from fastapi import FastAPI, UploadFile, File
import tempfile, os
from io import BytesIO
import PyPDF2
import torch
import re

app = FastAPI()


def extract_with_ocr(pdf_path):
    """
    Use OCR to extract text from PDF with proper Arabic support.
    This is the ONLY reliable way to get clean Arabic text from PDFs.
    """
    try:
        from pdf2image import convert_from_path
        import pytesseract
        
        print("🔍 Using Tesseract OCR for Arabic text extraction...")
        
        # Convert PDF to images at good resolution
        images = convert_from_path(pdf_path, dpi=300)
        
        pages = []
        for i, image in enumerate(images):
            # Extract with Arabic + English
            text = pytesseract.image_to_string(image, lang='ara+eng', config='--psm 6')
            text = re.sub(r'[\u200e\u200f]', '', text)
            
            if text.strip():
                pages.append({
                    "page": i + 1,
                    "text": text.strip()
                })
                
                if i == 0:  # Show first page sample
                    print(f"\n📄 OCR Sample (Page 1):\n{text[:400]}\n")
        
        print(f"✅ OCR extracted {len(pages)} pages")
        return pages
        
    except ImportError as e:
        print(f"❌ OCR libraries missing: {e}")
        print("\nInstall with:")
        print("  pip install pytesseract pdf2image pillow")
        print("\nAnd install Tesseract:")
        print("  Ubuntu/Debian: sudo apt-get install tesseract-ocr tesseract-ocr-ara")
        print("  macOS: brew install tesseract tesseract-lang")
        print("  Windows: https://github.com/UB-Mannheim/tesseract/wiki")
        return None
    except Exception as e:
        print(f"❌ OCR failed: {e}")
        return None


def is_section_heading(line):
    """
    Detect Arabic section headings - simple and robust.
    """
    line = line.strip()
    
    if not line or len(line) > 200:
        return False
    
    # Keywords that indicate headings
    section_keywords = [
        'الوحدة', 'وحدة',
        'الفصل', 'فصل', 
        'المقدمة', 'مقدمة',
        'الخاتمة', 'الأهداف', 'أهداف',
        'المنهجية', 'منهجية',
        'التقويم', 'تقويم',
        'الباب', 'القسم', 'الجزء',
        'فترة المراجعة',
    ]
    
    line_clean = line.lower().replace('ا', 'ا').replace('إ', 'ا')
    
    for keyword in section_keywords:
        if keyword in line_clean:
            return True
    
    # Pattern: "الوحدة الأولى:" or "1. Something"
    if re.match(r'^(الوحدة|الفصل|الباب).+(الأول|الثان|الثالث|الرابع|الخامس|السادس|السابع|الثامن)', line):
        return True
    
    # Short lines with colons (often titles)
    if ':' in line and len(line) < 100:
        return True
    
    return False


def extract_sections_from_pages(pages):
    """
    Extract all section headings from pages.
    """
    sections = []
    
    for page in pages:
        lines = page["text"].split('\n')
        
        for line in lines:
            line = line.strip()
            if is_section_heading(line):
                # Clean up bullets and extra spaces
                section = re.sub(r'^[•\-\*]\s*', '', line)
                section = re.sub(r'\s+', ' ', section).strip()
                
                if section and len(section) > 3:
                    sections.append(section)
                    print(f"  📌 Found section: {section}")
    
    return sections


def chunk_text_pages(pages, chunk_size=600, overlap=100):
    """
    Chunk pages into smaller pieces.
    """
    chunks = []
    
    for page in pages:
        text = page["text"]
        words = text.split()
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk_words = words[i:i + chunk_size]
            if chunk_words:
                chunks.append({
                    "text": " ".join(chunk_words),
                    "page": page["page"]
                })
    
    return chunks


def assign_sections_smart(chunks, sections):
    """
    Assign sections to chunks intelligently.
    """
    if not sections:
        print("⚠️ No sections found - using page numbers")
        return [{
            "text": c["text"],
            "meta": {
                "page": c["page"],
                "section": f"صفحة {c['page']}"
            }
        } for c in chunks]
    
    enriched = []
    current_section = sections[0]
    
    for chunk in chunks:
        chunk_text = chunk["text"]
        
        # Check if this chunk contains a section heading
        found_section = None
        for section in sections:
            # Simple substring matching
            if section in chunk_text[:400]:  # Check first 400 chars
                found_section = section
                current_section = section
                break
        
        if not found_section:
            found_section = current_section
        
        enriched.append({
            "text": chunk["text"],
            "meta": {
                "page": chunk["page"],
                "section": found_section
            }
        })
    
    return enriched


@app.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    """
    Ingest PDF with OCR for Arabic support.
    
    IMPORTANT: This endpoint requires OCR for proper Arabic text extraction.
    Install: pip install pytesseract pdf2image pillow
    And: sudo apt-get install tesseract-ocr tesseract-ocr-ara
    """
    content = await file.read()

    if not hasattr(torch, "xpu"):
        class FakeXPU:
            @staticmethod
            def is_available():
                return False
            @staticmethod
            def device_count():
                return 0
        torch.xpu = FakeXPU()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(content)
        pdf_path = tmp.name

    try:
        # ========================================
        # STEP 1: Extract text using OCR
        # ========================================
        print("\n" + "="*60)
        print("STEP 1: Extracting text with OCR")
        print("="*60)
        
        pages = extract_with_ocr(pdf_path)
        
        if not pages:
            return {
                "success": False,
                "error": "OCR extraction failed. Please install pytesseract and tesseract-ocr with Arabic support.",
                "install_instructions": {
                    "python": "pip install pytesseract pdf2image pillow",
                    "system": {
                        "ubuntu": "sudo apt-get install tesseract-ocr tesseract-ocr-ara",
                        "macos": "brew install tesseract tesseract-lang",
                        "windows": "Download from https://github.com/UB-Mannheim/tesseract/wiki"
                    }
                }
            }
        
        # ========================================
        # STEP 2: Extract sections
        # ========================================
        print("\n" + "="*60)
        print("STEP 2: Detecting sections")
        print("="*60)
        
        sections = extract_sections_from_pages(pages)
        print(f"\n✅ Found {len(sections)} sections")
        
        # ========================================
        # STEP 3: Create chunks
        # ========================================
        print("\n" + "="*60)
        print("STEP 3: Creating chunks")
        print("="*60)
        
        chunks = chunk_text_pages(pages, chunk_size=600, overlap=100)
        print(f"✅ Created {len(chunks)} chunks")
        
        # ========================================
        # STEP 4: Assign sections to chunks
        # ========================================
        print("\n" + "="*60)
        print("STEP 4: Assigning sections to chunks")
        print("="*60)
        
        enriched_chunks = assign_sections_smart(chunks, sections)
        
        # Show sample
        if enriched_chunks:
            print(f"\n📊 Sample chunk:")
            print(f"  Section: {enriched_chunks[0]['meta']['section']}")
            print(f"  Text: {enriched_chunks[0]['text'][:100]}...")
        
        os.unlink(pdf_path)
        
        return {
            "success": True,
            "method": "ocr_tesseract",
            "total_pages": len(pages),
            "total_chunks": len(enriched_chunks),
            "detected_sections": sections,
            "sections_count": len(sections),
            "chunks": enriched_chunks,
            "note": "Text extracted using OCR for proper Arabic support"
        }

    except Exception as e:
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)
        
        return {
            "success": False,
            "error": str(e),
            "traceback": __import__('traceback').format_exc()
        }


@app.get("/health")
async def health():
    """Check if OCR is available"""
    try:
        import pytesseract
        from pdf2image import convert_from_path
        
        # Try to get tesseract version
        version = pytesseract.get_tesseract_version()
        
        # Check for Arabic language
        langs = pytesseract.get_languages()
        has_arabic = 'ara' in langs
        
        return {
            "status": "healthy",
            "ocr_available": True,
            "tesseract_version": str(version),
            "arabic_support": has_arabic,
            "available_languages": langs
        }
    except Exception as e:
        return {
            "status": "limited",
            "ocr_available": False,
            "error": str(e),
            "message": "OCR not available - install pytesseract and tesseract-ocr"
        }


if __name__ == "__main__":
    import uvicorn
    print("\n🚀 Starting FastAPI server with OCR support for Arabic PDFs")
    print("📋 Check OCR status at: http://localhost:8000/health")
    print("📄 Upload PDFs at: http://localhost:8000/ingest\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)