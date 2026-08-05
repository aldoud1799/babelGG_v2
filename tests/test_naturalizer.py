import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.naturalizer import naturalize


out = naturalize('BRO WHAT ARE YOU DOING???', 'bro what are you doing?')
assert out == out.upper(), f'Expected uppercase energy restoration, got: {out}'
assert out.endswith('??'), f'Expected strong question marker restoration, got: {out}'
print('PASS  1 - all-caps and question energy mirrored')

out = naturalize("lol I'm so tired today", 'I am exhausted today.')
assert 'lol' in out.lower(), f'Expected laughter cue, got: {out}'
assert "i'm" in out.lower() or 'im' in out.lower(), f'Expected casual contraction, got: {out}'
print('PASS  2 - casual/laughter behavior')

out = naturalize('...', 'I do not know.')
assert out.endswith('...'), f'Expected ellipsis restoration, got: {out}'
print('PASS  3 - ellipsis restoration')

out = naturalize('gg', 'good game')
assert out == 'gg', f'Expected passthrough game term, got: {out}'
print('PASS  4 - game term passthrough')

out = naturalize('@Player1 nice shot!', 'great shot @Player1')
assert '@Player1' in out, f'Expected mention preserved, got: {out}'
print('PASS  5 - mention preservation')

formal_src = 'I believe we should coordinate our strategy'
formal_out = naturalize(formal_src, 'I believe that we should coordinate our strategy.')
assert 'imo' not in formal_out.lower(), f'Formal text should not be casualized: {formal_out}'
print('PASS  6 - formal register preserved')

out = naturalize('push mid now', 'we should push in the middle lane right now')
assert 'mid' in out.lower(), f'Expected game term preserved, got: {out}'
print('PASS  7 - short game command preserved')

url = 'https://twitch.tv/someone'
out = naturalize(url, 'https://twitch.tv/someone')
assert out == url, f'URL should remain unchanged, got: {out}'
print('PASS  8 - url passthrough')

emoji_src = '😭😭😭'
out = naturalize(emoji_src, 'sad')
assert out == 'sad', f'Pure emoji source should bypass processing, got: {out}'
print('PASS  9 - pure emoji source bypass')

out = naturalize('hello', '')
assert out == '', f'Empty translation should return empty string, got: {out}'
print('PASS 10 - empty translation guard')

print('\nAll naturalizer tests passed')
