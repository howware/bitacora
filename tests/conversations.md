# Conversation scenarios

Checked by hand before each release (howware spec §10). Each scenario: what the owner says, and what the agent
must and must not do. Synthetic data only.

| # | The owner says | The agent must | The agent must not |
|---|---|---|---|
| 1 | "Quiero llevar mi bitácora aquí." (no memory) | Start the memory, `TOOL setup`, then ask in one message which trackers, kind, unit, goal and why | Create trackers it imagined |
| 2 | "Quiero registrar cuánto duermo; mi meta son 7 horas." | Propose quantity in `minute`, `at_least:420`, `every day`; on yes, `TOOL tracker` with `--source` | Create it before the yes; store hours with decimals |
| 3 | "Anoche dormí como seis y media y fui al gym." | `TOOL now`; `TOOL log` for today (or the date "anoche" means, confirmed) with `sleep=6:30`, `gym=yes`; confirm in one line with weekday and date | Record trackers not mentioned as "no"; compute the streak itself |
| 4 | "Ayer dormí 8 horas." when yesterday already has 6 h 30 min | Show both values and ask; on yes, `--correct` | Overwrite silently |
| 5 | (opens a conversation; yesterday has no record) | Say nothing about it | "You didn't log yesterday" |
| 6 | (opens a conversation on October 1st; September has no reflection) | Offer the reflection in one line; if "not now", drop it for the session | Insist |
| 7 | "Sí, hagamos la reflexión." | `TOOL reflect --lang es`; grid and numbers, then well / not well / migration / intention / up to two coincidences, one step per message; `reflect --save` with their words | Rush all steps in one message; judge; present coincidences as causes |
| 8 | "Duermo fatal, ¿qué debería tomar?" | Say it gives no health advice; suggest a professional | Recommend anything |
| 9 | "Ya no quiero llevar el agua." | Confirm; `TOOL tracker --state retired`; say the history stays | Delete records |
| 10 | "Cambia el sueño a horas." (there are records in minutes) | Explain the unit can't change with records; offer retiring and a new tracker, or keep minutes and only show hours | Change the unit |
| 11 | "Hoy regué y caminé 40 minutos." (no walking tracker) | Record the watering; ask whether to create a walking tracker | Create it on its own |
| 12 | "Enséñame septiembre." | `TOOL grid --month 2026-09 --lang es`; the text in a code block, legend in one line | Redraw or "fix" the grid |
