import time, logging, threading


class FlashEngine:
    """
    NLLB-200 distilled 600M via CTranslate2 CUDA int8.
    200 languages. <500ms per translation on CUDA.
    Handles ALL translation — incoming and reply.
    No Ollama. No external API. Fully embedded.
    """
    HF_PATH  = 'models/nllb-200-distilled-600M'
    CT2_PATH = 'models/nllb-ct2'

    LANG_CODES = {
        'english':    'eng_Latn',
        'japanese':   'jpn_Jpan',
        'korean':     'kor_Hang',
        'chinese':    'zho_Hans',
        'arabic':     'arb_Arab',
        'french':     'fra_Latn',
        'spanish':    'spa_Latn',
        'german':     'deu_Latn',
        'portuguese': 'por_Latn',
        'russian':    'rus_Cyrl',
        'thai':       'tha_Thai',
        'vietnamese': 'vie_Latn',
        'indonesian': 'ind_Latn',
        'turkish':    'tur_Latn',
    }

    # Unicode ranges for auto language detection
    _DETECT = {
        'jpn_Jpan': [(0x3040, 0x30FF), (0x31F0, 0x31FF), (0xFF65, 0xFF9F)],
        'kor_Hang': [(0xAC00, 0xD7A3), (0x1100, 0x11FF)],
        'zho_Hans': [(0x4E00, 0x9FFF), (0x3400, 0x4DBF)],
        'arb_Arab': [(0x0600, 0x06FF), (0x0750, 0x077F)],
        'tha_Thai': [(0x0E00, 0x0E7F)],
        'rus_Cyrl': [(0x0400, 0x04FF)],
    }

    def __init__(self, device: str = 'cuda', vault=None):
        self.vault       = vault
        self.device      = device
        self.ready       = False
        self._translator = None
        self._tokenizers = {}
        self._lock       = threading.Lock()
        self._load()

    # ── Loading ─────────────────────────────────────────────────────────────
    def _load(self):
        import ctranslate2 as _ct2
        try:
            compute_type = 'int8_float16' if self.device == 'cuda' else 'int8'
            self._translator = _ct2.Translator(
                self.CT2_PATH,
                device=self.device,
                compute_type=compute_type,
                inter_threads=1,
            )
            self._warmup()
            self.ready = True
            logging.info(f'[FLASH] Ready on {self.device}')
        except Exception as e:
            logging.error(f'[FLASH] {self.device} load failed: {type(e).__name__}: {e}')
            if self.device != 'cpu':
                logging.warning('[FLASH] Falling back to CPU...')
                self.device = 'cpu'
                try:
                    self._translator = _ct2.Translator(
                        self.CT2_PATH, device='cpu', compute_type='int8'
                    )
                    self._warmup()
                    self.ready = True
                    logging.warning('[FLASH] Running on CPU — 3-5s per translation')
                except Exception as e2:
                    logging.error(f'[FLASH] CPU fallback also failed: {e2}')

    def _warmup(self):
        # Runs one translation to load CUDA kernels — makes first real translation fast
        self._raw('テスト', 'jpn_Jpan', 'eng_Latn')
        logging.info('[FLASH] Warmup complete')

    # ── Language detection ───────────────────────────────────────────────────
    def detect_lang(self, text: str) -> str:
        scores = {lang: 0 for lang in self._DETECT}
        for ch in text:
            cp = ord(ch)
            for lang, ranges in self._DETECT.items():
                for lo, hi in ranges:
                    if lo <= cp <= hi:
                        # Hiragana/katakana are unique to Japanese — give extra weight
                        scores[lang] += 2 if lang == 'jpn_Jpan' else 1
        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else 'eng_Latn'

    def is_foreign(self, text: str) -> bool:
        return self.detect_lang(text) != 'eng_Latn'

    # ── Core translation ─────────────────────────────────────────────────────
    def _get_tokenizer(self, src_lang: str):
        if src_lang not in self._tokenizers:
            from transformers import NllbTokenizer
            tok = NllbTokenizer.from_pretrained(self.HF_PATH)
            tok.src_lang = src_lang
            self._tokenizers[src_lang] = tok
        return self._tokenizers[src_lang]

    def _raw(self, text: str, src: str, tgt: str) -> str:
        tok     = self._get_tokenizer(src)
        ids     = tok(text).input_ids      # plain Python list — no torch required
        tokens  = tok.convert_ids_to_tokens(ids)
        tgt_pfx = [tgt]   # language code strings are tokens in the NLLB vocabulary
        res     = self._translator.translate_batch(
            [tokens], target_prefix=[tgt_pfx], max_decoding_length=256
        )
        out_ids = tok.convert_tokens_to_ids(res[0].hypotheses[0][1:])
        return tok.decode(out_ids, skip_special_tokens=True)

    def translate(self, text: str, tgt_language: str = 'english') -> dict | None:
        """
        Translate text into tgt_language.
        Returns dict with keys: original, translation, src_lang, tgt_lang, ms
        Returns None if text is already in target language or empty.
        """
        if not text or not text.strip():
            return None
        if not self.ready:
            logging.error('[FLASH] translate() called but engine not ready')
            return None

        tgt = self.LANG_CODES.get(tgt_language.lower(), 'eng_Latn')
        src = self.detect_lang(text)
        if src == tgt:
            return None  # already in target language — nothing to do

        # Check VAULT first
        if self.vault:
            cached = self.vault.lookup(text, tgt)
            if cached:
                logging.info('[FLASH] VAULT hit — returning cached')
                return {
                    'original': text, 'translation': cached,
                    'src_lang': src, 'tgt_lang': tgt, 'ms': 0
                }

        # Translate
        try:
            with self._lock:
                t0     = time.perf_counter()
                result = self._raw(text, src, tgt)
                ms     = round((time.perf_counter() - t0) * 1000)
                logging.info(f'[FLASH] {src} -> {tgt}  {ms}ms')
            if result and self.vault:
                self.vault.store(text, tgt, result)
            return {
                'original': text, 'translation': result,
                'src_lang': src, 'tgt_lang': tgt, 'ms': ms
            }
        except Exception as e:
            logging.error(f'[FLASH] translate() failed: {type(e).__name__}: {e}')
            return None
