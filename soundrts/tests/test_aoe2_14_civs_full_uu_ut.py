"""
D-Phase 3: Test all 14 new civs (1.5.1.3) have their AoE2 DE UU/UT
implemented and linked to the appropriate buildings.
"""
import os
import re

RULES_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'mods', 'aoe2', 'rules.txt')
RULES_PATH = os.path.normpath(RULES_PATH)


def _read_rules():
    with open(RULES_PATH, encoding='utf-8') as f:
        return f.read()


def _gather_civ_buildings(text, prefix):
    chunks = []
    for kind in ['_castle', '_stable', '_dock', '_monastery', '_shipyard',
                 '_university', '_blacksmith', '_barracks', '_workshop',
                 '_archery_range']:
        bname = prefix + kind
        m = re.search(r'def ' + bname + r'\n([\s\S]+?)(?=\n\n|\ndef )', text)
        if m:
            chunks.append(m.group(0))
    return '\n'.join(chunks)


# AoE2 DE reference: civ -> (building_prefix, expected_UU, expected_UT)
REFERENCE = {
    'goths':       ('goth',    ['huskarl'],                   ['anarchy', 'perfusion']),
    'persians':    ('persian', ['war_elephant'],              ['boiling_oil', 'mahouts']),
    'slavs':       ('slav',    ['boyar'],                     ['detinets', 'druzhina']),
    'cumans':      ('cuman',   ['kipchak'],                   ['steppe_husbandry', 'cuman_mercenaries']),
    'huns':        ('hun',     ['tarkan'],                    ['marauders', 'atikulu']),
    'koreans':     ('korean',  ['war_wagon', 'turtle_ship'],  ['eupseong', 'shinkichon']),
    'mayans':      ('mayan',   ['plumed_archer'],             ['obsidian_arrows', 'el_dorado']),
    'hindustanis': ('hindustani', ['armored_elephant', 'elephant_archer'], ['shatagni', 'frontier_defense']),
    'spanish':     ('spanish', ['conquistador', 'misionero'], ['inquisition', 'supremacy']),
    'magyars':     ('magyar',  ['magyar_huszar'],             ['fogarasi_mercenaries', 'corvinian_army']),
    'poles':       ('polish',  ['obuch', 'winged_hussar'],    ['szlachta_privileges', 'lechitic_legacy']),
    'italians':    ('italian', ['genoese_crossbowman'],       ['pavise', 'silk_road']),
    'bohemians':   ('bohemian', ['hussite_wagon', 'coustillier'], ['wagenburg_tactics', 'hussite_reforms']),
    'turks':       ('turk',    ['janissary', 'cannon_galleon'], ['sipahi', 'artillery']),
}


def test_14_new_civs_have_full_uu_ut():
    text = _read_rules()
    missing = []
    for civ, (prefix, uus, uts) in REFERENCE.items():
        buildings = _gather_civ_buildings(text, prefix)
        for u in uus:
            if not re.search(r'can_train[^\n]*\b' + re.escape(u) + r'\b', buildings):
                missing.append((civ, 'UU', u))
        for t in uts:
            if not re.search(r'can_research[^\n]*\b' + re.escape(t) + r'\b', buildings):
                missing.append((civ, 'UT', t))
    assert not missing, f"missing UU/UT: {missing}"


def test_all_uu_def_blocks_exist():
    """Every UU referenced in REFERENCE has a `def <name>` block; line_upgrade UUs have elite_*."""
    text = _read_rules()
    all_uus = []
    for civ, (prefix, uus, uts) in REFERENCE.items():
        all_uus.extend(uus)
    missing = []
    for u in all_uus:
        if not re.search(r'def ' + re.escape(u) + r'\n', text):
            missing.append(u)
        m = re.search(r'def ' + re.escape(u) + r'\n([\s\S]+?)(?=\n\n|\ndef )', text)
        if m and 'line_upgrade 1' in m.group(1):
            elite = 'elite_' + u
            if not re.search(r'def ' + re.escape(elite) + r'\n', text):
                missing.append(elite)
    assert not missing, f"missing UU defs: {missing}"


def test_all_ut_def_blocks_exist():
    """Every UT referenced in REFERENCE has a `def <name>` block with class upgrade."""
    text = _read_rules()
    all_uts = []
    for civ, (prefix, uus, uts) in REFERENCE.items():
        all_uts.extend(uts)
    missing = []
    for t in all_uts:
        m = re.search(r'def ' + re.escape(t) + r'\n([\s\S]+?)(?=\n\n|\ndef )', text)
        if not m:
            missing.append(t + ' (no def)')
            continue
        if 'class upgrade' not in m.group(1):
            missing.append(t + ' (not class upgrade)')
    assert not missing, f"missing UT defs: {missing}"
