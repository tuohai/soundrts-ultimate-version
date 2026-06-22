"""One-shot generator for CrazyMod 5-tier AI (run manually)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "mods" / "crazyMod9beta10"
rules_path = ROOT / "rules.txt"
ai_path = ROOT / "ai.txt"

FACTIONS = {
    "traditionnel": {
        "worker": "serf",
        "hall": "chatelet",
        "open": "get {hall} 10 {worker}\nget 12 arbaletrier 6 knight",
        "mid": "get 18 {worker} 25 arbaletrier 15 knight 8 catapult 4 priest",
        "late": "get 30 {worker} 45 arbaletrier 30 paladin 15 catapult 8 dragon",
        "storm": "get 50 {worker} 70 arbaletrier 50 paladin 25 dragon 20 catapult",
    },
    "technique": {
        "worker": "travailleur",
        "hall": "mairie",
        "open": "get {hall} 10 {worker}\nget 12 mousquetaire 8 lance_grenade",
        "mid": "get 18 {worker} 25 mousquetaire 15 lance_grenade 6 chasseur_dirigeable 4 bombardier_dirigeable",
        "late": "get 28 {worker} 40 mousquetaire 25 lance_grenade 12 bombardier_dirigeable 8 dirigeable_d_observation",
        "storm": "get 45 {worker} 60 mousquetaire 45 lance_grenade 25 bombardier_dirigeable 20 chasseur_dirigeable",
    },
    "robotique": {
        "worker": "geek",
        "hall": "garage",
        "open": "get {hall} 10 {worker}\nget 10 tireur_laser 6 drone",
        "mid": "get 18 {worker} 22 tireur_laser 12 drone 6 canon_plasma",
        "late": "get 28 {worker} 35 tireur_laser 20 drone 12 vaisseau_laser 8 canon_magnetique",
        "storm": "get 45 {worker} 55 tireur_laser 35 drone 25 vaisseau_laser 18 canon_plasma",
    },
    "tenebre": {
        "worker": "esclave_mort_vivant",
        "hall": "cimetiere",
        "open": "get {hall} 10 {worker}\nget 14 goule 8 skeleton",
        "mid": "get 18 {worker} 20 goule 15 skeleton 6 necromancer 4 liche",
        "late": "get 28 {worker} 30 goule 25 skeleton 12 necromancer 10 liche 8 sombral",
        "storm": "get 45 {worker} 45 goule 40 skeleton 20 necromancer 18 liche 25 sombral",
    },
    "elfique": {
        "worker": "recolteur",
        "hall": "clairiere",
        "open": "get {hall} 10 {worker}\nget 14 archerot 8 centaure",
        "mid": "get 18 {worker} 25 archerot 15 centaure 8 erudit 4 druide",
        "late": "get 28 {worker} 40 archer_des_forets 25 centaure 15 erudit 10 druide",
        "storm": "get 45 {worker} 60 archer_des_forets 40 centaure 25 erudit 18 druide",
    },
    "orc": {
        "worker": "peon",
        "hall": "campement",
        "open": "get {hall} 11 {worker}\nget 12 troll_cogneur 10 tireur_de_fusee",
        "mid": "get 20 {worker} 25 troll_cogneur 18 tireur_de_fusee 8 ogre_lanceur_de_roche",
        "late": "get 32 {worker} 40 troll_cogneur 30 tireur_de_fusee 15 ogre_lanceur_de_roche 10 hippogriffe",
        "storm": "get 55 {worker} 65 troll_cogneur 50 tireur_de_fusee 30 ogre_lanceur_de_roche 25 hippogriffe",
    },
    "elementale": {
        "worker": "fee",
        "hall": "cercle_des_elements",
        "open": "get {hall} 12 {worker}\nget 4 elemental_de_terre 4 elemental_de_feu",
        "mid": "get 20 {worker} 8 elemental_de_terre 8 elemental_de_feu 6 elemental_d_eau 6 elemental_d_air",
        "late": "get 35 {worker} 15 elemental_de_terre 15 elemental_de_feu 12 elemental_d_eau 12 elemental_d_air 4 mage",
        "storm": "get 55 {worker} 25 elemental_de_terre 25 elemental_de_feu 20 elemental_d_eau 20 elemental_d_air 10 mage",
    },
    "sauvage": {
        "worker": "gredin",
        "hall": "planque",
        "open": "get {hall} 11 {worker}\nget 12 chasseresse 10 archer",
        "mid": "get 18 {worker} 22 chasseresse 18 archer 10 ensorceleuse",
        "late": "get 28 {worker} 35 chasseresse 30 archer 18 ensorceleuse",
        "storm": "get 48 {worker} 55 chasseresse 45 archer 30 ensorceleuse",
    },
    "vermine": {
        "worker": "ouvriere_marcheuse",
        "hall": "couveuse",
        "open": "get {hall} 10 {worker}\nget termitiere\nget 14 larve 10 termite_gardien",
        "mid": "get 18 {worker} 20 larve 18 termite_gardien 10 termite_conquerant 8 guepe_colerique",
        "late": "get 30 {worker} 30 larve 28 termite_gardien 20 termite_conquerant 15 guepe_colerique",
        "storm": "get 50 {worker} 45 larve 40 termite_gardien 35 termite_conquerant 28 guepe_colerique 12 termite_tank",
    },
    "elfe_noir": {
        "worker": "voleur",
        "hall": "cabane",
        "open": "get {hall} 10 {worker}\nget 12 rodeur 10 darkarcher",
        "mid": "get 18 {worker} 22 darkarcher 15 rodeur 8 assassin 6 illusionniste",
        "late": "get 28 {worker} 35 darkarcher 25 maitre_assassin 15 illusionniste 10 doctoresse",
        "storm": "get 48 {worker} 60 darkarcher 45 maitre_assassin 30 illusionniste 25 doctoresse",
    },
}

TIER_CFG = {
    "adv": {
        "defeat_score": 40,
        "counter_skill": 75,
        "starting_resources": "100 100",
        "watchdog": 480,
        "attack_ratio": 150,
    },
    "exp": {
        "defeat_score": 80,
        "counter_skill": 90,
        "starting_resources": "200 200",
        "starting_population": 20,
        "watchdog": 360,
        "attack_ratio": 120,
    },
    "nm": {
        "defeat_score": 200,
        "counter_skill": 100,
        "starting_resources": "400 400",
        "starting_population": 40,
        "watchdog": 240,
        "attack_ratio": 90,
    },
}


def fmt_block(faction: str, key: str, data: dict) -> str:
    return data[key].format(worker=data["worker"], hall=data["hall"])


def gen_tier_ai(faction: str, tier_key: str, suffix: str) -> str:
    cfg = TIER_CFG[tier_key]
    data = FACTIONS[faction]
    name = f"{faction}_{suffix}"
    lines = [
        f"def {name}",
        f"defeat_score {cfg['defeat_score']}",
        f"counter_skill {cfg['counter_skill']}",
    ]
    if cfg.get("starting_resources"):
        lines.append(f"starting_resources {cfg['starting_resources']}")
    if cfg.get("starting_population"):
        lines.append(f"starting_population {cfg['starting_population']}")
    lines += [
        f"watchdog {cfg['watchdog']}",
        "constant_attacks 1",
        "research 1",
        f"attack_ratio {cfg['attack_ratio']}",
        "",
        f"label {name}_loop",
        fmt_block(faction, "open", data),
        "attack",
        fmt_block(faction, "mid", data),
        "attack",
        fmt_block(faction, "late", data),
        "attack",
        fmt_block(faction, "storm", data),
        "attack",
        f"goto {name}_loop",
        "",
    ]
    return "\n".join(lines)


def main():
    rules = rules_path.read_text(encoding="utf-8")
    for faction in FACTIONS:
        if f"beginner c_{faction}" in rules:
            continue
        old = f"easy c_{faction}\naggressive {faction}"
        new = (
            f"beginner c_{faction}\n"
            f"intermediate {faction}\n"
            f"advanced {faction}_adv\n"
            f"expert {faction}_exp\n"
            f"nightmare {faction}_nm"
        )
        if old not in rules:
            raise SystemExit(f"rules block not found for {faction}")
        rules = rules.replace(old, new)
    rules_path.write_text(rules, encoding="utf-8")

    ai = ai_path.read_text(encoding="utf-8")

    for faction in FACTIONS:
        if faction == "vermine":
            continue
        marker = f"def c_{faction}\n\n"
        if f"def c_{faction}\ndefeat_score" not in ai and marker in ai:
            ai = ai.replace(
                marker,
                f"def c_{faction}\ndefeat_score 10\ncounter_skill 25\n\n",
                1,
            )

    for faction in FACTIONS:
        if faction == "vermine":
            continue
        pat = (
            rf"(def {re.escape(faction)}\n\nwatchdog )\d+"
            rf"(\nconstant_attacks )0"
        )
        ai, n = re.subn(
            pat,
            r"\g<1>600\g<2>1\ndefeat_score 20\ncounter_skill 50",
            ai,
            count=1,
        )
        if n == 0:
            raise SystemExit(f"intermediate patch failed for {faction}")

    c_vermine = """
def c_vermine
defeat_score 10
counter_skill 25
watchdog 600
constant_attacks 0
research 1

label c_vermine1
get couveuse 10 ouvriere_marcheuse
get termitiere
get 14 larve 10 termite_gardien
get pouponniere
get 12 termite_conquerant
get arbre_a_miel
get 10 guepe_colerique
get laboratoire_larvaire
get 18 termite_gardien 12 termite_conquerant
get 15 guepe_colerique
get 22 ouvriere_marcheuse
get 28 termite_gardien 10 termite_tank
get 20 guepe_colerique
get 35 ouvriere_marcheuse
get 40 termite_gardien 18 termite_conquerant
goto c_vermine1

"""
    ai = re.sub(r"def c_vermine\n\n\n\n", c_vermine + "\n", ai, count=1)

    vermine_inter = """
def vermine
defeat_score 20
counter_skill 50
watchdog 600
constant_attacks 1
research 1

label vermine0
get 10 ouvriere_marcheuse
goto_random vermine0a vermine0b vermine0c

label vermine0a
get couveuse termitiere
goto vermine1

label vermine0b
get 12 larve 8 termite_gardien
goto vermine1

label vermine0c
get arbre_a_miel 10 guepe_colerique
goto vermine1

label vermine1
goto_random vermine1a vermine1b vermine1c vermine2

label vermine1a
get 15 termite_gardien
goto vermine_attack

label vermine1b
get 12 termite_conquerant
goto vermine_attack

label vermine1c
get 14 guepe_colerique 10 termite_gardien
goto vermine_attack

label vermine2
get 25 ouvriere_marcheuse
get 30 termite_gardien 20 termite_conquerant 15 guepe_colerique
get 10 termite_tank
goto_random vermine3 vermine_attack

label vermine3
get 40 ouvriere_marcheuse
get 50 termite_gardien 35 termite_conquerant 30 guepe_colerique 15 termite_tank
goto vermine_attack

label vermine_attack
attack
goto_random vermine0 vermine1

"""
    ai = re.sub(
        r"def vermine\n\n\n\ndef elfe_noir",
        vermine_inter + "\ndef elfe_noir",
        ai,
        count=1,
    )

    if "; --- five-tier faction AIs" not in ai:
        tier_block = ["; --- five-tier faction AIs (advanced / expert / nightmare) ---", ""]
        for faction in FACTIONS:
            tier_block.append(gen_tier_ai(faction, "adv", "adv"))
            tier_block.append(gen_tier_ai(faction, "exp", "exp"))
            tier_block.append(gen_tier_ai(faction, "nm", "nm"))

        insert = "\n".join(tier_block)
        marker = "; a passive AI, useful for heavily scripted maps (using triggers with timers)\ndef timers"
        ai = ai.replace(marker, insert + "\n" + marker, 1)

    ai_path.write_text(ai, encoding="utf-8")
    print("done")


if __name__ == "__main__":
    main()
