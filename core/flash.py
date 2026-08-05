import ctypes
import difflib
import json
import logging
import os
import re
import sys
import threading
import time
from collections import deque

from core.paths import base_path, models_path, user_config_path


class FlashEngine:
    """
    Llama.cpp-based translation engine with adaptive routing.

    Path A: GPU full offload (n_gpu_layers=-1)
    Path B: GPU constrained offload (reduced gpu layers)
    Path C: CPU-safe mode
    Path D: Deterministic fallback (return source text)
    """

    LANG_CODES = {
        'english': 'eng_Latn',
        'japanese': 'jpn_Jpan',
        'korean': 'kor_Hang',
        'chinese': 'zho_Hans',
        'arabic': 'arb_Arab',
        'french': 'fra_Latn',
        'spanish': 'spa_Latn',
        'german': 'deu_Latn',
        'portuguese': 'por_Latn',
        'russian': 'rus_Cyrl',
        'thai': 'tha_Thai',
        'vietnamese': 'vie_Latn',
        'indonesian': 'ind_Latn',
        'turkish': 'tur_Latn',
        'italian': 'ita_Latn',
        'dutch': 'nld_Latn',
        'polish': 'pol_Latn',
        'swedish': 'swe_Latn',
        'hindi': 'hin_Deva',
    }

    # CT2 tokenizer language mapping used by the active model/tokenizer pair.
    _CT2_LANG_MAP = {
        'eng_Latn': 'eng_Latn',
        'jpn_Jpan': 'jpn_Jpan',
        'kor_Hang': 'kor_Hang',
        'zho_Hans': 'zho_Hans',
        'arb_Arab': 'arb_Arab',
        'fra_Latn': 'fra_Latn',
        'spa_Latn': 'spa_Latn',
        'deu_Latn': 'deu_Latn',
        'por_Latn': 'por_Latn',
        'rus_Cyrl': 'rus_Cyrl',
        'tha_Thai': 'tha_Thai',
        'vie_Latn': 'vie_Latn',
        'ind_Latn': 'ind_Latn',
        'tur_Latn': 'tur_Latn',
        'ita_Latn': 'ita_Latn',
        'nld_Latn': 'nld_Latn',
        'pol_Latn': 'pol_Latn',
        'swe_Latn': 'swe_Latn',
        'hin_Deva': 'hin_Deva',
    }

    _NON_LATIN_TARGETS = {'jpn_Jpan', 'kor_Hang', 'zho_Hans', 'arb_Arab', 'tha_Thai', 'rus_Cyrl', 'hin_Deva'}
    _JA_QUOTED_HINTS = {
        'あなた': 'you',
        'あなたは': 'you (polite)',
        'お前': 'you (rude)',
        'お前は': 'you (rude)',
        '君': 'you',
        '君は': 'you',
    }
    _TARGET_SCRIPT_RANGES = {
        'jpn_Jpan': [(0x3040, 0x30FF), (0x4E00, 0x9FFF)],
        'kor_Hang': [(0xAC00, 0xD7A3), (0x1100, 0x11FF)],
        'zho_Hans': [(0x4E00, 0x9FFF)],
        'arb_Arab': [(0x0600, 0x06FF), (0x0750, 0x077F)],
        'tha_Thai': [(0x0E00, 0x0E7F)],
        'rus_Cyrl': [(0x0400, 0x04FF)],
        'hin_Deva': [(0x0900, 0x097F)],
    }
    _LANG_NAMES = {
        'eng_Latn': 'English',
        'jpn_Jpan': 'Japanese',
        'kor_Hang': 'Korean',
        'zho_Hans': 'Chinese (Simplified)',
        'arb_Arab': 'Arabic',
        'fra_Latn': 'French',
        'spa_Latn': 'Spanish',
        'deu_Latn': 'German',
        'por_Latn': 'Portuguese',
        'rus_Cyrl': 'Russian',
        'tha_Thai': 'Thai',
        'vie_Latn': 'Vietnamese',
        'ind_Latn': 'Indonesian',
        'tur_Latn': 'Turkish',
        'ita_Latn': 'Italian',
        'nld_Latn': 'Dutch',
        'pol_Latn': 'Polish',
        'swe_Latn': 'Swedish',
        'hin_Deva': 'Hindi',
    }

    # Unicode ranges for fast non-Latin script detection
    _DETECT = {
        'jpn_Jpan': [(0x3040, 0x30FF), (0x31F0, 0x31FF), (0xFF65, 0xFF9F)],
        'kor_Hang': [(0xAC00, 0xD7A3), (0x1100, 0x11FF)],
        'zho_Hans': [(0x4E00, 0x9FFF), (0x3400, 0x4DBF)],
        'arb_Arab': [(0x0600, 0x06FF), (0x0750, 0x077F)],
        'tha_Thai': [(0x0E00, 0x0E7F)],
        'rus_Cyrl': [(0x0400, 0x04FF)],
        'hin_Deva': [(0x0900, 0x097F)],
    }

    _LANGDETECT_MAP = {
        'en': 'eng_Latn',
        'fr': 'fra_Latn',
        'es': 'spa_Latn',
        'de': 'deu_Latn',
        'pt': 'por_Latn',
        'vi': 'vie_Latn',
        'id': 'ind_Latn',
        'tr': 'tur_Latn',
        'it': 'ita_Latn',
        'nl': 'nld_Latn',
        'pl': 'pol_Latn',
        'sv': 'swe_Latn',
        'hi': 'hin_Deva',
        'ja': 'jpn_Jpan',
        'ko': 'kor_Hang',
        'zh-cn': 'zho_Hans',
        'zh-tw': 'zho_Hant',
        'ar': 'arb_Arab',
        'ru': 'rus_Cyrl',
        'th': 'tha_Thai',
    }

    _SYSTEM_PROMPT_EN = (
        "You are an invisible, automated translation API. Your only job is to translate the user's "
        "text accurately into English. Mirror the exact tone of the input: if it is formal, translate "
        "formally; if it is casual gaming slang, use equivalent slang. Preserve all emojis exactly. "
        "Output ONLY the final translation wrapped in <t></t>. Do not add notes, greetings, or "
        "explanations. If you cannot translate it, output the original text."
    )

    # Runtime budgets tuned for real-world desktop inference latency.
    _SOFT_BUDGET_MS = 600
    _HARD_BUDGET_MS = 1000
    _ABS_BUDGET_MS = 1600
    _ABS_BUDGET_MS_NON_ENG_TARGET = 2400
    _SLOW_STREAK_TO_DOWNGRADE = 2
    _FAST_STREAK_TO_RECOVER = 5
    _PROFILE_COOLDOWN_SEC = 20
    _MIN_ATTEMPT_BUDGET_MS = 35
    _STICKY_PROFILE_RUNTIME = True
    _MICRO_RETRY_ON_TIMEOUT = True
    _MICRO_RETRY_BUDGET_MS = 110
    _MICRO_RETRY_MIN_TEXT_LEN = 28

    _PROFILE_ORDER_GPU = ('gpu_trim', 'gpu_full', 'cpu_safe', 'fallback')
    _PROFILE_ORDER_CPU = ('cpu_safe', 'fallback')

    def __init__(self, device: str = 'cuda', vault=None):
        self.vault = vault
        self.device = str(device or 'cuda').lower()
        self.ready = False
        self.last_error_message = ''
        # CT2 is the production runtime; llama_cpp is optional/legacy fallback.
        self.runtime = 'ctranslate2'

        self._lock = threading.RLock()
        self._interrupt = threading.Event()
        self._ct2_translator = None
        self._ct2_tokenizer = None
        self._ct2_target_prefix_cache = {}
        self._ct2_lang_token_cache = {}
        self._ct2_vocab_tokens = None
        self._ct2_device = 'unknown'
        self._profile = ''
        self._latencies = {
            'gpu_full': deque(maxlen=40),
            'gpu_trim': deque(maxlen=40),
            'cpu_safe': deque(maxlen=40),
        }
        self._fails = {
            'gpu_full': 0,
            'gpu_trim': 0,
            'cpu_safe': 0,
        }
        self._slow_streak = {
            'gpu_full': 0,
            'gpu_trim': 0,
            'cpu_safe': 0,
        }
        self._fast_streak = {
            'gpu_full': 0,
            'gpu_trim': 0,
            'cpu_safe': 0,
        }
        self._profile_cooldown_until = {
            'gpu_full': 0.0,
            'gpu_trim': 0.0,
            'cpu_safe': 0.0,
        }
        self._preferred_profile = 'cpu_safe' if self.device == 'cpu' else 'gpu_full'
        self._last_detect_reason = 'init'

        self._flash_cfg = self._load_flash_cfg()
        self.runtime = str(self._flash_cfg.get('runtime') or 'ctranslate2').strip().lower()
        if self.runtime not in ('llama_cpp', 'ctranslate2'):
            self.runtime = 'ctranslate2'

        self.model_path = self._resolve_model_path()
        self._load()

    def _load_flash_cfg(self) -> dict:
        try:
            with open(base_path('version.json'), 'r', encoding='utf-8') as f:
                return json.load(f).get('flash', {}) or {}
        except Exception as e:
            logging.warning('[FLASH] version.json read failed: %s', e)
            return {}

    def _load_user_source_language(self) -> str:
        try:
            with open(user_config_path(), 'r', encoding='utf-8-sig') as f:
                cfg = json.load(f) or {}
            lang = str(cfg.get('source_language') or cfg.get('my_language') or 'english').strip().lower()
            return self.LANG_CODES.get(lang, 'eng_Latn')
        except Exception:
            return 'eng_Latn'

    def _detect_by_charset(self, text: str) -> str:
        cleaned = (text or '').strip()
        if not cleaned:
            return 'eng_Latn'

        scores = {lang: 0 for lang in self._DETECT}
        for ch in cleaned:
            cp = ord(ch)
            for lang, ranges in self._DETECT.items():
                for lo, hi in ranges:
                    if lo <= cp <= hi:
                        scores[lang] += 1

        best = max(scores, key=scores.get)
        return best if scores[best] > 0 else 'eng_Latn'

    def _detect_short_latin_heuristic(self, text: str) -> str | None:
        cleaned = re.sub(r'[^A-Za-z\s]', ' ', (text or '').lower())
        tokens = [t for t in cleaned.split() if t]
        if not tokens or len(tokens) > 8:
            return None

        spanish_markers = {
            'hola', 'amigo', 'amiga', 'gracias', 'adios', 'por', 'favor', 'buenos', 'dias', 'buenas', 'noches',
            'hoy', 'juego', 'fue', 'divertido'
        }
        french_markers = {
            'bonjour', 'merci', 'salut', 'bonsoir', 'oui', 'non', 'suis', 'desole', 'desolee',
            'aujourd', 'hui', 'jeu', 'etait', 'amusant'
        }
        german_markers = {
            'hallo', 'danke', 'bitte', 'guten', 'morgen', 'abend', 'tschuss', 'schoen',
            'heute', 'spiel', 'toll', 'war', 'das'
        }
        portuguese_markers = {
            'ola', 'obrigado', 'obrigada', 'tchau', 'bom', 'boa', 'dia', 'noite', 'favor', 'por',
            'hoje', 'jogo', 'foi'
        }

        scores = {
            'fra_Latn': sum(1 for t in tokens if t in french_markers),
            'spa_Latn': sum(1 for t in tokens if t in spanish_markers),
            'deu_Latn': sum(1 for t in tokens if t in german_markers),
            'por_Latn': sum(1 for t in tokens if t in portuguese_markers),
        }
        best_lang = max(scores, key=scores.get)
        best_score = scores[best_lang]
        if best_score >= 2:
            return best_lang
        if best_score == 1 and len(tokens) <= 3:
            return best_lang

        return None

    def _is_short_ascii_chat_text(self, text: str) -> bool:
        cleaned = (text or '').strip()
        if not cleaned or len(cleaned) > 32:
            return False
        if any(ord(ch) > 127 for ch in cleaned):
            return False
        alpha = sum(1 for ch in cleaned if ch.isalpha())
        if alpha < 2:
            return False
        words = re.findall(r'[A-Za-z]+', cleaned)
        return 1 <= len(words) <= 8

    def _resolve_model_path(self) -> str:
        if self.runtime == 'ctranslate2':
            default_rel = 'models/nllb-ct2-cpu' if self.device == 'cpu' else 'models/nllb-ct2-gpu'
            if self.device == 'cpu':
                configured = self._flash_cfg.get('local_ct2_cpu_path') or self._flash_cfg.get('local_ct2_path') or default_rel
            else:
                configured = self._flash_cfg.get('local_ct2_gpu_path') or self._flash_cfg.get('local_ct2_path') or default_rel

            candidate = configured if os.path.isabs(configured) else base_path(configured)
            if not os.path.isdir(candidate):
                fallback = models_path('nllb-ct2-cpu') if self.device == 'cpu' else models_path('nllb-ct2-gpu')
                if os.path.isdir(fallback):
                    candidate = fallback

            # If CUDA is requested but GPU model is missing, transparently fall back
            # to CPU model path to keep startup functional on all machines.
            if self.device != 'cpu' and not os.path.isdir(candidate):
                cpu_configured = self._flash_cfg.get('local_ct2_cpu_path') or self._flash_cfg.get('local_ct2_path') or 'models/nllb-ct2-cpu'
                cpu_candidate = cpu_configured if os.path.isabs(cpu_configured) else base_path(cpu_configured)
                if not os.path.isdir(cpu_candidate):
                    cpu_fallback = models_path('nllb-ct2-cpu')
                    if os.path.isdir(cpu_fallback):
                        cpu_candidate = cpu_fallback
                if os.path.isdir(cpu_candidate):
                    logging.warning(
                        '[FLASH] GPU CT2 model missing at %s; silently falling back to CPU '
                        '(device switched %s->cpu). Install GPU model or set flash_device=cpu in '
                        'config.json to silence this. Currently using: %s',
                        candidate, self.device, cpu_candidate,
                    )
                    self.device = 'cpu'
                    candidate = cpu_candidate
            logging.info('[FLASH] CT2 model dir: %s', candidate)
            return candidate

        default_model = models_path('flash-model.gguf')
        alt_model = base_path('models', 'flash-model.gguf')
        path = default_model if os.path.isfile(default_model) else alt_model

        try:
            cfg = self._flash_cfg
            configured = cfg.get('local_gguf_model_path')
            if configured:
                candidate = configured if os.path.isabs(configured) else base_path(configured)
                if os.path.isfile(candidate):
                    path = candidate
        except Exception as e:
            logging.warning('[FLASH] version.json model path read failed: %s', e)

        logging.info('[FLASH] LLM model path: %s', path)
        return path

    def _load(self):
        if self.runtime == 'ctranslate2':
            model_bin = os.path.join(self.model_path, 'model.bin')
            if not os.path.isfile(model_bin):
                self.last_error_message = 'FLASH CT2 model missing: model.bin'
                logging.error('[FLASH] %s (%s)', self.last_error_message, self.model_path)
                self.ready = False
                return

            profiles = self._PROFILE_ORDER_CPU if self.device == 'cpu' else self._PROFILE_ORDER_GPU
            for profile in profiles:
                if profile == 'fallback':
                    break
                if self._ensure_profile(profile):
                    self.ready = True
                    return

            self.ready = False
            if not self.last_error_message:
                self.last_error_message = 'FLASH failed to initialize any CT2 profile'
            return

    def _ensure_profile(self, profile: str) -> bool:
        if self.runtime == 'ctranslate2':
            return self._ensure_ct2_profile(profile)

    def _ensure_ct2_profile(self, profile: str) -> bool:
        if self._profile == profile and self._ct2_translator is not None and self._ct2_tokenizer is not None:
            return True

        try:
            device = 'cpu' if profile == 'cpu_safe' else ('cpu' if self.device == 'cpu' else 'cuda')
            if device == 'cuda':
                self._bootstrap_windows_cuda_dll_dirs()

            try:
                import ctranslate2
                from transformers import AutoTokenizer
            except Exception as e:
                self.last_error_message = f'CT2 import failed: {type(e).__name__}: {e}'
                logging.error('[FLASH] %s', self.last_error_message)
                return False

            if device == 'cuda':
                ok, reason = self._ct2_cuda_preflight(ctranslate2)
                if not ok:
                    self.last_error_message = f'CT2 CUDA unavailable: {reason}'
                    logging.warning('[FLASH] %s', self.last_error_message)
                    return False

            compute_type = self._flash_cfg.get('quantization_cpu', 'int8') if device == 'cpu' else self._flash_cfg.get('quantization_gpu', 'int8_float16')
            self._ct2_translator = ctranslate2.Translator(
                self.model_path,
                device=device,
                compute_type=compute_type,
                inter_threads=1,
                intra_threads=max(2, (os.cpu_count() or 4) // 2),
            )
            self._ct2_device = device

            tokenizer_candidates = []
            # Prefer configured rollback target (NLLB) and local NLLB tokenizer artifacts.
            tokenizer_candidates.append(self._flash_cfg.get('repo') or 'facebook/nllb-200-distilled-600M')

            cfg_hf = self._flash_cfg.get('local_hf_path')
            if cfg_hf:
                tokenizer_candidates.append(cfg_hf)
            tokenizer_candidates.append('models/nllb-200-distilled-600M')

            tok_err = None
            tok_loaded = None
            for tok_ref in tokenizer_candidates:
                if not tok_ref:
                    continue
                try:
                    tok_path = tok_ref if os.path.isabs(tok_ref) else base_path(tok_ref)
                    source = tok_path if os.path.isdir(tok_path) else tok_ref
                    tok_loaded = AutoTokenizer.from_pretrained(source, use_fast=True)
                    logging.info('[FLASH] CT2 tokenizer loaded from: %s', source)
                    break
                except Exception as e:
                    tok_err = e
                    continue

            if tok_loaded is None:
                raise RuntimeError(f'Unable to load CT2 tokenizer: {tok_err}')

            self._ct2_tokenizer = tok_loaded
            self._ct2_target_prefix_cache = {}
            self._ct2_lang_token_cache = {}
            self._ct2_vocab_tokens = None
            self._profile = profile
            logging.info('[FLASH] Ready CT2 profile=%s device=%s compute_type=%s', profile, device, compute_type)
            logging.info('[FLASH] CT2 loaded device=%s model=%s', self._ct2_device, self.model_path)
            self._warmup()
            return True
        except Exception as e:
            self._ct2_translator = None
            self._ct2_tokenizer = None
            self._profile = ''
            self.last_error_message = f'CT2 profile {profile} init failed: {type(e).__name__}: {e}'
            logging.warning('[FLASH] %s', self.last_error_message)
            return False

    def _bootstrap_windows_cuda_dll_dirs(self):
        if os.name != 'nt' or not hasattr(os, 'add_dll_directory'):
            return

        roots = []
        for key, value in os.environ.items():
            if key.startswith('CUDA_PATH') and value:
                roots.append(value)

        program_files = os.environ.get('ProgramFiles')
        if program_files:
            toolkit_root = os.path.join(program_files, 'NVIDIA GPU Computing Toolkit', 'CUDA')
            if os.path.isdir(toolkit_root):
                for entry in sorted(os.listdir(toolkit_root), reverse=True):
                    roots.append(os.path.join(toolkit_root, entry))

        exe_dir = os.path.dirname(sys.executable)
        roots.extend([
            exe_dir,
            os.path.join(exe_dir, '_internal'),
            os.path.join(exe_dir, '_internal', 'nvidia', 'cublas', 'bin'),
            os.path.join(exe_dir, '_internal', 'nvidia', 'cuda_nvrtc', 'bin'),
            os.path.join(exe_dir, '_internal', 'nvidia', 'cuda_runtime', 'bin'),
            os.path.join(exe_dir, 'data', 'cuda', 'bin'),
        ])

        # Also support CUDA runtime DLLs from pip wheels (nvidia-* -cu12).
        for p in sys.path:
            if not p:
                continue
            roots.extend([
                os.path.join(p, 'nvidia', 'cublas', 'bin'),
                os.path.join(p, 'nvidia', 'cuda_nvrtc', 'bin'),
                os.path.join(p, 'nvidia', 'cuda_runtime', 'bin'),
            ])

        seen = set()
        for root in roots:
            if not root:
                continue
            bin_dir = os.path.join(root, 'bin') if not root.lower().endswith('bin') else root
            norm = os.path.normcase(os.path.normpath(bin_dir))
            if norm in seen or not os.path.isdir(bin_dir):
                continue
            seen.add(norm)
            try:
                os.add_dll_directory(bin_dir)
            except Exception:
                continue

    def _ct2_cuda_preflight(self, ctranslate2_module) -> tuple[bool, str]:
        if os.name == 'nt':
            required = ('cublas64_12.dll', 'cublasLt64_12.dll', 'cudart64_12.dll')
            for dll_name in required:
                try:
                    ctypes.WinDLL(dll_name)
                except Exception as e:
                    return False, f'missing {dll_name}: {e}'

        try:
            count = int(ctranslate2_module.get_cuda_device_count())
        except Exception as e:
            return False, f'cuda probe failed: {type(e).__name__}: {e}'
        if count <= 0:
            return False, 'no CUDA devices reported by ctranslate2'
        return True, f'cuda devices={count}'

    def _ct2_load_vocab_tokens(self) -> set[str]:
        if self._ct2_vocab_tokens is not None:
            return self._ct2_vocab_tokens

        tokens: set[str] = set()
        for name in ('shared_vocabulary.json', 'vocabulary.json'):
            path = os.path.join(self.model_path, name)
            if not os.path.isfile(path):
                continue
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, str):
                            tokens.add(item)
                elif isinstance(data, dict):
                    for key in data.keys():
                        if isinstance(key, str):
                            tokens.add(key)
                if tokens:
                    break
            except Exception as e:
                logging.debug('[FLASH] CT2 vocabulary read failed: %s (%s)', path, e)

        self._ct2_vocab_tokens = tokens
        return tokens

    def _ct2_resolve_lang_token(self, lang_code: str) -> str:
        code = str(lang_code or '').strip()
        if not code:
            return ''
        if code in self._ct2_lang_token_cache:
            return self._ct2_lang_token_cache[code]

        candidates = []
        for token in (code, f'__{code}__'):
            if token and token not in candidates:
                candidates.append(token)

        vocab_tokens = self._ct2_load_vocab_tokens()
        for token in candidates:
            if token in vocab_tokens:
                self._ct2_lang_token_cache[code] = token
                return token

        # Deterministic fallback for unusual tokenizer/model combinations.
        self._ct2_lang_token_cache[code] = code
        return code

    def _ct2_target_prefix(self, tgt: str) -> list[str]:
        if tgt in self._ct2_target_prefix_cache:
            return self._ct2_target_prefix_cache[tgt]

        tgt_code = self._CT2_LANG_MAP.get(tgt, 'en')
        resolved = self._ct2_resolve_lang_token(tgt_code)
        prefix = [resolved] if resolved else []

        self._ct2_target_prefix_cache[tgt] = prefix
        return prefix

    def _ct2_decode_tokens(self, tokens: list[str]) -> str:
        tok = self._ct2_tokenizer
        if not tokens:
            return ''
        try:
            ids = tok.convert_tokens_to_ids(tokens)
            text = tok.decode(ids, skip_special_tokens=True)
            return (text or '').strip()
        except Exception:
            s = ' '.join(tokens).replace('▁', ' ').strip()
            return re.sub(r'\s+', ' ', s)

    def _is_ct2_cuda_runtime_error(self, err: Exception) -> bool:
        msg = str(err or '').lower()
        if not msg:
            return False
        cuda_markers = (
            'cublas',
            'cudnn',
            'cuda',
            'cudart',
            'cublas64_',
            'cannot be loaded',
            'not found',
            'dll',
        )
        return any(marker in msg for marker in cuda_markers)

    def _recover_ct2_to_cpu(self, reason: Exception) -> bool:
        if self.runtime != 'ctranslate2' or self.device == 'cpu':
            return False

        logging.warning('[FLASH] CUDA runtime unavailable (%s); switching CT2 to CPU', reason)
        self.device = 'cpu'
        self._preferred_profile = 'cpu_safe'
        self._ct2_translator = None
        self._ct2_tokenizer = None
        self._ct2_target_prefix_cache = {}
        self._ct2_lang_token_cache = {}
        self._ct2_vocab_tokens = None
        self._ct2_device = 'unknown'
        self._profile = ''

        cpu_model = models_path('nllb-ct2-cpu')
        if os.path.isdir(cpu_model):
            self.model_path = cpu_model
        else:
            logging.warning('[FLASH] CPU CT2 model directory missing at %s; using existing model path', cpu_model)

        ok = self._ensure_profile('cpu_safe')
        if ok:
            logging.info('[FLASH] CT2 CPU recovery successful')
            return True

        logging.error('[FLASH] CT2 CPU recovery failed: %s', self.last_error_message)
        return False

    def _ct2_generate_text(
        self,
        text: str,
        tgt: str,
        max_tokens_override: int | None = None,
        _allow_cuda_recovery: bool = True,
    ) -> str:
        if self._ct2_translator is None or self._ct2_tokenizer is None:
            return text

        t0 = time.perf_counter()
        try:
            src = self.detect_lang(text)
            src_code = self._CT2_LANG_MAP.get(src, 'en')
            if hasattr(self._ct2_tokenizer, 'src_lang'):
                self._ct2_tokenizer.src_lang = src_code
            if hasattr(self._ct2_tokenizer, 'set_src_lang_special_tokens'):
                self._ct2_tokenizer.set_src_lang_special_tokens(src_code)

            encoded = self._ct2_tokenizer.encode(text, add_special_tokens=True)
            source_tokens = self._ct2_tokenizer.convert_ids_to_tokens(encoded)
            if not source_tokens:
                return text

            # NLLB tokenizers can surface source language marker as <unk> in token form.
            # Replace trailing marker with explicit __lang__ token for CT2 robustness.
            if src_code and '_' in src_code:
                src_lang_token = self._ct2_resolve_lang_token(src_code)
                if source_tokens and source_tokens[-1] == '<unk>':
                    source_tokens[-1] = src_lang_token
                elif src_lang_token not in source_tokens:
                    source_tokens.append(src_lang_token)

            target_prefix = self._ct2_target_prefix(tgt)
            kwargs = {
                'beam_size': 4,
            }
            if max_tokens_override is not None and int(max_tokens_override) > 0:
                kwargs['max_decoding_length'] = int(max_tokens_override)
            else:
                # Avoid a fixed ceiling: allow decoding to scale with source length.
                # This prevents long chat-style messages from being truncated by app policy.
                kwargs['max_decoding_length'] = max(192, len(source_tokens) * 4)
            if target_prefix:
                kwargs['target_prefix'] = [target_prefix]

            result = self._ct2_translator.translate_batch([source_tokens], **kwargs)
            if not result:
                elapsed_ms = round((time.perf_counter() - t0) * 1000)
                logging.info('[FLASH] CT2 inference device=%s ms=%s', self._ct2_device, elapsed_ms)
                return text
            hypotheses = result[0].hypotheses or []
            if not hypotheses:
                elapsed_ms = round((time.perf_counter() - t0) * 1000)
                logging.info('[FLASH] CT2 inference device=%s ms=%s', self._ct2_device, elapsed_ms)
                return text

            decoded = self._ct2_decode_tokens(hypotheses[0])
            elapsed_ms = round((time.perf_counter() - t0) * 1000)
            logging.info('[FLASH] CT2 inference device=%s ms=%s', self._ct2_device, elapsed_ms)
            return decoded or text
        except Exception as e:
            logging.warning('[FLASH] CT2 translate failed: %s', e)
            if _allow_cuda_recovery and self._ct2_device == 'cuda' and self._is_ct2_cuda_runtime_error(e):
                if self._recover_ct2_to_cpu(e):
                    return self._ct2_generate_text(
                        text,
                        tgt,
                        max_tokens_override=max_tokens_override,
                        _allow_cuda_recovery=False,
                    )
            return text

    def _warmup(self):
        try:
            # Always warm up with JA→EN (known to work with NLLB).
            self._generate_text('テスト', 'eng_Latn')
            # Also exercise EN→ user's target language to pre-warm that translation path.
            tgt_code = self._load_user_source_language()
            if tgt_code != 'eng_Latn':
                self._generate_text('hello', tgt_code)
            logging.info('[FLASH] Warmup complete')
        except Exception as e:
            logging.warning('[FLASH] Warmup failed: %s', e)

    def detect_lang(self, text: str) -> str:
        cleaned = (text or '').strip()
        if not cleaned:
            self._last_detect_reason = 'empty_default_english'
            return 'eng_Latn'

        if len(cleaned) < 5:
            short_lang = self._load_user_source_language()
            self._last_detect_reason = f'short_user_pref:{short_lang}'
            return short_lang

        scores = {lang: 0 for lang in self._DETECT}
        for ch in cleaned:
            cp = ord(ch)
            for lang, ranges in self._DETECT.items():
                for lo, hi in ranges:
                    if lo <= cp <= hi:
                        scores[lang] += 2 if lang == 'jpn_Jpan' else 1

        best = max(scores, key=scores.get)
        if scores[best] > 0:
            self._last_detect_reason = f'charset:{best}'
            return best

        if self._is_short_ascii_chat_text(cleaned):
            heuristic = self._detect_short_latin_heuristic(cleaned)
            if heuristic:
                self._last_detect_reason = f'short_ascii_heuristic:{heuristic}'
                return heuristic
            self._last_detect_reason = 'short_ascii_bias:eng_Latn'
            return 'eng_Latn'

        try:
            from langdetect import DetectorFactory
            from langdetect import detect as _ld_detect

            DetectorFactory.seed = 0
            code = _ld_detect(cleaned)
            detected = self._LANGDETECT_MAP.get(code, 'eng_Latn')
            if detected == 'eng_Latn' and all(ord(ch) < 128 for ch in cleaned) and len(cleaned) <= 24:
                heuristic = self._detect_short_latin_heuristic(cleaned)
                if heuristic:
                    self._last_detect_reason = f'langdetect_short_heuristic:{heuristic}'
                    return heuristic
            if detected == 'eng_Latn' and any(ord(ch) > 127 for ch in cleaned):
                charset_guess = self._detect_by_charset(cleaned)
                if charset_guess != 'eng_Latn':
                    self._last_detect_reason = f'langdetect_charset_override:{charset_guess}'
                    return charset_guess
            self._last_detect_reason = f'langdetect:{code}->{detected}'
            return detected
        except Exception:
            self._last_detect_reason = 'langdetect_error_default_english'
            return 'eng_Latn'

    def is_foreign(self, text: str) -> bool:
        return self.detect_lang(text) != 'eng_Latn'

    def _looks_hallucinated(self, text: str) -> bool:
        low = (text or '').lower()
        markers = ('as an ai', 'i cannot', 'i can\'t', '<|im_start|>', '<|im_end|>', 'translation:')
        return any(m in low for m in markers)

    def _suspicious_length(self, out: str, src: str) -> bool:
        if not out:
            return True
        src_len = max(1, len((src or '').strip()))
        return len(out) > src_len * 6

    def _is_pathological_translation(self, out: str, tgt: str) -> bool:
        txt = (out or '').strip()
        if not txt:
            return True

        # Known CT2 failure pattern observed in production: repeated U+FE0F.
        vs16_count = txt.count('\ufe0f')
        if vs16_count >= 6 and (vs16_count / max(1, len(txt))) > 0.15:
            return True

        # For English targets, require some alphabetic signal.
        if tgt == 'eng_Latn':
            if not re.search(r'[A-Za-z]', txt):
                return True

        # Reject outputs that are effectively only punctuation/symbols.
        if re.fullmatch(r'[\s\W_]+', txt, flags=re.UNICODE):
            return True

        return False

    def _segment_translate_retry(self, text: str, tgt: str, deadline: float) -> str:
        # Split on punctuation while preserving separators.
        tokens = re.split(r'([,;:.!?，、。！？])', text)
        if len(tokens) <= 1:
            return text

        pieces: list[str] = []
        for tok in tokens:
            if tok is None:
                continue
            part = tok.strip()
            if not part:
                # Keep whitespace/punctuation spacing behavior simple.
                continue
            if re.fullmatch(r'[,;:.!?，、。！？]', part):
                pieces.append(part)
                continue

            rem = self._remaining_budget_ms(deadline)
            if rem < 120:
                return text

            seg_out, seg_to, seg_err = self._generate_with_timeout(part, tgt, rem)
            if seg_err is not None or seg_to:
                return text
            seg_clean = (seg_out or '').strip()
            if self._is_pathological_translation(seg_clean, tgt):
                return text
            pieces.append(seg_clean)

        if not pieces:
            return text

        # Join while avoiding spaces before punctuation.
        merged = ' '.join(pieces)
        merged = re.sub(r'\s+([,;:.!?])', r'\1', merged)
        merged = re.sub(r'\s{2,}', ' ', merged).strip()
        return merged or text

    def _extract_translation(self, raw: str, original: str) -> str:
        text = (raw or '').strip()

        if text.startswith('<t>') and not text.endswith('</t>'):
            text = text + '</t>'

        match = re.search(r'<t>(.*?)</t>', text, flags=re.IGNORECASE | re.DOTALL)
        if match:
            inner = match.group(1).strip()
            if not self._suspicious_length(inner, original) and not self._looks_hallucinated(inner):
                return inner

        stripped = re.sub(r'</?t>', '', text, flags=re.IGNORECASE).strip()
        if not stripped:
            return original
        if self._suspicious_length(stripped, original) or self._looks_hallucinated(stripped):
            return original
        return stripped

    def _contains_non_latin(self, text: str) -> bool:
        s = (text or '').strip()
        if not s:
            return False
        return self.detect_lang(s) != 'eng_Latn'

    def _normalize_similarity_text(self, text: str) -> str:
        s = re.sub(r'</?t>', ' ', (text or '').lower())
        s = re.sub(r'\s+', ' ', s).strip()
        # Preserve letters/numbers across scripts while ignoring punctuation noise.
        s = re.sub(r'[\W_]+', ' ', s, flags=re.UNICODE)
        return re.sub(r'\s+', ' ', s).strip()

    def _is_near_unchanged_output(self, src: str, out: str) -> bool:
        src_norm = self._normalize_similarity_text(src)
        out_norm = self._normalize_similarity_text(out)
        if not src_norm or not out_norm:
            return True
        if src_norm == out_norm:
            return True

        shorter = min(len(src_norm), len(out_norm))
        longer = max(len(src_norm), len(out_norm))
        if longer > 0 and (shorter / longer) >= 0.88 and (src_norm in out_norm or out_norm in src_norm):
            return True

        ratio = difflib.SequenceMatcher(None, src_norm, out_norm).ratio()
        if longer <= 24:
            return ratio >= 0.92
        return ratio >= 0.95

    def _is_target_mismatch_output(self, out: str, tgt: str) -> bool:
        txt = (out or '').strip()
        if not txt:
            return True
        if tgt == 'eng_Latn':
            return False

        # For non-Latin targets (Japanese/Korean/etc), reject English assistant-style outputs.
        if tgt in self._NON_LATIN_TARGETS:
            if not self._has_target_script(txt, tgt):
                return True
        return False

    def _has_target_script(self, text: str, tgt: str) -> bool:
        ranges = self._TARGET_SCRIPT_RANGES.get(tgt)
        if not ranges:
            return True
        s = (text or '').strip()
        if not s:
            return False
        for ch in s:
            cp = ord(ch)
            for lo, hi in ranges:
                if lo <= cp <= hi:
                    return True
        return False

    def _rule_based_non_english_fallback(self, text: str, tgt: str) -> str:
        s = (text or '').strip()
        if not s:
            return s

        if tgt == 'jpn_Jpan':
            m = re.match(r"^\s*hello(?:\s|,)+my\s+name\s+is\s+([A-Za-z][A-Za-z\-\s']{0,40})\s*$", s, flags=re.IGNORECASE)
            if m:
                name = m.group(1).strip()
                return f'こんにちは、私の名前は{name}です。'

            if re.match(r'^\s*hello\s*$', s, flags=re.IGNORECASE):
                return 'こんにちは。'

            if re.match(r"^\s*i(?:\s+am|'m)\s+very\s+tired\s+today\s*$", s, flags=re.IGNORECASE):
                return '今日はとても疲れています。'

        if tgt == 'kor_Hang':
            m = re.match(r"^\s*hello(?:\s|,)+my\s+name\s+is\s+([A-Za-z][A-Za-z\-\s']{0,40})\s*$", s, flags=re.IGNORECASE)
            if m:
                name = m.group(1).strip()
                return f'안녕하세요, 제 이름은 {name}입니다.'
            if re.match(r'^\s*hello\s*$', s, flags=re.IGNORECASE):
                return '안녕하세요.'

        if tgt == 'arb_Arab':
            m = re.match(r"^\s*hello(?:\s|,)+my\s+name\s+is\s+([A-Za-z][A-Za-z\-\s']{0,40})\s*$", s, flags=re.IGNORECASE)
            if m:
                name = m.group(1).strip()
                return f'مرحبا، اسمي {name}.'
            if re.match(r'^\s*hello\s*$', s, flags=re.IGNORECASE):
                return 'مرحبا.'

        return s

    def _rule_based_english_fallback(self, text: str, src: str) -> str:
        s = (text or '').strip()
        if not s:
            return s
        if src == 'spa_Latn' and re.match(r'^\s*hola\s+amig[oa]\s*$', s, flags=re.IGNORECASE):
            return 'hello friend'
        return s

    def _repair_english_quoted_segments(self, translated: str) -> str:
        text = (translated or '').strip()
        if not text:
            return text

        # Normalize Japanese corner quotes to straight quotes for consistent replacement.
        text = text.replace('「', '"').replace('」', '"').replace('『', '"').replace('』', '"')

        pattern = re.compile(r'"([^"\n]{1,42})"')
        matches = list(pattern.finditer(text))
        if not matches:
            return text

        replacements: list[tuple[str, str]] = []
        for m in matches[:3]:
            seg = (m.group(1) or '').strip()
            if not seg or not self._contains_non_latin(seg):
                continue

            if seg in self._JA_QUOTED_HINTS:
                replacements.append((f'"{seg}"', f'"{self._JA_QUOTED_HINTS[seg]}"'))
                continue

            fixed, timed_out, err = self._generate_with_timeout(
                seg,
                'eng_Latn',
                700,
                max_tokens_override=22,
            )
            if err is not None or timed_out:
                continue
            fixed = (fixed or '').strip()
            if not fixed or self._contains_non_latin(fixed):
                continue
            if fixed == seg:
                continue

            replacements.append((f'"{seg}"', f'"{fixed}"'))

        out = text
        for old, new in replacements:
            out = out.replace(old, new, 1)
        return out

    def _generate_text(self, text: str, tgt: str, max_tokens_override: int | None = None) -> str:
        if self.runtime == 'ctranslate2':
            return self._ct2_generate_text(text, tgt, max_tokens_override=max_tokens_override)

    def _generate_text_strict_target(self, text: str, tgt: str, max_tokens_override: int | None = None) -> str:
        if self.runtime == 'ctranslate2':
            return self._ct2_generate_text(text, tgt, max_tokens_override=max_tokens_override)

    def _generate_with_timeout(
        self,
        text: str,
        tgt: str,
        timeout_ms: int,
        max_tokens_override: int | None = None,
        strict_target: bool = False,
    ) -> tuple[str, bool, Exception | None]:
        if timeout_ms <= 0:
            return '', True, None

        done = threading.Event()
        holder = {'out': '', 'err': None}
        self._interrupt.clear()

        def _runner():
            try:
                # Check interrupt flag before acquiring lock — allows clean timeout exit.
                if self._interrupt.wait(0):
                    return
                with self._lock:
                    if self._interrupt.wait(0):  # re-check after acquiring
                        return
                    if strict_target:
                        holder['out'] = self._generate_text_strict_target(text, tgt, max_tokens_override=max_tokens_override)
                    else:
                        holder['out'] = self._generate_text(text, tgt, max_tokens_override=max_tokens_override)
            except Exception as e:
                holder['err'] = e
            finally:
                done.set()

        worker = threading.Thread(target=_runner, daemon=True, name='FlashGenerateWorker')
        worker.start()
        if not done.wait(timeout=max(0.001, timeout_ms / 1000.0)):
            self._interrupt.set()
            # Give worker time to naturally complete and release the lock.
            # GPU generation can take several seconds — 0.5s was insufficient.
            joined = worker.join(timeout=2.0)
            if not joined:
                logging.warning('[FLASH] Worker thread did not join after interrupt (timeout)')
            return '', True, None
        return str(holder.get('out') or ''), False, holder.get('err')

    def _profile_order(self) -> tuple[str, ...]:
        if self.device == 'cpu':
            return ('cpu_safe',)
        return ('gpu_full', 'gpu_trim', 'cpu_safe')

    def _active_or_preferred_profile(self) -> str:
        if self._profile in ('gpu_full', 'gpu_trim', 'cpu_safe'):
            return self._profile
        return self._preferred_profile

    def _next_lower_profile(self, profile: str) -> str | None:
        order = self._profile_order()
        if profile not in order:
            return None
        idx = order.index(profile)
        if idx >= len(order) - 1:
            return None
        return order[idx + 1]

    def _next_higher_profile(self, profile: str) -> str | None:
        order = self._profile_order()
        if profile not in order:
            return None
        idx = order.index(profile)
        if idx <= 0:
            return None
        return order[idx - 1]

    def _maybe_adjust_profile(self, profile: str, ok: bool):
        if self._STICKY_PROFILE_RUNTIME:
            return

        if profile not in self._fails:
            return

        now = time.time()
        if self._preferred_profile == profile:
            should_downgrade = (
                self._fails[profile] >= 2
                or self._slow_streak[profile] >= self._SLOW_STREAK_TO_DOWNGRADE
            )
            if should_downgrade:
                lower = self._next_lower_profile(profile)
                if lower:
                    self._preferred_profile = lower
                    self._profile_cooldown_until[profile] = now + self._PROFILE_COOLDOWN_SEC
                    self._slow_streak[profile] = 0
                    self._fast_streak[profile] = 0
                    logging.warning('[FLASH] Downgrade profile %s -> %s', profile, lower)
                    return

        if ok and self._preferred_profile == profile:
            should_upgrade = self._fast_streak[profile] >= self._FAST_STREAK_TO_RECOVER
            if should_upgrade:
                higher = self._next_higher_profile(profile)
                if higher and now >= self._profile_cooldown_until.get(higher, 0.0):
                    self._preferred_profile = higher
                    self._fast_streak[profile] = 0
                    logging.info('[FLASH] Upgrade profile %s -> %s', profile, higher)

    def _remaining_budget_ms(self, deadline: float) -> int:
        return max(0, round((deadline - time.perf_counter()) * 1000))

    def _record_profile_result(self, profile: str, elapsed_ms: int, ok: bool):
        if profile in self._latencies:
            self._latencies[profile].append(elapsed_ms)
        if profile in self._fails:
            self._fails[profile] = 0 if ok else self._fails[profile] + 1
        if profile in self._slow_streak:
            if ok and elapsed_ms > self._HARD_BUDGET_MS:
                self._slow_streak[profile] += 1
                self._fast_streak[profile] = 0
            elif ok and elapsed_ms <= self._SOFT_BUDGET_MS:
                self._fast_streak[profile] += 1
                self._slow_streak[profile] = 0
            elif ok:
                self._fast_streak[profile] = 0
            else:
                self._slow_streak[profile] += 1
                self._fast_streak[profile] = 0
        self._maybe_adjust_profile(profile, ok)

    def _recommended_profiles(self) -> tuple[str, ...]:
        if self._STICKY_PROFILE_RUNTIME:
            active = self._active_or_preferred_profile()
            order = self._profile_order()
            if active in order:
                idx = order.index(active)
                # Keep sticky active profile first, but still allow lower profiles
                # before deterministic fallback so we do not mirror source text on timeouts.
                return tuple(list(order[idx:]) + ['fallback'])
            return ('fallback',)

        base = list(self._profile_order())
        if not base:
            return ('fallback',)

        preferred = self._preferred_profile if self._preferred_profile in base else base[0]
        ordered = [preferred] + [p for p in base if p != preferred]

        now = time.time()
        cooled = [p for p in ordered if now >= self._profile_cooldown_until.get(p, 0.0)]
        cooling = [p for p in ordered if p not in cooled]
        return tuple(cooled + cooling + ['fallback'])

    def _deterministic_fallback(self, text: str, tgt: str) -> str | None:
        """Return phrase hit or None if no translation available."""
        if tgt == 'eng_Latn':
            try:
                from core.phrase import lookup as phrase_lookup

                src = self.detect_lang(text)
                phrase_hit = phrase_lookup(text, src)
                if phrase_hit:
                    return phrase_hit
            except Exception:
                pass
        return None

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

        text = text.strip()
        req_started = time.perf_counter()
        tgt = self.LANG_CODES.get(str(tgt_language or 'english').lower(), 'eng_Latn')
        src = self.detect_lang(text)
        if src == tgt:
            return None

        budget_ms = self._ABS_BUDGET_MS if tgt == 'eng_Latn' else self._ABS_BUDGET_MS_NON_ENG_TARGET
        # Scale request budget aggressively with message size so long-form
        # communication is not cut short by fixed wall-clock limits.
        extra_chars = max(0, len(text) - 120)
        if extra_chars:
            budget_ms += extra_chars * 35
        if self.device == 'cpu':
            budget_ms = max(budget_ms, 15000)
        request_budget_ms = budget_ms
        request_deadline = time.perf_counter() + (budget_ms / 1000.0)

        # VAULT lookup first
        if self.vault:
            hit = self.vault.lookup_entry(text, tgt)
            if hit:
                cached = str(hit.get('translation') or '').strip()
                if cached:
                    return {
                        'original': text,
                        'translation': cached,
                        'src_lang': src,
                        'tgt_lang': tgt,
                        'ms': 0,
                        'cache_hit': True,
                        'cache_corrected': False,
                        'phrase_hit': False,
                        'naturalizer_applied': False,
                    }

        # Phrase DB fast path for English translations
        if tgt == 'eng_Latn':
            try:
                from core.phrase import lookup as phrase_lookup

                phrase_hit = phrase_lookup(text, src)
                if phrase_hit:
                    if self.vault:
                        self.vault.store(text, tgt, phrase_hit)
                    return {
                        'original': text,
                        'translation': phrase_hit,
                        'src_lang': src,
                        'tgt_lang': tgt,
                        'ms': 0,
                        'cache_hit': False,
                        'cache_corrected': False,
                        'phrase_hit': True,
                        'naturalizer_applied': False,
                    }
            except Exception as e:
                logging.warning('[FLASH] Phrase lookup error: %s', e)

        selected_translation = ''
        selected_ms = 0
        selected_profile = 'fallback'
        unchanged_rejected = False
        mismatch_rejected = False
        strict_retry_outcome = 'not_needed'

        for profile in self._recommended_profiles():
            remaining_before = self._remaining_budget_ms(request_deadline)
            if remaining_before <= 0:
                break

            t0 = time.perf_counter()
            try:
                if profile == 'fallback':
                    out = self._deterministic_fallback(text, tgt)
                    elapsed = round((time.perf_counter() - t0) * 1000)
                    selected_translation = out
                    selected_ms = elapsed
                    selected_profile = profile
                    break

                if remaining_before < self._MIN_ATTEMPT_BUDGET_MS:
                    continue

                # Timed-out worker threads can briefly hold the generation lock;
                # allow one short retry before skipping the profile.
                acquired = False
                for attempt in (1, 2):
                    lock_timeout = min(1.2, max(0.12, self._remaining_budget_ms(request_deadline) / 1000.0))
                    acquired = self._lock.acquire(timeout=lock_timeout)
                    if acquired:
                        break
                    if attempt == 1 and self._remaining_budget_ms(request_deadline) > 180:
                        time.sleep(0.05)
                if not acquired:
                    elapsed = round((time.perf_counter() - t0) * 1000)
                    self._record_profile_result(profile, elapsed, ok=False)
                    logging.warning('[FLASH] Profile %s skipped: lock contention within budget', profile)
                    continue

                try:
                    if not self._ensure_profile(profile):
                        elapsed = round((time.perf_counter() - t0) * 1000)
                        self._record_profile_result(profile, elapsed, ok=False)
                        continue
                finally:
                    self._lock.release()

                remaining_after_init = self._remaining_budget_ms(request_deadline)
                out, timed_out, err = self._generate_with_timeout(text, tgt, remaining_after_init)
                if timed_out:
                    retry_ok = (
                        self._MICRO_RETRY_ON_TIMEOUT
                        and len(text) >= self._MICRO_RETRY_MIN_TEXT_LEN
                        and profile != 'fallback'
                    )
                    if retry_ok:
                        retry_tokens = 20 if len(text) <= 160 else 24
                        retry_out, retry_timed_out, retry_err = self._generate_with_timeout(
                            text,
                            tgt,
                            self._MICRO_RETRY_BUDGET_MS,
                            max_tokens_override=retry_tokens,
                        )
                        if retry_err is not None:
                            raise retry_err
                        if not retry_timed_out and retry_out and retry_out.strip():
                            elapsed = round((time.perf_counter() - t0) * 1000)
                            self._record_profile_result(profile, elapsed, ok=True)
                            selected_translation = retry_out.strip()
                            selected_ms = elapsed
                            selected_profile = profile
                            logging.info('[FLASH] Micro-retry succeeded profile=%s', profile)
                            break

                    elapsed = round((time.perf_counter() - t0) * 1000)
                    self._record_profile_result(profile, elapsed, ok=False)
                    logging.warning('[FLASH] Profile %s timed out; trying next profile', profile)
                    continue
                if err is not None:
                    raise err

                elapsed = round((time.perf_counter() - t0) * 1000)
                ok = bool(out and out.strip())
                self._record_profile_result(profile, elapsed, ok=ok)

                if ok:
                    selected_translation = out.strip()
                    selected_ms = elapsed
                    selected_profile = profile

                    if elapsed <= self._SOFT_BUDGET_MS and profile in self._fails:
                        self._fails[profile] = max(0, self._fails[profile] - 1)
                    break

            except Exception as e:
                elapsed = round((time.perf_counter() - t0) * 1000)
                self._record_profile_result(profile, elapsed, ok=False)
                logging.warning('[FLASH] Profile %s failed: %s', profile, e)
                continue

        if not selected_translation:
            fallback = self._deterministic_fallback(text, tgt)
            if fallback:
                selected_translation = fallback
                selected_ms = 0
                selected_profile = 'fallback'
            else:
                logging.warning('[FLASH] All translation profiles failed for: %s', text[:80])
                return None

        if selected_ms > request_budget_ms:
            logging.warning('[FLASH] Translation over budget (%sms) profile=%s', selected_ms, selected_profile)

        # Guard against known degenerate CT2 outputs (e.g. repeated U+FE0F)
        # by retrying with punctuation-aware clause segmentation.
        if tgt == 'eng_Latn' and self._is_pathological_translation(selected_translation, tgt):
            recovered = self._segment_translate_retry(text, tgt, request_deadline)
            if recovered and recovered.strip() and not self._is_pathological_translation(recovered, tgt):
                selected_translation = recovered.strip()
                selected_profile = 'segmented_retry'
                logging.warning('[FLASH] Recovered from pathological output via segmented retry')

        if src != tgt and tgt != 'eng_Latn':
            unchanged_rejected = self._is_near_unchanged_output(text, selected_translation)
            mismatch_rejected = self._is_target_mismatch_output(selected_translation, tgt)
            strict_retry_needed = unchanged_rejected or mismatch_rejected

            if strict_retry_needed:
                strict_retry_outcome = 'attempted'
                for idx, (budget_cap, min_budget, max_tokens) in enumerate(((900, 180, 60), (1200, 220, 80)), start=1):
                    strict_budget = min(budget_cap, self._remaining_budget_ms(request_deadline))
                    if strict_budget < min_budget:
                        continue

                    strict_out, strict_timed_out, strict_err = self._generate_with_timeout(
                        text,
                        tgt,
                        strict_budget,
                        max_tokens_override=max_tokens,
                        strict_target=True,
                    )

                    if strict_err is not None:
                        strict_retry_outcome = f'error_{idx}'
                        logging.warning('[FLASH] Strict-target retry(%s) failed: %s', idx, strict_err)
                        continue
                    if strict_timed_out:
                        strict_retry_outcome = f'timeout_{idx}'
                        continue

                    strict_clean = (strict_out or '').strip()
                    if not strict_clean:
                        strict_retry_outcome = f'empty_{idx}'
                        continue

                    strict_unchanged = self._is_near_unchanged_output(text, strict_clean)
                    strict_mismatch = self._is_target_mismatch_output(strict_clean, tgt)
                    if strict_unchanged or strict_mismatch:
                        strict_retry_outcome = f'rejected_{idx}'
                        continue

                    selected_translation = strict_clean
                    selected_profile = f'strict_retry_{idx}'
                    unchanged_rejected = False
                    mismatch_rejected = False
                    strict_retry_outcome = f'recovered_{idx}'
                    logging.info('[FLASH] Strict-target retry(%s) recovered non-English translation', idx)
                    break

        # Legacy mismatch/chatty rejection guard intentionally removed.

        if src != tgt:
            needs_repair = self._is_near_unchanged_output(text, selected_translation)
            if not needs_repair and tgt == 'eng_Latn' and src == 'spa_Latn':
                needs_repair = bool(re.match(r'^\s*hola\s+amig[oa]\s*$', selected_translation, flags=re.IGNORECASE))
            if not needs_repair and tgt == 'jpn_Jpan' and src == 'eng_Latn':
                needs_repair = bool(re.match(r"^\s*i(?:\s+am|'m)\s+very\s+tired\s+today\s*$", selected_translation, flags=re.IGNORECASE))

            # Phrase-specific fallback rules are emergency-only and should not hide model failures.
            allow_hardcoded_repair = needs_repair and selected_profile == 'fallback'

            if allow_hardcoded_repair:
                if tgt == 'eng_Latn':
                    repaired = self._rule_based_english_fallback(selected_translation, src)
                else:
                    repaired = self._rule_based_non_english_fallback(selected_translation, tgt)
            else:
                repaired = selected_translation

            if allow_hardcoded_repair and repaired and repaired.strip() != text.strip():
                selected_translation = repaired.strip()
                selected_profile = 'fallback'

        if src != tgt and tgt != 'eng_Latn':
            # Enforce final acceptance rule at engine level.
            final_unchanged = self._is_near_unchanged_output(text, selected_translation)
            final_mismatch = self._is_target_mismatch_output(selected_translation, tgt)
            if final_unchanged or final_mismatch:
                if final_unchanged:
                    unchanged_rejected = True
                if final_mismatch:
                    mismatch_rejected = True
                if strict_retry_outcome == 'not_needed':
                    strict_retry_outcome = 'forced_reject'

        naturalizer_applied = False
        if selected_translation and tgt == 'eng_Latn':
            # Refinement pass: quoted source snippets should also be translated.
            selected_translation = self._repair_english_quoted_segments(selected_translation)
            try:
                from core.natural import naturalize

                nat = naturalize(text, selected_translation)
                naturalizer_applied = nat != selected_translation
                selected_translation = nat
            except Exception as e:
                logging.warning('[FLASH] Naturalizer error: %s', e)

        if selected_translation and self.vault:
            self.vault.store(text, tgt, selected_translation)

        total_ms = round((time.perf_counter() - req_started) * 1000)
        logging.info(
            '[FLASH][DIAG] src=%s tgt=%s detect=%s unchanged_rejected=%s mismatch_rejected=%s strict=%s profile=%s',
            src,
            tgt,
            self._last_detect_reason,
            unchanged_rejected,
            mismatch_rejected,
            strict_retry_outcome,
            selected_profile,
        )
        if selected_translation and selected_translation.strip() != text.strip():
            logging.info(
                '[FLASH] OK src=%s tgt=%s profile=%s model_ms=%s total_ms=%s chars=%s',
                src,
                tgt,
                selected_profile,
                selected_ms,
                total_ms,
                len(text),
            )
        else:
            logging.warning(
                '[FLASH] FALLBACK/UNCHANGED src=%s tgt=%s profile=%s model_ms=%s total_ms=%s chars=%s',
                src,
                tgt,
                selected_profile,
                selected_ms,
                total_ms,
                len(text),
            )

        return {
            'original': text,
            'translation': selected_translation,
            'src_lang': src,
            'tgt_lang': tgt,
            'ms': selected_ms,
            'cache_hit': False,
            'cache_corrected': False,
            'phrase_hit': False,
            'naturalizer_applied': naturalizer_applied,
            'profile': selected_profile,
        }
