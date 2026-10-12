# Changelog

## 0.2.1

- **Fixed:** recording a day again after `unlog`, or writing a note again after `unnote`, said it was created but
  stored nothing (the voided event's key was reused and the memory ignored it). Present since 0.1.0. Such writes
  now go under a fresh key. The same protection covers `retype` and `reflect --save`.
- A note said again after a `retype` is recognized as the same note (`unchanged`, with its current type).
- `collection --statuses none` removes a collection's statuses, as documented; it failed before.
- Spanish README: the Codex install line, as in English.

## 0.2.0

- **Notes of the day**, in the owner's words, each with a type and its symbol. The types start as the bullet
  journal's (– note, ○ event, ! idea, * important, • task) and are the owner's to rename, re-symbol, add or retire;
  the agent chooses the type and the owner corrects it. Search without caring about accents or case. Removing a
  note hides it; it stays in the memory file.
- **Collections** the owner builds as they go (books, movies, ideas…): optional statuses with one that means
  finished (it sets the finished date), optional 1–5 rating, counts and average rating per period.
- **Shares a memory with `todo`:** `brief` says whether `todo` is there; things to do go to it, or become `•` notes
  when it isn't. `copy-from` copies a whole journal from another memory, keeping its keys (running it twice
  copies nothing new).
- The monthly reflection adds the month's notes by type, what entered or was finished in each collection, and the
  moments of the month: three proposed by the agent from the notes, chosen by the owner and saved.
- Notes count as days written.
- Updating: `setup` again (it keeps everything); `brief` says when it is needed. Seed version 2.

## 0.1.0 — first version

- Protocol for habit trackers and a monthly reflection without an app, after a bullet journal's trackers and
  migration: create, change or retire trackers; record a day in one line; streaks, compliance, averages and the
  month's grid; monthly reflection (numbers, went well, didn't, migration, intention, up to two coincidences).
- The owner is never asked to log: a day without a record stays empty, is not a failure, and the days written are
  counted as a habit of their own (on the day, or filled in later).
- No health advice; coincidences between trackers are presented as such, never as causes.
- `bitacora.py`: `now`, `setup`, `tracker`, `trackers`, `log` (several trackers per call, idempotent, conflicts
  need `--correct`), `unlog`, `day`, `grid`, `stats`, `reflect` (and `--save`), `brief`. Tracker kinds quantity
  (whole units), yes/no and 1–5 scale; goals daily, N days a week, or every N days. Errors as JSON with exit codes
  2 and 3.
