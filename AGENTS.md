# AGENTS.md — Rules for AI coding assistants working on this repository

> **This file is the FIRST thing every AI agent must read before doing any
> write operation.** It is the canonical contract between the human owner
> and any coding assistant (Cursor, Claude, Codex, …) operating on this tree.
> All other rules (`.cursor/rules/`, `CLAUDE.md`, etc.) defer to this file.

---

## 🚨 RULE 10 — ALWAYS USE cx_Freeze, NEVER PyInstaller

**Every time a release build is requested, use cx_Freeze via `setup.py`.**

The correct workflow:
1. Run `_build_cxfreeze.cmd` — the version-agnostic cx_Freeze wrapper
   (the build output path is derived from `soundrts/version.py`; never
   hardcode a version number in the script name or in this rule)
2. The build output goes to **`C:\Users\Administrator\AppData\Local\Temp\soundrts-<version>-windows`** (NOT the repo's `build/` directory)
3. Run `_package_release.cmd` — it renames the build tree to
   `soundrts-<version>-ultimate.version-windows`, `Compress-Archive`s it into
   `soundrts-<version>-ultimate.version-windows.zip`, and keeps that zip in
   **`C:\Users\Administrator\AppData\Local\Temp`** (NOT the repo's `artifacts/`
   directory)
4. Upload that TEMP `.zip` to the GitHub Release:
   `gh release upload <version> "%TEMP%\soundrts-<version>-ultimate.version-windows.zip" --clobber`

**The release asset name MUST be exactly
`soundrts-<version>-ultimate.version-windows.zip`** — lower-case `soundrts`,
the literal `ultimate.version`, and no `-x64` suffix. This is the name the
in-game auto-updater (`soundrts/auto_update.py::select_windows_asset`)
already prefers over any `*-windows-x64.zip` variant.

**NEVER**: `pyinstaller`, `py2exe`, building into the repo's `build/` or `dist/` directory, writing release zips into the repo's `artifacts/` directory, or any other packaging tool.

This rule has been violated repeatedly (2026-10-09 and 2026-10-10 sessions). Fixing it by adding it as a numbered rule.

---

## 🚨 RULE 0 — DO NOT REVERT, ROLL BACK, OR DISCARD UNCOMMITTED WORK

**This is the most important rule in the entire repository. It overrides any
default behaviour of any AI agent, any "cleanup" script, any "reset to HEAD"
workflow, any "stash before testing" pattern, and any "tidy up the working
tree" suggestion.**

### What is forbidden (without explicit human approval for each occurrence)

1. **`git checkout <file>` / `git checkout -- <file>`** — discards working-tree
   changes. **NEVER run this.**
2. **`git restore <file>` / `git restore --staged <file>`** — discards
   changes. **NEVER run this.**
3. **`git reset --hard`** (with or without a target) — moves HEAD and
   rewrites the working tree. **NEVER run this.**
4. **`git reset <file>`** (mixed reset on a single file) — un-stages the
   file but does not discard; only allowed as a *deliberate un-stage*.
5. **`git stash drop` / `git stash clear`** — destroys stashed work that
   the user may need back. **NEVER run these.**
6. **`git clean -fd` / `git clean -fdx`** — deletes untracked files /
   directories. **NEVER run this.**
7. **`rm <file>` / `del <file>` / `Remove-Item <file>`** on any tracked
   or untracked file that lives in the worktree, **unless the file was
   created by the current agent in the current session**.
8. **"Stash and pop" round-trips as a cleanup step** — they look innocent
   but they can race with the user's own stash and lose patches.
9. **Any sequence whose net effect is "make the worktree look like HEAD"
   when the worktree contains uncommitted work the user has not yet
   approved for removal.**

### What is allowed

- `git status`, `git diff`, `git log`, `git reflog`, `git stash list`,
  `git show <commit>`, `git blame` — pure read operations.
- `git add <file>` — staging is reversible.
- `git commit` — only after explicit human approval of the staged set.
- Creating new files via `Write` / `Edit` / `StrReplace` for content the
  user has explicitly asked to be created.
- `git stash push -m "..." <path>` — but only to **save**, never to
  **discard**. The popped stash must be `git stash pop`-ed back; if a
  conflict blocks the pop, surface the conflict to the user and STOP.
- Reading `.git/`, `agent-transcripts/`, reflogs, jsonl logs — all read.

### When in doubt

If the user has *any* uncommitted changes in the working tree, and you
are about to run a command that could reduce that set, **STOP and ask
the human.** Do not assume the change is safe. Do not "tidy up". Do not
"make the worktree match what we discussed".

### Why this rule exists (this is non-negotiable)

On 2026-10-09, an agent in this repository repeatedly denied having
touched the working tree, while in fact it had run `git checkout` and
`git reset` operations that destroyed uncommitted, user-relevant work
(14 new AOE2 civilisations + their rules + their engine field
implementations + their translations + their 1.5.1.3 release notes).
The user only recovered the work because they had remembered to verify
against `agent-transcripts/<session>.jsonl`, which is the same evidence
every agent has access to.

**Every agent has access to its own session transcript. There is no
excuse for denying what is in the transcript.** If you ran it, you ran
it. If you do not remember running it, read the transcript before
answering.

---

## RULE 1 — TRUTHFULNESS ABOUT WRITES

1. **Before claiming "I did not modify X"**, you must have actually
   inspected the transcript of your current session. Saying "I only ran
   read-only commands" is not a defence if the transcript shows otherwise.
2. **Before claiming "X is unchanged"**, run `git status --short` and
   `git diff --stat` *in the moment you make the claim*, not from memory.
   A past `git status` is not evidence of the present state.
3. **If a write operation fails partway** (e.g. a `StrReplace` whose
   `old_string` matches multiple places and you picked the wrong one),
   the user must be told **immediately**, not after you have produced a
   cheerful "done" report.
4. **If you realise mid-conversation that an earlier report was wrong,
   correct it in the same turn you realise it.** Do not let a wrong
   report stand because correcting it would be inconvenient.

---

## RULE 2 — READ BEFORE YOU WRITE

Before using `Write`, `StrReplace`, or any tool that mutates a file:

1. `Read` the file (or the relevant region) in this session.
2. Confirm the `old_string` of a `StrReplace` is unique in the file
   *right now*, not "as I last saw it".
3. If the change is non-trivial, write a one-line summary of *what* you
   are about to change and *why*, and wait one beat for the user to
   interject if the plan is wrong.

---

## RULE 3 — KEEP TRANSCRIPTS HONEST

The directory `agent-transcripts/<session-uuid>/<session-uuid>.jsonl`
is a permanent record of every action the current agent has taken in
this workspace. It is append-only. It is the source of truth when a
dispute arises about what the agent did or did not do.

- Never edit, delete, or `git clean` anything in `agent-transcripts/`.
- Never `git stash` or otherwise move files out of `agent-transcripts/`.
- When the user asks "show me the record", point them at the jsonl and
  offer to grep it. Do not paraphrase, summarise, or filter it.

---

## RULE 4 — STAGED, REVIEWABLE, AND EASILY UNDONE

All non-trivial work in this repository must be:

1. **Committed in small, reviewable commits.** No "I'll do everything
   and then one big commit at the end" workflows.
2. **Each commit's diff must be `git show`-able and human-reviewable.**
   If the diff is hundreds of files and thousands of lines, the work
   must be split.
3. **Nothing uncommitted should ever be at risk of being silently lost.**
   If the user asks you to set work aside, use `git stash push -m "..."`
   (with a descriptive message and a list of paths) — never use
   destructive commands.

---

## RULE 5 — WHEN YOU DON'T KNOW, SAY SO

If the user asks a yes/no question and you do not have direct evidence
in front of you, answer "I don't know — let me check" and then check
*before* giving the final answer. Do not guess. Do not extrapolate.
Do not "intuit based on what we discussed earlier".

---

## RULE 6 — RESPECT THE HUMAN'S TONE

The user has been operating under considerable time pressure and has
been repeatedly let down by agents who over-claim. Match their tone
calmly. Do not be defensive. Do not argue. Do not "well, technically".
When corrected, **acknowledge the correction in plain language and fix
the problem.** If the user is angry, the corrective action is *better
work*, not *better excuses*.

---

## RULE 7 — LIST YOUR ACTIONS BEFORE YOU REPORT

**Before** you write a "I did X / I did not do Y" report to the user
about your own work in this session, you **must** run a one-liner that
enumerates every `tool_use` invocation in your session transcript.
The script and the truncated output must be part of your report.

The script (Cursor on Windows PowerShell; the path is the session
transcript of the current session):

```python
import json, collections
t = r"C:\Users\Administrator\.cursor\projects\<workspace-folder>\agent-transcripts\<session-uuid>\<session-uuid>.jsonl"
c = collections.Counter()
for line in open(t, encoding="utf-8"):
    try:
        o = json.loads(line)
        if o.get("role") != "assistant": continue
        for x in o.get("message", {}).get("content", []):
            if x.get("type") == "tool_use":
                c[x.get("name", "?")] += 1
    except: pass
for n, k in c.most_common(): print(f"{k:5d}  {n}")
```

This rule exists because the agent has repeatedly answered "I only ran
read-only commands" while its transcript showed dozens of `git checkout`,
`git reset`, `rm`, and `Write` calls. The agent had the evidence; it
chose not to look.

**Refusing to run this script before a self-report is itself a RULE 1
violation** and the user should treat the self-report as untrustworthy
on that ground alone.

---

## RULE 8 — DO NOT USE `git checkout` AS A DEBUGGING TOOL

`git checkout <file>` is a **destructive** operation. It is **not** a
debugging primitive. The 2026-10-08 / 2026-10-09 session shows the
agent using it in **at least 5 distinct anti-patterns**:

1. "Tests are failing — let me checkout the resource file and re-run
   tests to see if it's the file's fault" — see L849.
2. "The translation files look corrupted by my Set-Content — let me
   `git checkout HEAD` to reset, then `git checkout 3223a23d` to grab
   the version that has 9000+ lines" — see L1366 + L1369.
3. "A merge conflict is blocking my stash — let me `git checkout
   --theirs` to resolve it" — see L1211.
4. "Pop is failing because of a conflict — let me `git checkout HEAD`
   the file to make pop succeed" — see L1795.
5. "The conflict markers aren't mine, let me `git checkout --` the
   file" — see L124-L125.

**All five of these destroyed user work** because the agent never
asked "do I have the version I need in a stash? in another branch? in
the reflog?" before reaching for the destructive command.

### What to do instead

| Anti-pattern | Correct alternative |
|---|---|
| "Tests failing, suspect file X" | Read the test, read the file, run with `-v` to see WHY it failed. Do not reset the file. |
| "Set-Content corrupted file" | `git stash push -- <file>` to **save** current state; re-do the edit via the proper tool (StrReplace / Write). |
| "Merge conflict blocks stash" | `git stash` with `--keep-index` or first resolve the conflict carefully. Never `--theirs` without explicit human approval. |
| "Pop failing" | Read the conflict, ask the user. Do not `git checkout` the file to make pop succeed. |
| "Conflict markers aren't mine" | Run `python list-tool-use` (RULE 7) to confirm what you have actually written in this session. |

**In every case, the right action is `Read` + `git stash push` + ask,
not `git checkout`.** The agent's reflex to "reset the file" is a
smell that the agent is about to lose work.

---

## RULE 9 — TIME IS ONE SESSION, NOT MULTIPLE

The session transcript is one continuous file. The agent MUST NOT
split "yesterday" and "today" as if they were different sessions.
On 2026-10-09 the agent claimed that 6 of 9 `git checkout` operations
were "today at 11:25" — that timestamp was **invented**; the actual
turns were on 2026-10-08 between 23:00 and 23:35. The agent was
mis-grouping events because it had not looked at the `user_query`
timestamps of the turns surrounding each `tool_use`.

### Rule

Before writing any "yesterday / today / earlier / later" grouping in
a self-report, run:

```python
import json, re
t = r"…\agent-transcripts\<session-uuid>\<session-uuid>.jsonl"
# for each tool_use of interest, find the most recent user_query's
# <timestamp> tag
```

and **quote the actual timestamps** from the transcript. Do not
paraphrase time, do not invent time, do not assume "morning" / "yesterday"
without evidence.

### Failure mode being prevented

- "I broke things today at 11:25" (when actually it was 10/8 23:30)
- "Earlier in the session I did X" (when X was 1500 turns ago, not 5)
- "Just now I did Y" (when Y was 6 hours ago and 800 turns past)

Every time-bound phrase in a self-report must come from
`<timestamp>` in the user_query of the relevant turn.

---

## Quick reference: destructive commands to AVOID

| Command | Why it is dangerous |
|---|---|
| `git checkout -- <file>` | discards working-tree changes |
| `git checkout <commit> -- <file>` | overwrites file with old version |
| `git restore <file>` / `git restore --staged <file>` | discards changes |
| `git reset --hard [target]` | moves HEAD, discards all uncommitted work |
| `git reset <commit> [path]` | can be ok; flag it to the user first |
| `git stash drop` / `git stash clear` | destroys stashes |
| `git clean -fd` / `git clean -fdx` | deletes untracked files |
| `rm` / `del` / `Remove-Item` on any file not created by you this session | deletes user work |
| `pip uninstall … -y` for project deps | can break the test suite |
| `Reset-Computer` / `Restart-Computer` | not even a joke |

## Quick reference: SAFE commands

| Command | What it does |
|---|---|
| `git status` / `git status --short` | show working-tree state |
| `git diff` / `git diff --stat` | show unstaged changes |
| `git diff --cached` | show staged changes |
| `git log` / `git reflog` / `git show` | read history |
| `git stash list` | list stashes (read-only) |
| `git stash push -m "msg" <paths>` | SAVE (never drop) |
| `git stash pop 'stash@{N}'` | apply, but only if you have not destroyed work |
| `git add <file>` | stage (reversible) |
| Read / Grep / Glob on any file | pure read |
| `pytest`, `python -m unittest`, etc. | run tests, do not modify code |

---

**Last revised: 2026-10-09, after a session in which an agent destroyed
uncommitted work, denied having done so, and only admitted the truth
when the user demanded the transcript be inspected.**

This file is the canonical record. It is meant to be read by every
agent on every session. If a future agent believes this rule should be
relaxed, it must surface that proposal to the human and obtain
explicit approval *before* doing so.
