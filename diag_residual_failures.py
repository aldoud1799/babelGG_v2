"""
diag_residual_failures.py — with the fasttext fix applied, find which specific
Portuguese and Chinese sentences still fail and why.
"""
import sys, os, time, json
sys.path.insert(0, '.')
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import ftlangdetect
from core.flash import FlashEngine

# Apply the fasttext fix
_ISO_TO_FLASH = {
    'ja': 'jpn_Jpan', 'ko': 'kor_Hang', 'zh': 'zho_Hans', 'zh-cn': 'zho_Hans',
    'ar': 'arb_Arab', 'fr': 'fra_Latn', 'es': 'spa_Latn', 'de': 'deu_Latn',
    'pt': 'por_Latn', 'ru': 'rus_Cyrl', 'th': 'tha_Thai', 'vi': 'vie_Latn',
    'id': 'ind_Latn', 'tr': 'tur_Latn', 'it': 'ita_Latn', 'nl': 'nld_Latn',
    'pl': 'pol_Latn', 'sv': 'swe_Latn', 'hi': 'hin_Deva', 'en': 'eng_Latn',
}
_orig = FlashEngine.detect_lang
def patched(self, text):
    cleaned = (text or '').strip()
    if not cleaned:
        return 'eng_Latn'
    try:
        r = ftlangdetect.detect(text=cleaned, low_memory=True)
        iso = r.get('lang', 'unknown')
        score = r.get('score', 0.0)
        flash = _ISO_TO_FLASH.get(iso, 'eng_Latn')
        if score >= 0.60:
            self._last_detect_reason = f'ft:{iso}({score:.2f})'
            return flash
    except Exception:
        pass
    return _orig(self, text)
FlashEngine.detect_lang = patched

# Full Portuguese and Chinese corpus (matches bench.py)
PORTUGUESE = [
    "Vamos jogar juntos hoje", "Boa jogada!", "Socorro, três inimigos",
    "Espera um segundo", "Obrigado", "De novo",
    "Desculpa, cheguei atrasado", "Ganhamos!",
    "Esse chefe é forte demais", "Próxima rodada", "Compartilha o item",
    "Time está fraco", "Matei o inimigo", "Olha o mapa",
    "Não consigo conversar", "Recarrega", "Cobertura", "Posição",
    "Pouca vida", "Faço sozinho",
]
CHINESE = [
    "今天一起打游戏吧！", "打得好！", "帮帮我，有三个敌人", "等一下",
    "谢谢", "再来一次", "对不起，我迟到了", "赢了！", "这个boss太强了",
    "下一轮走起", "分享装备", "团队太弱了", "我干掉敌人了",
    "看地图", "不能聊天说话", "换弹", "找掩护", "占位置",
    "血量不多了", "我自己来",
]

engine = FlashEngine(device='cuda')
print(f"Ready, profile={engine._profile}\n")

# Helper to run translation
def run_pair(src_lang, tgt_lang, sentences, n_runs=5):
    failures = []
    for sentence in sentences:
        # Warmup
        engine.translate(sentence, tgt_lang)
        # 5 runs
        for _ in range(n_runs):
            t0 = time.perf_counter()
            r = engine.translate(sentence, tgt_lang)
            elapsed = round((time.perf_counter()-t0)*1000)
            if not r:
                failures.append({'sentence': sentence, 'ms': elapsed})
                break  # one failure is enough
    return failures

print("="*80)
print("PORTUGUESE -> ENGLISH (with fasttext fix)")
print("="*80)
pt_failures = run_pair('portuguese', 'english', PORTUGUESE)
print(f"Failures: {len(pt_failures)}/{len(PORTUGUESE)}")
for f in pt_failures:
    sent = f['sentence']
    detected = engine.detect_lang(sent)
    reason = engine._last_detect_reason
    print(f"  - {sent!r:<45} detected={detected} reason={reason}")

# Try directly calling CT2 to see if model can translate
print("\n--- Direct CT2 calls (bypassing detection) ---")
for f in pt_failures[:5]:  # first 5
    sent = f['sentence']
    out = engine._generate_text(sent, 'eng_Latn')
    print(f"  {sent!r:<45} -> {out[:60]!r}")

print("\n" + "="*80)
print("CHINESE -> ENGLISH (with fasttext fix)")
print("="*80)
zh_failures = run_pair('chinese', 'english', CHINESE)
print(f"Failures: {len(zh_failures)}/{len(CHINESE)}")
for f in zh_failures:
    sent = f['sentence']
    detected = engine.detect_lang(sent)
    reason = engine._last_detect_reason
    print(f"  - {sent!r:<45} detected={detected} reason={reason}")

print("\n--- Direct CT2 calls (bypassing detection) ---")
for f in zh_failures[:5]:
    sent = f['sentence']
    out = engine._generate_text(sent, 'eng_Latn')
    print(f"  {sent!r:<45} -> {out[:60]!r}")

# Length analysis
print("\n" + "="*80)
print("LENGTH ANALYSIS")
print("="*80)
for label, fails in [('Portuguese', pt_failures), ('Chinese', zh_failures)]:
    if not fails:
        continue
    failed_sents = [f['sentence'] for f in fails]
    failed_lens = [len(s) for s in failed_sents]
    all_sents = PORTUGUESE if label == 'Portuguese' else CHINESE
    all_lens = [len(s) for s in all_sents]
    passed = [s for s in all_sents if s not in [f['sentence'] for f in fails]]
    passed_lens = [len(s) for s in passed]
    print(f"\n{label}:")
    print(f"  Failed: {len(failed_lens)} sentences, mean length={sum(failed_lens)/len(failed_lens):.1f} chars")
    print(f"  Passed: {len(passed_lens)} sentences, mean length={sum(passed_lens)/len(passed_lens):.1f} chars")
    print(f"  Failed examples: {failed_sents[:3]}")
    print(f"  Passed examples: {passed[:3]}")