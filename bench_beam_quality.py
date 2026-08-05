"""
bench_beam_quality.py — measure whether beam=4 actually produces better
translations than beam=1, using CTranslate2's own log-probability score
as a quality proxy. Higher score = higher model probability = "more
likely correct" by the model's own measure.

We also compare pairwise: how often does beam=4 differ from beam=1?
When they differ, which has higher score? When they agree, what
fraction of total corpus?
"""
import sys, os, time, statistics, json
sys.path.insert(0, '.')
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from core.flash import FlashEngine

# Test corpus: varied lengths and difficulty
TEST_SENTENCES = [
    # Japanese -> English (10 sentences)
    ("jpn_Jpan", "eng_Latn", "今日一緒にゲームしよう！"),
    ("jpn_Jpan", "eng_Latn", "ナイスプレイ！"),
    ("jpn_Jpan", "eng_Latn", "助けてくれ！敵が三人いる"),
    ("jpn_Jpan", "eng_Latn", "ちょっと待って"),
    ("jpn_Jpan", "eng_Latn", "ありがとう"),
    ("jpn_Jpan", "eng_Latn", "もう一度やろう"),
    ("jpn_Jpan", "eng_Latn", "ごめん、遅れた"),
    ("jpn_Jpan", "eng_Latn", "勝った！"),
    ("jpn_Jpan", "eng_Latn", "このボスは強すぎる"),
    ("jpn_Jpan", "eng_Latn", "次のラウンドいくぞ"),

    # Korean -> English (10)
    ("kor_Hang", "eng_Latn", "오늘 같이 게임하자!"),
    ("kor_Hang", "eng_Latn", "잘 했어!"),
    ("kor_Hang", "eng_Latn", "도와줘, 적이 셋이야"),
    ("kor_Hang", "eng_Latn", "잠깐만"),
    ("kor_Hang", "eng_Latn", "고마워"),
    ("kor_Hang", "eng_Latn", "다시 하자"),
    ("kor_Hang", "eng_Latn", "미안, 늦었어"),
    ("kor_Hang", "eng_Latn", "이겼다!"),
    ("kor_Hang", "eng_Latn", "이 보스는 너무 강해"),
    ("kor_Hang", "eng_Latn", "다음 라운드 가자"),

    # Chinese -> English (10)
    ("zho_Hans", "eng_Latn", "今天一起打游戏吧！"),
    ("zho_Hans", "eng_Latn", "打得好！"),
    ("zho_Hans", "eng_Latn", "帮帮我，有三个敌人"),
    ("zho_Hans", "eng_Latn", "等一下"),
    ("zho_Hans", "eng_Latn", "谢谢"),
    ("zho_Hans", "eng_Latn", "再来一次"),
    ("zho_Hans", "eng_Latn", "对不起，我迟到了"),
    ("zho_Hans", "eng_Latn", "赢了！"),
    ("zho_Hans", "eng_Latn", "这个boss太强了"),
    ("zho_Hans", "eng_Latn", "下一轮走起"),

    # French -> English (10)
    ("fra_Latn", "eng_Latn", "On joue ensemble aujourd'hui !"),
    ("fra_Latn", "eng_Latn", "Bien joué !"),
    ("fra_Latn", "eng_Latn", "Aide-moi, il y a trois ennemis"),
    ("fra_Latn", "eng_Latn", "Attends une seconde"),
    ("fra_Latn", "eng_Latn", "Merci"),
    ("fra_Latn", "eng_Latn", "On refait ça"),
    ("fra_Latn", "eng_Latn", "Désolé, je suis en retard"),
    ("fra_Latn", "eng_Latn", "On a gagné !"),
    ("fra_Latn", "eng_Latn", "Ce boss est trop fort"),
    ("fra_Latn", "eng_Latn", "Prochaine manche"),

    # Spanish -> English (10)
    ("spa_Latn", "eng_Latn", "Jugamos juntos hoy"),
    ("spa_Latn", "eng_Latn", "Bien jugado!"),
    ("spa_Latn", "eng_Latn", "Ayuda, hay tres enemigos"),
    ("spa_Latn", "eng_Latn", "Espera un momento"),
    ("spa_Latn", "eng_Latn", "Gracias"),
    ("spa_Latn", "eng_Latn", "Otra vez"),
    ("spa_Latn", "eng_Latn", "Perdón, llegué tarde"),
    ("spa_Latn", "eng_Latn", "Ganamos!"),
    ("spa_Latn", "eng_Latn", "Este jefe es muy fuerte"),
    ("spa_Latn", "eng_Latn", "Siguiente ronda"),

    # German -> English (10)
    ("deu_Latn", "eng_Latn", "Lasst uns heute zusammen spielen"),
    ("deu_Latn", "eng_Latn", "Gut gespielt!"),
    ("deu_Latn", "eng_Latn", "Hilfe, drei Feinde"),
    ("deu_Latn", "eng_Latn", "Warte kurz"),
    ("deu_Latn", "eng_Latn", "Danke"),
    ("deu_Latn", "eng_Latn", "Nochmal"),
    ("deu_Latn", "eng_Latn", "Sorry, bin spät"),
    ("deu_Latn", "eng_Latn", "Gewonnen!"),
    ("deu_Latn", "eng_Latn", "Dieser Boss ist zu stark"),
    ("deu_Latn", "eng_Latn", "Nächste Runde"),

    # English -> Japanese (10) — reply direction
    ("eng_Latn", "jpn_Jpan", "good game, well played"),
    ("eng_Latn", "jpn_Jpan", "nice shot"),
    ("eng_Latn", "jpn_Jpan", "need help"),
    ("eng_Latn", "jpn_Jpan", "one second"),
    ("eng_Latn", "jpn_Jpan", "thanks"),
    ("eng_Latn", "jpn_Jpan", "let's try again"),
    ("eng_Latn", "jpn_Jpan", "sorry i'm late"),
    ("eng_Latn", "jpn_Jpan", "we won"),
    ("eng_Latn", "jpn_Jpan", "this boss is too strong"),
    ("eng_Latn", "jpn_Jpan", "next round"),
]


def translate_with_beam(engine, src_code, tgt_code, text, beam_size):
    """Translate at a specific beam size, return (translation, score)."""
    # Setup tokenizer
    if hasattr(engine._ct2_tokenizer, 'src_lang'):
        engine._ct2_tokenizer.src_lang = src_code
    if hasattr(engine._ct2_tokenizer, 'set_src_lang_special_tokens'):
        engine._ct2_tokenizer.set_src_lang_special_tokens(src_code)

    encoded = engine._ct2_tokenizer.encode(text, add_special_tokens=True)
    source_tokens = engine._ct2_tokenizer.convert_ids_to_tokens(encoded)
    if not source_tokens:
        return text, None

    # NLLB token handling
    if src_code and '_' in src_code:
        src_lang_token = engine._ct2_resolve_lang_token(src_code)
        if source_tokens and source_tokens[-1] == '<unk>':
            source_tokens[-1] = src_lang_token
        elif src_lang_token not in source_tokens:
            source_tokens.append(src_lang_token)

    target_prefix = engine._ct2_target_prefix(tgt_code)
    kwargs = {
        'beam_size': beam_size,
        'max_decoding_length': max(192, len(source_tokens) * 4),
    }
    if target_prefix:
        kwargs['target_prefix'] = [target_prefix]

    result = engine._ct2_translator.translate_batch(
        [source_tokens],
        return_scores=True,
        **kwargs,
    )
    if not result or not result[0].hypotheses:
        return text, None

    # Pick top hypothesis (first in list)
    hyp = result[0].hypotheses[0]
    score = result[0].scores[0] if result[0].scores else None
    decoded = engine._ct2_decode_tokens(hyp)
    return decoded or text, score


def main():
    print("Loading GPU engine...")
    engine = FlashEngine(device='cuda')
    print(f"Ready, profile={engine._profile}\n")

    beam_sizes = [1, 2, 4, 8]
    results_by_beam = {b: [] for b in beam_sizes}  # list of (translation, score) per sentence
    latencies_by_beam = {b: [] for b in beam_sizes}

    print(f"Running {len(TEST_SENTENCES)} sentences at beam sizes {beam_sizes}...")

    for src_code, tgt_code, sentence in TEST_SENTENCES:
        per_beam = {}
        for beam_size in beam_sizes:
            # Warmup at this beam
            try:
                translate_with_beam(engine, src_code, tgt_code, sentence, beam_size)
            except Exception:
                pass

            # Measurement
            t0 = time.perf_counter()
            try:
                translation, score = translate_with_beam(engine, src_code, tgt_code, sentence, beam_size)
                elapsed_ms = round((time.perf_counter() - t0) * 1000)
            except Exception as e:
                translation, score = None, None
                elapsed_ms = None
            per_beam[beam_size] = (translation, score)
            latencies_by_beam[beam_size].append(elapsed_ms)
        for beam_size in beam_sizes:
            results_by_beam[beam_size].append(per_beam[beam_size])

    # Analysis
    print(f"\n{'='*80}")
    print("BEAM SIZE ANALYSIS")
    print(f"{'='*80}\n")

    # Latency
    print("LATENCY:")
    print(f"{'Beam':<6} {'Median (ms)':<14} {'Mean (ms)':<12} {'vs beam=1'}")
    print(f"{'-'*50}")
    base_median = statistics.median(latencies_by_beam[1])
    for beam_size in beam_sizes:
        med = statistics.median(latencies_by_beam[beam_size])
        mean = statistics.mean(latencies_by_beam[beam_size])
        ratio = med / base_median if base_median else 0
        print(f"{beam_size:<6} {med:<14.1f} {mean:<12.1f} {ratio:.2f}x")

    # Score comparison (only meaningful when score is non-null)
    print(f"\nMODEL SCORE (log-probability — higher = more probable):")
    print(f"{'Beam':<6} {'Median':<10} {'Mean':<10} {'Min':<10} {'Max':<10} {'n'}")
    print(f"{'-'*60}")
    for beam_size in beam_sizes:
        scores = [s for t, s in results_by_beam[beam_size] if s is not None]
        if scores:
            print(f"{beam_size:<6} {statistics.median(scores):<10.3f} {statistics.mean(scores):<10.3f} "
                  f"{min(scores):<10.3f} {max(scores):<10.3f} {len(scores)}")

    # Pairwise agreement and score comparison
    print(f"\nPAIRWISE COMPARISON (vs beam=4):")
    for beam_size in [1, 2, 8]:
        agree = 0
        disagree_beam_higher_score = 0
        disagree_beam_lower_score = 0
        disagree_beam_equal_score = 0
        for i in range(len(TEST_SENTENCES)):
            t_b, s_b = results_by_beam[beam_size][i]
            t_4, s_4 = results_by_beam[4][i]
            if t_b == t_4:
                agree += 1
            elif s_b is not None and s_4 is not None:
                if s_b > s_4:
                    disagree_beam_higher_score += 1
                elif s_b < s_4:
                    disagree_beam_lower_score += 1
                else:
                    disagree_beam_equal_score += 1

        total = len(TEST_SENTENCES)
        print(f"\n  beam={beam_size} vs beam=4:")
        print(f"    Agreement: {agree}/{total} ({agree/total*100:.0f}%)")
        print(f"    beam={beam_size} has HIGHER score: {disagree_beam_higher_score}")
        print(f"    beam={beam_size} has LOWER score:  {disagree_beam_lower_score}")
        print(f"    beam={beam_size} has equal score:  {disagree_beam_equal_score}")

    # What does beam=4 produce that beam=1 doesn't? Show some examples.
    print(f"\n{'='*80}")
    print("EXAMPLES WHERE BEAM=4 DIFFERS FROM BEAM=1 (first 15)")
    print(f"{'='*80}\n")
    shown = 0
    for i in range(len(TEST_SENTENCES)):
        src_code, tgt_code, sentence = TEST_SENTENCES[i]
        t_1, s_1 = results_by_beam[1][i]
        t_4, s_4 = results_by_beam[4][i]
        if t_1 != t_4:
            shown += 1
            if shown <= 15:
                score_diff = (s_4 - s_1) if (s_1 is not None and s_4 is not None) else None
                s_1_str = f"{s_1:.3f}" if s_1 is not None else "N/A"
                s_4_str = f"{s_4:.3f}" if s_4 is not None else "N/A"
                print(f"  {src_code}->{tgt_code}  {sentence!r}")
                print(f"    beam=1 ({s_1_str}): {t_1!r}")
                print(f"    beam=4 ({s_4_str}): {t_4!r}")
                if score_diff is not None:
                    better = "beam=4" if score_diff > 0 else "beam=1"
                    print(f"    Score difference: {score_diff:+.3f} ({better} higher)")
                print()

    # Save raw results
    out = {
        "test_corpus_size": len(TEST_SENTENCES),
        "beam_sizes_tested": beam_sizes,
        "results": [
            {
                "src": TEST_SENTENCES[i][0],
                "tgt": TEST_SENTENCES[i][1],
                "sentence": TEST_SENTENCES[i][2],
                **{f"beam{b}": {"translation": t, "score": s, "latency_ms": latencies_by_beam[b][i]}
                   for b in beam_sizes
                   for t, s in [results_by_beam[b][i]]}
            }
            for i in range(len(TEST_SENTENCES))
        ]
    }
    with open("bench_beam_quality_results.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
    print(f"\nFull results written to bench_beam_quality_results.json")


if __name__ == "__main__":
    main()