"""
bench.py — one-shot latency benchmark for the paper.

Sweeps:
  - 20 sentences x 10 language pairs x 5 runs on GPU (filtered: timeouts excluded)
  - same matrix on CPU
  - beam-size sweep {1, 2, 4, 8} on a 10-sentence subset, GPU

Writes results to bench_results.json and prints a summary table.

Usage:
  .venv/Scripts/python.exe bench.py [--gpu-only | --cpu-only | --all]
"""
import io
import json
import os
import sys
import time
import statistics

# UTF-8 stdout so CJK doesn't crash Windows cp1252 console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.flash import FlashEngine


# ---------------------------------------------------------------------------
# Test corpus: 20 sentences per language, 10 source languages
# ---------------------------------------------------------------------------

TEST_SENTENCES = {
    "japanese": [
        "今日一緒にゲームしよう！", "ナイスプレイ！", "助けてくれ！敵が三人いる",
        "ちょっと待って", "ありがとう", "もう一度やろう", "ごめん、遅れた",
        "勝った！", "このボスは強すぎる", "次のラウンドいくぞ", "アイテムを共有して",
        "チームが弱い", "敵を倒した", "マップを見て", "チャットで話せない",
        "リロードして", "カバーに入って", "ポジションを取れ", "ヘルスが残り少ない",
        "一人でやる",
    ],
    "korean": [
        "오늘 같이 게임하자!", "잘 했어!", "도와줘, 적이 셋이야", "잠깐만",
        "고마워", "다시 하자", "미안, 늦었어", "이겼다!", "이 보스는 너무 강해",
        "다음 라운드 가자", "아이템 공유해", "팀이 약해", "적을 죽였어",
        "지도를 봐", "채팅으로 말할 수 없어", "재장전해", "엄폐해",
        "위치 잡아", "체력이 얼마 안 남았어", "혼자 할게",
    ],
    "chinese": [
        "今天一起打游戏吧！", "打得好！", "帮帮我，有三个敌人", "等一下",
        "谢谢", "再来一次", "对不起，我迟到了", "赢了！", "这个boss太强了",
        "下一轮走起", "分享装备", "团队太弱了", "我干掉敌人了",
        "看地图", "不能聊天说话", "换弹", "找掩护", "占位置",
        "血量不多了", "我自己来",
    ],
    "french": [
        "On joue ensemble aujourd'hui !", "Bien joué !",
        "Aide-moi, il y a trois ennemis", "Attends une seconde", "Merci",
        "On refait ça", "Désolé, je suis en retard", "On a gagné !",
        "Ce boss est trop fort", "Prochaine manche", "Partage l'objet",
        "L'équipe est faible", "J'ai tué l'ennemi", "Regarde la carte",
        "Je ne peux pas parler", "Recharge", "Mets-toi à couvert",
        "Prends position", "J'ai presque plus de vie", "Je fais ça seul",
    ],
    "spanish": [
        "Jugamos juntos hoy", "Bien jugado!", "Ayuda, hay tres enemigos",
        "Espera un momento", "Gracias", "Otra vez", "Perdón, llegué tarde",
        "Ganamos!", "Este jefe es muy fuerte", "Siguiente ronda",
        "Comparte el objeto", "El equipo es débil", "Maté al enemigo",
        "Mira el mapa", "No puedo chatear", "Recarga", "Tapa",
        "Toma posición", "Casi sin vida", "Lo hago solo",
    ],
    "german": [
        "Lasst uns heute zusammen spielen", "Gut gespielt!",
        "Hilfe, drei Feinde", "Warte kurz", "Danke", "Nochmal",
        "Sorry, bin spät", "Gewonnen!", "Dieser Boss ist zu stark",
        "Nächste Runde", "Item teilen", "Team ist schwach",
        "Feind erledigt", "Schau auf die Karte", "Kann nicht chatten",
        "Nachladen", "Deckung", "Position halten", "Wenig Leben",
        "Mach ich allein",
    ],
    "portuguese": [
        "Vamos jogar juntos hoje", "Boa jogada!", "Socorro, três inimigos",
        "Espera um segundo", "Obrigado", "De novo",
        "Desculpa, cheguei atrasado", "Ganhamos!",
        "Esse chefe é forte demais", "Próxima rodada", "Compartilha o item",
        "Time está fraco", "Matei o inimigo", "Olha o mapa",
        "Não consigo conversar", "Recarrega", "Cobertura", "Posição",
        "Pouca vida", "Faço sozinho",
    ],
    "russian": [
        "Давай сегодня поиграем вместе", "Хорошая игра!",
        "Помоги, трое врагов", "Подожди", "Спасибо", "Ещё раз",
        "Извини, опоздал", "Победили!", "Этот босс слишком сильный",
        "Следующий раунд", "Поделись предметом", "Команда слабая",
        "Убил врага", "Смотри карту", "Не могу говорить", "Перезаряди",
        "Укройся", "Займи позицию", "Мало здоровья", "Сделаю сам",
    ],
    "thai": [
        "วันนี้เล่นเกมด้วยกัน", "เล่นดีมาก!", "ช่วยด้วย มีศัตรูสามตัว",
        "รอแป๊บ", "ขอบคุณ", "เล่นอีกครั้ง", "ขอโทษ มาช้า", "ชนะแล้ว!",
        "บอสนี้แข็งเกินไป", "รอบต่อไป", "แชร์ไอเทม", "ทีมอ่อน",
        "ฆ่าศัตรูแล้ว", "ดูแผนที่", "แชทไม่ได้", "รีโหลด", "หลบ",
        "ยึดตำแหน่ง", "เลือดเหลือน้อย", "ทำคนเดียว",
    ],
    "vietnamese": [
        "Hôm nay chơi game cùng nhau nhé", "Chơi hay quá!",
        "Cứu tôi, có ba kẻ địch", "Đợi một chút", "Cảm ơn",
        "Chơi lại", "Xin lỗi, đến muộn", "Thắng rồi!",
        "Boss này mạnh quá", "Vòng tiếp theo", "Chia sẻ đồ",
        "Đội yếu", "Giết địch rồi", "Nhìn bản đồ",
        "Không chat được", "Nạp đạn", "Tìm chỗ ẩn nấp",
        "Giữ vị trí", "Ít máu", "Làm một mình",
    ],
    "english": [
        "good game, well played", "nice shot", "need help", "one second",
        "thanks", "let's try again", "sorry i'm late", "we won",
        "this boss is too strong", "next round", "share the item",
        "team is weak", "enemy down", "check the map",
        "can't talk right now", "reload", "take cover", "hold position",
        "low health", "i'll solo this",
    ],
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

TIMEOUT_MS = 5000  # engine internal timeout — calls that hit this are failures


def _bench_one(engine, src_lang, sentence, tgt_lang, n_runs):
    """Run n_runs translations. Return (success_times, failure_count)."""
    engine.translate(sentence, tgt_lang)  # warmup, ignored
    success_times = []
    failures = 0
    for _ in range(n_runs):
        t0 = time.perf_counter()
        result = engine.translate(sentence, tgt_lang)
        elapsed_ms = round((time.perf_counter() - t0) * 1000)
        if result and result.get("translation"):
            success_times.append(elapsed_ms)
        else:
            failures += 1
    return success_times, failures


def run_matrix(device, label, n_runs=5):
    print(f"\n{'=' * 72}")
    print(f"  Loading {label} engine...", flush=True)
    t0 = time.perf_counter()
    engine = FlashEngine(device=device)
    if not engine.ready:
        print(f"  {label} engine NOT READY: {engine.last_error_message}")
        return {}
    load_ms = round((time.perf_counter() - t0) * 1000)
    print(f"  Loaded in {load_ms} ms, profile={engine._profile}, device={engine._ct2_device}")
    print(f"{'=' * 72}\n")

    results = {}
    for src_lang, tgt_lang in LANGUAGE_PAIRS:
        sentences = TEST_SENTENCES.get(src_lang, [])
        if not sentences:
            continue
        pair_key = f"{src_lang}->{tgt_lang}"
        all_success = []
        total_failures = 0
        total_attempts = 0
        for sentence in sentences:
            s, f = _bench_one(engine, src_lang, sentence, tgt_lang, n_runs)
            all_success.extend(s)
            total_failures += f
            total_attempts += n_runs
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
            min_s = f"{r['min_ms']:>5}" if r['min_ms'] is not None else "  -- "
            max_s = f"{r['max_ms']:>5}" if r['max_ms'] is not None else "  -- "
            std_s = f"{r['stdev_ms']:>5.1f}" if r['mean_ms'] is not None else "  -- "
            print(
                f"  {pair_key:<22}  mean={mean_s}ms  med={med_s}  "
                f"min={min_s}  max={max_s}  std={std_s}  "
                f"fail={r['failure_rate']:.0%} ({r['successes']}/{r['attempts']})"
            )
    return results


def run_beam_sweep():
    """Beam-size sweep on GPU with a 10-sentence subset. Use a fresh engine per beam."""
    print(f"\n{'=' * 72}")
    print(f"  Beam-size sweep on GPU (10 sentences × 3 runs each)...", flush=True)
    print(f"{'=' * 72}\n")

    from core.flash import FlashEngine

    sentences = [
        ("japanese", "english", "今日一緒にゲームしよう！"),
        ("japanese", "english", "助けてくれ！敵が三人いる"),
        ("japanese", "english", "このボスは強すぎる"),
        ("korean", "english", "오늘 같이 게임하자!"),
        ("korean", "english", "도와줘, 적이 셋이야"),
        ("chinese", "english", "今天一起打游戏吧！"),
        ("chinese", "english", "帮帮我，有三个敌人"),
        ("english", "japanese", "good game, well played"),
        ("english", "japanese", "need help right now"),
        ("english", "korean", "let's try again"),
    ]

    beam_results = {}
    for beam_size in (1, 2, 4, 8):
        # Force a particular beam_size via the kwargs dict in flash.py by
        # wrapping _ct2_generate_text. We monkey-patch the engine instance.
        engine = FlashEngine(device="cuda")
        if not engine.ready:
            beam_results[beam_size] = {"error": engine.last_error_message}
            continue
        # Override beam_size in kwargs by intercepting the kwargs dict
        original_generate = engine._ct2_generate_text

        def make_generate(orig, beam=beam_size):
            def wrapped(text, tgt, max_tokens_override=None, _allow_cuda_recovery=True):
                # Build a custom path: re-implement with explicit beam_size
                import os as _os
                if engine._ct2_translator is None or engine._ct2_tokenizer is None:
                    return text
                try:
                    src = engine.detect_lang(text)
                    src_code = engine._CT2_LANG_MAP.get(src, "en")
                    if hasattr(engine._ct2_tokenizer, "src_lang"):
                        engine._ct2_tokenizer.src_lang = src_code
                    if hasattr(engine._ct2_tokenizer, "set_src_lang_special_tokens"):
                        engine._ct2_tokenizer.set_src_lang_special_tokens(src_code)
                    encoded = engine._ct2_tokenizer.encode(text, add_special_tokens=True)
                    source_tokens = engine._ct2_tokenizer.convert_ids_to_tokens(encoded)
                    if src_code and "_" in src_code:
                        src_lang_token = engine._ct2_resolve_lang_token(src_code)
                        if source_tokens and source_tokens[-1] == "<unk>":
                            source_tokens[-1] = src_lang_token
                        elif src_lang_token not in source_tokens:
                            source_tokens.append(src_lang_token)
                    target_prefix = engine._ct2_target_prefix(tgt)
                    kwargs = {"beam_size": beam}
                    if max_tokens_override and int(max_tokens_override) > 0:
                        kwargs["max_decoding_length"] = int(max_tokens_override)
                    else:
                        kwargs["max_decoding_length"] = max(192, len(source_tokens) * 4)
                    if target_prefix:
                        kwargs["target_prefix"] = [target_prefix]
                    result = engine._ct2_translator.translate_batch([source_tokens], **kwargs)
                    if not result or not result[0].hypotheses:
                        return text
                    return engine._ct2_decode_tokens(result[0].hypotheses[0]) or text
                except Exception as e:
                    return text
            return wrapped

        engine._ct2_generate_text = make_generate(original_generate, beam_size)

        all_times = []
        for src_lang, tgt_lang, sentence in sentences:
            # Warmup
            engine.translate(sentence, tgt_lang)
            t0 = time.perf_counter()
            r = engine.translate(sentence, tgt_lang)
            elapsed_ms = round((time.perf_counter() - t0) * 1000)
            if r and r.get("translation"):
                all_times.append(elapsed_ms)
        engine._ct2_generate_text = original_generate

        if all_times:
            beam_results[beam_size] = {
                "mean_ms": round(statistics.mean(all_times), 1),
                "median_ms": round(statistics.median(all_times), 1),
                "min_ms": min(all_times),
                "max_ms": max(all_times),
                "n": len(all_times),
            }
        else:
            beam_results[beam_size] = {"error": "all calls failed"}
        if "mean_ms" in beam_results[beam_size]:
            r = beam_results[beam_size]
            print(f"  beam={beam_size}  mean={r['mean_ms']:>7.1f}ms  "
                  f"median={r['median_ms']:>7.1f}ms  "
                  f"min={r['min_ms']:>5}  max={r['max_ms']:>5}  n={r['n']}")

    return beam_results


def main():
    mode = "all"
    if "--gpu-only" in sys.argv:
        mode = "gpu"
    elif "--cpu-only" in sys.argv:
        mode = "cpu"

    out = {}
    if mode in ("all", "gpu"):
        out["gpu"] = run_matrix("cuda", "GPU")
    if mode in ("all", "cpu"):
        out["cpu"] = run_matrix("cpu", "CPU")
    if mode in ("all", "gpu"):
        out["beam_sweep_gpu"] = run_beam_sweep()

    out["meta"] = {
        "ctranslate2_version": None,
        "gpu": "NVIDIA GeForce RTX 3080 10GB",
        "cuda_driver": None,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    try:
        import ctranslate2
        out["meta"]["ctranslate2_version"] = ctranslate2.__version__
    except Exception:
        pass
    try:
        import subprocess
        smi = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
            text=True, timeout=5,
        ).strip()
        out["meta"]["cuda_driver"] = smi
    except Exception:
        pass

    with open("bench_results.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
    print(f"\nResults written to bench_results.json")


if __name__ == "__main__":
    main()