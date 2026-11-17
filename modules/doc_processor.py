"""
Document Processor Module for Wife God Agent
Offline OCR (EasyOCR/Tesseract), Image Compression, PDF Generation
"""

import asyncio
import logging
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

try:
    from PIL import Image, ImageEnhance, ImageFilter
except ImportError:
    Image = None

try:
    import easyocr
except ImportError:
    easyocr = None

try:
    import pytesseract
except ImportError:
    pytesseract = None

try:
    import img2pdf
except ImportError:
    img2pdf = None

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None
    np = None

logger = logging.getLogger("WifeGod.DocProcessor")


class DocType(Enum):
    AADHAAR = "aadhaar"
    PHOTO = "photo"
    SIGNATURE = "signature"
    MARKSHEET = "marksheet"
    INCOME_CERT = "income_certificate"
    CASTE_CERT = "caste_certificate"
    DOMICILE = "domicile"
    BIRTH_CERT = "birth_certificate"
    DEATH_CERT = "death_certificate"
    MARRIAGE_CERT = "marriage_certificate"
    PENSION = "pension"
    RATION_CARD = "ration_card"
    LAND_RECORD = "land_record"
    ADDRESS_PROOF = "address_proof"
    BANK_PASSBOOK = "bank_passbook"
    OTHER = "other"


class SizeLimit(Enum):
    SIGNATURE_KB = 50
    PHOTO_KB = 100
    AADHAAR_KB = 200
    DOCUMENT_KB = 500


@dataclass
class DocConfig:
    ocr_engine: str = "easyocr"
    easyocr_languages: list = field(default_factory=lambda: ["en", "hi"])
    tesseract_path: str = "tesseract"
    max_file_size_mb: int = 10
    compression_quality: int = 85
    output_dpi: int = 200
    size_limits: Dict[str, int] = field(default_factory=lambda: {
        "signature_kb": 50,
        "photo_kb": 100,
        "document_kb": 500,
        "aadhaar_kb": 200
    })
    supported_formats: list = field(default_factory=lambda: [
        ".jpg", ".jpeg", ".png", ".pdf", ".tiff", ".bmp"
    ])


@dataclass
class ProcessedDocument:
    original_path: str
    processed_path: str
    file_hash: str
    doc_type: DocType
    ocr_text: str
    structured_data: Dict
    size_kb: float
    compression_ratio: float
    pages: int
    status: str
    error: Optional[str] = None


class DocProcessor:
    """
    Document processor for eMitra:
    - Offline OCR (EasyOCR/Tesseract)
    - Image compression to exact byte limits
    - PDF generation
    - Document validation
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = DocConfig(**config) if isinstance(config, dict) else config
        self._ocr_reader = None
        self._tesseract_available = False
        self._size_limits = {
            DocType.SIGNATURE: SizeLimit.SIGNATURE_KB.value * 1024,
            DocType.PHOTO: SizeLimit.PHOTO_KB.value * 1024,
            DocType.AADHAAR: SizeLimit.AADHAAR_KB.value * 1024,
        }
        # Default for other doc types
        for dt in DocType:
            if dt not in self._size_limits:
                self._size_limits[dt] = SizeLimit.DOCUMENT_KB.value * 1024

    async def initialize(self):
        """Initialize OCR engines"""
        logger.info("Initializing DocProcessor...")

        # Initialize EasyOCR
        if self.config.ocr_engine == "easyocr" and easyocr:
            try:
                loop = asyncio.get_event_loop()
                self._ocr_reader = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: easyocr.Reader(self.config.easyocr_languages, gpu=False)
                )
                logger.info("EasyOCR initialized")
            except Exception as e:
                logger.error(f"EasyOCR init failed: {e}")

        # Check Tesseract
        if pytesseract:
            try:
                pytesseract.pytesseract.tesseract_cmd = self.config.tesseract_path
                version = pytesseract.get_tesseract_version()
                self._tesseract_available = True
                logger.info(f"Tesseract available: {version}")
            except Exception as e:
                logger.warning(f"Tesseract not available: {e}")

        if not self._ocr_reader and not self._tesseract_available:
            logger.warning("No OCR engine available!")

        logger.info("DocProcessor initialized")

    def _get_size_limit(self, doc_type: DocType) -> int:
        """Get size limit in bytes for document type"""
        return self._size_limits.get(doc_type, SizeLimit.DOCUMENT_KB.value * 1024)

    def _detect_doc_type(self, file_path: str, ocr_text: str = "") -> DocType:
        """Detect document type from filename and OCR text"""
        filename = Path(file_path).stem.lower()
        text_lower = ocr_text.lower()

        # Filename-based detection
        if any(kw in filename for kw in ['sign', 'signature']):
            return DocType.SIGNATURE
        if any(kw in filename for kw in ['photo', 'pic', 'image']):
            return DocType.PHOTO
        if any(kw in filename for kw in ['aadhaar', 'aadhar', 'uid']):
            return DocType.AADHAAR
        if any(kw in filename for kw in ['marksheet', 'mark', 'result']):
            return DocType.MARKSHEET
        if any(kw in filename for kw in ['income', 'salary']):
            return DocType.INCOME_CERT
        if any(kw in filename for kw in ['caste', 'jati']):
            return DocType.CASTE_CERT
        if any(kw in filename for kw in ['domicile', 'niwas']):
            return DocType.DOMICILE
        if any(kw in filename for kw in ['birth', 'janam']):
            return DocType.BIRTH_CERT
        if any(kw in filename for kw in ['death', 'mrityu']):
            return DocType.DEATH_CERT
        if any(kw in filename for kw in ['marriage', 'vivah']):
            return DocType.MARRIAGE_CERT
        if any(kw in filename for kw in ['pension']):
            return DocType.PENSION
        if any(kw in filename for kw in ['ration']):
            return DocType.RATION_CARD
        if any(kw in filename for kw in ['land', 'khata', 'khasra']):
            return DocType.LAND_RECORD
        if any(kw in filename for kw in ['address', 'pata']):
            return DocType.ADDRESS_PROOF
        if any(kw in filename for kw in ['bank', 'passbook']):
            return DocType.BANK_PASSBOOK

        # OCR text-based detection
        if any(kw in text_lower for kw in ['आधार', 'aadhaar', 'uidai']):
            return DocType.AADHAAR
        if any(kw in text_lower for kw in ['अंकतालिका', 'marksheet', 'result']):
            return DocType.MARKSHEET
        if any(kw in text_lower for kw in ['आय प्रमाण', 'income certificate']):
            return DocType.INCOME_CERT
        if any(kw in text_lower for kw in ['जाति प्रमाण', 'caste certificate']):
            return DocType.CASTE_CERT
        if any(kw in text_lower for kw in ['निवास प्रमाण', 'domicile']):
            return DocType.DOMICILE
        if any(kw in text_lower for kw in ['जन्म प्रमाण', 'birth certificate']):
            return DocType.BIRTH_CERT
        if any(kw in text_lower for kw in ['मृत्यु प्रमाण', 'death certificate']):
            return DocType.DEATH_CERT

        return DocType.OTHER

    async def process_document(self, file_path: str, doc_type_hint: str = "") -> ProcessedDocument:
        """Process a single document"""
        file_path = Path(file_path)
        if not file_path.exists():
            return ProcessedDocument(
                original_path=str(file_path),
                processed_path="",
                file_hash="",
                doc_type=DocType.OTHER,
                ocr_text="",
                structured_data={},
                size_kb=0,
                compression_ratio=0,
                pages=0,
                status="error",
                error="File not found"
            )

        logger.info(f"Processing document: {file_path.name}")

        # Calculate file hash
        file_hash = self._calculate_hash(file_path)

        # Read image
        image = self._load_image(file_path)
        if image is None:
            return ProcessedDocument(
                original_path=str(file_path),
                processed_path="",
                file_hash=file_hash,
                doc_type=DocType.OTHER,
                ocr_text="",
                structured_data={},
                size_kb=0,
                compression_ratio=0,
                pages=0,
                status="error",
                error="Failed to load image"
            )

        # OCR
        ocr_text = await self._extract_text(image)

        # Detect document type
        doc_type = self._detect_doc_type(str(file_path), ocr_text)
        if doc_type_hint:
            try:
                doc_type = DocType(doc_type_hint.lower())
            except ValueError:
                pass

        # Compress to size limit
        processed_image, compression_ratio = self._compress_to_limit(image, doc_type)

        # Save processed image
        output_path = await self._save_processed(processed_image, file_path, doc_type)

        # Convert to PDF if needed
        pdf_path = await self._convert_to_pdf(output_path, doc_type)

        # Determine final path
        final_path = pdf_path if pdf_path else output_path

        # Get final size
        final_size_kb = os.path.getsize(final_path) / 1024

        # Create structured data placeholder (filled by LLM later)
        structured_data = {
            "doc_type": doc_type.value,
            "ocr_text_preview": ocr_text[:500],
            "original_size_kb": os.path.getsize(file_path) / 1024,
            "processed_size_kb": final_size_kb,
            "compression_ratio": compression_ratio,
            "meets_size_limit": final_size_kb * 1024 <= self._get_size_limit(doc_type)
        }

        return ProcessedDocument(
            original_path=str(file_path),
            processed_path=final_path,
            file_hash=file_hash,
            doc_type=doc_type,
            ocr_text=ocr_text,
            structured_data=structured_data,
            size_kb=final_size_kb,
            compression_ratio=compression_ratio,
            pages=1,
            status="success"
        )

    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file"""
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _load_image(self, file_path: Path) -> Optional[Image.Image]:
        """Load image from file"""
        if not Image:
            return None

        try:
            if file_path.suffix.lower() == '.pdf':
                # For PDF, convert first page to image
                # This would need pdf2image or similar
                logger.warning("PDF processing not fully implemented")
                return None
            return Image.open(file_path).convert('RGB')
        except Exception as e:
            logger.error(f"Failed to load image: {e}")
            return None

    async def _extract_text(self, image: Image.Image) -> str:
        """Extract text using OCR"""
        texts = []

        # Try EasyOCR first
        if self._ocr_reader:
            try:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: self._ocr_reader.readtext(np.array(image))
                )
                for detection in result:
                    texts.append(detection[1])
            except Exception as e:
                logger.warning(f"EasyOCR failed: {e}")

        # Fallback to Tesseract
        if not texts and self._tesseract_available:
            try:
                text = pytesseract.image_to_string(
                    image,
                    lang='hin+eng',
                    config='--psm 6'
                )
                if text.strip():
                    texts.append(text)
            except Exception as e:
                logger.warning(f"Tesseract failed: {e}")

        return "\n".join(texts)

    def _compress_to_limit(self, image: Image.Image, doc_type: DocType) -> Tuple[Image.Image, float]:
        """Compress image to meet size limit"""
        limit_bytes = self._get_size_limit(doc_type)
        original_size = 0

        # Get original size estimate
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            image.save(tmp.name, 'JPEG', quality=95)
            original_size = os.path.getsize(tmp.name)
            os.unlink(tmp.name)

        if original_size <= limit_bytes:
            return image, 1.0

        # Binary search for quality
        low, high = 10, 95
        best_image = image
        best_quality = 95

        while low <= high:
            mid = (low + high) // 2
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                image.save(tmp.name, 'JPEG', quality=mid, optimize=True)
                size = os.path.getsize(tmp.name)
                os.unlink(tmp.name)

            if size <= limit_bytes:
                best_quality = mid
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
                    image.save(tmp.name, 'JPEG', quality=mid, optimize=True)
                    best_image = Image.open(tmp.name).copy()
                os.unlink(tmp.name)
                low = mid + 1
            else:
                high = mid - 1

        compression_ratio = original_size / (limit_bytes if original_size > limit_bytes else original_size)
        return best_image, compression_ratio

    async def _save_processed(self, image: Image.Image, original_path: Path, doc_type: DocType) -> str:
        """Save processed image"""
        output_dir = Path(self.config.output_folder) if hasattr(self.config, 'output_folder') else Path("./output")
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{doc_type.value}_{timestamp}_{original_path.stem}.jpg"
        output_path = output_dir / filename

        # Save with optimization
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: image.save(
                output_path,
                'JPEG',
                quality=self.config.compression_quality,
                optimize=True,
                dpi=(self.config.output_dpi, self.config.output_dpi)
            )
        )

        return str(output_path)

    async def _convert_to_pdf(self, image_path: str, doc_type: DocType) -> Optional[str]:
        """Convert image to PDF if required"""
        if not img2pdf:
            return None

        # eMitra often requires PDF for documents
        pdf_required = doc_type in [
            DocType.AADHAAR, DocType.MARKSHEET, DocType.INCOME_CERT,
            DocType.CASTE_CERT, DocType.DOMICILE, DocType.BIRTH_CERT,
            DocType.DEATH_CERT, DocType.MARRIAGE_CERT, DocType.PENSION,
            DocType.RATION_CARD, DocType.LAND_RECORD
        ]

        if not pdf_required:
            return None

        try:
            pdf_path = image_path.replace('.jpg', '.pdf').replace('.png', '.pdf')
            with open(pdf_path, "wb") as f:
                f.write(img2pdf.convert(image_path))
            return pdf_path
        except Exception as e:
            logger.error(f"PDF conversion failed: {e}")
            return None

    async def process_batch(self, file_paths: List[str]) -> Dict[str, Any]:
        """Process multiple documents"""
        results = []
        for fp in file_paths:
            try:
                result = await self.process_document(fp)
                results.append({
                    "file": fp,
                    "status": result.status,
                    "processed_path": result.processed_path,
                    "doc_type": result.doc_type.value,
                    "size_kb": result.size_kb,
                    "ocr_text": result.ocr_text[:200] if result.ocr_text else ""
                })
            except Exception as e:
                results.append({"file": fp, "status": "error", "error": str(e)})

        return {"results": results, "total": len(results), "successful": sum(1 for r in results if r.get("status") == "success")}

    async def validate_document(self, file_path: str, doc_type: DocType) -> Dict[str, Any]:
        """Validate document meets requirements"""
        result = await self.process_document(file_path, doc_type.value)

        validation = {
            "valid": result.status == "success",
            "size_ok": result.size_kb * 1024 <= self._get_size_limit(doc_type),
            "size_kb": result.size_kb,
            "limit_kb": self._get_size_limit(doc_type) / 1024,
            "has_ocr_text": len(result.ocr_text) > 10,
            "meets_requirements": True
        }

        if not validation["size_ok"]:
            validation["meets_requirements"] = False
            validation["error"] = f"File size {validation['size_kb']:.1f}KB exceeds limit {validation['limit_kb']}KB"

        if not validation["has_ocr_text"]:
            validation["meets_requirements"] = False
            validation["error"] = "Document text not readable. Please provide clearer image."

        return validation

    def get_status(self) -> Dict[str, Any]:
        return {
            "ocr_engine": self.config.ocr_engine,
            "easyocr_ready": self._ocr_reader is not None,
            "tesseract_ready": self._tesseract_available,
            "img2pdf_ready": img2pdf is not None,
            "size_limits": {k.value: v for k, v in self._size_limits.items()}
        }