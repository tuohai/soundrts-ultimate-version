# -*- coding: utf-8 -*-
"""Generate the AoE2 civ intro blocks (TTS 8520-8567) for every locale
straight from the authoritative DE strings.

Source of truth
---------------
``_de_civ_data.json``  (built by ``_build_de_civ_data.py``)  - the official
                       DE civ blurb per locale: civ bonus bullets,
                       unique tech names + effect text, team bonus.
``_de_civ_names.json`` (built by ``_build_de_civ_names.py``) - the official
                       localized display names of the unique units and
                       unique technologies.

Our shipped intro block has a fixed shape::

    <unique unit line>
    <unique techs line>
    <one line per civ bonus>
    <one line per unique tech effect>
    <team bonus line>

i.e. ``2 + len(bonuses) + len(techs) + 1`` lines.

The English file spells numbers out ("twenty-five percent") because the
lines are spoken by a TTS voice; the other locales use the official DE
wording verbatim, which already carries each language's own natural way
of expressing percentages.

Usage::

    python _gen_civ_intros.py             # write every locale
    python _gen_civ_intros.py --check     # report differences only
"""
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

LOCALES = ['ui', 'ui-zh', 'ui-be', 'ui-cs', 'ui-de', 'ui-es', 'ui-fr',
           'ui-it', 'ui-pl', 'ui-pt-BR', 'ui-ru', 'ui-sk', 'ui-vi']

CIV_ID = {
    'britons': 8520, 'franks': 8521, 'chinese': 8522, 'mongols': 8523,
    'byzantines': 8524, 'japanese': 8525, 'teutons': 8526, 'vikings': 8527,
    'vietnamese': 8528, 'portuguese': 8529, 'aztecs': 8530, 'celts': 8531,
    'malians': 8532, 'saracens': 8533, 'goths': 8540, 'persians': 8541,
    'slavs': 8542, 'cumans': 8543, 'huns': 8544, 'koreans': 8545,
    'maya': 8546, 'hindustanis': 8547, 'spanish': 8548, 'magyars': 8549,
    'poles': 8550, 'italians': 8551, 'bohemians': 8552, 'turks': 8553,
    'bulgarians': 8554, 'lithuanians': 8555, 'tatars': 8556, 'berbers': 8557,
    'ethiopians': 8558, 'khmer': 8559, 'malay': 8560, 'burmese': 8561,
    'burgundians': 8562, 'sicilians': 8563, 'armenians': 8564,
    'georgians': 8565, 'inca': 8566, 'romans': 8567,
}
ID_CIV = {v: k for k, v in CIV_ID.items()}
INTRO_IDS = sorted(CIV_ID.values())

# Per-locale frame for the "unique unit" / "unique techs" / "team bonus"
# lines.
FRAMES = {
    'ui': {
        'uu': 'Unique unit {}.',
        'techs': 'Unique techs {}.',
        'team': 'Team bonus: {}.',
        'join': ' and ',
    },
    'ui-zh': {
        'uu': '独特单位：{}。',
        'techs': '独特科技：{}。',
        'team': '组队：{}。',
        'join': '，',
    },
    'ui-be': {
        'uu': 'Унікальны юніт: {}.',
        'techs': 'Унікальныя тэхналогіі: {}.',
        'team': 'Бонус каманды: {}.',
        'join': ' і ',
    },
    'ui-cs': {
        'uu': 'Unikátní jednotka: {}.',
        'techs': 'Unikátní technologie: {}.',
        'team': 'Bonus týmu: {}.',
        'join': ' a ',
    },
    'ui-de': {
        'uu': 'Einheit: {}.',
        'techs': 'Unique Techs: {}.',
        'team': 'Team: {}.',
        'join': ' und ',
    },
    'ui-es': {
        'uu': 'Unidad única: {}.',
        'techs': 'Tecnologías únicas: {}.',
        'team': 'Bonificación de equipo: {}.',
        'join': ' y ',
    },
    'ui-fr': {
        'uu': 'Unité unique : {}.',
        'techs': 'Techs uniques : {}.',
        'team': "Bonus d'équipe : {}.",
        'join': ' et ',
    },
    'ui-it': {
        'uu': 'Unità unica: {}.',
        'techs': 'Tecnologie uniche: {}.',
        'team': 'Bonus di squadra: {}.',
        'join': ' e ',
    },
    'ui-pl': {
        'uu': 'Unikalna jednostka: {}.',
        'techs': 'Unikalne technologie: {}.',
        'team': 'Bonus drużyny: {}.',
        'join': ' i ',
    },
    'ui-pt-BR': {
        'uu': 'Unidade única: {}.',
        'techs': 'Tecnologias únicas: {}.',
        'team': 'Bônus de equipe: {}.',
        'join': ' e ',
    },
    'ui-ru': {
        'uu': 'Уникальный юнит: {}.',
        'techs': 'Уникальные технологии: {}.',
        'team': 'Бонус команды: {}.',
        'join': ' и ',
    },
    'ui-sk': {
        'uu': 'Unikátna jednotka: {}.',
        'techs': 'Unikátne technológie: {}.',
        'team': 'Bonus tímu: {}.',
        'join': ' a ',
    },
    'ui-vi': {
        'uu': 'Đơn vị độc quyền: {}.',
        'techs': 'Công nghệ độc quyền: {}.',
        'team': 'Thưởng đội: {}.',
        'join': ' và ',
    },
}

# ---------------------------------------------------------------------------
# English number spelling (the shipped English tts.txt never uses digits
# or the "%" sign -- the lines are spoken by a TTS voice).
# ---------------------------------------------------------------------------

WORD_NUM = {
    0: 'zero', 1: 'one', 2: 'two', 3: 'three', 4: 'four', 5: 'five',
    6: 'six', 7: 'seven', 8: 'eight', 9: 'nine', 10: 'ten', 11: 'eleven',
    12: 'twelve', 13: 'thirteen', 14: 'fourteen', 15: 'fifteen',
    16: 'sixteen', 17: 'seventeen', 18: 'eighteen', 19: 'nineteen',
    20: 'twenty', 30: 'thirty', 40: 'forty', 50: 'fifty', 60: 'sixty',
    70: 'seventy', 80: 'eighty', 90: 'ninety',
}


def spell(n):
    n = int(n)
    if n in WORD_NUM:
        return WORD_NUM[n]
    if n < 100:
        return '%s-%s' % (WORD_NUM[n - n % 10], WORD_NUM[n % 10])
    if n < 1000:
        rest = n % 100
        head = '%s hundred' % WORD_NUM[n // 100]
        return head if rest == 0 else '%s %s' % (head, spell(rest))
    return str(n)


def en_numbers(text):
    """Rewrite the DE numeric notation as spoken English.

    * ``25%``            -> ``twenty-five percent``
    * ``+25%``           -> ``twenty-five percent``  (a plain amount)
    * ``costs -25%``     -> ``costs twenty-five percent less``
    * ``+1``             -> ``plus one``
    * ``-1``             -> ``minus one``
    """
    # a signed percentage list, e.g. "-15/20/25/30%" or "+10/15/20% HP"
    def pct_list(m):
        sign, nums = m.group(1), m.group(2)
        parts = '/'.join(spell(n) for n in nums.split('/'))
        if sign == '-':
            return '%s percent less' % parts
        return '%s percent' % parts

    text = re.sub(r'([+-])(\d+(?:/\d+)*)\s*%', pct_list, text)
    # an unsigned percentage
    text = re.sub(r'(?<![\w.])(\d+)\s*%',
                  lambda m: '%s percent' % spell(m.group(1)), text)
    # "+1" / "-1"
    text = re.sub(r'\+(\d+)', lambda m: 'plus %s' % spell(m.group(1)), text)
    text = re.sub(r'-(\d+)', lambda m: 'minus %s' % spell(m.group(1)), text)
    # remaining bare numbers
    text = re.sub(r'(?<![\w.])(\d+)(?![\d%])',
                  lambda m: spell(m.group(1)), text)
    return text


def en_join(items, sep=' and '):
    items = list(items)
    if len(items) <= 1:
        return ''.join(items)
    if len(items) == 2:
        return sep.join(items)
    return ', '.join(items[:-1]) + sep + items[-1]


def en_line(text):
    """An English intro body line: spelled-out numbers, one sentence."""
    out = en_numbers(text).strip()
    out = re.sub(r'\s+', ' ', out)
    # "plus one/plus two/plus three" -> "plus one/two/three"
    out = re.sub(r'\bplus\s+([\w-]+)((?:/plus\s+[\w-]+)+)',
                 lambda m: 'plus ' + m.group(1)
                 + re.sub(r'/plus\s+', '/', m.group(2)), out)
    # a line that starts with a bare amount reads better without "plus"
    # and starts with a capital letter
    out = re.sub(r'^plus\s+(?=[\w-]*\s+population)', '', out)
    if out:
        out = out[0].upper() + out[1:]
    if out and not out.endswith(('.', '!', '?')):
        out += '.'
    return out


def tech_effect_of(entry):
    """A tech entry -> its effect text."""
    if isinstance(entry, dict):
        return entry['effect']
    m = re.match(r'^(.*?)\s*\((.*)\)\s*$', entry)
    return m.group(2) if m else entry


def tech_name_of(entry):
    """A tech entry -> its name."""
    if isinstance(entry, dict):
        return entry['name']
    m = re.match(r'^(.*?)\s*\((.*)\)\s*$', entry)
    return m.group(1).strip() if m else entry.strip()


def clean_tail(text):
    """Collapse a doubled sentence terminator ("faster..")."""
    text = re.sub(r'\s+', ' ', text.strip())
    text = re.sub(r'([.!?])\1+', r'\1', text)
    return text


def build_blocks(loc, DE, NAMES):
    """{intro id: [lines]} for one locale."""
    fr = FRAMES[loc]
    de_loc = DE[loc]
    names_loc = NAMES.get(loc, {})
    out = {}
    for key, cid in CIV_ID.items():
        d = de_loc[key]
        nm = names_loc.get(key, {'uu': {}, 'techs': {}})

        # The DE civ blurb carries the *localized* unique-unit and
        # unique-tech names exactly as the DE civ info panel displays
        # them, so they are used verbatim.  The tech-tree string table
        # (``_de_civ_names.json``) is only a cross-check: the DE
        # tech-tree display strings occasionally differ in spelling
        # ("Keshig" vs. "Keshik", "Coutilier" vs. "Coustillier") and the
        # civ-info panel is the authoritative one.
        uu_names = list(d['uu_names'])
        tech_names = [tech_name_of(t) for t in d['techs']]

        lines = [fr['uu'].format(en_join(uu_names, ', '))]
        lines.append(fr['techs'].format(en_join(tech_names, fr['join'])))

        for b in d['bonuses']:
            lines.append(en_line(b) if loc == 'ui' else clean_tail(b))
        for t in d['techs']:
            eff = tech_effect_of(t)
            lines.append(en_line(eff) if loc == 'ui' else clean_tail(eff))
        lines.append(fr['team'].format(
            (en_line(d['team']).rstrip('.') if loc == 'ui'
             else clean_tail(d['team']).rstrip('.'))))
        out[cid] = lines
    return out


def rewrite(path, blocks):
    """Replace the 42 intro blocks in a tts.txt with the generated ones."""
    src = io.open(path, encoding='utf-8').read()
    lines = src.split('\n')
    out = []
    i = 0
    replaced = 0
    while i < len(lines):
        raw = lines[i]
        m = re.match(r'^(\d{4})\s', raw)
        cid = int(m.group(1)) if m else None
        if cid in blocks:
            # skip the existing block (head + indented continuation lines)
            j = i + 1
            while j < len(lines) and lines[j][:1] in ' \t' \
                    and lines[j].strip():
                j += 1
            out.append('%d %s' % (cid, blocks[cid][0]))
            for line in blocks[cid][1:]:
                out.append('  ' + line)
            replaced += 1
            i = j
            continue
        out.append(raw)
        i += 1
    return '\n'.join(out), replaced


def main():
    check = '--check' in sys.argv
    DE = json.load(io.open('_de_civ_data.json', encoding='utf-8'))
    NAMES = json.load(io.open('_de_civ_names.json', encoding='utf-8'))

    total_diff = 0
    for loc in LOCALES:
        path = 'mods/aoe2/%s/tts.txt' % loc
        if not os.path.exists(path):
            continue
        blocks = build_blocks(loc, DE, NAMES)
        new_text, replaced = rewrite(path, blocks)
        old_text = io.open(path, encoding='utf-8').read()
        if new_text == old_text:
            print('%-8s up to date (%d blocks)' % (loc, replaced))
            continue
        total_diff += 1
        if check:
            print('%-8s DIFFERS (%d blocks)' % (loc, replaced))
        else:
            io.open(path, 'w', encoding='utf-8', newline='\n').write(new_text)
            print('%-8s rewritten (%d blocks)' % (loc, replaced))
    print()
    print('locales differing:', total_diff)


if __name__ == '__main__':
    main()
