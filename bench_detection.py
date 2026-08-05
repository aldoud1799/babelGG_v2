"""
bench_detection.py — compare current detect_lang() vs fasttext-langdetect on the benchmark corpus.
"""
import sys, os
sys.path.insert(0, '.')

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from core.flash import FlashEngine
import ftlangdetect

# Same corpus as diag_detection.py
TEST = {
    "japanese": ["今日一緒にゲームしよう！", "ナイスプレイ！", "助けてくれ！敵が三人いる",
                 "ちょっと待って", "ありがとう", "もう一度やろう", "ごめん、遅れた",
                 "勝った！", "このボスは強すぎる", "次のラウンドいくぞ"],
    "korean": ["오늘 같이 게임하자!", "잘 했어!", "도와줘, 적이 셋이야", "잠깐만",
               "고마워", "다시 하자", "미안, 늦었어", "이겼다!",
               "이 보스는 너무 강해", "다음 라운드 가자"],
    "chinese": ["今天一起打游戏吧！", "打得好！", "帮帮我，有三个敌人", "等一下",
                "谢谢", "再来一次", "对不起，我迟到了", "赢了！",
                "这个boss太强了", "下一轮走起"],
    "french": ["On joue ensemble aujourd'hui !", "Bien joué !",
               "Aide-moi, il y a trois ennemis", "Attends une seconde", "Merci",
               "On refait ça", "Désolé, je suis en retard", "On a gagné !",
               "Ce boss est trop fort", "Prochaine manche"],
    "spanish": ["Jugamos juntos hoy", "Bien jugado!", "Ayuda, hay tres enemigos",
                "Espera un momento", "Gracias", "Otra vez", "Perdón, llegué tarde",
                "Ganamos!", "Este jefe es muy fuerte", "Siguiente ronda"],
    "german": ["Lasst uns heute zusammen spielen", "Gut gespielt!",
               "Hilfe, drei Feinde", "Warte kurz", "Danke", "Nochmal",
               "Sorry, bin spät", "Gewonnen!", "Dieser Boss ist zu stark",
               "Nächste Runde"],
    "portuguese": ["Vamos jogar juntos hoje", "Boa jogada!",
                   "Socorro, três inimigos", "Espera um segundo", "Obrigado",
                   "De novo", "Desculpa, cheguei atrasado", "Ganhamos!",
                   "Esse chefe é forte demais", "Próxima rodada"],
}

# Map fasttext ISO codes to BabelGG BCP-47 codes
ISO_TO_FLASH = {
    'ja': 'jpn_Jpan', 'ko': 'kor_Hang', 'zh': 'zho_Hans', 'zh-cn': 'zho_Hans',
    'ar': 'arb_Arab', 'fr': 'fra_Latn', 'es': 'spa_Latn', 'de': 'deu_Latn',
    'pt': 'por_Latn', 'ru': 'rus_Cyrl', 'th': 'tha_Thai', 'vi': 'vie_Latn',
    'id': 'ind_Latn', 'tr': 'tur_Latn', 'it': 'ita_Latn', 'nl': 'nld_Latn',
    'pl': 'pol_Latn', 'sv': 'swe_Latn', 'hi': 'hin_Deva',
    'en': 'eng_Latn',
}

print("Loading engine...")
engine = FlashEngine(device='cuda')

# Warmup
for _ in range(2):
    engine.translate("hello world", "english")

print(f"\n{'='*80}")
print(f"{'intended':<12} {'sentence':<35} {'current':<12} {'fasttext':<10} {'score':<6}")
print(f"{'-'*80}")

stats_current = {l: 0 for l in TEST}
stats_fasttext = {l: 0 for l in TEST}
total = 0

for intended_lang, sentences in TEST.items():
    for sent in sentences:
        total += 1
        # Current detection
        current_detected = engine.detect_lang(sent)
        current_correct = current_detected == engine.LANG_CODES[intended_lang]
        if current_correct:
            stats_current[intended_lang] += 1

        # Fasttext detection
        try:
            ft_result = ftlangdetect.detect(text=sent, low_memory=True)
            ft_iso = ft_result.get('lang', 'unknown')
            ft_score = ft_result.get('score', 0.0)
            ft_flash = ISO_TO_FLASH.get(ft_iso, 'eng_Latn')
            ft_correct = ft_flash == engine.LANG_CODES[intended_lang]
            if ft_correct:
                stats_fasttext[intended_lang] += 1
        except Exception as e:
            ft_iso = f"ERR:{e}"
            ft_score = 0.0
            ft_correct = False

        marker_c = "+" if current_correct else "-"
        marker_f = "+" if ft_correct else "-"
        sent_display = sent[:33]
        print(f"  {intended_lang:<10} {marker_c}/{marker_f} {sent_display:<33} "
              f"-> cur={current_detected:<10} ft={ft_iso:<8} ({ft_score:.2f})")

print(f"\n{'='*80}")
print("ACCURACY COMPARISON")
print(f"{'='*80}")
print(f"{'Language':<12} {'Current':<12} {'Fasttext':<12}")
print(f"{'-'*40}")
current_total = 0
fasttext_total = 0
for lang in TEST:
    c = stats_current[lang]
    f = stats_fasttext[lang]
    current_total += c
    fasttext_total += f
    print(f"  {lang:<10} {c}/{len(TEST[lang])}            {f}/{len(TEST[lang])}")
print(f"{'-'*40}")
print(f"  {'TOTAL':<10} {current_total}/{total}          {fasttext_total}/{total}")
print(f"  {'%':<10} {current_total/total*100:.0f}%             {fasttext_total/total*100:.0f}%")