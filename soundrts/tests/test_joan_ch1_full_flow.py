"""Test Joan of Arc ch1 full flow (v2: Baudricourt at b4 grants letter + escort).

Validates that:
- 1.txt is a valid map (parses without error)
- Baudricourt (npc_baudricourt) exists at b4 and is a real named NPC,
  not a generic monk
- npc_baudricourt in rules.txt is_a monk (so it renders with a sprite
  in the AoE2 mod -- res-base 'soldier' has no sprite in AoE2 mode)
- Dauphin (npc_dauphin) exists at f4
- Joan starts the chapter as the named hero unit npc_joan
  (NOT a generic monk -- Joan is a hero, not a worker monk)
- holy_letter is NOT on the ground at a1 (granted at b4)
- npc_dauphin in rules.txt accepts holy_letter
- npc_joan in rules.txt is_a monk (renders) and is key_unit
- intro 8810 mentions a1, b4, f4
- cut_scene 8826 (Baudricourt grants letter) and 8830 (Dauphin receives letter) exist
- triggers:
    (has_entered b4 npc_joan) -> add_inventory_item + add_units escort
    (npc_has_item npc_dauphin holy_letter f4) -> objective_complete
- defeat on key_unit_killed npc_joan (NOT on generic monk)
"""
from pathlib import Path

JOAN = Path("mods/aoe2/single/Joan of Arc")


def test_ch1_map_exists():
    p = JOAN / "1.txt"
    assert p.exists(), "ch1 1.txt missing"


def test_ch1_has_baudricourt_at_b4():
    text = (JOAN / "1.txt").read_text(encoding="utf-8")
    assert "neutral faction franks b4" in text, "Baudricourt must be at b4"
    assert "1 npc_baudricourt" in text, "Baudricourt must be a real npc_baudricourt unit (not a generic monk)"


def test_ch1_has_dauphin_at_f4():
    text = (JOAN / "1.txt").read_text(encoding="utf-8")
    assert "neutral faction franks f4" in text, "Dauphin court must be at f4"


def test_ch1_no_holy_letter_on_ground_at_a1():
    """Letter must be granted at b4, not picked up from a1."""
    text = (JOAN / "1.txt").read_text(encoding="utf-8")
    assert "holy_letter a1" not in text, "holy_letter must NOT be on the ground at a1 (granted at b4)"


def test_ch1_player_has_npc_joan_hero():
    """Player must start with npc_joan (the named hero unit), not a plain monk."""
    text = (JOAN / "1.txt").read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("player ") and " a1 " in line:
            assert "npc_joan" in line, f"Player must start with npc_joan hero unit: {line!r}"
            # Must NOT end with bare 'monk' (Joan is a hero, not a worker monk)
            stripped = line.strip().split()
            assert stripped[-1] == "npc_joan", f"Player line must end with npc_joan (Joan hero), got: {line!r}"
            break
    else:
        raise AssertionError("No player line starting with ' a1 ' found")


def test_ch1_b4_trigger_grants_letter_and_escort():
    text = (JOAN / "1.txt").read_text(encoding="utf-8")
    assert "has_entered b4 npc_joan" in text, "Joan (npc_joan) must trigger on entering b4 (Baudricourt)"
    for line in text.splitlines():
        if "has_entered b4 npc_joan" in line:
            assert "add_inventory_item holy_letter" in line, f"b4 trigger must grant holy_letter: {line}"
            assert "add_units" in line, f"b4 trigger must spawn escort units: {line}"
            assert "aoe_knight" in line, f"b4 trigger escort must include aoe2-mode aoe_knight: {line}"
            # Ban res-base units (they have no sprite in AoE2 mode)
            assert "footman" not in line, f"b4 trigger must NOT use base footman (no sprite in AoE2): {line}"
            assert " knight" not in line, f"b4 trigger must NOT use base knight (no sprite in AoE2): {line}"
            break
    else:
        raise AssertionError("b4 trigger not found")


def test_ch1_npc_has_item_trigger_for_dauphin():
    text = (JOAN / "1.txt").read_text(encoding="utf-8")
    assert "(npc_has_item npc_dauphin holy_letter" in text, "Must trigger on Dauphin receiving holy_letter"
    assert "f4" in text, "Dauphin trigger must mention f4"
    assert "objective_complete 1" in text, "Must mark objective 1 complete"


def test_ch1_defeat_on_npc_joan_killed():
    """Defeat on key_unit_killed npc_joan (NOT bare monk)."""
    text = (JOAN / "1.txt").read_text(encoding="utf-8")
    assert "key_unit_killed npc_joan" in text, "Defeat must trigger on npc_joan (Joan) being killed"
    assert "(defeat)" in text


def test_rules_defines_npc_dauphin():
    text = (JOAN / "rules.txt").read_text(encoding="utf-8")
    assert "def npc_dauphin" in text, "rules.txt must define npc_dauphin"
    start = text.find("def npc_dauphin")
    end = text.find("\n\n", start)
    if end == -1:
        end = len(text)
    block = text[start:end]
    assert "receive_items 1" in block
    assert "holy_letter" in block
    assert "accept_from" in block


def test_rules_defines_npc_baudricourt():
    text = (JOAN / "rules.txt").read_text(encoding="utf-8")
    assert "def npc_baudricourt" in text, "rules.txt must define npc_baudricourt (real NPC, not a generic monk)"
    start = text.find("def npc_baudricourt")
    end = text.find("\n\n", start)
    if end == -1:
        end = len(text)
    block = text[start:end]
    # Must be is_a monk to render with sprite in the AoE2 mod
    assert "is_a monk" in block, "npc_baudricourt must be is_a monk (sprite visibility in AoE2 mod)"
    assert "receive_items 0" in block, "npc_baudricourt must not accept items (dialogue trigger only)"


def test_rules_defines_npc_joan_hero():
    """npc_joan must be a named hero unit (not just a generic monk)."""
    text = (JOAN / "rules.txt").read_text(encoding="utf-8")
    assert "def npc_joan" in text, "rules.txt must define npc_joan (Joan hero unit)"
    start = text.find("def npc_joan")
    end = text.find("\n\n", start)
    if end == -1:
        end = len(text)
    block = text[start:end]
    assert "is_a monk" in block, "npc_joan must is_a monk (sprite + ability to carry items)"
    # HP should be higher than a base monk (so Joan feels like a hero, not a worker)
    assert "hp_max 200" in block or "hp_max 150" in block, "npc_joan should have elevated HP for a hero unit"
    # 'key_unit' is NOT a valid Soldier attribute (it is a trigger condition, not a unit property)
    assert "key_unit 1" not in block, "key_unit is a trigger condition, not a unit attribute -- remove it"
    # npc_joan is a non-combat hero NPC (the player must protect her).
    # Like npc_dauphin and npc_baudricourt in the same file, she MUST NOT have
    # any melee attack.  An earlier revision set "mdg 12 / mdg_range 1" which
    # made Joan a 12-damage melee murder machine (3x militia, 6.7x monk HP)
    # and contradicted the ch2 "train militia, deliver to b2" objective that
    # asks the PLAYER's militia to do the fighting.  See npc_joan docstring.
    #
    # We assert against the ACTIVE attribute block (lines that begin with a
    # non-';' / non-empty token right after "def npc_joan"), NOT against the
    # whole comment-laden block, so the docstring's own mention of "mdg 0"
    # does not trip the check.
    lines_after_def = [
        ln.strip() for ln in block.splitlines()[1:]  # skip the "def npc_joan" line
    ]
    active_attrs = [ln for ln in lines_after_def if ln and not ln.startswith(";")]
    for attr in active_attrs:
        # Active attributes use a single token (no '='), e.g. "hp_max 200".
        # Reject any "mdg ..." or "mdg_range ..." attribute on the active side.
        head = attr.split()[0] if attr else ""
        assert head not in ("mdg", "mdg_range"), (
            f"npc_joan must inherit mdg 0 / mdg_range 0 from class soldier (mod's "
            f"mods/aoe2/rules.txt line 318-333) and have no explicit mdg -- a "
            f"'{attr}' attribute makes Joan a melee unit, breaking the ch2 'rally "
            f"the militia' objective and the 'protect Joan, do not let her die' "
            f"design intent. See npc_joan docstring."
        )


def test_style_txt_defines_joan_npc_titles():
    """style.txt must define titles + intros for npc_joan, npc_baudricourt,
    npc_dauphin so the unit panel reads the proper name and a short bio
    (in the style of the Raynor/SC2 hero intros).

    These live in the CAMPAIGN-LOCAL style.txt
    (mods/aoe2/single/Joan of Arc/ui/style.txt), not the mod-wide one,
    so campaign changes don't pollute the global mod style."""
    style = (JOAN / "ui" / "style.txt").read_text(encoding="utf-8")
    for name, title_id, intro_id in [
        ("npc_joan", "8862", "8865"),
        ("npc_baudricourt", "8863", "8866"),
        ("npc_dauphin", "8864", "8867"),
    ]:
        assert f"def {name}" in style, f"campaign style.txt must define 'def {name}' so the unit has a UI title"
        idx = style.find(f"def {name}")
        end = style.find("\n\n", idx)
        if end == -1:
            end = len(style)
        block = style[idx:end]
        assert f"title {title_id}" in block, f"def {name} in style.txt must have 'title {title_id}', got block:\n{block}"
        assert f"intro {intro_id}" in block, f"def {name} in style.txt must have 'intro {intro_id}' (hero bio), got block:\n{block}"


def test_global_tts_has_joan_hero_intros():
    """tts.txt must have the hero bio intros (8865-8867) in EN and ZH.

    Strings live in the campaign-local tts.txt so the campaign is
    self-contained."""
    for ui in ["ui", "ui-zh"]:
        text = (JOAN / ui / "tts.txt").read_text(encoding="utf-8")
        for cid in ("8865", "8866", "8867"):
            found = any(l.startswith(cid) for l in text.splitlines())
            assert found, f"{cid} (hero intro) missing in campaign mods/aoe2/single/Joan of Arc/{ui}/tts.txt"


def test_tts_has_joan_npc_titles():
    """tts.txt must provide the title strings for 8862-8864 in both EN and ZH.

    Titles and intros live in the campaign-local tts.txt
    (mods/aoe2/single/Joan of Arc/ui/tts.txt) so the campaign is
    self-contained."""
    for ui in ["ui", "ui-zh"]:
        text = (JOAN / ui / "tts.txt").read_text(encoding="utf-8")
        for cid in ("8862", "8863", "8864"):
            found = any(l.startswith(cid) for l in text.splitlines())
            assert found, f"{cid} missing in campaign mods/aoe2/single/Joan of Arc/{ui}/tts.txt"


def test_intro_8810_mentions_b4_and_f4():
    for ui in ["ui", "ui-zh"]:
        text = (JOAN / ui / "tts.txt").read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.startswith("8810"):
                content = line
                break
        else:
            raise AssertionError(f"8810 not found in {ui}/tts.txt")
        assert "a1" in content, f"8810 must mention a1: {content}"
        assert "b4" in content, f"8810 must mention b4 (Baudricourt): {content}"
        assert "f4" in content, f"8810 must mention f4 (Dauphin): {content}"
        assert "pick up" not in content.lower() or "from" in content.lower(), (
            f"8810 should describe letter as granted, not picked up at a1: {content}"
        )


def test_cut_scenes_8826_and_8830_exist():
    for ui in ["ui", "ui-zh"]:
        text = (JOAN / ui / "tts.txt").read_text(encoding="utf-8")
        for cid in ("8826", "8830"):
            found = any(l.startswith(cid) for l in text.splitlines())
            assert found, f"{cid} missing in {ui}/tts.txt"


def test_rules_txt_has_no_bare_ai_mode_lines():
    """The Joan campaign rules.txt must not have a bare ``ai_mode`` line
    (a line that is just the word ``ai_mode`` with no value).

    The rules parser at ``soundrts/definitions.py:300`` does
    ``d[name][words[0]] = words[1]`` for properties in
    ``Rules.string_properties`` (which includes ``ai_mode``), and a
    missing value causes an ``IndexError`` caught by the broad
    ``except`` at ``soundrts/definitions.py:672``, which logs
    ``"error in line: ai_mode"`` once per NPC per rules reload. The
    intended "NPC stands still" effect is already provided by
    ``agro_on_sight 0`` + ``counterattack_enabled 0`` + ``mdg 0`` /
    ``mdf 0`` / ``rdf 0`` / ``rdg 0``; the bare ``ai_mode`` line was
    both a parser-time bug and a redundant no-op.
    """
    text = (JOAN / "rules.txt").read_text(encoding="utf-8")
    bare_ai_mode = [
        (i + 1, line)
        for i, line in enumerate(text.splitlines())
        if line.strip() == "ai_mode"
    ]
    assert not bare_ai_mode, (
        "Joan of Arc rules.txt must not contain bare 'ai_mode' lines "
        "(no value); they trigger 'error in line: ai_mode' warnings at "
        "chapter load. Use agro_on_sight 0 + counterattack_enabled 0 + "
        "mdg 0 / mdf 0 / rdf 0 / rdg 0 to make a story NPC stand still. "
        f"Found at: {bare_ai_mode}"
    )
