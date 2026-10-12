<h1 align="center">bitacora · your bullet journal, without an app</h1>

<p align="center">
  <b>Tell your AI agent what you did and what happened today. It keeps your habits, your notes and your
  collections, and once a month it walks you through a review, like a bullet journal's migration.</b>
</p>

<p align="center">
  <a href="https://github.com/howware/bitacora/actions/workflows/ci.yml"><img src="https://github.com/howware/bitacora/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/version-0.2.0-blue" alt="Version 0.2.0">
  <a href="https://howware.org"><img src="https://img.shields.io/badge/howware-0.2-5a45d6" alt="howware 0.2"></a>
  <img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/license-Apache%202.0-green" alt="Apache 2.0">
</p>

<p align="center"><a href="README.es.md">Español</a> · <a href="docs/building.md">How it was built</a></p>

> **A [howware](https://howware.org):** your know-how, put to work with AI. Here the know-how is a bullet journal's
> trackers, notes and collections, plus **your own decisions**: what you track, with what goal, and why. No app, no boxes to draw: you say
> it, a small tool keeps the numbers exact, and a memory you own keeps everything. (*Bitácora* is Spanish for
> logbook.)

```text
› Last night I slept about six and a half hours, went to the gym, and it was my cousin's wedding. I had an idea: a
  vertical garden.
✓ Sunday 11: sleep 6 h 30 min, gym yes.
  ○ My cousin's wedding · ! A vertical garden

› Finished Hopscotch, I give it a 4. How many books so far this year?
✓ Books: Hopscotch, read on Oct 11, 4/5. This year: 7 read, average 4.1/5.

› Show me September.
         123456789012345678901234567890
         twtfssmtwtfssmtwtfssmtwtfssmtw
Sleep    ○●●○●●○○●○○·○○●●○●●○○●○○●○○●●○
Gym      ●●●○○○●●●●○·○●●●●○○○●●●●○○○●●●
Plants   ○○●○○●○○●○○·○○●○○●○○●○○●○○●○○●
written  ●●●●●●●●●●●·●●●●●●●●●●●●●●●●●●
  ● done · ○ recorded, goal not met · · no data

› (October 1st)
  Shall we do September's reflection?
```

## What it does

| You say | It does |
|---|---|
| "I want to track how much I sleep, my goal is 7 hours" | Creates a **tracker** with you: its kind (quantity, yes/no or a 1–5 scale), its unit and an optional goal (daily, N times a week, or every N days) |
| "Slept six and a half, went to the gym" | **Records** the day in one line and confirms the date and the exact values |
| "It was my cousin's wedding" · "I had an idea…" | Keeps a **note** of the day in your words, with its symbol: `–` note, `○` event, `!` idea, `*` important. The agent picks the type and you correct it; types and symbols are yours (say, `♡` gratitude) |
| "When did I go to Guanajuato?" | **Searches** your notes, ignoring accents and case |
| "I want to keep the books I read" · "Finished Hopscotch" | **Collections** you build as you go (books, movies, ideas, places…), with the statuses you choose, a rating and the day you finished something; "how many did I read this year?" is counted by the tool |
| "I have to call the plumber" | If you also use [todo](https://github.com/howware/todo) in the same folder, it goes to your **to-dos**; otherwise it stays as a `•` note |
| "How's the gym going?" · "Show me the month" | **Streaks, compliance and averages**, and the **month's grid** as text |
| (when a month begins) | Offers the **monthly reflection**: the numbers, the month's notes and collections, what went well, what didn't, what continues (the *migration*), an intention, **three moments of the month** you choose from your notes, and up to two coincidences from your own record |

**It doesn't ask you to log.** Writing is part of the habit: a day with no record or note stays empty and is not
counted as a failure. The tool tracks separately how many days you wrote, and how many of them you filled in later.

**Designed to give no health advice.** It records, counts and shows you your data. Coincidences ("on gym days your mood averaged
3.8 vs 2.9") are just that, coincidences in your record, not causes.

## How it works

| Part | Here |
|---|---|
| Protocol | [`skill/bitacora/SKILL.md`](skill/bitacora/SKILL.md): the method and the agent's rules, in plain words |
| Tool | [`bitacora.py`](skill/bitacora/scripts/bitacora.py): only what must be exact: the date, validating each value against its tracker, one record per tracker and day, one note per text and day, streaks, compliance, gaps, search, collection statuses and counts, the grid and the coincidences |
| Memory | The [Long-Term Memory for AI](https://github.com/howware/long-term-memory-for-AI) adapter: your whole journal, in a local file, with history. It can be the same memory as [todo](https://github.com/howware/todo)'s, so your to-dos and your journal live together |

## Install

```bash
git clone https://github.com/howware/long-term-memory-for-AI
python long-term-memory-for-AI/tools/install_skill.py --target ~/.claude/skills/project-memory
git clone https://github.com/howware/bitacora
python bitacora/tools/install_skill.py                                       # Claude Code
python bitacora/tools/install_skill.py --target ~/.codex/skills/bitacora      # Codex
```

Create a folder for your journal, open Claude Code there (add the persistent-memory instruction of
[Long-Term Memory for AI](https://github.com/howware/long-term-memory-for-AI#set-up-a-project) to its `CLAUDE.md`)
and say *"I want to keep my journal here."*

**Already on 0.1?** Reinstall the skill; in the next conversation the agent runs `setup` by itself and keeps
everything. **Want your journal together with your `todo` to-dos?** In `todo`'s folder, `bitacora.py copy-from`
copies your whole journal (running it twice duplicates nothing, and the original folder is not touched); the agent
walks you through it.

## Privacy and limits

| Designed to stay on your computer | What the AI agent sees |
|---|---|
| The memory file with your trackers, every day's records, your notes, your collections and your reflections | Your trackers, their goals and why you keep them; values, streaks and statistics when it queries them; your notes and collections when it queries or searches them; your reflections' text; what you type |

**What it cannot do or guarantee:**
- What the agent sees leaves your computer for your AI provider, under its terms. Some habits (sleep, mood) can be
  health-related data: track only what you are willing to share with it.
- The memory file is not encrypted.
- **Removing hides, it doesn't erase:** a removed note or item stops showing, but stays in the memory file, marked
  as voided.
- **No notifications.** The reflection is offered when you open a conversation.
- The protocol tells the agent not to give health advice, but an AI's replies can't be guaranteed; its patterns
  are not causes.

## Development

```bash
python -m unittest discover -s tests -v
git ls-files -z | xargs -0 python tools/check_private_data.py
```

Tests use synthetic data only. See [AGENTS.md](AGENTS.md).

## License

[Apache 2.0](LICENSE). Not affiliated with Ryder Carroll; Bullet Journal® is his trademark.
