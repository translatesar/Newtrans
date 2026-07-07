from typing import Dict, Any, Optional
from providers.base import TranslationProvider
from providers.gemini import GeminiProvider
from providers.local import LocalProvider
from prompts.translation_prompts import (
    TRANSLATION_SYSTEM_PROMPT,
    TRANSLATION_STYLE_PROMPTS,
    EDITORIAL_REWRITE_PROMPT,
    QUALITY_CHECK_PROMPT,
)
from utils.logger import setup_logger

logger = setup_logger(__name__)


class TranslationService:
    def __init__(self):
        self.providers: list[TranslationProvider] = []
        
        if GeminiProvider.is_available():
            self.providers.append(GeminiProvider())
            logger.info("Gemini provider added")
        
        self.providers.append(LocalProvider())
        logger.info("Local provider added as fallback")
        
        if not self.providers:
            logger.error("No translation providers available!")
    
    async def translate(self, text: str, source_lang: str, target_lang: str, style: str = "natural") -> Dict[str, Any]:
        faithful_result = await self._perform_translation(
            text=text, source_lang=source_lang, target_lang=target_lang,
            style=style, pass_type="faithful",
        )
        
        if not faithful_result:
            raise Exception("Translation failed - no provider available")
        
        faithful_translation = faithful_result["translated_text"]
        
        if style != "faithful":
            natural_result = await self._perform_translation(
                text=faithful_translation, source_lang=target_lang,
                target_lang=target_lang, style=style, pass_type="editorial",
            )
            final_translation = natural_result.get("translated_text", faithful_translation)
        else:
            final_translation = faithful_translation
        
        quality_result = await self._quality_check(
            source_text=text, translated_text=final_translation,
            source_lang=source_lang, target_lang=target_lang,
        )
        
        if quality_result and quality_result.get("issues"):
            logger.warning(f"Quality issues detected: {quality_result['issues']}")
        
        return {
            "translated_text": final_translation,
            "provider": faithful_result.get("provider", "unknown"),
            "quality_issues": quality_result.get("issues", []),
        }
    
    async def _perform_translation(self, text: str, source_lang: str, target_lang: str,
                                   style: str, pass_type: str = "faithful") -> Optional[Dict[str, Any]]:
        for provider in self.providers:
            try:
                if not await provider.healthcheck():
                    logger.warning(f"Provider {provider.provider_name()} unhealthy, skipping")
                    continue
                
                if pass_type == "editorial":
                    system_prompt = EDITORIAL_REWRITE_PROMPT.format(
                        style=TRANSLATION_STYLE_PROMPTS.get(style, "")
                    )
                    user_prompt = f"Rewrite this Persian text to be more {style}:\n\n{text}"
                else:
                    system_prompt = TRANSLATION_SYSTEM_PROMPT.format(
                        style=TRANSLATION_STYLE_PROMPTS.get(style, "")
                    )
                    user_prompt = (
                        f"Translate the following {source_lang} text to {target_lang}.\n\n"
                        f"Source text:\n{text}"
                    )
                
                full_prompt = f"{system_prompt}\n\n{user_prompt}"
                
                translated = await provider.translate(
                    text=full_prompt, source_lang=source_lang,
                    target_lang=target_lang, style=style,
                )
                
                if translated:
                    logger.info(f"Translation succeeded with {provider.provider_name()}")
                    return {
                        "translated_text": translated,
                        "provider": provider.provider_name(),
                    }
                
            except Exception as e:
                logger.error(f"Provider {provider.provider_name()} failed: {e}", exc_info=True)
                continue
        
        return None
    
    async def _quality_check(self, source_text: str, translated_text: str,
                            source_lang: str, target_lang: str) -> Optional[Dict[str, Any]]:
        for provider in self.providers[:1]:
            try:
                if not await provider.healthcheck():
                    continue
                
                prompt = QUALITY_CHECK_PROMPT.format(
                    source_text=source_text, translated_text=translated_text,
                    source_lang=source_lang, target_lang=target_lang,
                )
                
                result = await provider.translate(
                    text=prompt, source_lang=source_lang,
                    target_lang=target_lang, style="faithful",
                )
                
                if result:
                    issues = [line.strip() for line in result.split("\n") if line.strip().startswith("-")]
                    return {"issues": issues}
                    
            except Exception as e:
                logger.error(f"Quality check failed: {e}")
                continue
        
        return None
