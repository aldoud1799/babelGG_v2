import logging
import re
import asyncio
import importlib
import os
import shutil
import tempfile
from dataclasses import dataclass

from PIL import Image, ImageFilter, ImageOps


@dataclass
class OCRResult:
    text: str
    backend: str
    error: str = ''


class OCRReader:
    """Best-effort OCR reader with optional backends.

    Backends are discovered lazily so the app can run even when OCR deps
    are not installed.
    """

    def __init__(self):
        self._backend_order = ['windows_ocr', 'easyocr']
        self._windows_checked = False
        self._windows_error = ''
        self._windows_engine = None
        self._easy_readers = {}
        self._easy_error = ''
        self._easy_cache_repaired = False

    def _foreign_script_score(self, text: str) -> int:
        score = 0
        for ch in text:
            cp = ord(ch)
            if (
                0x3040 <= cp <= 0x30FF  # Japanese kana
                or 0x4E00 <= cp <= 0x9FFF  # CJK ideographs
                or 0xAC00 <= cp <= 0xD7A3  # Hangul
            ):
                score += 2
            elif 0x0020 <= cp <= 0x007E:
                score += 0
        return score

    def is_likely_garbled(self, text: str) -> bool:
        """Heuristic filter to avoid translating OCR noise as if it were language."""
        if not text:
            return True
        t = text.strip()
        if len(t) < 2:
            cp = ord(t[0]) if t else 0
            # Allow single-character CJK/Hangul/Kana outputs from tiny crops.
            if (
                0x3040 <= cp <= 0x30FF
                or 0x4E00 <= cp <= 0x9FFF
                or 0xAC00 <= cp <= 0xD7A3
            ):
                return False
            # Allow compact alnum tokens like "R5"/"A" style UI labels.
            if t.isalnum():
                return False
            return True

        total = len(t)
        alpha = sum(1 for ch in t if ch.isalpha())
        digit = sum(1 for ch in t if ch.isdigit())
        cjk = sum(1 for ch in t if (
            0x3040 <= ord(ch) <= 0x30FF
            or 0x4E00 <= ord(ch) <= 0x9FFF
            or 0xAC00 <= ord(ch) <= 0xD7A3
        ))
        punct_like = sum(1 for ch in t if not ch.isalnum() and not ch.isspace())

        # Healthy OCR should have enough alphabetic/CJK signal and not be
        # dominated by punctuation artifacts.
        alpha_ratio = alpha / max(total, 1)
        cjk_ratio = cjk / max(total, 1)
        punct_ratio = punct_like / max(total, 1)
        digit_ratio = digit / max(total, 1)

        # Tiny OCR snippets with meaningful CJK signal are often valid.
        if total <= 3 and cjk >= 1:
            return False

        if (alpha_ratio + cjk_ratio) < 0.28 and punct_ratio > 0.22:
            return True
        if digit_ratio > 0.45 and (alpha_ratio + cjk_ratio) < 0.22:
            return True
        return False

    def _maybe_repair_easyocr_cache(self, err_text: str):
        # EasyOCR occasionally leaves a corrupt model archive/weights file.
        # If detected, clear model cache once and allow a clean redownload.
        low = (err_text or '').lower()
        markers = ('badzipfile', 'crc-32', 'decompress', 'invalid code lengths')
        if self._easy_cache_repaired or not any(m in low for m in markers):
            return
        model_dir = os.path.join(os.path.expanduser('~'), '.EasyOCR', 'model')
        try:
            if os.path.isdir(model_dir):
                shutil.rmtree(model_dir, ignore_errors=True)
            self._easy_cache_repaired = True
            logging.warning('[OCR] easyocr cache repaired; forcing fresh model download')
        except Exception as e:
            logging.warning(f'[OCR] easyocr cache repair failed: {type(e).__name__}: {e}')

    def _normalize(self, text: str) -> str:
        if not text:
            return ''
        # Collapse noisy whitespace while keeping line boundaries meaningful.
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        lines = [re.sub(r'\s+', ' ', ln).strip() for ln in text.split('\n')]
        lines = [ln for ln in lines if ln]
        return '\n'.join(lines).strip()

    def _get_easy_reader(self, langs: tuple[str, ...]):
        if langs in self._easy_readers:
            return self._easy_readers[langs]
        if self._easy_error:
            return None
        self._easy_error = 'easyocr backend disabled'
        return None

    def _prepare_ocr_variant(self, image_path: str) -> str:
        """Create a high-readability image variant for tiny/low-contrast crops."""
        try:
            img = Image.open(image_path).convert('RGB')
            w, h = img.size
            if min(w, h) < 220:
                scale = 3
            elif min(w, h) < 420:
                scale = 2
            else:
                scale = 1

            if scale > 1:
                img = img.resize((w * scale, h * scale), Image.Resampling.LANCZOS)

            gray = ImageOps.grayscale(img)
            gray = ImageOps.autocontrast(gray, cutoff=2)
            gray = gray.filter(ImageFilter.SHARPEN)

            fd, out_path = tempfile.mkstemp(prefix='ocr_pre_', suffix='.png')
            os.close(fd)
            gray.save(out_path, format='PNG')
            return out_path
        except Exception as e:
            logging.warning(f'[OCR] Preprocess failed, using raw image: {type(e).__name__}: {e}')
            return image_path

    def _extract_with_easy_profile(self, image_path: str, langs: tuple[str, ...]) -> OCRResult:
        reader = self._get_easy_reader(langs)
        if reader is None:
            return OCRResult(text='', backend='easyocr', error=self._easy_error or 'easyocr unavailable')

        try:
            # detail=1 gives confidence values; paragraph=False improves short crop fidelity.
            rows = reader.readtext(
                image_path,
                detail=1,
                paragraph=False,
                decoder='beamsearch',
                text_threshold=0.55,
                low_text=0.25,
                link_threshold=0.2,
            )
            if not rows:
                return OCRResult(text='', backend='easyocr', error='No text detected in selection.')

            parts = []
            conf_sum = 0.0
            for row in rows:
                if len(row) >= 3:
                    txt = str(row[1] or '').strip()
                    conf = float(row[2] or 0.0)
                    if txt:
                        parts.append(txt)
                        conf_sum += conf
            text = self._normalize('\n'.join(parts))
            if not text:
                return OCRResult(text='', backend='easyocr', error='No text detected in selection.')

            avg_conf = conf_sum / max(len(parts), 1)
            script_bonus = self._foreign_script_score(text) / max(len(text), 1)
            if avg_conf < 0.18 and script_bonus < 0.20:
                return OCRResult(
                    text='',
                    backend='easyocr',
                    error=f'Low OCR confidence ({avg_conf:.2f})',
                )
            # Stash score in error field temporarily for chooser logic.
            return OCRResult(text=text, backend='easyocr', error=f'score:{avg_conf + script_bonus:.4f}')
        except Exception as e:
            err = f'{type(e).__name__}: {e}'
            logging.error(f'[OCR] easyocr extraction failed ({list(langs)}): {err}')
            return OCRResult(text='', backend='easyocr', error=err)

    def _init_windows_ocr(self):
        if self._windows_checked:
            return self._windows_engine
        self._windows_checked = True
        try:
            ocr_mod = importlib.import_module('winsdk.windows.media.ocr')
            OcrEngine = getattr(ocr_mod, 'OcrEngine')

            engine = OcrEngine.try_create_from_user_profile_languages()
            if engine is None:
                self._windows_error = 'No Windows OCR language packs available.'
                logging.warning(f'[OCR] windows_ocr unavailable: {self._windows_error}')
                return None
            self._windows_engine = engine
            return self._windows_engine
        except Exception as e:
            self._windows_error = f'{type(e).__name__}: {e}'
            logging.warning(f'[OCR] windows_ocr unavailable: {self._windows_error}')
            return None

    async def _windows_ocr_async(self, image_path: str) -> OCRResult:
        engine = self._init_windows_ocr()
        if engine is None:
            return OCRResult(text='', backend='windows_ocr', error=self._windows_error or 'windows_ocr unavailable')
        try:
            imaging_mod = importlib.import_module('winsdk.windows.graphics.imaging')
            streams_mod = importlib.import_module('winsdk.windows.storage.streams')
            BitmapDecoder = getattr(imaging_mod, 'BitmapDecoder')
            DataWriter = getattr(streams_mod, 'DataWriter')
            InMemoryRandomAccessStream = getattr(streams_mod, 'InMemoryRandomAccessStream')

            with open(image_path, 'rb') as f:
                image_bytes = f.read()

            stream = InMemoryRandomAccessStream()
            writer = DataWriter(stream)
            writer.write_bytes(image_bytes)
            await writer.store_async()
            writer.detach_stream()
            stream.seek(0)

            decoder = await BitmapDecoder.create_async(stream)
            bitmap = await decoder.get_software_bitmap_async()
            result = await engine.recognize_async(bitmap)
            text = self._normalize(result.text)
            if not text:
                return OCRResult(text='', backend='windows_ocr', error='No text detected in selection.')
            return OCRResult(text=text, backend='windows_ocr', error='')
        except Exception as e:
            err = f'{type(e).__name__}: {e}'
            logging.error(f'[OCR] windows_ocr extraction failed: {err}')
            return OCRResult(text='', backend='windows_ocr', error=err)

    def _extract_with_windows_ocr(self, image_path: str) -> OCRResult:
        try:
            return asyncio.run(self._windows_ocr_async(image_path))
        except Exception as e:
            err = f'{type(e).__name__}: {e}'
            logging.error(f'[OCR] windows_ocr runtime failed: {err}')
            return OCRResult(text='', backend='windows_ocr', error=err)

    def _extract_with_easyocr(self, image_path: str) -> OCRResult:
        # Try multiple language profiles and keep best confident output.
        profiles = [
            ('ja', 'en'),
            ('ko', 'en'),
            ('ch_sim', 'en'),
            ('en',),
        ]
        best: OCRResult | None = None
        best_score = -1.0
        best_err = ''

        variant_path = self._prepare_ocr_variant(image_path)
        paths = [image_path]
        if variant_path != image_path:
            paths.append(variant_path)
        try:
            for p in paths:
                for langs in profiles:
                    result = self._extract_with_easy_profile(p, langs)
                    if not result.text:
                        best_err = result.error or best_err
                        continue
                    score = 0.0
                    if result.error.startswith('score:'):
                        try:
                            score = float(result.error.split(':', 1)[1])
                        except Exception:
                            score = 0.0
                    if score > best_score:
                        best_score = score
                        best = OCRResult(text=result.text, backend='easyocr', error='')

            if best is not None and best.text:
                logging.info(f'[OCR] easyocr selected result score={best_score:.4f}')
                return best

            return OCRResult(text='', backend='easyocr', error=best_err or self._easy_error or 'No text detected in selection.')
        finally:
            if variant_path != image_path:
                try:
                    os.remove(variant_path)
                except OSError:
                    pass

    def is_available(self) -> bool:
        if self._init_windows_ocr() is not None:
            return True
        # Probe one lightweight profile for availability check.
        return self._get_easy_reader(('en',)) is not None

    def availability_error(self) -> str:
        if self.is_available():
            return ''
        parts = []
        if self._windows_error:
            parts.append(f'windows_ocr: {self._windows_error}')
        if self._easy_error:
            parts.append(f'easyocr: {self._easy_error}')
        return '; '.join(parts) or 'No OCR backend available (winsdk/easyocr missing).'

    def extract_text_from_image(self, image_path: str) -> OCRResult:
        for backend in self._backend_order:
            if backend == 'windows_ocr':
                result = self._extract_with_windows_ocr(image_path)
            elif backend == 'easyocr':
                result = self._extract_with_easyocr(image_path)
            else:
                continue

            if result.text:
                return result

        return OCRResult(
            text='',
            backend='none',
            error=self.availability_error() or 'OCR backend failed to read text.',
        )
