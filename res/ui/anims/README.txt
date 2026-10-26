Optional unit animation packs for Ctrl+F2 map view.

Place packs under: res/ui/anims/<type_name>/
Example: res/ui/anims/peasant/meta.json

Draw priority on the map:
  1) anim pack (this folder)
  2) ui/map/<type>.png
  3) colored circle / square (schematic)
Attack / gather FX still overlay regardless.

Command-card icons (ui/icons/) are HUD-only and are not used on the map.

------------------------------------------------
A) Spritesheet (works out of the box, no extra libs)

meta.json example:

{
  "backend": "spritesheet",
  "sheet": "sheet.png",
  "frame_w": 32,
  "frame_h": 32,
  "fps": 8,
  "animations": {
    "idle":   {"row": 0, "frames": 4},
    "walk":   {"row": 1, "frames": 6},
    "attack": {"row": 2, "frames": 4},
    "gather": {"row": 3, "frames": 4}
  }
}

Or list frame files:

{
  "backend": "spritesheet",
  "fps": 10,
  "animations": {
    "idle": ["idle_0.png", "idle_1.png", "idle_2.png"]
  }
}

Or folders: idle/0.png, idle/1.png, ...

The game picks idle / walk / attack / gather / build from current orders.

Four directions (optional): set "dirs": 4 in meta.json. Each animation
uses four consecutive rows (east / north / west / south). Example row
layout: idle rows 0-3, walk 4-7, attack 8-11, gather/build 12-15.

Regenerate starter geometric packs:
  python tools/gen_unit_anims.py
(writes res/ui/anims/ and mods/aoe2/ui/anims/ for common mobile types)

------------------------------------------------
B) Spine skeletal (optional)

{
  "backend": "spine",
  "spine": {
    "skeleton": "skeleton.json",
    "atlas": "skeleton.atlas"
  }
}

Requires a Spine runtime Python package usable with pygame
(e.g. spine_pygame / spine). If the package is missing or load fails,
the engine silently falls back to spritesheet in the same folder,
then icons, then schematic shapes. Spine is never required to run SoundRTS.

------------------------------------------------
Also used by (and documented in) the modding guide:
  doc_src → player manuals / modding.rst (“Ctrl+F2 map view: icons and unit animation”).
