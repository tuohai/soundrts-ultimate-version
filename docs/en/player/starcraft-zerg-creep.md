# StarCraft mod: Zerg creep & Queen tumors

Mod: enable `mods = starcraft` in `SoundRTS.ini`.

Rule keywords: `doc_src/src/en/modding.rst` (Build fields). Terran/Protoss guides: [starcraft-terran-addons.md](starcraft-terran-addons.md), [starcraft-resources-vespene.md](starcraft-resources-vespene.md).

---

## 1. Two radius properties

Set **one** per creep/psi provider; keep the other at **0**.

| Property | Range | Notes |
| --- | --- | --- |
| `build_field_radius` | BFS tile steps from the building's square | Discrete squares; legacy style |
| `build_field_radius_m` | Meters from building `(x, y)` | Same scale as attack range; one map square ≈ **12 m** |

StarCraft mod defaults:

| Building | Radius |
| --- | --- |
| Hatchery | `build_field_radius_m 12` |
| Creep tumor | `build_field_radius_m 4` |
| Nexus | `18 m` |
| Pylon | `12 m` |

---

## 2. Live creep vs marked creep

| Kind | Meaning |
| --- | --- |
| **Live** | Currently emitted by a standing Hatchery/tumor (you hear creep when moving nearby) |
| **Marked** | Persistent square paint + spread (`build_field_persists`, `build_field_spreads`) |

- **Zerg buildings** need a **marked** square (`requires_build_field_on_square 1`).
- Moving onto visible marked creep can announce the field label.
- After Hatchery death, **marked** creep remains; you can still build on it.

Meter-radius Hatcheries **also paint marks** when `build_field_persists` / `build_field_spreads` is set — otherwise you could hear live creep but get "cannot build here".

---

## 3. Spread

`build_field_spreads 1` — each game second, creep marks expand one layer to adjacent squares (`build_field_spread_squares N` for faster spread).

Test map: `mods/starcraft/multi/zerg_creep_test.txt`.

---

## 4. Queen creep tumors (SC2-style)

Train **Queen** from **Queen's Nest** (requires Spawning Pool).

| Skill | Cost | Range | Target rule |
| --- | --- | --- | --- |
| **Spawn creep tumor** | 25 mana, 20 s cast | 11 | Square with **live or marked** creep |
| **Extend creep tumor** (on tumor) | 12 s cast | 8 | Square with **marked** creep only |

- **Spawn** places an invisible `creep_tumor` building on the target square.
- Each tumor provides **4 m** creep and spreads like Hatchery creep.
- **Extend** chains tumors toward distant build sites (cannot skip onto live-only edge — must wait for spread/mark).

Test map: `mods/starcraft/multi/zerg_creep_tumor_test.txt`.

Modder attributes on `class skill`:

```txt
summon_requires_build_field creep
summon_requires_marked_field 1    ; extend only
```

---

## 5. Quick checklist

1. Hatchery paints creep → wait for spread **or** use Queen tumors to reach far squares.
2. Build Zerg structures only on **marked** creep (F9/objectives unrelated).
3. Spire / pool / extractor on lingering creep after Hatchery dies — `zerg_creep_test` step 2.
