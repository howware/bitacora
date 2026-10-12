<h1 align="center">bitacora · your habits, without an app</h1>

<p align="center">
  <b>Tell your AI agent what you did today. It keeps your trackers, your streaks and your monthly grid, and once a
  month it walks you through a review, like a bullet journal's migration.</b>
</p>

<p align="center">
  <a href="https://github.com/howware/bitacora/actions/workflows/ci.yml"><img src="https://github.com/howware/bitacora/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/version-0.1.0-blue" alt="Version 0.1.0">
  <a href="https://howware.org"><img src="https://img.shields.io/badge/howware-0.2-5a45d6" alt="howware 0.2"></a>
  <img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/license-Apache%202.0-green" alt="Apache 2.0">
</p>

<p align="center"><a href="README.es.md">Español</a> · <a href="docs/building.md">How it was built</a></p>

> **A [howware](https://howware.org):** your know-how, put to work with AI. Here the know-how is a bullet journal's
> trackers plus **your own decisions**: what you track, with what goal, and why. No app, no boxes to draw: you say
> it, a small tool keeps the numbers exact, and a memory you own keeps everything. (*Bitácora* is Spanish for
> logbook.)

```text
› Last night I slept about six and a half hours, went to the gym and watered the plants.
✓ Sunday 11: sleep 6 h 30 min, gym yes, plants yes.

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
| "How's the gym going?" · "Show me the month" | **Streaks, compliance and averages**, and the **month's grid** as text |
| (when a month begins) | Offers the **monthly reflection**: the numbers, what went well, what didn't, which trackers continue, change or retire (the *migration*), an intention, and up to two coincidences from your own record |

**It doesn't ask you to log.** Writing is part of the habit: a day with no record stays empty and is not counted as
a failure. The tool tracks separately how many days you wrote, and how many of them you filled in later.

**Designed to give no health advice.** It records, counts and shows you your data. Coincidences ("on gym days your mood averaged
3.8 vs 2.9") are just that, coincidences in your record, not causes.

## How it works

| Part | Here |
|---|---|
| Protocol | [`skill/bitacora/SKILL.md`](skill/bitacora/SKILL.md): the method and the agent's rules, in plain words |
| Tool | [`bitacora.py`](skill/bitacora/scripts/bitacora.py): only what must be exact: the date, validating each value against its tracker, one record per tracker and day, streaks, compliance, gaps, the grid and the coincidences |
| Memory | The [Long-Term Memory for AI](https://github.com/howware/long-term-memory-for-AI) adapter: your trackers, records and reflections, in a local file, with history |

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

## Privacy and limits

| Designed to stay on your computer | What the AI agent sees |
|---|---|
| The memory file with your trackers, every day's records and your reflections | Your trackers, their goals and why you keep them; values, streaks and statistics when it queries them; your reflections' text; what you type |

**What it cannot do or guarantee:**
- What the agent sees leaves your computer for your AI provider, under its terms. Some habits (sleep, mood) can be
  health-related data: track only what you are willing to share with it.
- The memory file is not encrypted.
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
