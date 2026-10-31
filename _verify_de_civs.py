# -*- coding: utf-8 -*-
"""Verify our civ intros (TTS 8520-8567) against the authoritative DE data.

Ground truth: ``_de_civ_data.json``, built from the official AoE2 DE
string table (``_de_strings/*.json``) and the official per-civ tech
trees (``_de_trees/*.json``) -- see ``_build_de_civ_data.py``.

For every locale and every civ we check, *exactly*:

    * the intro names the DE unique unit(s)
    * the intro names every DE unique technology
    * the intro's last line is the team bonus
    * the intro has exactly ``2 + len(bonuses) + len(techs) + 1`` lines
    * every DE civ bonus has its own line, 1-to-1 (Kuhn matching)
    * every DE unique-tech *effect* has its own line, 1-to-1
    * there are no extra lines

The non-English locales ship the official DE wording verbatim, so the
comparison is a plain equality after canonicalization.  The English file
spells the numbers out for the TTS voice ("twenty-five percent"), so
both sides are pushed through :func:`canon`, which folds the spoken
number words back into the DE numeric notation.
"""
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

INTRO_IDS = list(range(8520, 8534)) + list(range(8540, 8568))

LOCALES = ['ui', 'ui-zh', 'ui-be', 'ui-cs', 'ui-de', 'ui-es', 'ui-fr',
           'ui-it', 'ui-pl', 'ui-pt-BR', 'ui-ru', 'ui-sk', 'ui-vi']

# our civ key -> the intro id we ship it under
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

DE = json.load(io.open('_de_civ_data.json', encoding='utf-8'))

# ---------------------------------------------------------------------------
# number normalization
# ---------------------------------------------------------------------------

WORD_NUM = {
    'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11,
    'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15,
    'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19,
    'twenty': 20, 'thirty': 30, 'forty': 40, 'fifty': 50, 'sixty': 60,
    'seventy': 70, 'eighty': 80, 'ninety': 90,
}


def _wordnum(w):
    """'twenty-five' -> 25, 'fifty' -> 50, otherwise None."""
    if '-' in w:
        parts = w.split('-')
        vals = [_wordnum(p) for p in parts]
        if all(v is not None for v in vals):
            return sum(vals)
        return None
    return WORD_NUM.get(w)


def _read_num(toks, i, english):
    """Read one number at ``toks[i]``.

    Returns ``(value, next_index, had_percent, sign)``.
    """
    t = toks[i]
    # a number may carry trailing punctuation ("5%;", "+3,")
    m = re.match(r'^([+-]?)(\d+)(%?)([^\w%]*)$', t)
    if m:
        return int(m.group(2)), i + 1, bool(m.group(3)), m.group(1)
    if not english:
        return None, i, False, ''
    vals = []
    j = i
    while j < len(toks):
        w = toks[j]
        w = re.sub(r'[^\w%-].*$', '', w)
        if w.endswith('%'):
            w = w[:-1]
        w = w.strip('-')
        if w == 'hundred':
            vals.append(100)
            j += 1
            continue
        v = _wordnum(w)
        if v is None:
            break
        vals.append(v)
        j += 1
    if not vals:
        return None, i, False, ''
    cur = 0
    for v in vals:
        if v == 100:
            cur = (cur if cur else 1) * 100
        else:
            cur += v
    return cur, j, False, ''


def _parse_numexpr(toks, i, english):
    """Parse one numeric expression starting at ``toks[i]``.

    Handles an optional sign word ("plus"/"minus"), a slash-joined list
    ("1/2/3", "five/ten/fifteen") and a trailing "percent" / "percent
    less" marker.

    Returns ``(canonical_text, next_index)`` or ``(None, i)``.
    """
    n = len(toks)
    word_sign = ''
    if english and toks[i] in ('plus', 'minus'):
        word_sign = '-' if toks[i] == 'minus' else '+'
        i += 1

    vals = []
    signs = []
    pcts = []
    while True:
        val, j, pct, dsign = _read_num(toks, i, english)
        if val is None:
            if not vals:
                return None, i
            break
        vals.append(val)
        signs.append(dsign)
        pcts.append(pct)
        i = j
        if i + 1 < n and toks[i] == '/':
            i += 1
            continue
        break

    percent = any(pcts)
    less = False
    if i < n and toks[i].rstrip('.,;:!?') == 'percent':
        percent = True
        i += 1
    if i < n and toks[i].rstrip('.,;:!?') == 'less':
        less = True
        i += 1

    if percent:
        neg = less or (signs and signs[0] == '-')
        body = ('-' if neg else '') + '/'.join(str(v) for v in vals) + '%'
    else:
        parts = []
        for v, s in zip(vals, signs):
            if s == '-':
                parts.append('-%d' % v)
            elif word_sign == '-' and s == '':
                parts.append('-%d' % v)
            else:
                parts.append('%d' % v)
        body = '/'.join(parts)
    return body, i


def _fold_numbers(text, english):
    """Rewrite numeric notation into a canonical, comparable form.

    * ``"+25%"``                      -> ``"25%"``
    * ``"-50%"``                      -> ``"-50%"``
    * ``"twenty-five percent"``       -> ``"25%"``
    * ``"fifty percent less"``        -> ``"-50%"``
    * ``"plus one/two/three"``        -> ``"1/2/3"``
    * ``"minus one hundred"``         -> ``"-100"``
    * ``"one hundred"``               -> ``"100"``
    * ``"-15/25%"``                   -> ``"-15/25%"``
    """
    text = text.lower()
    text = text.replace('\u2212', '-')
    text = re.sub(r'([+-])\s+(\d)', r'\1\2', text)
    text = re.sub(r'\s*/\s*', ' / ', text)

    toks = text.split()
    out = []
    i = 0
    n = len(toks)
    while i < n:
        t = toks[i]
        if t in ('plus', 'minus') and english:
            body, j = _parse_numexpr(toks, i, english)
            if body is not None:
                out.append(body)
                i = j
                continue
        body, j = _parse_numexpr(toks, i, english)
        if body is not None:
            out.append(body)
            i = j
            continue
        out.append(t)
        i += 1
    return ' '.join(out)


def canon(text, english=False):
    """Canonical comparable form of a bonus/effect/team line."""
    t = text
    t = re.sub(r'<br\s*/?>', ' ', t)
    t = re.sub(r'<[^>]+>', '', t)
    t = t.replace('\u00a0', ' ').replace('\u2019', "'").strip()
    # drop the sentence terminator *before* folding, so that a trailing
    # "less." / "faster." is still recognized as a token
    t = t.rstrip('.。．！!？? ')
    t = _fold_numbers(t, english)
    t = re.sub(r'\s+', ' ', t).strip()
    t = t.rstrip('.。．！!？? ')
    t = t.lower()
    t = re.sub(r'[«»"“”\'`]', '', t)
    t = re.sub(r'\s*([,;:])\s*', r'\1', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def parse_intros(path):
    """{intro id: [lines]}"""
    blocks = {}
    current = None
    for raw in io.open(path, encoding='utf-8').read().split('\n'):
        stripped = raw.strip()
        if not stripped or stripped.startswith(';'):
            continue
        head = re.match(r'^(\d{4})\s+(.*\S)$', raw)
        if head:
            current = int(head.group(1))
            if current in INTRO_IDS:
                blocks.setdefault(current, []).append(head.group(2).strip())
            continue
        if raw[:1] in ' \t' and current in INTRO_IDS:
            blocks[current].append(stripped)
        else:
            current = None
    return blocks


def tech_effect_of(entry):
    if isinstance(entry, dict):
        return entry['effect']
    m = re.match(r'^(.*?)\s*\((.*)\)\s*$', entry)
    return m.group(2) if m else entry


def max_matching(edges, n_right):
    """Kuhn's algorithm -> (size, match_r)."""
    match_r = [-1] * n_right

    def try_kuhn(u, seen):
        for v in edges[u]:
            if seen[v]:
                continue
            seen[v] = True
            if match_r[v] == -1 or try_kuhn(match_r[v], seen):
                match_r[v] = u
                return True
        return False

    size = 0
    for u in range(len(edges)):
        if try_kuhn(u, [False] * n_right):
            size += 1
    return size, match_r


def check_locale(loc):
    """Return a list of problem strings for one locale."""
    problems = []
    blocks = parse_intros('mods/aoe2/%s/tts.txt' % loc)
    de = DE.get(loc, {})
    english = (loc == 'ui')

    for key, cid in CIV_ID.items():
        d = de.get(key)
        if d is None:
            problems.append('%s %-12s: no DE reference data' % (loc, key))
            continue
        lines = blocks.get(cid)
        if not lines:
            problems.append('%s %-12s: intro id %d missing' % (loc, key, cid))
            continue

        expected_count = 2 + len(d['bonuses']) + len(d['techs']) + 1
        if len(lines) != expected_count:
            problems.append(
                '%s %-12s: %d lines, DE blurb implies %d'
                % (loc, key, len(lines), expected_count))

        uu_line, ut_line = lines[0], lines[1]
        body = lines[2:-1]
        team_line = lines[-1]

        # --- unique unit(s) -------------------------------------------------
        # the DE civ info panel names them as the blurb does
        for uu in d['uu_names']:
            if canon(uu, english) not in canon(uu_line, english):
                problems.append(
                    '%s %-12s UU %r not named in %r' % (loc, key, uu, uu_line))

        # --- unique technologies -------------------------------------------
        for tn in d['tech_names']:
            if canon(tn, english) not in canon(ut_line, english):
                problems.append(
                    '%s %-12s UT %r not named in %r'
                    % (loc, key, tn, ut_line))

        # --- team bonus -----------------------------------------------------
        # our line carries the locale's "Team bonus:" frame; strip it before
        # comparing against the raw DE team-bonus text.
        team_core = team_line
        for prefix in ('Team bonus:', 'Bonus týmu:', 'Bonus tímu:',
                       'Бонус команды:', 'Бонус каманды:', '组队：'):
            if team_core.startswith(prefix):
                team_core = team_core[len(prefix):].strip()
                break
        else:
            team_core = re.sub(r'^[^:：]{0,40}[:：]\s*', '', team_core)
        if canon(d['team'], english) != canon(team_core, english):
            problems.append(
                '%s %-12s team bonus mismatch: DE %r vs ours %r'
                % (loc, key, d['team'], team_line))

        # --- civ bonuses + tech effects, 1-to-1 ------------------------------
        canons = [canon(b, english) for b in d['bonuses']]
        canons += [canon(tech_effect_of(t), english) for t in d['techs']]
        cand = [canon(l, english) for l in body]

        edges = []
        for c in canons:
            edges.append([j for j, l in enumerate(cand) if c == l])

        size, match_r = max_matching(edges, len(cand))
        matched_body = set()
        matched_canon = set()
        for j, u in enumerate(match_r):
            if u != -1:
                matched_body.add(j)
                matched_canon.add(u)

        for u, c in enumerate(canons):
            if u in matched_canon:
                continue
            if u < len(d['bonuses']):
                label = d['bonuses'][u]
            else:
                label = d['techs'][u - len(d['bonuses'])]
            problems.append('%s %-12s MISSING %r' % (loc, key, label))

        for i, l in enumerate(body):
            if i in matched_body:
                continue
            problems.append('%s %-12s EXTRA line %r' % (loc, key, l))

    return problems


def main():
    all_problems = []
    for loc in LOCALES:
        if not os.path.exists('mods/aoe2/%s/tts.txt' % loc):
            continue
        probs = check_locale(loc)
        print('=== %-8s problems: %d' % (loc, len(probs)))
        all_problems.extend(probs)

    print()
    for p in all_problems:
        print(p)
    print()
    print('TOTAL PROBLEMS:', len(all_problems))
    return 1 if all_problems else 0


if __name__ == '__main__':
    sys.exit(main())
