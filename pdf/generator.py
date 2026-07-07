import os
from datetime import datetime
from pathlib import Path
import tempfile
from weasyprint import HTML
from utils.logger import setup_logger

logger = setup_logger(__name__)


class PDFGenerator:
    PERSIAN_FONTS = ["Vazirmatn", "Noto Naskh Arabic", "Tahoma", "Arial"]
    
    def generate_translation_pdf(self, source_text: str, translated_text: str,
                                 source_lang: str, target_lang: str,
                                 style: str = "natural", mode: str = "source_translation") -> str:
        html_content = self._build_html(
            source_text=source_text, translated_text=translated_text,
            source_lang=source_lang, target_lang=target_lang,
            style=style, mode=mode,
        )
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            output_path = tmp.name
        
        try:
            HTML(string=html_content).write_pdf(output_path, presentational_hints=True)
            logger.info(f"PDF generated: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"PDF generation error: {e}", exc_info=True)
            raise
    
    def _build_html(self, source_text: str, translated_text: str, source_lang: str,
                    target_lang: str, style: str, mode: str) -> str:
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d %H:%M")
        
        lang_names = {"ar": "عربی", "fa": "فارسی", "en": "انگلیسی"}
        source_lang_name = lang_names.get(source_lang, source_lang)
        target_lang_name = lang_names.get(target_lang, target_lang)
        
        style_names = {
            "faithful": "دقیق و وفادار", "natural": "روان و طبیعی",
            "formal": "رسمی", "literary": "ادبی",
        }
        style_name = style_names.get(style, style)
        
        font_family = ", ".join(f"'{font}'" for font in self.PERSIAN_FONTS)
        
        source_text_escaped = source_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        translated_text_escaped = translated_text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        if mode == "side_by_side":
            content_html = f"""
            <div style="display: flex; gap: 20px;">
                <div style="flex: 1;">
                    <h3>📝 متن اصلی ({source_lang_name})</h3>
                    <div style="text-align: justify; font-size: 14px; padding: 15px; background-color: #F8F9FA; border-radius: 8px; white-space: pre-wrap;">{source_text_escaped}</div>
                </div>
                <div style="flex: 1;">
                    <h3>🔄 ترجمه ({target_lang_name})</h3>
                    <div style="text-align: justify; font-size: 14px; padding: 15px; background-color: #E8F5E9; border-radius: 8px; white-space: pre-wrap;">{translated_text_escaped}</div>
                </div>
            </div>
            """
        elif mode == "translation_source":
            content_html = f"""
            <div style="margin-bottom: 30px;">
                <h3>🔄 ترجمه ({target_lang_name})</h3>
                <div style="text-align: justify; font-size: 14px; padding: 15px; background-color: #E8F5E9; border-radius: 8px; white-space: pre-wrap;">{translated_text_escaped}</div>
            </div>
            <div style="margin-bottom: 30px;">
                <h3>📝 متن اصلی ({source_lang_name})</h3>
                <div style="text-align: justify; font-size: 14px; padding: 15px; background-color: #F8F9FA; border-radius: 8px; white-space: pre-wrap;">{source_text_escaped}</div>
            </div>
            """
        else:
            content_html = f"""
            <div style="margin-bottom: 30px;">
                <h3>📝 متن اصلی ({source_lang_name})</h3>
                <div style="text-align: justify; font-size: 14px; padding: 15px; background-color: #F8F9FA; border-radius: 8px; white-space: pre-wrap;">{source_text_escaped}</div>
            </div>
            <div style="margin-bottom: 30px;">
                <h3>🔄 ترجمه ({target_lang_name})</h3>
                <div style="text-align: justify; font-size: 14px; padding: 15px; background-color: #E8F5E9; border-radius: 8px; white-space: pre-wrap;">{translated_text_escaped}</div>
            </div>
            """
        
        html = f"""
        <!DOCTYPE html>
        <html dir="rtl" lang="fa">
        <head>
            <meta charset="UTF-8">
            <style>
                @page {{ size: A4; margin: 2cm; }}
                body {{ font-family: {font_family}, sans-serif; line-height: 2; color: #333; }}
                .header {{ text-align: center; margin-bottom: 30px; padding-bottom: 20px; border-bottom: 2px solid #4A90E2; }}
                .title {{ font-size: 24px; font-weight: bold; color: #2C3E50; margin-bottom: 10px; }}
                .meta {{ font-size: 12px; color: #7F8C8D; margin-bottom: 5px; }}
                h3 {{ color: #4A90E2; font-size: 18px; margin-bottom: 15px; border-right: 4px solid #4A90E2; padding-right: 10px; }}
                .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #BDC3C7; text-align: center; font-size: 10px; color: #95A5A6; }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="title">📄 ترجمه</div>
                <div class="meta">تاریخ: {date_str}</div>
                <div class="meta">زبان مبدأ: {source_lang_name} | زبان مقصد: {target_lang_name}</div>
                <div class="meta">سبک ترجمه: {style_name}</div>
            </div>
            {content_html}
            <div class="footer">تولید شده توسط ربات مترجم فارسی | {date_str}</div>
        </body>
        </html>
        """
        
        return html
