# How this howware was built

A record of building `bitacora` with the
[`howware-builder`](https://github.com/howware/howware/blob/main/skills/howware-builder/SKILL.md) protocol. The
owner's words are kept verbatim, in Spanish.

## 1. Choosing it

The owner brought a productivity video to analyze. It covered Getting Things Done (capture, clarify, organize,
act) plus five principles: an empty mind, few tools, sleep, food and exercise. The GTD part was already
[`todo`](https://github.com/howware/todo), almost step by step, so a new howware would have duplicated it. The
owner left that part aside and asked about the rest:

> «vamos a ver lo de energia y habitos. ¿Es aqui donde se hace algo como los bullet jurnals o similares?»

When a bullet journal is split into its parts, the tasks and their migration belong to `todo`, events belong to a
calendar, and the rest (trackers, notes, collections and reflection) is a personal journal. The owner chose to
design the whole journal but publish trackers and the monthly reflection first:

> «opción 2, empezamos con trackers y reflexión mensual»

It passes the howware test only in part. The value of a tracker is in recording without friction, exact counts
and a guided review, and a conversation does all three better than an app. What a conversation does worse is the
visual grid, so the tool draws one as text.

## 2. Interview

| Topic | The owner's words |
|---|---|
| Kinds of trackers | «depende mucho de que es a lo que le estoy haciendo tracker, es variable» |
| First trackers | «Sueño, gimnacio, agua, tiempo sin celular y computadora, regar mi jardin y plantas» |
| When to record | Whenever they want, in any conversation, with no daily prompt |
| A forgotten day | «el dia se queda vacio (que el escribir sea parte del habito)» |
| The monthly reflection | The six steps proposed: numbers, went well, didn't, migration, intention, patterns |
| Crossing with `todo` or finances | «lo dejamos para despues» |
| Health | «si, defiitivamene dejar fuera lo de la salud» |

## 3. Design decisions

| Decision | Why |
|---|---|
| Trackers, kinds, units and goals are data in the memory, created with the owner's approval | «es variable»: what one person tracks is not what another does |
| Three kinds (whole quantity in a declared unit, yes/no, 1–5 scale) and three goal shapes (daily, N days a week, every N days) | They cover the owner's five trackers: sleep needs a threshold, the gym a weekly count and watering a maximum gap |
| Minute trackers accept `6:30` and `6.5h`, and the tool converts them | The agent never does arithmetic, not even to turn hours into minutes |
| One record per tracker and day with a stable key; a different value is a conflict until the owner says `--correct` | Recording twice must not duplicate anything, and nothing gets overwritten silently |
| No reminders to record. An empty day stays empty, breaks the streak and is not counted as a failure; the days written are tracked as a habit of their own, on the day or filled in later | The owner's rule: writing is part of the habit |
| Compliance counted over the days that have a record | A day without data says nothing about the habit |
| A past month is measured against the goals in force at its end | The migration changes goals, and it must not rewrite the past |
| Coincidences between trackers, only with four or more days on each side and a minimum strength, offered at most two at a time as coincidences | The owner's record is small; anything stronger than a coincidence would be advice |
| No health advice in the protocol; the README says so without promising it | The owner's choice, and a precise privacy and claims language |

## 4. Real use

The owner kept the journal in their own folder, with their own memory and their five trackers, and asked to
publish it:

> «estoy utilizando la bitacora y se ve muy bien, publicala de una vez»

## 5. Not included in 0.1

Daily notes and collections (planned for 0.2, which completes the bullet journal), crossing data with `todo` or
finances through the shared memory, image charts, importing from watches or apps, notifications, and any health
advice.
