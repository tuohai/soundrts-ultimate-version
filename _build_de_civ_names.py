# -*- coding: utf-8 -*-
"""Build the localized unique-unit / unique-tech names for each of the
42 civs, from the official DE string tables.

The per-civ tech trees (``_de_trees/<civ>.json``) give the official
``name_string_id`` of every unique unit and unique technology; the
official string table (``_de_strings/<locale>.json``) maps that id to
the localized display name.

Output: ``_de_civ_names.json``::

    {locale: {civ_key: {
        'uu': {english_name: localized_name},
        'techs': {english_name: localized_name},
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


def norm(s):
    """Normalize a DE display name: collapse the <br> line breaks.

    A break after a hyphen is a hyphenated word split across two lines
    ("Circum-<br>navigation"), so the hyphen is kept and the break is
    removed without inserting a space.
    """
    s = re.sub(r'-\s*<br\s*/?>\s*', '-', s)
    s = re.sub(r'<br\s*/?>', ' ', s)
    s = re.sub(r'<[^>]+>', '', s)
    return re.sub(r'\s+', ' ', s).strip()


def main():
    # English unique units / techs per civ, with their string ids
    base = {}
    for fn in sorted(os.listdir('_de_trees')):
        key = fn[:-5]
        d = json.load(io.open(os.path.join('_de_trees', fn), encoding='utf-8'))
        uu, techs = {}, {}
        for node in d.get('units_techs', []):
            nt = node.get('node_type')
            name = node.get('name')
            nsid = node.get('name_string_id')
            if not name or not nsid:
                continue
            if nt == 'UniqueTech':
                techs[name] = nsid
            elif nt == 'UniqueUnit':
                # the elite upgrade shares the base unit's line; keep the
                # base (non-"Elite") entry
                if not name.startswith('Elite'):
                    uu[name] = nsid
        base[key] = {'uu': uu, 'techs': techs}

    out = {}
    for loc in LOCALES:
        path = os.path.join('_de_strings', '%s.json' % loc)
        if not os.path.exists(path):
            continue
        strings = json.load(io.open(path, encoding='utf-8'))
        per_civ = {}
        for key, entry in base.items():
            item = {'uu': {}, 'techs': {}}
            for name, nsid in entry['uu'].items():
                item['uu'][name] = norm(strings.get(str(nsid), name))
            for name, nsid in entry['techs'].items():
                item['techs'][name] = norm(strings.get(str(nsid), name))
            per_civ[key] = item
        out[loc] = per_civ

    io.open('_de_civ_names.json', 'w', encoding='utf-8').write(
        json.dumps(out, ensure_ascii=False, indent=1))

    # report unresolved names (identical to the English fallback)
    for loc in LOCALES:
        bad = []
        for key, item in out[loc].items():
            for name, loc_name in item['uu'].items():
                if loc_name == name and loc != 'ui':
                    bad.append('uu %s' % name)
            for name, loc_name in item['techs'].items():
                if loc_name == name and loc != 'ui':
                    bad.append('tech %s' % name)
        print('%-8s untranslated: %d %s' % (loc, len(bad), bad[:8]))


main()
