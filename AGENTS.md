# AGENTS.md

Rules for AI agents (and people) **developing** this howware. To **use** it, the protocol is
[skill/bitacora/SKILL.md](skill/bitacora/SKILL.md).

## Never copy the owner's real data here

- Real documents, exports and the memory (`.memory/`) live in the owner's folder, never in this repository.
- Tests and fixtures use synthetic data only. If a test needs a valid-looking identifier (card, account), build
  it in code; the guard rejects valid ones written in files.

## Where each change goes

| Change | Where |
|---|---|
| A rule of the job (how the work is done for everyone) | `SKILL.md` |
| A tracker, its unit or its goal | The memory, as data, through `bitacora.py tracker` — never code |
| An operation that must be exact (parsing, money, dates, ids, storage) | The tool, with tests |

## Conventions (howware spec §6, §8)

- Tools: JSON on stdout, errors as JSON with documented exit codes, no prompts, no network, standard library.
- Quantities as whole numbers in the tracker's declared unit; dates at noon local time; one record per tracker and
  day with a stable key.
- No health advice anywhere: not in the protocol, the tool's messages or the README.
- Bump `version` in `howware.json` and the tool's `__version__` together; changing `seed.json` bumps
  `seed_version`.

## Commands

```bash
python -m unittest discover -s tests -v
git ls-files -z | xargs -0 python tools/check_private_data.py
python tools/install_skill.py
```
