"""
bench_with_fix.py — full translation benchmark with fasttext-based detection fix applied.
Re-runs the 10-pair × 20-sentence matrix and reports the new failure rates.
"""
import json
import os
import sys
import time
import statistics

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, '.')
import ftlangdetect

from core import flash as flash_mod
from core.flash import FlashEngine


# Patch detect_lang to use fasttext as primary detector with fallback to existing logic
_original_detect_lang = FlashEngine.detect_lang

# Map fasttext ISO codes to BabelGG BCP-47 codes
_ISO_TO_FLASH = {
    'ja': 'jpn_Jpan', 'ko': 'kor_Hang', 'zh': 'zho_Hans', 'zh-cn': 'zho_Hans',
    'ar': 'arb_Arab', 'fr': 'fra_Latn', 'es': 'spa_Latn', 'de': 'deu_Latn',
    'pt': 'por_Latn', 'ru': 'rus_Cyrl', 'th': 'tha_Thai', 'vi': 'vie_Latn',
    'id': 'ind_Latn', 'tr': 'tur_Latn', 'it': 'ita_Latn', 'nl': 'nld_Latn',
    'pl': 'pol_Latn', 'sv': 'swe_Latn', 'hi': 'hin_Deva',
    'en': 'eng_Latn',
}


def patched_detect_lang(self, text):
    """Use fasttext-langdetect as primary detector with confidence threshold."""
    cleaned = (text or '').strip()
    if not cleaned:
        self._last_detect_reason = 'empty_default_english'
        return 'eng_Latn'

    try:
        result = ftlangdetect.detect(text=cleaned, low_memory=True)
        ft_iso = result.get('lang', 'unknown')
        ft_score = result.get('score', 0.0)
        ft_flash = _ISO_TO_FLASH.get(ft_iso, 'eng_Latn')
        # High-confidence fasttext result wins
        if ft_score >= 0.60 and ft_flash in self._DETECT or ft_flash in (
            'fra_Latn', 'spa_Latn', 'deu_Latn', 'por_Latn', 'ita_Latn',
            'nld_Latn', 'pol_Latn', 'swe_Latn', 'rus_Cyrl', 'hin_Deva',
            'tur_Latn', 'vie_Latn', 'ind_Latn',
        ):
            self._last_detect_reason = f'ft:{ft_iso}->{ft_flash}({ft_score:.2f})'
            return ft_flash
    except Exception as e:
        self._last_detect_reason = f'ft_err:{e}'
        return _original_detect_lang(self, text)

    # Fall back to original detection (charset-based, heuristic)
    return _original_detect_lang(self, text)


FlashEngine.detect_lang = patched_detect_lang


# Now run the bench
TEST_SENTENCES = {
    "japanese": ["今日一緒にゲームしよう！", "ナイスプレイ！", "助けてくれ！敵が三人いる",
                 "ちょっと待って", "ありがとう", "もう一度やろう", "ごめん、遅れた",
                 "勝った！", "このボスは強すぎる", "次のラウンドいくぞ", "アイテムを共有して",
                 "チームが弱い", "敵を倒した", "マップを見て", "チャットで話せない",
                 "リロードして", "カバーに入って", "ポジションを取れ", "ヘルスが残り少ない",
                 "一人でやる"],
    "korean": ["오늘 같이 게임하자!", "잘 했어!", "도와줘, 적이 셋이야", "잠깐만",
               "고마워", "다시 하자", "미안, 늦었어", "이겼다!", "이 보스는 너무 강해",
               "다음 라운드 가자", "아이템 공유해", "팀이 약해", "적을 죽였어",
               "지도를 봐", "채팅으로 말할 수 없어", "재장전해", "엄폐해",
               "위치 잡아", "체력이 얼마 안 남았어", "혼자 할게"],
    "chinese": ["今天一起打游戏吧！", "打得好！", "帮帮我，有三个敌人", "等一下",
                "谢谢", "再来一次", "对不起，我迟到了", "赢了！", "这个boss太强了",
                "下一轮走起", "分享装备", "团队太弱了", "我干掉敌人了",
                "看地图", "不能聊天说话", "换弹", "找掩护", "占位置",
                "血量不多了", "我自己来"],
    "french": ["On joue ensemble aujourd'hui !", "Bien joué !",
               "Aide-moi, il y a trois ennemis", "Attends une seconde", "Merci",
               "On refait ça", "Désolé, je suis en retard", "On a gagné !",
               "Ce boss est trop fort", "Prochaine manche", "Partage l'objet",
               "L'équipe est faible", "J'ai tué l'ennemi", "Regarde la carte",
               "Je ne peux pas parler", "Recharge", "Mets-toi à couvert",
               "Prends position", "J'ai presque plus de vie", "Je fais ça seul"],
    "spanish": ["Jugamos juntos hoy", "Bien jugado!", "Ayuda, hay tres enemigos",
                "Espera un momento", "Gracias", "Otra vez", "Perdón, llegué tarde",
                "Ganamos!", "Este jefe es muy fuerte", "Siguiente ronda",
                "Comparte el objeto", "El equipo es débil", "Maté al enemigo",
                "Mira el mapa", "No puedo chatear", "Recarga", "Tapa",
                "Toma posición", "Casi sin vida", "Lo hago solo"],
    "german": ["Lasst uns heute zusammen spielen", "Gut gespielt!",
               "Hilfe, drei Feinde", "Warte kurz", "Danke", "Nochmal",
               "Sorry, bin spät", "Gewonnen!", "Dieser Boss ist zu stark",
               "Nächste Runde", "Item teilen", "Team ist schwach",
               "Feind erledigt", "Schau auf die Karte", "Kann nicht chatten",
               "Nachladen", "Deckung", "Position halten", "Wenig Leben",
               "Mach ich allein"],
    "portuguese": ["Vamos jogar juntos hoje", "Boa jogada!", "Socorro, três inimigos",
                   "Espera um segundo", "Obrigado", "De novo",
                   "Desculpa, cheguei atrasado", "Ganhamos!",
                   "Esse chefe é forte demais", "Próxima rodada", "Compartilha o item",
                   "Time está fraco", "Matei o inimigo", "Olha o mapa",
                   "Não consigo conversar", "Recarrega", "Cobertura", "Posição",
                   "Pouca vida", "Faço sozinho"],
}

LANGUAGE_PAIRS = [
    ("japanese", "english"),
    ("korean", "english"),
    ("chinese", "english"),
    ("english", "japanese"),
    ("english", "korean"),
    ("english", "chinese"),
    ("french", "english"),
    ("spanish", "english"),
    ("german", "english"),
    ("portuguese", "english"),
]


def main():
    print("Loading GPU engine with fasttext detection fix...")
    engine = FlashEngine(device='cuda')
    if not engine.ready:
        print(f"NOT READY: {engine.last_error_message}")
        return
    print(f"Ready, profile={engine._profile}\n")

    results = {}
    for src_lang, tgt_lang in LANGUAGE_PAIRS:
        sentences = TEST_SENTENCES.get(src_lang, [])
        if not sentences:
            continue
        pair_key = f"{src_lang}->{tgt_lang}"
        all_success = []
        total_failures = 0
        total_attempts = 0

        # Warmup
        engine.translate(sentences[0], tgt_lang)

        for sentence in sentences:
            # Warmup per sentence
            engine.translate(sentence, tgt_lang)
            for _ in range(5):
                t0 = time.perf_counter()
                result = engine.translate(sentence, tgt_lang)
                elapsed_ms = round((time.perf_counter() - t0) * 1000)
                total_attempts += 1
                if result and result.get('translation'):
                    all_success.append(elapsed_ms)
                else:
                    total_failures += 1

        if all_success or total_attempts:
            results[pair_key] = {
                "mean_ms": round(statistics.mean(all_success), 1) if all_success else None,
                "median_ms": round(statistics.median(all_success), 1) if all_success else None,
                "min_ms": min(all_success) if all_success else None,
                "max_ms": max(all_success) if all_success else None,
                "stdev_ms": round(statistics.stdev(all_success), 1) if len(all_success) > 1 else 0.0,
                "successes": len(all_success),
                "attempts": total_attempts,
                "failure_rate": round(total_failures / total_attempts, 3) if total_attempts else 0,
            }
            r = results[pair_key]
            mean_s = f"{r['mean_ms']:>7.1f}" if r['mean_ms'] is not None else "  --   "
            med_s = f"{r['median_ms']:>7.1f}" if r['median_ms'] is not None else "  --   "
            print(f"  {pair_key:<22}  mean={mean_s}ms  med={med_s}  "
                  f"fail={r['failure_rate']:.0%} ({r['successes']}/{r['attempts']})")

    out = {"gpu_with_fasttext_fix": results}
    with open("bench_results_with_fix.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
    print(f"\nResults written to bench_results_with_fix.json")


if __name__ == "__main__":
    main()