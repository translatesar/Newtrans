import asyncio
from pathlib import Path
from typing import Optional
import aiofiles
from docx import Document
from PyPDF2 import PdfReader
from utils.logger import setup_logger

logger = setup_logger(__name__)


class FileHandler:
    SUPPORTED_EXTENSIONS = {".txt", ".md", ".docx", ".pdf"}
    
    def is_supported(self, filename: str) -> bool:
        ext = Path(filename).suffix.lower()
        return ext in self.SUPPORTED_EXTENSIONS
    
    async def extract_text(self, file_path: str) -> Optional[str]:
        ext = Path(file_path).suffix.lower()
        
        try:
            if ext in {".txt", ".md"}:
                async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                    text = await f.read()
                return text
            
            elif ext == ".docx":
                loop = asyncio.get_event_loop()
                text = await loop.run_in_executor(None, self._extract_docx, file_path)
                return text
            
            elif ext == ".pdf":
                loop = asyncio.get_event_loop()
                text = await loop.run_in_executor(None, self._extract_pdf, file_path)
                return text
            
            else:
                logger.warning(f"Unsupported file format: {ext}")
                return None
                
        except Exception as e:
            logger.error(f"Text extraction error: {e}", exc_info=True)
            return None
    
    def _extract_docx(self, file_path: str) -> str:
        doc = Document(file_path)
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        return "\n\n".join(paragraphs)
    
    def _extract_pdf(self, file_path: str) -> str:
        reader = PdfReader(file_path)
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        return "\n\n".join(text_parts)
