"""
diag_detection.py — for every test sentence, run detect_lang() and report.
This will quantify which sentences get misidentified as English.
"""
import sys, os
sys.path.insert(0, '.')

# Force UTF-8 stdout
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from core.flash import FlashEngine

engine = FlashEngine(device='cuda')

# Warmup
for _ in range(2):
    engine.translate("hello world", "english")

# Full corpus (subset that matters)
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

# Group: detect_lang() vs intended language
print(f"\n{'='*80}")
print("LANGUAGE DETECTION ANALYSIS")
print(f"{'='*80}")
print(f"{'intended':<12} {'sentence':<35} {'detected':<12} {'reason'}")
print(f"{'-'*80}")

stats = {}
for intended_lang, sentences in TEST.items():
    correct = 0
    total = len(sentences)
    for sent in sentences:
        detected = engine.detect_lang(sent)
        reason = engine._last_detect_reason
        correct += (detected == engine.LANG_CODES[intended_lang])
        marker = "✓" if detected == engine.LANG_CODES[intended_lang] else "✗"
        sent_display = sent[:33]
        print(f"  {intended_lang:<10} {marker} {sent_display:<33} -> {detected:<12} ({reason})")
    stats[intended_lang] = f"{correct}/{total}"
    print()

print(f"\n{'='*80}")
print("SUMMARY")
print(f"{'='*80}")
for lang, score in stats.items():
    print(f"  {lang:<12} {score}")