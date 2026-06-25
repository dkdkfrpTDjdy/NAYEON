from __future__ import annotations

from functools import lru_cache
from typing import Protocol

from .image_preprocess import preprocess_for_ocr
from .models import OCRToken


class OCREngine(Protocol):
    def extract(self, image_bytes: bytes, filename: str, page_no: int = 1) -> list[OCRToken]:
        ...


class EasyOCREngine:
    def __init__(self, languages: list[str] | None = None, gpu: bool = False):
        import easyocr

        self.languages = languages or ["ko", "en"]
        self.reader = easyocr.Reader(self.languages, gpu=gpu)

    def extract(self, image_bytes: bytes, filename: str, page_no: int = 1) -> list[OCRToken]:
        image = preprocess_for_ocr(image_bytes)
        results = self.reader.readtext(image, detail=1, paragraph=False)
        tokens: list[OCRToken] = []
        for bbox, text, confidence in results:
            clean = str(text).strip()
            if not clean:
                continue
            tokens.append(
                OCRToken(
                    filename=filename,
                    page_no=page_no,
                    text=clean,
                    confidence=float(confidence) if confidence is not None else None,
                    bbox=[[float(x), float(y)] for x, y in bbox] if bbox else None,
                )
            )
        return tokens


class NoopOCREngine:
    """Fallback used only when OCR dependencies are unavailable.

    This keeps the app bootable in CI. Runtime extraction still requires EasyOCR.
    """

    def extract(self, image_bytes: bytes, filename: str, page_no: int = 1) -> list[OCRToken]:
        raise RuntimeError(
            "OCR engine is not available. Install requirements.txt and verify EasyOCR model download."
        )


@lru_cache(maxsize=1)
def get_ocr_engine(engine_name: str = "easyocr") -> OCREngine:
    if engine_name == "easyocr":
        return EasyOCREngine()
    raise ValueError(f"Unsupported OCR_ENGINE: {engine_name}")
