from fastapi import FastAPI, UploadFile, File
import tempfile, os
from io import BytesIO
import PyPDF2
import torch
import re

app = FastAPI()


def is_likely_heading(line, debug=False):
    """
    Detect if a line is likely a heading/section title.
    """
    line = line.strip()
    
    if not line or len(line) > 200:
        return False
    
    # Strategy 1: Common Arabic/English heading words
    heading_keywords = [
        # Arabic (various forms)
        'الوحدة', 'وحدة', 'الفصل', 'فصل', 'المقدمة', 'مقدمة',
        'الخاتمة', 'خاتمة', 'الأهداف', 'أهداف', 'المنهجية', 'منهجية',
        'التقويم', 'تقويم', 'الباب', 'باب', 'القسم', 'قسم',
        'الجزء', 'جزء', 'الفرع', 'فرع', 'الدرس', 'درس',
        
        # English
        'CHAPTER', 'UNIT', 'SECTION', 'INTRODUCTION', 'CONCLUSION',
        'OBJECTIVES', 'METHODOLOGY', 'ASSESSMENT', 'LESSON',
    ]
    
    line_lower = line.lower()
    for keyword in heading_keywords:
        if keyword.lower() in line_lower:
            if debug:
                print(f"  ✅ Found keyword '{keyword}' in: {line[:50]}...")
            return True
    
    # Strategy 2: Numbered headings (1., 2., etc or ١., ٢., etc)
    if re.match(r'^(\d+|[٠-٩]+)[\.\-\:]\s*.+', line):
        if debug:
            print(f"  ✅ Found numbered heading: {line[:50]}...")
        return True
    
    # Strategy 3: Short lines (likely titles) - but not too short
    if 10 < len(line) < 100:
        # Check if it contains Arabic characters
        arabic_count = sum(1 for c in line if '\u0600' <= c <= '\u06FF')
        if arabic_count > 3:  # At least 3 Arabic chars
            # Should not end with common sentence endings
            if not line.endswith(('.', '،', '؛', '!')):
                if debug:
                    print(f"  ✅ Found short Arabic line: {line[:50]}...")
                return True
    
    # Strategy 4: Lines with colons (often headings)
    if ':' in line or '：' in line:
        if len(line) < 150:
            if debug:
                print(f"  ✅ Found colon heading: {line[:50]}...")
            return True
    
    # Strategy 5: All CAPS lines (short)
    if len(line) < 100 and line.isupper() and len(line) > 5:
        if debug:
            print(f"  ✅ Found CAPS heading: {line[:50]}...")
        return True
    
    return False


def extract_sections_from_text(text, debug=False):
    """
    Extract section titles from text.
    Returns list of section titles.
    """
    sections = []
    lines = text.split('\n')
    
    if debug:
        print(f"\n📄 Processing {len(lines)} lines...")
    
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
            
        if is_likely_heading(line, debug=debug):
            # Clean up the line
            section = re.sub(r'^[•\-\*\+]\s*', '', line)  # Remove bullets
            section = section.strip()
            
            if section and len(section) > 3:
                sections.append(section)
                if debug:
                    print(f"  📌 Section #{len(sections)}: {section[:80]}...")
    
    if debug:
        print(f"\n✅ Total sections found: {len(sections)}\n")
    
    return sections


def extract_text_with_pypdf2(pdf_content):
    """Extract text using PyPDF2"""
    pages = []
    try:
        reader = PyPDF2.PdfReader(BytesIO(pdf_content))
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                pages.append({
                    "page": i + 1,
                    "text": text
                })
        return pages
    except Exception as e:
        print(f"PyPDF2 error: {e}")
        return None


def chunk_plain_text(text_pages, chunk_size=600, overlap=100):
    """Simple chunking"""
    chunks = []
    for page in text_pages:
        words = page["text"].split()
        for i in range(0, len(words), chunk_size - overlap):
            chunk = words[i:i + chunk_size]
            if chunk:
                chunks.append({
                    "text": " ".join(chunk),
                    "meta": {
                        "page": page["page"],
                    }
                })
    return chunks


def assign_sections_to_chunks(chunks_data, all_sections):
    """
    Assign sections to chunks based on text matching.
    """
    if not all_sections:
        print("⚠️  No sections detected - using default")
        # Use page numbers as fallback
        return [{
            "text": c["text"],
            "meta": {
                "page": c["meta"]["page"],
                "section": f"Page {c['meta']['page']}"
            }
        } for c in chunks_data]
    
    enriched = []
    current_section = all_sections[0]  # Start with first section
    
    print(f"\n📊 Assigning {len(all_sections)} sections to {len(chunks_data)} chunks...")
    
    for chunk_idx, chunk in enumerate(chunks_data):
        chunk_text = chunk["text"]
        matched_section = None
        
        # Check if this chunk contains any section title
        for section in all_sections:
            # Try to find section in first 500 chars of chunk
            search_text = chunk_text[:500]
            
            # Create a simple version for matching (remove diacritics, etc)
            section_simple = re.sub(r'[ًٌٍَُِّْ]', '', section)  # Remove Arabic diacritics
            search_simple = re.sub(r'[ًٌٍَُِّْ]', '', search_text)
            
            if section_simple in search_simple or section in search_text:
                matched_section = section
                current_section = section
                print(f"  ✅ Chunk {chunk_idx}: Matched section: {section[:50]}...")
                break
        
        # If no match found, use current section
        if not matched_section:
            matched_section = current_section
        
        enriched.append({
            "text": chunk["text"],
            "meta": {
                "page": chunk["meta"]["page"],
                "section": matched_section
            }
        })
    
    return enriched


# ----------------------------
# FastAPI endpoint
# ----------------------------
@app.post("/ingest")
async def ingest(file: UploadFile = File(...), use_ocr: bool = False, debug: bool = False):
    """
    Ingest PDF and extract chunks with sections.
    
    Parameters:
    - use_ocr: Enable OCR (requires pytesseract)
    - debug: Enable debug output to see what's being detected
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
        text_pages = None
        all_sections = []
        method = "unknown"
        
        # ----------------------------
        # Try OCR if requested
        # ----------------------------
        if use_ocr:
            try:
                from pdf2image import convert_from_path
                import pytesseract
                
                print("🔍 Using OCR for text extraction...")
                images = convert_from_path(pdf_path, dpi=200)
                
                text_pages = []
                for i, image in enumerate(images):
                    text = pytesseract.image_to_string(image, lang='ara+eng')
                    if text.strip():
                        text_pages.append({
                            "page": i + 1,
                            "text": text
                        })
                        if debug and i == 0:
                            print(f"\n📄 OCR Sample (Page 1 first 500 chars):")
                            print(text[:500])
                            print("...\n")
                
                method = "ocr"
                print(f"✅ OCR extracted {len(text_pages)} pages")
                
            except ImportError:
                print("⚠️  OCR libraries not installed")
            except Exception as e:
                print(f"⚠️  OCR failed: {e}")
        
        # ----------------------------
        # Try Docling
        # ----------------------------
        if not text_pages:
            try:
                from docling.document_converter import DocumentConverter
                from docling.chunking import HybridChunker
                from docling.datamodel.pipeline_options import PdfPipelineOptions

                print("🔍 Using Docling for text extraction...")
                
                pipeline_options = PdfPipelineOptions()
                pipeline_options.do_table_structure = True
                pipeline_options.do_ocr = use_ocr
                
                converter = DocumentConverter(pipeline_options=pipeline_options)
                result = converter.convert(pdf_path, raises_on_error=False)

                if result.document:
                    doc = result.document
                    full_text = doc.export_to_markdown()
                    
                    if debug:
                        print(f"\n📄 Docling Sample (first 500 chars):")
                        print(full_text[:500])
                        print("...\n")
                    
                    # Extract sections with debug
                    all_sections = extract_sections_from_text(full_text, debug=debug)
                    
                    # Chunk
                    chunker = HybridChunker(
                        tokenizer="bert-base-uncased",
                        max_tokens=600,
                        overlap_tokens=100,
                    )
                    
                    chunks = list(chunker.chunk(doc))
                    chunks_data = [{
                        "text": c.text,
                        "meta": {"page": c.meta.get("page")}
                    } for c in chunks]
                    
                    enriched_chunks = assign_sections_to_chunks(chunks_data, all_sections)
                    
                    os.unlink(pdf_path)
                    
                    return {
                        "success": True,
                        "method": "docling",
                        "total_chunks": len(enriched_chunks),
                        "detected_sections": all_sections,
                        "sections_count": len(all_sections),
                        "sample_text": full_text[:300] if debug else None,
                        "chunks": enriched_chunks
                    }

            except Exception as e:
                print(f"Docling failed: {e}")
        
        # ----------------------------
        # PyPDF2 Fallback
        # ----------------------------
        if not text_pages:
            print("🔍 Using PyPDF2 for text extraction...")
            text_pages = extract_text_with_pypdf2(content)
            method = "pypdf2"
        
        if text_pages:
            # Combine all text
            all_text = "\n".join([p["text"] for p in text_pages])
            
            if debug:
                print(f"\n📄 PyPDF2 Sample (first 500 chars):")
                print(all_text[:500])
                print("...\n")
            
            # Extract sections with debug
            all_sections = extract_sections_from_text(all_text, debug=debug)
            
            # Create chunks
            chunks_data = chunk_plain_text(text_pages)
            
            # Assign sections
            enriched_chunks = assign_sections_to_chunks(chunks_data, all_sections)
            
            os.unlink(pdf_path)
            
            return {
                "success": True,
                "method": method,
                "total_pages": len(text_pages),
                "total_chunks": len(enriched_chunks),
                "detected_sections": all_sections,
                "sections_count": len(all_sections),
                "sample_text": all_text[:300] if debug else None,
                "chunks": enriched_chunks
            }

    finally:
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)

    return {
        "success": False,
        "error": "Failed to extract document"
    }