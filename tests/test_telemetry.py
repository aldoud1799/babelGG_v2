import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.telemetry import Telemetry


tmp_dir = tempfile.mkdtemp(prefix='babelgg_telemetry_test_')
store = os.path.join(tmp_dir, 'telemetry.json')
t = Telemetry(storage_path=store, max_events=500)

# 1) 5 translation events
for i in range(5):
    t.log_translation(
        src_lang='jpn_Jpan',
        tgt_lang='eng_Latn',
        text_length=40 + i,
        translation_ms=180 + i,
        cache_hit=False,
        phrase_db_hit=(i % 2 == 0),
        slang_normalized=True,
        emoji_cleaned=False,
        naturalizer_applied=True,
    )

t.flush()
with open(store, 'r', encoding='utf-8') as f:
    events = json.load(f)
assert len(events) == 5, f'Expected 5 events, got {len(events)}'
print('PASS  1 — 5 translations logged')

# 2) Ensure no text content keys exist
for ev in events:
    assert 'original' not in ev and 'translation' not in ev, 'Telemetry must not contain text content'
print('PASS  2 — no original/translation text stored')

# 3) quality report from dismiss data
t.log_card_dismissed('jpn_Jpan', 600, 'user_x')
t.log_card_dismissed('jpn_Jpan', 4200, 'auto')
report = t.get_quality_report()
assert 'jpn_Jpan' in report, 'Quality report should include jpn_Jpan'
assert 'avg_read_ms' in report['jpn_Jpan'], 'avg_read_ms missing'
print('PASS  3 — quality report computed')

# 4) Rolling window (500 max)
for i in range(520):
    t.log_translation(
        src_lang='kor_Hang',
        tgt_lang='eng_Latn',
        text_length=10,
        translation_ms=100,
        cache_hit=False,
        phrase_db_hit=False,
        slang_normalized=False,
        emoji_cleaned=False,
        naturalizer_applied=False,
    )
t.flush()
with open(store, 'r', encoding='utf-8') as f:
    events = json.load(f)
assert len(events) == 500, f'Expected rolling window of 500, got {len(events)}'
print('PASS  4 — rolling window pruning works')

# 5) Clear data
t.clear_data()
assert not os.path.exists(store), 'Telemetry file should be removed after clear_data()'
print('PASS  5 — clear data works')

print('\nAll telemetry tests passed')
