import os
from typing import Optional
import google.generativeai as genai
from providers.base import TranslationProvider
from utils.logger import setup_logger

logger = setup_logger(__name__)


class GeminiProvider(TranslationProvider):
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel("gemini-1.5-flash")
        else:
            self.model = None
    
    @staticmethod
    def is_available() -> bool:
        return bool(os.getenv("GEMINI_API_KEY"))
    
    async def translate(self, text: str, source_lang: str, target_lang: str, style: str = "natural") -> Optional[str]:
        if not self.model:
            return None
        try:
            response = await self.model.generate_content_async(text)
            if response and response.text:
                return response.text.strip()
            return None
        except Exception as e:
            logger.error(f"Gemini translation error: {e}")
            return None
    
    async def healthcheck(self) -> bool:
        if not self.model:
            return False
        try:
            response = await self.model.generate_content_async("test")
            return bool(response and response.text)
        except Exception:
            return False
    
    def provider_name(self) -> str:
        return "gemini"
    
    def estimated_cost_mode(self) -> str:
        return "free"
