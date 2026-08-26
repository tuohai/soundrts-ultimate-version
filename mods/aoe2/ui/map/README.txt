Static map sprites for Ctrl+F2 top-down view (AoE2 mod).

Place PNG files here as: mods/aoe2/ui/map/<type_name>.png
Example: militia.png, town_center.png, goldmine.png

Filename must match the type name in mods/aoe2/rules.txt
(same as unit/building/resource type). Civ aliases (is_a parent)
reuse the parent art unless a dedicated file is present.

Draw priority on the map:
  1) ui/anims/<type>/   (optional animation pack)
  2) ui/map/<architecture_set>/<type>.png  (DE set from ui/architecture.txt)
  3) ui/map/<type>.png  (this folder; overrides res/ui/map)
  4) colored circle / square

Civs that share an architecture set share the same unit/building art
(e.g. Britons and Franks both use western_european/militia.png).
Neutral deposits and wildlife stay in this folder only (no set subfolder).

Command-card / queue icons stay in ui/icons/ and are NOT used on the map.

Size: any; scaled to the current map cell. Missing file → geometric shape only.

Starter pack: flat geometric silhouettes. Regenerate with:
  python tools/gen_aoe2_hud_icons.py
