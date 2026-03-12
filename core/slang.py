import re, logging
from typing import Optional


_SLANG: dict[str, str] = {
    # ── Universal ────────────────────────────────────────────────
    'gg wp':           'good game, well played',
    'gg ez':           'good game, that was easy',
    'glhf':            'good luck, have fun',
    'gg':              'good game',
    'wp':              'well played',
    'gl':              'good luck',
    'hf':              'have fun',
    'ez':              'that was easy',
    'afk':             'away from keyboard',
    'brb':             'be right back',
    'bbl':             'be back later',
    'g2g':             'got to go',
    'gtg':             'got to go',
    'omw':             'on my way',
    'rn':              'right now',
    'ngl':             'not going to lie',
    'tbh':             'to be honest',
    'imo':             'in my opinion',
    'imho':            'in my humble opinion',
    'lmfao':           'laughing very hard',
    'lmao':            'laughing hard',
    'rofl':            'laughing on the floor',
    'lol':             'laughing',
    'omg':             'oh my god',
    'wtf':             'what the heck',
    'wth':             'what the heck',
    'ffs':             'for goodness sake',
    'smh':             'shaking my head',
    'irl':             'in real life',
    'nvm':             'never mind',
    'idk':             'I do not know',
    'ik':              'I know',
    'ikr':             'I know right',
    'npc':             'non-player character',
    'rng':             'random luck',
    'n00b':            'new player',
    'noob':            'new player',
    'newbie':          'new player',
    'nub':             'new player',
    'pwned':           'defeated badly',
    'rekt':            'defeated badly',
    'owned':           'defeated badly',
    'stomped':         'defeated badly',
    'hard carry':      'single-handedly won the game',
    'carried':         'helped to win by a teammate',
    'on tilt':         'frustrated and playing poorly',
    'tilted':          'frustrated and playing poorly',
    'tilt':            'frustration affecting play',
    'toxic':           'unsportsmanlike',
    'salty':           'bitter after losing',
    'salt':            'bitterness after losing',
    'rage quit':       'quit the game in anger',
    'dc':              'disconnected from the game',
    # ── Toxicity / Trash Talk ─────────────────────────────────────
    'get rekt':        'you were defeated badly',
    'get owned':       'you were defeated badly',
    'l bozo':          'you lost, you fool',
    'cope and seethe': 'be angry and deal with your loss',
    'ratio':           'more people disagreed with you',
    'cope':            'deal with your loss',
    'seethe':          'be angry about your loss',
    'malding':         'angry and frustrated',
    'mald':            'be angry and frustrated',
    'rent free':       'you cannot stop thinking about it',
    'touch grass':     'go outside and take a break',
    'git gud':         'improve your skills',
    'skill issue':     'you need to improve your skills',
    'skill diff':      'there is a skill difference',
    'dogwater':        'playing very poorly',
    'trash':           'playing very poorly',
    'hardstuck':       'stuck at the same rank for a long time',
    'boosted animal':  'player carried to a high rank undeservedly',
    'boosted':         'carried to a higher rank than deserved',
    'clown':           'foolish player',
    'bozo':            'foolish player',
    'bot':             'playing as badly as a computer bot',
    'inting':          'intentionally feeding the enemy',
    'int':             'intentionally feed the enemy',
    # ── Twitch / Streaming ────────────────────────────────────────
    'pogchamp':        'wow, incredible',
    'poggers':         'amazing, exciting',
    'pog moment':      'an amazing moment',
    'pog':             'wow, amazing',
    'kekw':            'laughing hard',
    'kek':             'laughing',
    'lulw':            'laughing hard',
    'lul':             'laughing',
    'monkaw':          'very scared and nervous',
    'monkas':          'scared and nervous',
    'monkahmm':        'thinking nervously',
    'pepega':          'that was foolish',
    'pepehands':       'that is sad',
    'feelsbadman':     'that feels bad',
    'feelsgoodman':    'that feels good',
    'ez clap':         'that was too easy, applause',
    'clap':            'well done, applause',
    'huffing copium':  'deep in denial about a loss',
    'on copium':       'refusing to accept defeat',
    'copium':          'coping with a loss through denial',
    'hopium':          'unrealistic hope',
    'w chat':          'the chat was right',
    'l chat':          'the chat was wrong',
    'based':           'admirable and true',
    'cringe':          'embarrassing',
    'gigachad':        'extremely confident and impressive',
    'chad':            'confident and admirable',
    'no cap':          'I am not lying',
    'cap':             'that is a lie',
    'lowkey':          'somewhat',
    'highkey':         'very much',
    'bussin':          'excellent',
    'slaps':           'is excellent',
    'hits different':  'feels uniquely good',
    'mid':             'mediocre and average',
    'sus':             'suspicious',
    'caught in 4k':    'caught doing something very clearly',
    # ── MOBA ──────────────────────────────────────────────────────
    'ff at 15':        'vote to surrender at 15 minutes',
    'open mid':        'stop defending and let the enemy win',
    'ff15':            'vote to surrender at 15 minutes',
    'ff':              'surrender the match',
    'soft int':        'playing badly on purpose subtly',
    'int build':       'building items to die on purpose',
    'mid diff':        'the mid lane player made the difference',
    'jungle diff':     'the jungler made the difference',
    'support diff':    'the support made the difference',
    'diff':            'there is a skill difference',
    'ganking':         'ambushing a lane from the jungle',
    'gank':            'ambush attack from the jungle',
    'split push':      'pushing a side lane alone',
    'backdoor':        'attacking the enemy base directly',
    'tower dive':      'attacking an enemy under their tower',
    'dive':            'attack an enemy under their tower',
    'wave clear':      'clearing the minion wave',
    'all in':          'commit to a full fight',
    'poke':            'harass from a distance',
    'rotating':        'moving to another lane to help',
    'roam':            'move to help other lanes',
    'invade':          'enter the enemy jungle',
    'vision control':  'controlling map vision with wards',
    'deward':          'destroy an enemy ward',
    'ward':            'place a vision ward',
    'peel':            'protect a teammate from enemies',
    'engage':          'initiate a team fight',
    'disengage':       'retreat from a fight',
    'kite':            'attack while moving away from enemies',
    'leash':           'help the jungler start their camps',
    'farm':            'collect gold from minions',
    'farming':         'collecting gold from minions',
    'cs':              'creep score, number of minions killed',
    # ── FPS ───────────────────────────────────────────────────────
    'spray transfer':  'moving aim between targets while spraying',
    'spray down':      'rapidly kill multiple enemies',
    'spray':           'fire rapidly without careful aiming',
    'one tap':         'kill with a single shot to the head',
    'wallbang':        'shoot through a wall to kill an enemy',
    'shoulder peek':   'briefly show yourself to bait shots',
    'jiggle peek':     'quickly peek back and forth',
    'wide peek':       'move far out from cover aggressively',
    'pre-fire':        'shoot before seeing the enemy',
    'pre-aim':         'aim at where an enemy will appear',
    'flick shot':      'a quick aim snap to a target',
    'flick':           'rapidly move aim to a target',
    'crosshair placement': 'keeping aim at head level',
    'holding angle':   'waiting at a corner for an enemy',
    'clearing corners': 'checking all hiding spots',
    'clutched it':     'won the round against the odds',
    'clutch':          'win a round against the odds',
    'entry frag':      'first kill of an attack',
    'frag out':        'throw a grenade',
    'fragging':        'killing enemies',
    'frag':            'kill an enemy',
    'retake':          'recapture a site after it was taken',
    'execute':         'coordinated attack on a site',
    'rush':            'fast aggressive push',
    'force buy':       'spend all money even when low on funds',
    'full buy':        'purchase all equipment this round',
    'eco':             'save money this round with minimal spending',
    'pistol round':    'first round with only pistols',
    'info':            'intelligence about enemy position',
    'calling':         'communicating enemy positions to the team',
    'trade':           'kill an enemy who just killed a teammate',
    'peek':            'move out from cover briefly',
}

# Sort by length descending — multi-word phrases must match before single words
_PATTERNS: list[tuple] = [
    (re.compile(r'(?<![\w])' + re.escape(k) + r'(?![\w])', re.IGNORECASE), v)
    for k, v in sorted(_SLANG.items(), key=lambda x: len(x[0]), reverse=True)
]


def normalize(text: str) -> str:
    """Expand gaming slang into plain English. Returns modified text."""
    if not text or not text.strip():
        return text
    result  = text
    changes = 0
    for pattern, replacement in _PATTERNS:
        new = pattern.sub(replacement, result)
        if new != result:
            changes += 1
            result   = new
    if changes:
        logging.info(f'[SLANG] {changes} substitution(s): {text!r} -> {result!r}')
    return result


def normalize_for_translation(text: str) -> tuple[str, bool]:
    """Returns (normalized_text, was_changed)."""
    normalized = normalize(text)
    return normalized, normalized != text


def lookup(term: str) -> Optional[str]:
    """Direct single-term lookup. Returns plain English or None."""
    return _SLANG.get(term.strip().lower())


if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    tests = [
        'gg ez lmao',
        'she is inting hard rn',
        'Pog that clutch was insane',
        'ff at 15 this is over',
        'spray down then eco next round',
        'on copium after that L',
        'git gud skill issue tbh',
    ]
    for t in tests:
        n, changed = normalize_for_translation(t)
        print(f'   IN:  {t}')
        print(f'   OUT: {n}')
        print()
