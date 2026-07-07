from langdetect import detect, DetectorFactory
from utils.logger import setup_logger

DetectorFactory.seed = 0
logger = setup_logger(__name__)


def detect_language(text: str) -> str:
    try:
        sample = text[:200] if len(text) > 200 else text
        if not sample.strip():
            return "unknown"
        lang = detect(sample)
        return lang
    except Exception as e:
        logger.error(f"Language detection error: {e}")
        return "unknown"


def is_persian(lang_code: str) -> bool:
    return lang_code == "fa"


def is_arabic(lang_code: str) -> bool:
    return lang_code == "ar"
