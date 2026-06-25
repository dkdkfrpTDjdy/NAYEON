from __future__ import annotations

from io import BytesIO

import numpy as np
from PIL import Image, ImageOps, ImageFilter


def load_image(image_bytes: bytes) -> Image.Image:
    image = Image.open(BytesIO(image_bytes))
    image = ImageOps.exif_transpose(image)
    return image.convert("RGB")


def preprocess_for_ocr(image_bytes: bytes) -> np.ndarray:
    """Return a numpy RGB/gray image suitable for OCR.

    The preprocessing is intentionally conservative. Over-aggressive thresholding can
    remove thin Korean characters and receipt/table lines.
    """
    image = load_image(image_bytes)

    max_width = 2200
    if image.width < 1200:
        scale = 1200 / max(image.width, 1)
        image = image.resize((int(image.width * scale), int(image.height * scale)))
    elif image.width > max_width:
        scale = max_width / image.width
        image = image.resize((max_width, int(image.height * scale)))

    gray = ImageOps.grayscale(image)
    gray = ImageOps.autocontrast(gray)
    gray = gray.filter(ImageFilter.MedianFilter(size=3))

    return np.array(gray)
