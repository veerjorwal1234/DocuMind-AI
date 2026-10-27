import os
import re
from typing import List, Optional
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from PIL import Image

def clean_extracted_text(text: str) -> str:
    """
    Normalize and clean extracted text.
    Removes null bytes, non-printable control characters, and common encoding artifacts
    while preserving meaningful formatting and punctuation.
    """
    if not text:
        return ""
    
    # Remove null bytes and non-printable control characters (keep \n, \r, \t)
    cleaned = "".join(
        ch for ch in text 
        if ch in "\n\r\t " or (ch.isprintable() and ord(ch) != 0 and ord(ch) != 0xFFFD)
    )
    
    # Normalize common Unicode ligatures and special quotes/dashes
    replacements = {
        "ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl",
        "’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-",
        "\xa0": " ", "\u200b": ""
    }
    for orig, rep in replacements.items():
        cleaned = cleaned.replace(orig, rep)
        
    # Standardize line breaks
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    
    # Collapse 3+ consecutive newlines to double newline
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    
    # Collapse multiple consecutive horizontal spaces
    cleaned = re.sub(r'[ \t]{2,}', ' ', cleaned)
    
    return cleaned.strip()

def is_text_usable(text: str, min_alphanumeric: int = 30) -> bool:
    """
    Assess whether extracted text is intelligible and sufficiently complete,
    or if it indicates a scanned/empty/corrupted page requiring OCR fallback.
    """
    if not text:
        return False
    # Count printable alphanumeric characters
    alnum_count = sum(1 for ch in text if ch.isalnum())
    if alnum_count < min_alphanumeric:
        return False
        
    # Check if text is dominated by raw glyph identifiers like (cid:...)
    cid_matches = len(re.findall(r'\(cid:\d+\)', text))
    if cid_matches > 5 and cid_matches > (len(text.split()) * 0.3):
        return False
        
    return True

def extract_ocr_from_image(image: Image.Image) -> str:
    """
    Extract text from a PIL Image using available OCR engines.
    Uses native Windows OCR (winocr) first, with fallback to pytesseract.
    """
    # 1. Try winocr on Windows (Fast, built-in, no external executable required)
    try:
        import winocr
        res = winocr.recognize_pil_sync(image)
        if isinstance(res, dict) and "text" in res and res["text"]:
            text = res["text"].strip()
            if text:
                return text
    except Exception:
        pass

    # 2. Try pytesseract as cross-platform fallback
    try:
        import pytesseract
        text = pytesseract.image_to_string(image)
        if text and text.strip():
            return text.strip()
    except Exception:
        pass

    return ""

class DocumentProcessor:
    """Handles document loading, multi-engine text extraction, OCR fallback, and chunking."""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize the document processor.
        
        Args:
            chunk_size: Size of chunks in characters
            chunk_overlap: Overlap between chunks in characters
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", "? ", "! ", "; ", " ", ""]
        )
        
    def _extract_page_with_pdfium_and_ocr(self, file_path: str, page_index: int) -> tuple[str, str]:
        """
        Extract text from a specific PDF page using pypdfium2, with automatic OCR fallback.
        Returns (extracted_text, extraction_method).
        """
        try:
            import pypdfium2 as pdfium
            pdf = pdfium.PdfDocument(file_path)
            if page_index >= len(pdf):
                return "", "failed"
                
            page = pdf[page_index]
            
            # Try native PDFium text extraction first
            textpage = page.get_textpage()
            native_text = textpage.get_text_range()
            cleaned_native = clean_extracted_text(native_text)
            
            if is_text_usable(cleaned_native):
                return cleaned_native, "pdfium"
                
            # If native text is unusable or empty, render page image for OCR
            image = page.render(scale=2.0).to_pil()
            ocr_text = extract_ocr_from_image(image)
            cleaned_ocr = clean_extracted_text(ocr_text)
            
            if cleaned_ocr:
                return cleaned_ocr, "ocr"
                
            # Return whatever native text was extracted if OCR produced nothing
            return cleaned_native or "(No readable text detected on this page)", "native_unclear"
        except Exception:
            return "", "error"

    def load_pdf(self, file_path: str) -> List[Document]:
        """
        Load a PDF document, extract text with encoding repairs and OCR fallback.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            List of document pages with rich metadata
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        filename = os.path.basename(file_path)
        loader = PyPDFLoader(file_path)
        
        try:
            documents = loader.load()
        except Exception as e:
            # If PyPDF fails entirely on a malformed PDF, attempt pypdfium2 directly
            documents = []
            try:
                import pypdfium2 as pdfium
                pdf = pdfium.PdfDocument(file_path)
                for idx in range(len(pdf)):
                    text, method = self._extract_page_with_pdfium_and_ocr(file_path, idx)
                    documents.append(Document(
                        page_content=text,
                        metadata={
                            "source": filename,
                            "page": idx + 1,
                            "extraction_method": method,
                            "ocr_applied": (method == "ocr")
                        }
                    ))
                return documents
            except Exception:
                raise Exception(f"Error loading PDF: {str(e)}")
        
        # Enhance loaded documents with encoding cleanup and OCR fallback when needed
        for idx, doc in enumerate(documents):
            # Ensure metadata exists
            if not hasattr(doc, "metadata") or doc.metadata is None:
                doc.metadata = {}
            doc.metadata["source"] = filename
            if "page" not in doc.metadata:
                doc.metadata["page"] = idx + 1
            else:
                # Normalize page index to 1-based numbering if 0-indexed
                if doc.metadata["page"] == 0:
                    doc.metadata["page"] = 1
                    
            content = getattr(doc, "page_content", "")
            if isinstance(content, str):
                cleaned = clean_extracted_text(content)
                if is_text_usable(cleaned):
                    doc.page_content = cleaned
                    doc.metadata["extraction_method"] = "native"
                    doc.metadata["ocr_applied"] = False
                else:
                    # Attempt PDFium extraction and OCR fallback
                    enhanced_text, method = self._extract_page_with_pdfium_and_ocr(file_path, idx)
                    if enhanced_text:
                        doc.page_content = enhanced_text
                        doc.metadata["extraction_method"] = method
                        doc.metadata["ocr_applied"] = (method == "ocr")
                    else:
                        doc.page_content = cleaned
                        doc.metadata["extraction_method"] = "native_insufficient"
                        doc.metadata["ocr_applied"] = False
            
            doc.metadata["char_count"] = len(doc.page_content) if isinstance(doc.page_content, str) else 0

        return documents

    def load_image(self, file_path: str) -> List[Document]:
        """
        Load an image-based document (.png, .jpg, etc.) using OCR.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            List of Document objects
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        filename = os.path.basename(file_path)
        try:
            image = Image.open(file_path)
            ocr_text = extract_ocr_from_image(image)
            cleaned = clean_extracted_text(ocr_text)
            
            metadata = {
                "source": filename,
                "page": 1,
                "extraction_method": "ocr",
                "ocr_applied": True,
                "char_count": len(cleaned)
            }
            return [Document(page_content=cleaned, metadata=metadata)]
        except Exception as e:
            raise Exception(f"Error processing image document: {str(e)}")

    def chunk_documents(self, documents: List[Document]) -> List[Document]:
        """
        Split documents into semantically coherent chunks while preserving metadata.
        
        Args:
            documents: List of documents to chunk
            
        Returns:
            List of chunked documents
        """
        chunks = self.text_splitter.split_documents(documents)
        # Enrich each chunk with chunk index metadata
        for idx, chunk in enumerate(chunks):
            if hasattr(chunk, "metadata"):
                chunk.metadata["chunk_index"] = idx + 1
                chunk.metadata["char_count"] = len(chunk.page_content) if isinstance(chunk.page_content, str) else 0
        return chunks
    
    def process_document(self, file_path: str) -> List[Document]:
        """
        Process a document: load (with OCR fallback) and chunk it.
        
        Args:
            file_path: Path to the document
            
        Returns:
            List of chunked documents with rich metadata
        """
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp']:
            documents = self.load_image(file_path)
        else:
            documents = self.load_pdf(file_path)
        return self.chunk_documents(documents)