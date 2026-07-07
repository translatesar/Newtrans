from abc import ABC, abstractmethod
from typing import Optional


class TranslationProvider(ABC):
    @abstractmethod
    async def translate(self, text: str, source_lang: str, target_lang: str, style: str = "natural") -> Optional[str]:
        pass
    
    @abstractmethod
    async def healthcheck(self) -> bool:
        pass
    
    @abstractmethod
    def provider_name(self) -> str:
        pass
    
    @abstractmethod
    def estimated_cost_mode(self) -> str:
        pass
