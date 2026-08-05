"""
tests/test_all_languages.py
Bidirectional language test: every supported language <-> English.
Run: python tests/test_all_languages.py
"""
import logging, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
logging.basicConfig(level=logging.WARNING)

from core.flash import FlashEngine
from core.vault import TranslationVault

vault = TranslationVault()
f = FlashEngine(device='cpu', vault=vault)

if not f.ready:
    print('ENGINE NOT READY')
    sys.exit(1)

test_sentences = {
    'japanese':   '\u4eca\u65e5\u306f\u826f\u3044\u30b2\u30fc\u30e0\u3060\u3063\u305f',
    'korean':     '\uc624\ub298 \uac8c\uc784 \uc7ac\ubbf8\uc788\uc5c8\uc5b4',
    'chinese':    '\u4eca\u5929\u6e38\u620f\u5f88\u597d\u73a9',
    'arabic':     '\u0627\u0644\u064a\u0648\u0645 \u0643\u0627\u0646\u062a \u0627\u0644\u0644\u0639\u0628\u0629 \u0645\u0645\u062a\u0639\u0629',
    'french':     "Aujourd'hui le jeu etait amusant",
    'spanish':    'Hoy el juego fue divertido',
    'german':     'Heute war das Spiel toll',
    'portuguese': 'Hoje o jogo foi divertido',
    'russian':    '\u0421\u0435\u0433\u043e\u0434\u043d\u044f \u0438\u0433\u0440\u0430 \u0431\u044b\u043b\u0430 \u043e\u0442\u043b\u0438\u0447\u043d\u0430\u044f',
    'thai':       '\u0e27\u0e31\u0e19\u0e19\u0e35\u0e49\u0e40\u0e01\u0e21\u0e2a\u0e19\u0e38\u0e01\u0e21\u0e32\u0e01',
    'vietnamese': 'H\xf4m nay tr\xf2 ch\u01a1i r\u1ea5t vui',
    'indonesian': 'Hari ini permainannya menyenangkan',
    'turkish':    'Bug\xfcn oyun \xe7ok g\xfczeldi',
}

SEP = '=' * 72
failures = []

print(SEP)
print(f'  INCOMING: foreign language -> English  ({len(test_sentences)} languages)')
print(SEP)
for lang, sentence in test_sentences.items():
    result = f.translate(sentence, 'english')
    if result and result.get('translation'):
        src = sentence[:28].ljust(28)
        tgt = result['translation'][:38].ljust(38)
        print(f'  PASS  {lang:<12}  {src}  ->  {tgt}  ({result["ms"]}ms)')
    else:
        print(f'  FAIL  {lang:<12}  no result returned')
        failures.append(f'{lang} -> english')

print()
print(SEP)
print(f'  OUTGOING: English -> every language  ({len(test_sentences)} languages)')
print(SEP)
base = 'Good game, well played!'
for lang in test_sentences:
    result = f.translate(base, lang)
    if result and result.get('translation'):
        tgt = result['translation'][:48].ljust(48)
        print(f'  PASS  -> {lang:<12}  {tgt}  ({result["ms"]}ms)')
    else:
        print(f'  FAIL  -> {lang:<12}  no result returned')
        failures.append(f'english -> {lang}')

print()
print(SEP)
if failures:
    print(f'  FAILURES ({len(failures)}):')
    for f_ in failures:
        print(f'    - {f_}')
    sys.exit(1)
else:
    total = len(test_sentences) * 2
    print(f'  ALL {total} TESTS PASSED')
print(SEP)
