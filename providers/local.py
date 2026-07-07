from typing import Optional
from providers.base import TranslationProvider
from utils.logger import setup_logger

logger = setup_logger(__name__)


class LocalProvider(TranslationProvider):
    def __init__(self):
        self.available = False
        try:
            import argostranslate.package
            import argostranslate.translate
            argostranslate.package.update_package_index()
            available_packages = argostranslate.package.get_available_packages()
            for pkg in available_packages:
                if pkg.from_code == "ar" and pkg.to_code == "fa":
                    self.available = True
                    break
            if not self.available:
                logger.warning("Arabic to Persian translation package not found")
        except Exception as e:
            logger.warning(f"Argos Translate initialization failed: {e}")
            self.available = False
    
    async def translate(self, text: str, source_lang: str, target_lang: str, style: str = "natural") -> Optional[str]:
        if not self.available:
            return None
        try:
            import argostranslate.translate
            from_code = self._map_language_code(source_lang)
            to_code = self._map_language_code(target_lang)
            translated = argostranslate.translate.translate(text, from_code, to_code)
            return translated if translated else None
        except Exception as e:
            logger.error(f"Local translation error: {e}")
            return None
    
    async def healthcheck(self) -> bool:
        return self.available
    
    def provider_name(self) -> str:
        return "local_argos"
    
    def estimated_cost_mode(self) -> str:
        return "free"
    
    def _map_language_code(self, code: str) -> str:
        mapping = {"ar": "ar", "fa": "fa", "en": "en"}
        return mapping.get(code, code)
