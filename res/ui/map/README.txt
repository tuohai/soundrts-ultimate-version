Static map sprites for Ctrl+F2 top-down view.

Place PNG files here as: res/ui/map/<type_name>.png
Example: peasant.png, footman.png, townhall.png, goldmine.png

Filename must match the type name in rules.txt (same as unit/building/resource type).

Draw priority on the map:
  1) ui/anims/<type>/   (optional animation pack)
  2) ui/map/<type>.png  (this folder)
  3) colored circle / square

Command-card / queue icons stay in ui/icons/ and are NOT used on the map.

Size: any; scaled to the current map cell. Missing file → geometric shape only.

Starter pack: flat geometric silhouettes copied from the same designs as
tools/gen_hud_icons.py (unit/building/resource only). Regenerate both with:
  python tools/gen_hud_icons.py
