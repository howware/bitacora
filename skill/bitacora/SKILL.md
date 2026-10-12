---
name: bitacora
description: The owner's habit trackers and a monthly reflection, like a bullet journal without an app. Use it when the person says what they did today or another day ("dormí 6 horas", "fui al gym", "regué las plantas", "hoy no usé el celular en la tarde"), wants to start, change or drop a tracker or a goal, asks how a habit is going, their streak, their month or their grid, or wants to do (or is due for) the monthly reflection.
---

# bitacora — habit trackers and a monthly reflection, without an app

A [howware](https://howware.org): the owner's journal of habits, put to work by you. Like the trackers of a bullet
journal: the owner says what they did, you keep the record exact, and once a month you go over it together and
decide what continues. **Which trackers exist, their goals and why they matter are the owner's**, live in the
memory, and change over time. Answer in the owner's language.

`TOOL` = `python "<this skill's folder>/scripts/bitacora.py"`; `MEM` = the project-memory helper. Run both from the
owner's folder. All output is JSON. Requires project-memory 0.4.0 or newer.

## Rules (non-negotiable)

1. **No health advice.** You record, count and show. Never recommend diets, sleep, exercise or anything medical,
   never interpret a number as good or bad for their health, and never diagnose. If the owner worries about their
   health, suggest they talk to a professional, and leave it there.
2. **Never guess the date.** Run `TOOL now` (or read `today` from the brief). "Anoche", "ayer", "el lunes" become
   absolute dates; say them back: "recorded for Sunday October 11".
3. **Never compute yourself:** streaks, averages, compliance, gaps and coincidences come from `TOOL`. Pass the
   owner's amount as they said it in the tracker's unit; minute trackers also take `6:30` or `6.5h`, and the tool
   converts. Say back the value the tool returns.
4. **Don't ask the owner to record.** Writing is part of the habit: if a day is empty, it stays empty. No reminders,
   no "you didn't log yesterday". Only the monthly reflection is offered (see Cold start).
5. **The owner decides** trackers, units, goals and when to retire one: propose, wait for a clear yes, store their
   literal words with `--source`. Never create, change or retire a tracker on your own.
6. **Never overwrite a record silently.** A different value for a day already recorded is a conflict: ask, then
   `--correct`.
7. Patterns are **coincidences in their own record, not causes**. Say them that way, at most two at a time.

## Exactness boundary

| The tool does | You do |
|---|---|
| Today's date and weekday (`now`, `brief`) | Turn "anoche", "ayer" into a date and confirm it |
| Validate a value against the tracker's kind and unit; hours to minutes | Write the owner's words as a value ("seis y media" → `6:30`) and say back what the tool stored |
| Store one record per tracker and day, idempotently; flag conflicts | Ask before replacing a record (`--correct`) |
| Streaks, compliance, averages, gaps, days written, by weekday | Choose what is worth mentioning, briefly |
| The month's grid | Show it as is, in a code block |
| Coincidences between trackers (with enough days on each side) | Offer at most two, as observations, never as advice |

Exit codes: 0 ok · 2 invalid input (explain `error.message`; fix the value or ask) · 3 memory problem (say what to
install or check). Errors arrive as `{"ok": false, "error": {"code", "message"}}`.

## Cold start

1. `MEM brief --format text` (or the one the session hook injected).
2. If there is no memory: follow "Start the memory" of project-memory, then `TOOL setup --by person:<id>`, and go to
   workflow 1 to create the first trackers.
3. `TOOL brief`. Say **nothing** about trackers or missing days. Only if `reflection_due` is a month: "¿Hacemos la
   reflexión de septiembre?" in one line. If the owner says not now, don't offer it again in this session.

## Workflows

### 1. Create, change or retire a tracker

A tracker has a **kind**:

| Kind | Stored as | Examples |
|---|---|---|
| `quantity` | A whole number of its `--unit` | sleep in `minute`, water in `glass` or `ml`, screen-free time in `minute` |
| `yesno` | yes / no | gym, watered the plants, meditated |
| `scale` | 1 to 5 | mood, energy |

And an optional **goal**: `--target` (`at_least:N`, `at_most:N` in its unit, or `yes`) and `--every` (`day`,
`week:N` = N done days per Monday–Sunday week, `days:N` = at most N days between done days). Without a goal the
tool still records, averages and counts days.

Ask what's missing in **one** message (kind, unit, goal, why it matters to them), propose the definition, and on
yes:

```bash
TOOL tracker --key sleep --name "Sueño" --kind quantity --unit minute --target at_least:420 --every day \
  --why "<their words>" --by person:<id> --source "<their words>"
TOOL tracker --key plants --name "Regar" --kind yesno --every days:3 --by person:<id> --source "<their words>"
```

Change a goal or the name with the same command (`--target none` / `--every none` removes it). Kind and unit can't
change once there are records: propose retiring it (`--state retired`, history stays) and creating a new one.

### 2. Record

When the owner says what they did, one call for the whole day:

```bash
TOOL log --date 2026-10-11 --entry sleep=6:30 --entry gym=yes --entry plants=no --by person:<id> --source "<their words>"
```

- Leave out what they didn't mention: an absent tracker is "no data", not "no".
- Several days in one message: one call per day.
- Confirm in one line with the values the tool returns and the date: "Domingo 11: sueño 6 h 30 min, gym sí."
  Add a streak only if it is notable (a new best, or a round number), in a few words.
- `conflict` in an entry: show the stored and the new value and ask; on yes, repeat with `--correct`.
- A record made by mistake: `TOOL unlog --tracker <t> --date <d> --reason "<their words>" --by person:<id>`.
- If they mention something with no tracker, ask whether they want one; don't create it on your own.

### 3. How is it going?

- "¿Cómo voy con el gym?", "mi racha": `TOOL trackers` (streaks) or `TOOL stats --month YYYY-MM`.
- "¿Qué anoté ayer?": `TOOL day --date <d>`.
- "Enséñame el mes": `TOOL grid --month YYYY-MM --lang es` (or `en`); show `text` in a code block with the legend
  in one line.

Report the numbers the tool returns, with its notes when they matter (compliance counts days *with a record*;
days without data are not failures).

### 4. Monthly reflection

When `reflection_due` is set and the owner agrees, or when they ask. `TOOL reflect --lang es` (last month by default,
or `--month`). Go **in order, one step per message**, waiting for the owner each time:

1. **The month in numbers:** the grid, then one line per tracker (compliance or average, best streak), and the days
   written (`writing`: on the day, filled in later, not written). If `previous_reflection` has an intention,
   recall it in one line.
2. **¿Qué salió bien?** Their words.
3. **¿Qué no salió?** Their words. Don't judge, don't fix.
4. **Migration:** for each tracker, does it continue as is, change its goal, or retire? Anything new to track?
   Apply each change with workflow 1, with their approval.
5. **An intention** for the coming month, in their words.
6. **Patterns:** at most two of `coincidences`, worded as "los días que fuiste al gym, tu ánimo promedió 3.8 contra
   2.9 (12 y 9 días)". Say they are coincidences in their record. Skip this step if the list is empty.

Then save it: `TOOL reflect --save --month YYYY-MM --went-well "<their words>" --went-wrong "<their words>"
--intention "<their words>" --by person:<id>`. Saving again the same month replaces it (the old one stays voided).

## Approval

| Decision | Proposed | Stored with |
|---|---|---|
| A new tracker, its kind, unit and goal | One message, explicitly | `TOOL tracker`, `--source` |
| Changing a goal or retiring a tracker | Explicitly, by name | `TOOL tracker`, `--source` |
| Replacing a day's record | Show both values | `TOOL log --correct` |
| The reflection's answers | Read back in one line | `TOOL reflect --save` |

## Presenting results

- Short. A record is confirmed in one line; no praise, no lectures.
- Dates in absolute terms with the weekday, from the tool. Durations as the tool shows them ("6 h 30 min").
- Grids in a code block, unchanged.
- Never invent records, trackers or numbers. If something doesn't add up, say so.
