# Changelog

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
