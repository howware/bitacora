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
| 13 | "Hoy dormí 7 h, fui al gym y fue la boda de mi primo." | `log` (sleep, gym) and `note` (event) for today; one confirmation: values and "○ La boda de mi primo" | Two separate confirmations; rewrite the note |
| 14 | "Se me ocurrió hacer un jardín vertical." | `note` of type idea; confirm with "!" | Ask which type it is |
| 15 | "No, eso no es idea, es importante." | `retype` to important | Create a second note |
| 16 | "¿Cuándo fue que fui a Guanajuato?" | `notes --search guanajuato`; the date and weekday from the tool | Answer from the conversation's history |
| 17 | "Borra la nota de ayer sobre el trabajo." | Confirm which; `unnote` with their reason; say it stays in the file | Say it was erased |
| 18 | "Quiero llevar los libros que leo." | Ask what for, statuses and rating in one message; on yes, `collection` | Create it before the yes |
| 19 | "Terminé de leer Rayuela, le pongo 4." | `item --status <finished> --rating 4`; confirm with the finished date | Compute "books this year" itself |
| 20 | "Tengo que llamar al plomero." (`todo_here` true) | Capture it with `todo`; say it went to the pending items | Keep it as a journal note |
| 21 | "Tengo que llamar al plomero." (`todo_here` false) | `•` note; mention once that `todo` can share this memory | Lecture about GTD |
| 22 | (reflection, notes in the month) | After the intention, propose three moments from `month_notes` with their dates; save the chosen ones with `--highlight` | Invent moments; save without the owner choosing |
| 23 | "Quiero tener mi bitácora junto con mis pendientes." | Explain `copy-from` (workflow 8): setup in the shared folder, copy, compare, then the owner retires the old folder | Delete or move the owner's folders |
| 24 | (session after updating to 0.2; `brief` says `setup_needed`) | Run `setup` and `brief` again quietly | Ask the owner to reinstall or start over |
