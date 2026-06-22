# SoundRTS 1.4.4.8 Release Notes

**Version**: 1.4.4.8  
**Type**: sub-cell terrain for maps and the map editor  
**Audience**: map/mod authors; players using zoom-mode map browsing

---

## Highlights

1. **Sub-cell terrain**: define high ground, mountains, water, cover, speed and other terrain properties inside one map square.
2. **Configurable precision**: use `subcell_precision N` to choose a 2x2 to 20x20 subdivision; the default is 3x3.
3. **Zoom-aware browsing**: zoom mode announces the terrain of the current sub-cell, so partial high ground is spoken only where it exists.
4. **Editor support**: in zoom mode, the experimental map editor applies terrain to the current sub-cell instead of the whole square.

---

## Sub-cell terrain syntax

Add `/x,y` after a square coordinate. The sub-cell coordinates are 1-based:

```text
high_grounds a1/1,1 a1/1,2
terrain mountain a1/2,2
ground a1/2,2
no_air a1/2,2
```

With the default 3x3 precision, `a1/1,1` is the first sub-cell of `a1`. To use a finer grid:

```text
subcell_precision 20
high_grounds a1/10,10 a1/10,11
terrain mountain a1/1,1 a1/2,2 a1/3,3
```

Supported commands: `terrain`, `high_grounds`, `speed`, `cover`, `water`, `ground`, and `no_air`. Sub-cells not mentioned inherit the parent square's terrain.

---

## Gameplay and browsing

Terrain checks can now use the unit's actual sub-cell for high ground, terrain type, movement speed, cover, and passability.

In zoom mode, map browsing uses the current sub-cell for terrain voice output. For example, if only `a1/1,1` is high ground, browsing that sub-cell announces plateau while the other sub-cells do not.

---

## Map editor

In the experimental map editor:

- Enter outside zoom mode still applies terrain to the whole square.
- Enter in zoom mode applies terrain to the current sub-cell.
- Saving the map writes sub-cell overrides as `square/x,y` entries.

---

## See also

- Mapmaking guide: `doc/en/mapmaking.htm`; source `doc_src/src/en/mapmaking.rst`
- Tests: `soundrts/tests/test_subcell_terrain.py`
