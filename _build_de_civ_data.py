# -*- coding: utf-8 -*-
"""Build ``_de_civ_data.json``: the authoritative AoE2 DE civ data for
every locale we ship.

Source of truth:
  * ``_de_strings/<locale>.json`` - the official DE string table
    (extracted from the game by the aoe2techtree project).
  * ``_de_trees/<civ>.json``      - the official DE tech tree per civ,
    used to map each civ to its civ-blurb string id unambiguously and
    to provide the localized display names of the unique units and
    unique technologies.

Output shape::

    {locale: {civ_key: {
        'blurb_id': int,
        'type': str,            # e.g. "Infantry civilization"
        'bonuses': [str],       # the civ bonus bullets
        'uu_names': [str],      # unique unit(s), localized
        'techs': [{             # the unique technologies, localized
            'name': str,
            'effect': str,
        }],
        'tech_names': [str],    # bare unique tech names
        'team': str,            # team bonus
        'tech_ages': {name: age},
    }}}
"""
import io
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

LOCALES = ['ui', 'ui-zh', 'ui-be', 'ui-cs', 'ui-de', 'ui-es', 'ui-fr',
           'ui-it', 'ui-pl', 'ui-pt-BR', 'ui-ru', 'ui-sk', 'ui-vi']

TAG = re.compile(r'<[^>]+>')

# The official DE blurbs are not perfectly uniform across locales:
#   * the bullet marker is "•" in most locales and "—" in the Russian
#     and Belarusian ones,
#   * the Russian Huns blurb loses the bullet of its second bonus and
#     starts the line with the minus sign instead,
#   * some locales omit the bullet on the first unique tech,
#   * some locales write the unique-tech effect without parentheses.
BULLET_RE = re.compile(r'^\s*[•—–]\s*')
MINUS_BULLET_RE = re.compile(r'^\s*−\s*(?=\d)')


def _plain(fragment):
    frag = re.sub(r'<br\s*/?>', '\n', fragment)
    frag = TAG.sub('', frag)
    frag = frag.replace('\xa0', ' ')
    return [l.strip() for l in frag.split('\n') if l.strip()]


def _is_bullet(line):
    """Is this line the start of a new bullet?"""
    if BULLET_RE.match(line):
        return True
    # the Russian Huns blurb drops the bullet and starts the line with
    # the minus sign of the discount
    return bool(MINUS_BULLET_RE.match(line))


def _strip_bullet(line):
    return BULLET_RE.sub('', line).strip()


def split_blurb(raw):
    """Split one civ blurb into its sections.

    The markup skeleton is identical in every locale::

        <type> civilization<br><br>
        • bonus<br>
        <b>Unique Unit:</b> <br>Name (Type)<br>
        <b>Unique Techs:</b> <br>• Tech (effect)<br>
        <b>Team Bonus:</b> <br>effect

    so we split on the ``<b>`` markers rather than on the (localized)
    section titles.

    Some locales put the section title *inside* the ``<b>`` element
    (e.g. ``<b>特殊單位：</b>``); in that case the title survives in the
    following fragment and has to be stripped again.
    """
    parts = [p for p in re.split(r'<b(?:\s[^>]*)?>', raw)
             if TAG.sub('', p).strip()]
    if not parts:
        return None

    def bullets(lines):
        """Collect the bonus bullets."""
        out = []
        for l in lines:
            if _is_bullet(l):
                out.append(_strip_bullet(l))
            elif out and not l.rstrip().endswith(':'):
                out[-1] += ' ' + l
        return out

    def strip_label(lines):
        """Drop a leading "Unique Unit:" style label.

        The label may use an ASCII colon or a full-width one (zh/ja).
        """
        out = list(lines)
        if out and re.search(r'[:：]\s*$', out[0]):
            out = out[1:]
        return out

    def strip_type(text):
        """Drop the unit-type annotation.

        "Huskarl (Infantry)" / "хускарл (пехота)." / "哥德衛隊 (步兵)"

        The annotation may sit anywhere inside the name (the Chinese
        blurb writes "风琴炮 (攻城火药单位)，卡拉维尔战舰"), so every
        parenthesised group is removed.
        """
        text = re.sub(r'[(（][^)）]*[)）]', '', text)
        return re.sub(r'\s+', ' ', text).strip().rstrip('.,')

    def split_units(text):
        """Split a unit list into the individual unit names.

        The separator is a comma in most locales and a full-width comma
        in the Chinese one.
        """
        out = []
        for chunk in re.split(r'[,，]', text):
            chunk = strip_type(chunk)
            chunk = BULLET_RE.sub('', chunk).strip()
            if chunk:
                out.append(chunk)
        return out

    def tech_entries(lines):
        """Collect the unique-tech entries.

        Most locales write one tech per line, each starting with a
        bullet.  A few (Polish Magyars, Portuguese Malays) omit the
        bullet on the first tech; a line that follows a *complete*
        entry (one whose parentheses are balanced) therefore starts a
        new entry, while a line that follows an *incomplete* entry is a
        continuation of it.
        """
        out = []
        for l in lines:
            s = l.strip()
            if not s:
                continue
            if BULLET_RE.match(s):
                out.append(_strip_bullet(s))
                continue
            if out and not out[-1].rstrip().endswith(')'):
                out[-1] = out[-1].rstrip() + ' ' + s
                continue
            out.append(s)
        return out

    header = _plain(parts[0])
    info = {'type': header[0] if header else '',
            'bonuses': bullets(header[1:]),
            'uu_names': [], 'techs': [], 'team': ''}
    if len(parts) > 1:
        uu = strip_label(_plain(parts[1]))
        names = []
        for l in uu:
            names.extend(split_units(l))
        info['uu_names'] = names
    if len(parts) > 2:
        tech = strip_label(_plain(parts[2]))
        info['techs'] = tech_entries(tech)
    if len(parts) > 3:
        team = ' '.join(strip_label(_plain(parts[3]))).strip()
        info['team'] = _strip_bullet(team).strip()
    return info


def split_tech_name_effect(text):
    """Split "Name (effect)" into ("Name", "effect").

    The parentheses may be nested ("Fereters (Infantry (except
    Spearman-line) +30 HP)") and there may be trailing text after the
    closing parenthesis (the Italian Chinese blurb appends "; lou chuan
    sparano razzi").  A blurb that does not use parentheses at all (the
    German Franks blurb) yields ``(text, text)``.
    """
    text = text.strip()
    open_at = text.find('(')
    if open_at < 0:
        return text, text
    depth = 0
    close_at = -1
    for i in range(open_at, len(text)):
        if text[i] == '(':
            depth += 1
        elif text[i] == ')':
            depth -= 1
            if depth == 0:
                close_at = i
                break
    if close_at < 0:
        return text, text
    name = text[:open_at].strip()
    effect = text[open_at + 1:close_at].strip()
    trailing = text[close_at + 1:].strip()
    if trailing and not re.fullmatch(r'[.,;:!?…\s]*', trailing):
        # the Italian Chinese blurb appends a second sentence to the
        # effect ("Missilistica (...); lou chuan sparano razzi")
        effect = (effect + ' ' + trailing).strip()
    return name, effect


def load_blurbs(path):
    data = json.load(io.open(path, encoding='utf-8'))
    out = {}
    for k, v in data.items():
        if k.isdigit() and isinstance(v, str) and '<b>' in v:
            info = split_blurb(v)
            if info:
                out[int(k)] = info
    return out


def load_tree(path):
    """The civ's official tech tree -> its unique units and techs."""
    d = json.load(io.open(path, encoding='utf-8'))
    uu, techs = [], []
    for node in d.get('units_techs', []):
        nt = node.get('node_type')
        name = node.get('name')
        nsid = node.get('name_string_id')
        if not name or not nsid:
            continue
        if nt == 'UniqueTech':
            techs.append({'name': name, 'age': node.get('age_id'),
                          'string_id': nsid})
        elif nt == 'UniqueUnit':
            # the elite upgrade shares the base unit's line; keep the
            # base (non-"Elite") entry
            if not name.startswith('Elite'):
                uu.append({'name': name, 'string_id': nsid})
    return {'uu': uu, 'techs': techs}


def display_name(strings, string_id, fallback):
    """The localized display name of a DE unit / technology."""
    raw = strings.get(str(string_id))
    if not raw:
        return fallback
    # a hyphenated word split across two lines keeps its hyphen
    raw = re.sub(r'-\s*<br\s*/?>\s*', '-', raw)
    raw = re.sub(r'<br\s*/?>', ' ', raw)
    raw = TAG.sub('', raw)
    raw = re.sub(r'\s+', ' ', raw).strip()
    return raw or fallback


def main():
    trees = {}
    for fn in sorted(os.listdir('_de_trees')):
        trees[fn[:-5]] = load_tree(os.path.join('_de_trees', fn))

    en = load_blurbs(os.path.join('_de_strings', 'ui.json'))

    by_techs = {}
    for bid, info in en.items():
        by_techs.setdefault(frozenset(
            split_tech_name_effect(t)[0] for t in info['techs']),
            []).append(bid)

    # civ key -> blurb id (resolved via the civ's official tech tree)
    blurb_of = {}
    for key, tree in trees.items():
        want = frozenset(t['name'] for t in tree['techs'])
        cands = by_techs.get(want, [])
        if len(cands) != 1:
            print('UNRESOLVED %-12s %s -> %s' % (key, sorted(want), cands))
            continue
        blurb_of[key] = cands[0]

    print('resolved civs:', len(blurb_of))

    result = {}
    for loc in LOCALES:
        path = os.path.join('_de_strings', '%s.json' % loc)
        if not os.path.exists(path):
            continue
        strings = json.load(io.open(path, encoding='utf-8'))
        bl = load_blurbs(path)
        per_civ = {}
        for key, bid in blurb_of.items():
            info = bl.get(bid)
            if info is None:
                continue
            tree = trees[key]

            # --- the unique units -------------------------------------------
            uu_names = list(info['uu_names'])
            if not uu_names:
                uu_names = [display_name(strings, u['string_id'], u['name'])
                            for u in tree['uu']]

            # --- the unique technologies ------------------------------------
            techs = []
            for i, raw in enumerate(info['techs']):
                name, effect = split_tech_name_effect(raw)
                fallback = tree['techs'][i] if i < len(tree['techs']) else None
                if fallback is not None:
                    # the official localized display name of the tech
                    disp = display_name(strings, fallback['string_id'],
                                        fallback['name'])
                    # the blurb sometimes writes the tech without
                    # parentheses ("In Ordonnanzkompanien kosten ...");
                    # in that case the display name is the better one
                    if name == raw and len(name.split()) > 4:
                        name = disp
                    # otherwise the blurb's own spelling wins, because
                    # the DE tech-tree strings occasionally differ
                    # ("Keshig" vs. "Keshik")
                techs.append({'name': name, 'effect': effect})

            entry = {
                'blurb_id': bid,
                'type': info['type'],
                'bonuses': info['bonuses'],
                'uu_names': uu_names,
                'techs': techs,
                'tech_names': [t['name'] for t in techs],
                'team': info['team'],
                'tech_ages': {t['name']: t['age'] for t in tree['techs']},
            }
            per_civ[key] = entry
        result[loc] = per_civ
        print('=== %-8s civs=%d' % (loc, len(per_civ)))

    io.open('_de_civ_data.json', 'w', encoding='utf-8').write(
        json.dumps(result, ensure_ascii=False, indent=1))


main()
