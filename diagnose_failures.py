"""
diagnose_failures.py — figure out WHY translation calls are returning None.

For each pair with high failure rate, capture:
  - the source sentence
  - what translate() returns (None = failure)
  - what the underlying CTranslate2 generation produced (raw)
  - what the post-processing decoded to
  - which guard rejected it (near-unchanged, target-mismatch, pathological)
"""
import json
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.flash import FlashEngine


# A few sentences per problem direction
TEST = {
    "german->english": [
        "Hilfe, drei Feinde",
        "Nachladen",
        "Schau auf die Karte",
        "Gewonnen!",
        "Danke",
    ],
    "spanish->english": [
        "Bien jugado!",
        "Espera un momento",
        "Mira el mapa",
        "Gracias",
        "Recarga",
    ],
    "chinese->english": [
        "今天一起打游戏吧！",
        "帮帮我，有三个敌人",
        "看地图",
        "换弹",
        "谢谢",
    ],
    "french->english": [
        "Bien joué !",
        "Attends une seconde",
        "Recharge",
        "Merci",
        "Regarde la carte",
    ],
}


def diagnose_pair(engine, src_lang, tgt_lang, sentences):
    print(f"\n=== {src_lang} -> {tgt_lang} ===")
    for sent in sentences:
        # Run through translate() — what user sees
        result = engine.translate(sent, tgt_lang)
        if result:
            print(f"  OK   {sent!r} -> {result['translation'][:60]!r}")
            continue

        # It failed. Now diagnose what actually came out.
        # Reach into _ct2_generate_text and look at each guard.
        tgt = engine.LANG_CODES[tgt_lang]
        src = engine.detect_lang(sent)
        src_code = engine._CT2_LANG_MAP.get(src, "en")

        # Tokenize
        if hasattr(engine._ct2_tokenizer, "src_lang"):
            engine._ct2_tokenizer.src_lang = src_code
        if hasattr(engine._ct2_tokenizer, "set_src_lang_special_tokens"):
            engine._ct2_tokenizer.set_src_lang_special_tokens(src_code)

        encoded = engine._ct2_tokenizer.encode(sent, add_special_tokens=True)
        source_tokens = engine._ct2_tokenizer.convert_ids_to_tokens(encoded)
        target_prefix = engine._ct2_target_prefix(tgt)

        # Apply the same unk fixup
        if src_code and "_" in src_code:
            src_lang_token = engine._ct2_resolve_lang_token(src_code)
            if source_tokens and source_tokens[-1] == "<unk>":
                source_tokens[-1] = src_lang_token
            elif src_lang_token not in source_tokens:
                source_tokens.append(src_lang_token)

        kwargs = {"beam_size": 4, "max_decoding_length": max(192, len(source_tokens) * 4)}
        if target_prefix:
            kwargs["target_prefix"] = [target_prefix]

        try:
            raw_result = engine._ct2_translator.translate_batch([source_tokens], **kwargs)
        except Exception as e:
            print(f"  ERR  {sent!r} -> CT2 exception: {type(e).__name__}: {e}")
            continue

        if not raw_result or not raw_result[0].hypotheses:
            print(f"  ??   {sent!r} -> CT2 returned no hypotheses")
            continue

        hypothesis_tokens = raw_result[0].hypotheses[0]
        raw_decoded = engine._ct2_decode_tokens(hypothesis_tokens)
        extracted = engine._extract_translation(raw_decoded, sent)

        # Run the same guards the engine runs
        near_unchanged = engine._is_near_unchanged_output(sent, extracted)
        target_mismatch = engine._is_target_mismatch_output(extracted, tgt)
        pathological = engine._is_pathological_translation(extracted, tgt)

        print(f"  FAIL {sent!r}")
        print(f"       raw tokens     : {hypothesis_tokens[:30]}")
        print(f"       raw decoded    : {raw_decoded[:80]!r}")
        print(f"       after <t> parse: {extracted[:80]!r}")
        print(f"       guards: near_unchanged={near_unchanged} target_mismatch={target_mismatch} pathological={pathological}")


def main():
    print("Loading GPU engine...")
    engine = FlashEngine(device="cuda")
    if not engine.ready:
        print(f"NOT READY: {engine.last_error_message}")
        return
    print(f"Ready, profile={engine._profile}")

    for pair_key, sentences in TEST.items():
        src_lang, tgt_lang = pair_key.split("->")
        diagnose_pair(engine, src_lang, tgt_lang, sentences)


if __name__ == "__main__":
    main()