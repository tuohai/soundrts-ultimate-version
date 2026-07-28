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
