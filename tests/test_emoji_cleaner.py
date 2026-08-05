import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core import emoji_cleaner


# Input 1: Discord custom tag + unicode emoji
cleaned, emojis = emoji_cleaner.clean('hello <:PogChamp:123456> world 😀')
assert '<:PogChamp:123456>' not in cleaned, 'Discord tag should be stripped'
assert '😀' not in cleaned, 'Unicode emoji should be stripped before FLASH'
restored = emoji_cleaner.restore('hello world', emojis)
assert restored.endswith('😀'), 'Unicode emoji should be restored at end'
print('PASS  1 — discord stripped, unicode restored')

# Input 2: pure unicode emoji should be moved to end after restore
cleaned, emojis = emoji_cleaner.clean('안녕 😀 😎')
assert '😀' not in cleaned and '😎' not in cleaned, 'Unicode emoji should be removed'
restored = emoji_cleaner.restore('hello there', emojis)
assert restored.endswith('😀😎'), 'Multiple unicode emoji should preserve order'
print('PASS  2 — multiple unicode restored in order')

# Input 3: ASCII emoticons and kaomoji stripped forever
cleaned, emojis = emoji_cleaner.clean('gg ez xD (>_<)')
assert 'xD' not in cleaned, 'ASCII emoticon should be stripped'
assert '>_<' not in cleaned, 'Kaomoji should be stripped'
assert emojis == [], 'ASCII/kaomoji should not be restored'
restored = emoji_cleaner.restore('good game', emojis)
assert restored == 'good game', 'No restore for non-unicode emoji types'
print('PASS  3 — ascii and kaomoji stripped permanently')

# Input 4: clean text unchanged and no emoji payload
text = 'plain text only'
cleaned, emojis = emoji_cleaner.clean(text)
assert cleaned == text, 'Plain text should remain unchanged'
assert emojis == [], 'Plain text should produce empty emoji list'
assert emoji_cleaner.restore('translation', emojis) == 'translation'
print('PASS  4 — clean text passes through unchanged')

print('\nAll emoji cleaner tests passed')
