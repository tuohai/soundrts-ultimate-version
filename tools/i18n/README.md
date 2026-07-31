# Translation tooling (tts.txt <-> gettext PO)

SoundRTS stores translatable text as `<id> <text>` lines in `tts.txt` files
scattered across `res/ui*`, every `res/single/<campaign>/ui*`, and every
`mods/<name>/**/ui*`. The same numeric IDs also name recorded `.ogg` voice
lines, and third-party mods/campaigns freely invent their own IDs in their
own `tts.txt` and reference them from map/trigger scripts — so that scheme
isn't changing: this tooling only adds a translator-facing layer on top of
it, producing a standard gettext `.pot`/`.po` catalog that tools like
Crowdin or Poedit understand, and syncing it back to `tts.txt` afterwards.

Runtime behaviour, the `tts.txt` format, audio files, and mod/campaign
compatibility are all completely untouched by this tooling.

## Files

- `i18n/tts.pot` — the template: every translatable string found anywhere
  in the repo, in ONE file (not one per `res/single/*`/`mods/*` tree).
- `i18n/tts-<lang>.po` — one consolidated translation file per language,
  same idea: everything a translator for that language needs is in this
  single file, not spread across a dozen `ui-<lang>/tts.txt`.

Each entry's `msgid` is the actual source text (not a bare number). The
`msgctxt` carries the underlying tts key (plus, for anything outside the
base game, the owning tree's path, e.g. `1029@mods/tang/ui`, so two mods
that happen to reuse the same number never collide). The `#:` comment
lines record exactly which physical `tts.txt` file(s) and key the string
came from — that's what lets `build_tts.py` write it back unambiguously.
A `#.` comment surfaces the symbolic constant name from `soundrts/msgparts.py`
(e.g. `SCORE_TOTAL`) as extra context, for the base game's own strings.

## Workflow

1. **Extract** — after any `tts.txt` change (new base-game string, new mod
   content, etc.), regenerate the catalog:
   ```
   python tools/i18n/extract_pot.py
   ```
   This only ever writes files under `i18n/`.

2. **Translate** — sync `i18n/tts.pot` / `i18n/tts-<lang>.po` with Crowdin
   (see `crowdin.yml`), or hand these `.po` files to a translator directly
   (Poedit, or any gettext-aware editor).

3. **Build** — after pulling updated translations back, regenerate every
   `ui-<lang>/tts.txt` the game actually loads:
   ```
   python tools/i18n/build_tts.py            # all languages
   python tools/i18n/build_tts.py --lang fr   # just one
   ```
   Commit the regenerated `tts.txt` files as usual — they stay checked in,
   there's no new build step for running or packaging the game.

4. **Check status** at any point:
   ```
   python tools/i18n/check_translations.py
   python tools/i18n/check_translations.py --lang fr --strict   # CI gate
   ```

## Translating with an LLM (e.g. Claude)

`i18n/tts-<lang>.po` files can be filled in by an LLM instead of (or before)
a human translator. `dump_missing.py` and `apply_translations.py` support
that workflow directly:

1. **Survey** what's missing and how it's grouped:
   ```
   python tools/i18n/dump_missing.py --lang de --list-groups
   ```
   Groups are `base` (the core game), `single:<campaign name>`, and
   `mod:<mod name>`. Translate one group at a time, not the whole file at
   once — a campaign's dialogue shares character names, place names, and
   tone, and mixing groups makes that consistency harder to hold onto.

2. **Dump** one group's missing entries to a scratch JSON file:
   ```
   python tools/i18n/dump_missing.py --lang de --group "mod:tang" -o /tmp/tang.json
   ```

3. **Translate** into a scratch Python file, not JSON — it sidesteps string
   escaping entirely if you use the target language's own quotation marks
   (e.g. German „…", French «…») instead of ASCII `"`:
   ```python
   # /tmp/batch_tang.py
   TRANSLATIONS = {
       "8500@mods/tang/single/tang campaign/ui": "Die Türken standen kurz davor, …",
       "12801@mods/tang/ui": "Glänzende Rüstung",
       ...
   }
   ```
   Proper nouns from licensed game IPs referenced by a mod (e.g. `Zealot`,
   `Marine`, `Nexus` in the `starcraft` mod) are usually best left
   untranslated — that's how players actually refer to them — while the
   surrounding descriptive/instructional text still gets translated.

4. **Verify** the batch exactly covers what was dumped, before writing
   anything, catching missed or misspelled keys early:
   ```
   python tools/i18n/apply_translations.py --lang de --check /tmp/tang.json /tmp/batch_tang.py
   ```

5. **Merge** one or more verified batches into the `.po` (existing non-empty
   `msgstr` values are left alone unless `--force` is given, so re-running
   is always safe):
   ```
   python tools/i18n/apply_translations.py --lang de /tmp/batch_tang.py /tmp/batch_raynor.py
   ```

6. **Build and confirm**, same as any other translation update:
   ```
   python tools/i18n/build_tts.py --lang de
   python tools/i18n/check_translations.py --lang de --strict
   ```

## Adding a new language

Add the language to Crowdin (or create `i18n/tts-<code>.po` by hand from
`i18n/tts.pot`), translate it, then run `build_tts.py`. It creates every
missing `ui-<code>/tts.txt` (and `ui-<code>/` directory) needed, mirroring
whichever trees have translated strings for that language.

## Notes

- Untranslated entries (empty `msgstr`) are simply omitted from the
  rebuilt `tts.txt`, exactly like an untranslated line being absent
  today — the existing runtime fallback to the base language still
  applies unchanged.
- A `tts.txt` in a translation layer occasionally defines a key that
  its own tree's base `ui/tts.txt` doesn't have (e.g. a campaign
  overriding just the wording of a base-game phrase for one language).
  These "orphan" keys are kept in the catalog with a comment explaining
  where they come from, rather than being silently dropped.
- Regenerating `tts.txt` reformats it (fresh `; coding: utf-8` header,
  stable ordering); ad hoc comments that existed only in the old
  hand-edited files are not preserved. That's expected once `tts.txt`
  becomes a generated artifact of the `.po` files.
- This does not touch `msgparts.py`, sound files, or the numeric ID
  scheme — see the discussion that led here if you want the background
  on why (mods/campaigns depend on that scheme staying stable).
