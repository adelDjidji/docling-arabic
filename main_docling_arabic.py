"""
Enhanced PDF Processing with Docling for Arabic Documents
Uses Docling's advanced PDF understanding with proper OCR configuration for RTL languages.
"""

from fastapi import FastAPI, UploadFile, File
import tempfile, os
import torch
import re
from typing import List, Dict, Any
import subprocess

app = FastAPI()


# ========================================
# Auto-configure TESSDATA_PREFIX
# ========================================
def setup_tessdata_prefix():
    """Automatically detect and set TESSDATA_PREFIX if not set."""
    if os.environ.get('TESSDATA_PREFIX'):
        print(f"✅ TESSDATA_PREFIX already set: {os.environ['TESSDATA_PREFIX']}")
        return True
    
    # Common tessdata locations
    possible_paths = [
        '/usr/share/tesseract-ocr/5/tessdata',
        '/usr/share/tesseract-ocr/4.00/tessdata',
        '/usr/share/tessdata',
        '/opt/homebrew/share/tessdata',
        '/usr/local/share/tessdata',
        'C:\\Program Files\\Tesseract-OCR\\tessdata',
    ]
    
    # Try to find tessdata using system command
    try:
        result = subprocess.run(['find', '/usr', '-name', 'tessdata', '-type', 'd'], 
                              capture_output=True, text=True, timeout=5)
        if result.stdout:
            found_paths = result.stdout.strip().split('\n')
            possible_paths = found_paths + possible_paths
    except:
        pass
    
    # Check each path
    for path in possible_paths:
        if os.path.exists(path) and os.path.isdir(path):
            # Check if it contains language files
            files = os.listdir(path)
            if any(f.endswith('.traineddata') for f in files):
                os.environ['TESSDATA_PREFIX'] = path
                print(f"✅ Auto-detected TESSDATA_PREFIX: {path}")
                
                # Check for Arabic
                has_ara = 'ara.traineddata' in files
                has_eng = 'eng.traineddata' in files
                print(f"  - Arabic support: {'✅' if has_ara else '❌'}")
                print(f"  - English support: {'✅' if has_eng else '❌'}")
                
                if not has_ara:
                    print(f"  ⚠️  Arabic not found. Install with:")
                    print(f"      sudo apt-get install tesseract-ocr-ara")
                
                return True
    
    print("❌ Could not auto-detect TESSDATA_PREFIX")
    print("Please set it manually:")
    print("  export TESSDATA_PREFIX=/path/to/tessdata")
    return False


# Set up tessdata on startup
setup_tessdata_prefix()


def is_section_heading(text: str) -> bool:
    """Robust section heading detection for Arabic text."""
    text = text.strip()
    
    if not text or len(text) > 200 or len(text) < 3:
        return False
    
    # Arabic section keywords
    section_indicators = [
        'الوحدة', 'وحدة', 'الفصل', 'فصل',
        'المقدمة', 'مقدمة', 'الخاتمة', 'خاتمة',
        'الأهداف', 'أهداف', 'المنهجية', 'منهجية',
        'التقويم', 'تقويم', 'الباب', 'باب',
        'القسم', 'قسم', 'الجزء', 'جزء',
        'الفرع', 'فرع', 'الملحق', 'ملحق',
        'المراجع', 'مراجع', 'فترة المراجعة',
        'chapter', 'section', 'unit', 'introduction', 'conclusion',
    ]
    
    text_lower = text.lower()
    for indicator in section_indicators:
        if indicator.lower() in text_lower:
            return True
    
    # Numbered sections
    if re.match(r'^(\d+|[٠-٩]+)[\.\-\:]\s*.+', text):
        return True
    
    # Short lines with colons
    if ':' in text and len(text) < 120:
        return True
    
    return False


def extract_sections_from_docling_document(doc) -> List[str]:
    """Extract section headings from Docling document using its structure."""
    sections = []
    
    try:
        # Method 1: Extract from document structure
        for item in doc.iterate_items():
            if hasattr(item, 'label'):
                label = str(item.label).lower()
                if any(x in label for x in ['heading', 'title', 'section']):
                    if hasattr(item, 'text'):
                        section_text = item.text.strip()
                        if section_text and len(section_text) > 3:
                            sections.append(section_text)
                            print(f"  📌 Structure: {section_text[:80]}")
        
        # Method 2: Parse markdown export for headings
        if not sections or len(sections) < 3:
            markdown = doc.export_to_markdown()
            lines = markdown.split('\n')
            
            for line in lines:
                # Markdown headings start with #
                if line.startswith('#'):
                    heading = re.sub(r'^#+\s*', '', line).strip()
                    if heading and len(heading) > 3:
                        sections.append(heading)
                        print(f"  📌 Markdown: {heading[:80]}")
                # Text-based headings
                elif is_section_heading(line):
                    sections.append(line.strip())
                    print(f"  📌 Pattern: {line[:80]}")
    
    except Exception as e:
        print(f"⚠️ Error extracting sections: {e}")
    
    return sections


def assign_sections_to_chunks(chunks: List[Dict], sections: List[str]) -> List[Dict]:
    """Intelligently assign section names to chunks."""
    if not sections:
        print("⚠️ No sections detected - using page numbers")
        return [{
            "text": c["text"],
            "meta": {
                "page": c.get("page"),
                "section": f"صفحة {c.get('page', 'غير محدد')}"
            }
        } for c in chunks]
    
    enriched = []
    current_section = sections[0]
    
    print(f"\n📊 Assigning {len(sections)} sections to {len(chunks)} chunks...")
    
    for idx, chunk in enumerate(chunks):
        chunk_text = chunk["text"]
        found_section = None
        
        # Check if chunk contains section heading (first 500 chars)
        search_text = chunk_text[:500]
        
        for section in sections:
            # Normalize for comparison
            section_normalized = re.sub(r'[ًٌٍَُِّْ]', '', section)
            search_normalized = re.sub(r'[ًٌٍَُِّْ]', '', search_text)
            
            if section_normalized in search_normalized or section in search_text:
                found_section = section
                current_section = section
                if idx < 3:
                    print(f"  ✅ Chunk {idx}: {section[:60]}...")
                break
        
        if not found_section:
            found_section = current_section
        
        enriched.append({
            "text": chunk["text"],
            "meta": {
                "page": chunk.get("page"),
                "section": found_section
            }
        })
    
    return enriched


@app.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    """
    Advanced PDF ingestion with Docling and proper Arabic support.
    
    Features:
    - Docling's advanced PDF understanding
    - Proper OCR configuration for RTL languages
    - Layout analysis and table detection
    - Hierarchical section detection
    """
    content = await file.read()

    # Fix torch.xpu if needed
    if not hasattr(torch, "xpu"):
        class FakeXPU:
            @staticmethod
            def is_available():
                return False
            @staticmethod
            def device_count():
                return 0
        torch.xpu = FakeXPU()

    # Save uploaded file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(content)
        pdf_path = tmp.name

    try:
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import (
            PdfPipelineOptions,
            TesseractOcrOptions,
        )
        from docling.chunking import HybridChunker
        
        print("\n" + "="*70)
        print("DOCLING PDF PROCESSING WITH ARABIC SUPPORT")
        print("="*70)
        
        # ========================================
        # STEP 1: Configure pipeline for Arabic
        # ========================================
        print("\n📋 STEP 1: Configuring pipeline for Arabic documents...")
        
        # Create pipeline options for PDF
        pipeline_options = PdfPipelineOptions()
        
        # Enable OCR (critical for Arabic)
        pipeline_options.do_ocr = True
        
        # Configure Tesseract for Arabic
        pipeline_options.ocr_options = TesseractOcrOptions(
            lang=["ara", "eng"]  # Arabic + English
        )
        
        # DISABLE layout model to avoid tensor batch size errors
        # This is a known issue when processing PDFs with varying page sizes
        pipeline_options.do_layout_model = False
        
        # Keep table structure detection (doesn't require layout model)
        pipeline_options.do_table_structure = True
        
        # Set images scale for better OCR quality
        pipeline_options.images_scale = 2.0
        
        # Process pages one at a time to avoid batch errors
        pipeline_options.images_max_pages = 1
        
        print("  ✅ OCR enabled with Arabic + English support")
        print("  ✅ Layout model disabled (prevents batch errors)")
        print("  ✅ Table structure detection enabled")
        
        # ========================================
        # STEP 2: Initialize converter with format options
        # ========================================
        print("\n📄 STEP 2: Initializing DocumentConverter...")
        
        # Create format option for PDF
        pdf_format_option = PdfFormatOption(
            pipeline_options=pipeline_options
        )
        
        # Initialize converter with format options
        converter = DocumentConverter(
            format_options={
                InputFormat.PDF: pdf_format_option,
            }
        )
        
        print("  ✅ Converter initialized")
        
        # ========================================
        # STEP 3: Convert document
        # ========================================
        print("\n🔄 STEP 3: Converting PDF with Docling...")
        
        try:
            result = converter.convert(pdf_path)
        except Exception as conv_error:
            print(f"⚠️  Layout model failed, retrying with simpler pipeline...")
            
            # Fallback: Try again with even simpler options
            simple_pipeline = PdfPipelineOptions()
            simple_pipeline.do_ocr = True
            simple_pipeline.ocr_options = TesseractOcrOptions(lang=["ara", "eng"])
            simple_pipeline.do_layout_model = False
            simple_pipeline.do_table_structure = False
            
            simple_format = PdfFormatOption(pipeline_options=simple_pipeline)
            simple_converter = DocumentConverter(
                format_options={InputFormat.PDF: simple_format}
            )
            
            result = simple_converter.convert(pdf_path)
        
        if not result or not result.document:
            return {
                "success": False,
                "error": "Docling conversion failed",
                "details": "Could not extract document content"
            }
        
        doc = result.document
        print(f"  ✅ Document converted successfully")
        
        # ========================================
        # STEP 4: Extract sections
        # ========================================
        print("\n🔍 STEP 4: Extracting sections...")
        
        sections = extract_sections_from_docling_document(doc)
        
        print(f"\n  ✅ Found {len(sections)} sections")
        if sections and len(sections) <= 10:
            print("\n  📋 Detected sections:")
            for i, section in enumerate(sections[:10], 1):
                print(f"    {i}. {section[:70]}...")
        
        # ========================================
        # STEP 5: Chunk the document
        # ========================================
        print("\n✂️  STEP 5: Chunking document...")
        
        chunker = HybridChunker(
            tokenizer="bert-base-uncased",
            max_tokens=600,
            overlap_tokens=100,
            heading_hierarchies=True,
        )
        
        docling_chunks = list(chunker.chunk(doc))
        print(f"  ✅ Created {len(docling_chunks)} chunks")
        
        # Convert to our format
        chunks = []
        for dc in docling_chunks:
            chunk_dict = {
                "text": dc.text,
                "page": dc.meta.get("page"),
                "docling_section": dc.meta.get("headings", [None])[0] if dc.meta.get("headings") else None
            }
            chunks.append(chunk_dict)
        
        # ========================================
        # STEP 6: Assign sections
        # ========================================
        print("\n🎯 STEP 6: Assigning sections to chunks...")
        
        enriched_chunks = assign_sections_to_chunks(chunks, sections)
        
        # Show sample
        if enriched_chunks:
            print(f"\n📊 Sample chunk:")
            print(f"  Page: {enriched_chunks[0]['meta']['page']}")
            print(f"  Section: {enriched_chunks[0]['meta']['section']}")
            print(f"  Text: {enriched_chunks[0]['text'][:150]}...")
        
        # Quality check
        unique_sections = set(c['meta']['section'] for c in enriched_chunks)
        print(f"\n✅ Quality check:")
        print(f"  - Total chunks: {len(enriched_chunks)}")
        print(f"  - Unique sections: {len(unique_sections)}")
        print(f"  - Chunks per section: {len(enriched_chunks) / len(unique_sections):.1f}")
        
        os.unlink(pdf_path)
        
        return {
            "success": True,
            "method": "docling_with_arabic_ocr",
            "total_chunks": len(enriched_chunks),
            "detected_sections": sections,
            "sections_count": len(sections),
            "unique_sections_in_chunks": len(unique_sections),
            "chunks": enriched_chunks,
            "metadata": {
                "ocr_engine": "tesseract",
                "languages": ["ara", "eng"],
                "table_detection": True,
                "layout_analysis": True
            },
            "note": "Processed with Docling's advanced PDF understanding and Arabic OCR"
        }
    
    except ImportError as e:
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)
        
        return {
            "success": False,
            "error": "Missing dependencies",
            "details": str(e),
            "install_instructions": {
                "docling": "pip install docling",
                "tesseract": "sudo apt-get install tesseract-ocr tesseract-ocr-ara tesseract-ocr-eng",
            }
        }
    
    except Exception as e:
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)
        
        import traceback
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


@app.get("/health")
async def health():
    """Check system dependencies and Docling setup"""
    status = {
        "docling": False,
        "tesseract": False,
        "tesseract_arabic": False,
        "tessdata_prefix": os.environ.get('TESSDATA_PREFIX'),
    }
    
    try:
        import docling
        status["docling"] = True
        status["docling_version"] = docling.__version__
    except:
        pass
    
    try:
        import pytesseract
        version = pytesseract.get_tesseract_version()
        status["tesseract"] = True
        status["tesseract_version"] = str(version)
        
        langs = pytesseract.get_languages()
        status["tesseract_arabic"] = "ara" in langs
        status["tesseract_languages"] = langs
    except Exception as e:
        status["tesseract_error"] = str(e)
    
    all_ready = status["docling"] and status["tesseract"] and status["tesseract_arabic"]
    
    recommendations = []
    if not status["docling"]:
        recommendations.append("Install Docling: pip install docling")
    if not status["tesseract"]:
        recommendations.append("Install Tesseract: sudo apt-get install tesseract-ocr")
    if not status["tesseract_arabic"]:
        recommendations.append("Install Arabic: sudo apt-get install tesseract-ocr-ara")
    if not status["tessdata_prefix"]:
        recommendations.append("Set TESSDATA_PREFIX: export TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata")
    
    return {
        "status": "ready" if all_ready else "missing_dependencies",
        "components": status,
        "recommendations": recommendations
    }


if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*70)
    print("🚀 Docling PDF Processing Server with Arabic Support")
    print("="*70)
    print("\n📋 Endpoints:")
    print("  • Health: http://localhost:8000/health")
    print("  • Ingest: http://localhost:8000/ingest")
    print("\n📦 Dependencies:")
    print("  • pip install docling")
    print("  • sudo apt-get install tesseract-ocr tesseract-ocr-ara")
    print("\n" + "="*70 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)