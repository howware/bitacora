"""bitacora — tool of the bitacora howware: the owner's trackers and their monthly reflection.

Commands (JSON on stdout, diagnostics on stderr, documented exit codes):
  setup      load seed.json into the memory (predicates, settings, high-volume event types)
  now        today's date, weekday and time, from the clock (never guess them)
  tracker    create or change a tracker: kind, unit, goal, state (retired keeps its history)
  trackers   the trackers with their goals
  log        record several trackers for one day in one call, idempotently
  unlog      void one day's record of a tracker, with a reason
  day        what is recorded for a date
  grid       the month as a text grid, one row per tracker plus the days written
  stats      compliance, streaks, averages, weekdays and coincidences for a month
  reflect    everything the monthly reflection needs; with --save, store the owner's answers
  brief      start of session: today, the trackers, whether a monthly reflection is due

Contract (howware spec §6): no network, no interactive prompts, idempotent writes, exact quantities as integers in
the tracker's declared unit, dates at noon local time, refuse unsafe input with a clear error. Standard library only.
Judgment (what to highlight, what a pattern might mean) is the agent's and the owner's, never this file's.
"""

from __future__ import annotations

import argparse
import calendar
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

__version__ = "0.1.0"
HERE = Path(__file__).resolve().parent
SEED = HERE / "seed.json"
MIN_MEMORY = (0, 4, 0)

# Exit codes (documented in SKILL.md)
OK, BAD_INPUT, MEMORY_ERROR = 0, 2, 3

KINDS = ("quantity", "yesno", "scale")
STATES = ("active", "retired")
YES = {"yes", "y", "si", "sí", "s", "1", "true"}
NO = {"no", "n", "0", "false"}
MAX_TEXT = 2000
MAX_QUANTITY = 1_000_000
MINUTE_UNITS = ("minute", "minuto", "min")   # these also take H:MM and hours (6.5h)
MIN_SIDE = 4            # days on each side before a coincidence between two trackers is reported
MIN_STRENGTH = 0.1      # difference of averages over the measure's range in the month; below it, nothing to say
WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
GRID_WORDS = {"en": ("mtwtfss", "written"), "es": ("lmmjvsd", "escrito")}   # weekday initials, last row
WEEKDAY_NAMES = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")   # not the locale's


class ToolError(Exception):
    def __init__(self, message: str, code: int = BAD_INPUT):
        super().__init__(message)
        self.code = code


# -- memory (project-memory helper) -------------------------------------------------
def find_helper(explicit: str | None) -> Path:
    for c in (explicit, os.environ.get("HOWWARE_MEMORY_HELPER"),
              Path.home() / ".claude/skills/project-memory/scripts/memory.py",
              Path.home() / ".codex/skills/project-memory/scripts/memory.py"):
        if c and Path(c).is_file():
            return Path(c)
    raise ToolError("project-memory is not installed (or pass --mem / HOWWARE_MEMORY_HELPER).", MEMORY_ERROR)


class Memory:
    PAGE = 5000

    def __init__(self, helper: Path, db: str | None):
        self.helper, self.db = helper, db

    def command(self, args: tuple[str, ...]) -> list[str]:
        return [sys.executable, str(self.helper)] + (["--db", self.db] if self.db else []) + list(args)

    def run(self, *args: str, stdin: dict | None = None) -> Any:
        for attempt in (1, 2):
            proc = subprocess.run(self.command(args),
                                  input=json.dumps(stdin, ensure_ascii=False) if stdin is not None else None,
                                  capture_output=True, text=True, encoding="utf-8")
            if proc.returncode == 0:
                return json.loads(proc.stdout) if proc.stdout.strip() else None
            message = (proc.stderr or proc.stdout).strip()
            # The memory compares validity per second: a change to a fact in the second it began waits one.
            if attempt == 1 and ("at least one second" in message or "is not after" in message):
                time.sleep(1.1)
                continue
            raise ToolError(f"memory {args[0]} failed: {message[-600:]}", MEMORY_ERROR)

    def check_version(self) -> None:
        out = subprocess.run([sys.executable, str(self.helper), "--version"], capture_output=True, text=True).stdout
        found = re.search(r"(\d+)\.(\d+)\.(\d+)", out or "")
        if not found or tuple(int(x) for x in found.groups()) < MIN_MEMORY:
            raise ToolError(f"project-memory >= {'.'.join(map(str, MIN_MEMORY))} is required (found: {out.strip()}).",
                            MEMORY_ERROR)

    def rows_many(self, queries: list[tuple[str, ...]]) -> list[list[dict]]:
        """Several `list` queries at once, in parallel processes; later pages, rarely needed, one by one."""
        procs = [subprocess.Popen(self.command(("list", *q, "--limit", str(self.PAGE))), stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True, encoding="utf-8") for q in queries]
        out = []
        for q, proc in zip(queries, procs):
            stdout, stderr = proc.communicate()
            if proc.returncode != 0:
                raise ToolError(f"memory list failed: {(stderr or stdout).strip()[-600:]}", MEMORY_ERROR)
            page = json.loads(stdout)
            rows, offset = page["rows"], self.PAGE
            while page.get("truncated"):
                page = self.run("list", *q, "--limit", str(self.PAGE), "--offset", str(offset))
                rows += page["rows"]
                offset += self.PAGE
            out.append(rows)
        return out

    def write(self, by: str, content: str, kind: str = "user_statement", **sections) -> dict:
        return self.run("write", stdin={"source": {"type": kind, "content": content, "provided_by": by,
                                                   "captured_at": "now"},
                                        "performed_by": by, **sections})


# -- exact helpers ------------------------------------------------------------------------
def parse_offset(text: str) -> timezone:
    m = re.fullmatch(r"([+-])(\d{2}):?(\d{2})", text.strip())
    if not m:
        raise ToolError(f"Time zone offset must look like -06:00, not {text!r}")
    minutes = int(m.group(2)) * 60 + int(m.group(3))
    return timezone(timedelta(minutes=minutes if m.group(1) == "+" else -minutes))


def local_offset() -> str:
    z = datetime.now().astimezone().strftime("%z")
    return f"{z[:3]}:{z[3:]}"


def parse_day(text: str, what: str = "date") -> date:
    try:
        return date.fromisoformat(text)
    except (TypeError, ValueError):
        raise ToolError(f"{what} must be YYYY-MM-DD, not {text!r}") from None


def parse_month(text: str) -> tuple[date, date]:
    """First and last day of YYYY-MM."""
    m = re.fullmatch(r"(\d{4})-(\d{2})", (text or "").strip())
    if not m or not 1 <= int(m.group(2)) <= 12:
        raise ToolError(f"--month must be YYYY-MM, not {text!r}")
    y, mo = int(m.group(1)), int(m.group(2))
    return date(y, mo, 1), date(y, mo, calendar.monthrange(y, mo)[1])


def previous_month(day: date) -> str:
    first = day.replace(day=1) - timedelta(days=1)
    return first.strftime("%Y-%m")


def noon(day: date, tz: timezone) -> str:
    return datetime(day.year, day.month, day.day, 12, tzinfo=tz).isoformat(timespec="seconds")


def day_of(value: Any) -> date | None:
    return date.fromisoformat(str(value)[:10]) if value else None


def slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "x"


def tracker_key(ref: str) -> str:
    return ref if ref.startswith("tracker:") else f"tracker:{slug(ref)}"


def text_field(value: str | None, what: str) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if len(value) > MAX_TEXT:
        raise ToolError(f"{what} is {len(value)} characters; keep it under {MAX_TEXT}.")
    return value or None


def percent(part: int, whole: int) -> int | None:
    return round(100 * part / whole) if whole else None


def mean(values: list[int]) -> float | None:
    return round(sum(values) / len(values), 1) if values else None


def show(tracker: dict, value: int | float | None) -> str | None:
    """Human form of a stored value, for the agent to read back (it still translates it)."""
    if value is None:
        return None
    if tracker["kind"] == "yesno":
        return "yes" if value else "no"
    if tracker["kind"] == "scale":
        return f"{value}/5"
    if tracker["unit"] in MINUTE_UNITS:
        h, m = divmod(round(value), 60)
        return f"{h} h {m:02d} min" if h else f"{m} min"
    return f"{value:g} {tracker['unit']}" if isinstance(value, float) else f"{value} {tracker['unit']}"


# -- goals ----------------------------------------------------------------------------------
def parse_target(text: str, kind: str) -> tuple[str | None, int | None]:
    """at_least:N | at_most:N | yes | none."""
    text = (text or "").strip().lower()
    if text == "none":
        return None, None
    if text == "yes":
        if kind != "yesno":
            raise ToolError("--target yes is for yes/no trackers; for the others use at_least:N or at_most:N.")
        return "yes", None
    m = re.fullmatch(r"(at_least|at_most):(\d+)", text)
    if not m:
        raise ToolError(f"--target is at_least:N, at_most:N, yes or none, not {text!r}")
    if kind == "yesno":
        raise ToolError("A yes/no tracker's target is just 'yes' (a done day).")
    value = int(m.group(2))
    if kind == "scale" and not 1 <= value <= 5:
        raise ToolError("A scale goes from 1 to 5.")
    return m.group(1), value


def parse_every(text: str) -> tuple[str | None, int | None]:
    """day | week:N (N done days per Monday-Sunday week) | days:N (at most N days between done days) | none."""
    text = (text or "").strip().lower()
    if text == "none":
        return None, None
    if text == "day":
        return "day", None
    m = re.fullmatch(r"(week|days):(\d+)", text)
    if not m:
        raise ToolError(f"--every is day, week:N, days:N or none, not {text!r}")
    n = int(m.group(2))
    if m.group(1) == "week" and not 1 <= n <= 7:
        raise ToolError("week:N needs N from 1 to 7 (done days per week).")
    if m.group(1) == "days" and not 1 <= n <= 365:
        raise ToolError("days:N needs N from 1 to 365.")
    return m.group(1), n


def parse_value(tracker: dict, text: str) -> int:
    raw = text.strip().lower()
    if tracker["kind"] == "yesno":
        if raw in YES:
            return 1
        if raw in NO:
            return 0
        raise ToolError(f"{tracker['name']} is yes/no, not {text!r}.")
    if tracker["kind"] == "quantity" and tracker["unit"] in MINUTE_UNITS:
        hm = re.fullmatch(r"(\d+):([0-5]\d)", raw)
        hours = re.fullmatch(r"(\d+(?:\.\d+)?)\s*h", raw)
        if hm:
            raw = str(int(hm.group(1)) * 60 + int(hm.group(2)))
        elif hours:
            minutes = Decimal(hours.group(1)) * 60
            if minutes != minutes.to_integral_value():
                raise ToolError(f"{text!r} is not a whole number of minutes; use H:MM.")
            raw = str(int(minutes))
    if not re.fullmatch(r"\d+", raw):
        unit = "1 to 5" if tracker["kind"] == "scale" else f"a whole number of {tracker['unit']}"
        hint = " (or H:MM, or hours like 6.5h)" if tracker["unit"] in MINUTE_UNITS else ""
        raise ToolError(f"{tracker['name']} takes {unit}{hint}, not {text!r}.")
    value = int(raw)
    if tracker["kind"] == "scale" and not 1 <= value <= 5:
        raise ToolError(f"{tracker['name']} is a scale from 1 to 5, not {value}.")
    if tracker["kind"] == "quantity":
        limit = 1440 if tracker["unit"] in MINUTE_UNITS else MAX_QUANTITY
        if value > limit:
            raise ToolError(f"{value} {tracker['unit']} in one day is not possible for {tracker['name']}.")
    return value


def done(tracker: dict, value: int) -> bool | None:
    """Whether a day's value counts toward the goal. None: a scale without a target has no 'done'."""
    op, target = tracker["target"], tracker["target_value"]
    if op == "at_least":
        return value >= target
    if op == "at_most":
        return value <= target
    if tracker["kind"] == "scale":
        return None
    return value > 0


def goal_text(t: dict) -> str | None:
    if not t["target"] and not t["every"]:
        return None
    what = {"at_least": f"at least {show(t, t['target_value'])}", "at_most": f"at most {show(t, t['target_value'])}",
            "yes": "yes", None: "done"}[t["target"]]
    when = {"day": "every day", "week": f"{t['every_n']} days a week", "days": f"at least every {t['every_n']} days",
            None: "every day"}[t["every"]]
    return f"{what}, {when}"


# -- the journal: trackers and records, read once per command --------------------------------
TRACKER_FACTS = ("tracker_kind", "tracker_unit", "tracker_target", "tracker_target_value", "tracker_every",
                 "tracker_every_n", "tracker_state", "tracker_since", "tracker_until", "tracker_why", "tracker_seq")


class Journal:
    def __init__(self, mem: Memory, tz: timezone, today: date, as_of: date | None = None):
        self.mem, self.tz, self.today = mem, tz, today
        cols = [x for f in ("key", "name", *(f"fact:{f}" for f in TRACKER_FACTS)) for x in ("--column", f)]
        as_of_args = ("--as-of", datetime(as_of.year, as_of.month, as_of.day, 23, 59, 59, tzinfo=tz)
                      .isoformat(timespec="seconds")) if as_of else ()
        settings, trackers, logs, reflections, then = mem.rows_many([
            ("--entity-type", "settings", "--where", "key = settings:bitacora", "--column", "key"),
            ("--entity-type", "tracker", *cols),
            ("--event-type", "tracker_logged", *[x for c in ("key", "occurred_at", "attr:tracker_value",
                                                              "attr:late_days", "link:about_tracker/key")
                                                  for x in ("--column", c)]),
            ("--event-type", "month_reflected", *[x for c in ("key", "occurred_at", "attr:reflect_month",
                                                               "attr:went_well", "attr:went_wrong", "attr:intention")
                                                   for x in ("--column", c)]),
            ("--entity-type", "tracker", *cols, *as_of_args) if as_of else ("--entity-type", "settings", "--column", "key")])
        if not settings:
            raise ToolError("This memory has no bitacora settings yet: run TOOL setup first.", MEMORY_ERROR)
        self.trackers: dict[str, dict] = {}
        for r in trackers:
            f = lambda name: r[f"fact:{name}"]
            self.trackers[r["key"]] = {
                "key": r["key"], "name": r["name"], "kind": f("tracker_kind"), "unit": f("tracker_unit"),
                "target": f("tracker_target"), "target_value": f("tracker_target_value"),
                "every": f("tracker_every"), "every_n": f("tracker_every_n"),
                "state": f("tracker_state") or "active", "since": day_of(f("tracker_since")),
                "until": day_of(f("tracker_until")), "why": f("tracker_why"), "seq": f("tracker_seq") or 0}
        # A past month is measured with the goals in force at its end; trackers created later keep today's.
        for r in then if as_of else []:
            t = self.trackers.get(r["key"])
            if t:
                t.update({"target": r["fact:tracker_target"], "target_value": r["fact:tracker_target_value"],
                          "every": r["fact:tracker_every"], "every_n": r["fact:tracker_every_n"]})
        # records[tracker][day] = {"key", "value", "late"}; one per tracker and day (corrections void the old one)
        self.records: dict[str, dict[date, dict]] = {}
        for r in logs:
            day = day_of(r["occurred_at"])
            self.records.setdefault(r["link:about_tracker/key"], {})[day] = {
                "key": r["key"], "value": r["attr:tracker_value"], "late": (r["attr:late_days"] or 0) > 0}
        self.reflections = {r["attr:reflect_month"]: {"key": r["key"], "month": r["attr:reflect_month"],
                                                      "went_well": r["attr:went_well"],
                                                      "went_wrong": r["attr:went_wrong"],
                                                      "intention": r["attr:intention"],
                                                      "saved_on": day_of(r["occurred_at"]).isoformat()}
                            for r in reflections}

    def ordered(self, include_retired: bool = False) -> list[dict]:
        return sorted((t for t in self.trackers.values() if include_retired or t["state"] == "active"),
                      key=lambda t: (t["seq"], t["key"]))

    def find(self, ref: str) -> dict:
        key = tracker_key(ref)
        found = self.trackers.get(key) or next((t for t in self.trackers.values()
                                                 if t["name"].casefold() == ref.strip().casefold()), None)
        if not found:
            names = ", ".join(f"{t['name']} ({t['key']})" for t in self.ordered()) or "none yet"
            raise ToolError(f"There is no tracker {ref!r}. Trackers: {names}.")
        return found

    def window(self, t: dict, first: date, last: date) -> tuple[date, date] | None:
        """The days of [first, last] the tracker existed and are not in the future."""
        start = max(first, t["since"] or first)
        end = min(last, self.today, (t["until"] - timedelta(days=1)) if t["until"] else last)
        return (start, end) if start <= end else None

    def written(self) -> dict[date, bool]:
        """Days with at least one record → whether all of that day's records were written later."""
        days: dict[date, bool] = {}
        for recs in self.records.values():
            for day, r in recs.items():
                days[day] = days.get(day, True) and r["late"]
        return days

    # -- per tracker ------------------------------------------------------------------------
    def done_days(self, t: dict) -> list[date]:
        return sorted(d for d, r in self.records.get(t["key"], {}).items() if done(t, r["value"]))

    def streak(self, t: dict) -> dict:
        recs = self.records.get(t["key"], {})
        every = t["every"] or ("day" if t["target"] else None)
        if every == "days":
            days = self.done_days(t)
            if not days:
                return {"unit": "times", "current": 0, "best": 0, "last_done": None, "next_by": None}
            runs, run = [], 1
            for a, b in zip(days, days[1:]):
                run = run + 1 if (b - a).days <= t["every_n"] else (runs.append(run) or 1)
            runs.append(run)
            alive = (self.today - days[-1]).days <= t["every_n"]
            return {"unit": "times", "current": runs[-1] if alive else 0, "best": max(runs),
                    "last_done": days[-1].isoformat(), "days_since": (self.today - days[-1]).days,
                    "next_by": (days[-1] + timedelta(days=t["every_n"])).isoformat()}
        if every == "week":
            this_monday = self.today - timedelta(days=self.today.weekday())
            first = t["since"] or min(recs, default=self.today)
            weeks, monday = [], first - timedelta(days=first.weekday())
            while monday <= this_monday:
                count = sum(1 for d in self.done_days(t) if monday <= d < monday + timedelta(days=7))
                weeks.append((monday, count >= t["every_n"], count))
                monday += timedelta(days=7)
            current_count = weeks[-1][2] if weeks else 0
            closed = weeks if weeks and weeks[-1][1] else weeks[:-1]     # the week in progress doesn't break it yet
            return {"unit": "weeks", "current": run_length([ok for _, ok, _ in closed]),
                    "best": best_run([ok for _, ok, _ in weeks]),
                    "this_week": {"done": current_count, "goal": t["every_n"]}}
        # daily goal, or no goal (then: consecutive days with a record)
        ok_on = (lambda d: d in recs and bool(done(t, recs[d]["value"]))) if every == "day" else (lambda d: d in recs)
        start = t["since"] or min(recs, default=self.today)
        days = [start + timedelta(days=i) for i in range((self.today - start).days + 1)]
        flags = [ok_on(d) for d in days]
        if flags and not flags[-1] and self.today not in recs:
            flags = flags[:-1]                                        # today isn't over: it doesn't break it yet
        return {"unit": "days", "current": run_length(flags), "best": best_run(flags)}

    def month_stats(self, t: dict, first: date, last: date) -> dict | None:
        win = self.window(t, first, last)
        if not win:
            return None
        start, end = win
        span = (end - start).days + 1
        recs = {d: r for d, r in self.records.get(t["key"], {}).items() if start <= d <= end}
        values = [r["value"] for r in recs.values()]
        flags = {d: done(t, r["value"]) for d, r in recs.items()}
        out = {"tracker": t["key"], "name": t["name"], "goal": goal_text(t), "days": span, "logged": len(recs),
               "no_data": span - len(recs)}
        if t["kind"] != "yesno":
            out |= {"average": show(t, mean(values)), "average_value": mean(values),
                    "min": show(t, min(values, default=None)), "max": show(t, max(values, default=None))}
        has_done = any(v is not None for v in flags.values()) or t["kind"] != "scale" or t["target"]
        if has_done:
            met = sum(1 for v in flags.values() if v)
            out |= {"done_days": met, "not_done_days": len(recs) - met}
        every = t["every"] or ("day" if t["target"] else None)
        if every == "day":
            out["compliance_percent"] = percent(out["done_days"], len(recs))
            out["compliance_note"] = "done days out of days with a record; days without data are not failures"
        elif every == "week":
            mondays = sorted({d - timedelta(days=d.weekday()) for d in
                              (start + timedelta(days=i) for i in range(span))})
            # weeks that end this month and began once the tracker existed
            full = [m for m in mondays if start <= m + timedelta(days=6) <= end and (not t["since"] or m >= t["since"])]
            all_done = self.done_days(t)        # a week that began last month counts its days from then too
            weeks = [{"week_of": m.isoformat(), "done": sum(1 for d in all_done if m <= d < m + timedelta(days=7)),
                      "goal": t["every_n"]} for m in full]
            for w in weeks:
                w["met"] = w["done"] >= w["goal"]
            out["weeks"] = weeks
            out["compliance_percent"] = percent(sum(w["met"] for w in weeks), len(weeks))
            out["compliance_note"] = "complete Monday-Sunday weeks of the month that met the goal"
        elif every == "days":
            days = sorted(d for d, v in flags.items() if v)
            before = [d for d in self.done_days(t) if d < start]
            chain = ([before[-1]] if before else []) + days
            gaps = [(b - a).days for a, b in zip(chain, chain[1:])]
            out |= {"longest_gap_days": max(gaps, default=None),
                    "gaps_over_goal": sum(1 for g in gaps if g > t["every_n"]),
                    "compliance_percent": percent(sum(1 for g in gaps if g <= t["every_n"]), len(gaps)),
                    "compliance_note": f"intervals between done days of at most {t['every_n']} days"}
        by_wd: dict[str, list[int]] = {}
        for d, r in recs.items():
            by_wd.setdefault(WEEKDAYS[d.weekday()], []).append(
                r["value"] if t["kind"] != "yesno" and not t["target"] else int(bool(flags[d])))
        out["by_weekday"] = {wd: ({"days": len(v), "average": show(t, mean(v))} if t["kind"] != "yesno"
                                  and not t["target"] else {"days": len(v), "done": sum(v)})
                             for wd in WEEKDAYS if (v := by_wd.get(wd))}
        out["streak"] = self.streak(t)
        return out

    def coincidences(self, first: date, last: date) -> list[dict]:
        """For each pair (A with done/not done, B a number): B's average on days A was done vs not done.
        These are coincidences in the owner's own record, not causes."""
        found = []
        trackers = self.ordered(include_retired=True)
        for a in trackers:
            a_recs = {d: done(a, r["value"]) for d, r in self.records.get(a["key"], {}).items() if first <= d <= last}
            if not any(v is not None for v in a_recs.values()):
                continue
            for b in trackers:
                if b is a or b["kind"] == "yesno":
                    continue
                b_recs = {d: r["value"] for d, r in self.records.get(b["key"], {}).items() if first <= d <= last}
                yes = [b_recs[d] for d, v in a_recs.items() if v and d in b_recs]
                no = [b_recs[d] for d, v in a_recs.items() if v is False and d in b_recs]
                if len(yes) < MIN_SIDE or len(no) < MIN_SIDE:
                    continue
                my, mn = sum(yes) / len(yes), sum(no) / len(no)
                scale = max(max(yes + no) - min(yes + no), 1)
                found.append({"when": a["name"], "measure": b["name"],
                              "average_when_done": show(b, round(my, 1)), "days_done": len(yes),
                              "average_when_not": show(b, round(mn, 1)), "days_not": len(no),
                              "difference": ("+" if my >= mn else "-") + show(b, round(abs(my - mn), 1)),
                              "strength": round(abs(my - mn) / scale, 2)})
        return sorted((f for f in found if f["strength"] >= MIN_STRENGTH), key=lambda x: -x["strength"])[:5]

    def writing(self, first: date, last: date) -> dict:
        start = max(first, min((t["since"] for t in self.trackers.values() if t["since"]), default=first))
        end = min(last, self.today)
        days = self.written()
        span = max((end - start).days + 1, 0)
        in_month = {d: late for d, late in days.items() if start <= d <= end}
        all_days = [min(days, default=self.today) + timedelta(days=i)
                    for i in range((self.today - min(days, default=self.today)).days + 1)]
        flags = [d in days for d in all_days]
        if flags and not flags[-1]:
            flags = flags[:-1]
        return {"days": span, "written": len(in_month), "on_the_day": sum(1 for late in in_month.values() if not late),
                "filled_in_later": sum(1 for late in in_month.values() if late), "not_written": span - len(in_month),
                "streak": {"unit": "days", "current": run_length(flags), "best": best_run(flags)}}

    def grid(self, first: date, last: date, lang: str = "en") -> dict:
        initials, written_label = GRID_WORDS.get(lang, GRID_WORDS["en"])
        n = (last - first).days + 1
        rows, width = [], max([len(t["name"]) for t in self.ordered(True)] + [7])
        header = " " * (width + 1) + "".join(str((first + timedelta(days=i)).day % 10) for i in range(n))
        weekdays = " " * (width + 1) + "".join(initials[(first + timedelta(days=i)).weekday()] for i in range(n))
        for t in self.ordered(include_retired=True):
            win = self.window(t, first, last)
            if not win:
                continue
            recs = self.records.get(t["key"], {})
            cells = []
            for i in range(n):
                d = first + timedelta(days=i)
                if not win[0] <= d <= win[1]:
                    cells.append(" ")
                elif d not in recs:
                    cells.append("·")
                else:
                    v = done(t, recs[d]["value"])
                    cells.append(str(recs[d]["value"]) if v is None else ("●" if v else "○"))
            rows.append(t["name"].ljust(width) + " " + "".join(cells))
        days = self.written()
        cells = "".join(" " if (first + timedelta(days=i)) > self.today else
                        ("·" if (first + timedelta(days=i)) not in days else
                         ("◐" if days[first + timedelta(days=i)] else "●")) for i in range(n))
        rows.append(written_label.ljust(width) + " " + cells)
        return {"text": "\n".join([header, weekdays, *rows]),
                "legend": {"●": "done (or written on the day)", "○": "recorded, goal not met", "1-5": "scale value",
                           "·": "no data", "◐": "written later", " ": "before the tracker existed, or future"}}


def run_length(flags: list[bool]) -> int:
    count = 0
    for f in reversed(flags):
        if not f:
            break
        count += 1
    return count


def best_run(flags: list[bool]) -> int:
    best = run = 0
    for f in flags:
        run = run + 1 if f else 0
        best = max(best, run)
    return best


def tracker_view(j: Journal, t: dict) -> dict:
    return {"tracker": t["key"], "name": t["name"], "kind": t["kind"], "unit": t["unit"], "goal": goal_text(t),
            "target": t["target"], "target_value": t["target_value"], "every": t["every"], "every_n": t["every_n"],
            "state": t["state"], "since": t["since"].isoformat() if t["since"] else None,
            "until": t["until"].isoformat() if t["until"] else None, "why": t["why"]}


# -- commands -------------------------------------------------------------------------------
def cmd_setup(mem: Memory, args, now: datetime) -> dict:
    seed = json.loads(SEED.read_text(encoding="utf-8"))
    result = mem.write(args.by, f"bitacora seed v{seed['seed_version']}", "helper_command",
                       predicates=[{**p, "distinct_from_similar": True} for p in seed["predicates"]],
                       entities=seed["entities"])
    for event_type in seed["high_volume_event_types"]:
        mem.run("define-event-type", "--type", event_type, "--high-volume", "--by", args.by,
                "--reason", "One per tracker and day: thousands per year")
    return {"ok": True, "seed_version": seed["seed_version"], "warnings": result.get("warnings", [])}


def cmd_now(mem: Memory, args, now: datetime) -> dict:
    return {"ok": True, "today": now.date().isoformat(), "weekday": WEEKDAY_NAMES[now.weekday()],
            "time": now.strftime("%H:%M"), "yesterday": (now.date() - timedelta(days=1)).isoformat(),
            "month": now.strftime("%Y-%m")}


def cmd_tracker(mem: Memory, args, now: datetime) -> dict:
    j = Journal(mem, now.tzinfo, now.date())
    key = tracker_key(args.key)
    current = j.trackers.get(key)
    has_records = bool(j.records.get(key))
    if not current and not (args.name and args.kind):
        raise ToolError(f"New tracker {key}: give it a --name and a --kind ({', '.join(KINDS)}).")
    kind = args.kind or current["kind"]
    if kind not in KINDS:
        raise ToolError(f"--kind is {', '.join(KINDS)}.")
    if current and has_records and args.kind and args.kind != current["kind"]:
        raise ToolError("This tracker already has records: changing its kind would change their meaning. "
                        "Retire it and create a new one.")
    unit = args.unit.strip() if args.unit else (current["unit"] if current else None)
    if kind == "quantity" and not unit:
        raise ToolError("A quantity tracker needs a --unit (e.g. minute, glass, ml, page).")
    if current and has_records and args.unit and args.unit.strip() != current["unit"]:
        raise ToolError("This tracker already has records in its unit: changing the unit would change their value. "
                        "Retire it and create a new one.")
    if kind != "quantity":
        unit = None
    facts: list[tuple[str, Any]] = []
    entity = {"key": key, "type": "tracker", "name": (args.name or current["name"]).strip()}
    if current and args.name and args.name.strip() != current["name"]:
        entity["rename"] = True
    if not current:
        facts += [("tracker_kind", kind), ("tracker_state", "active"), ("tracker_since", noon(now.date(), now.tzinfo)),
                  ("tracker_seq", len(j.trackers) + 1)]
        if unit:
            facts.append(("tracker_unit", unit))
    elif args.kind and args.kind != current["kind"]:
        facts.append(("tracker_kind", kind))
    if current and unit and unit != current["unit"]:
        facts.append(("tracker_unit", unit))
    if args.target is not None:
        op, value = parse_target(args.target, kind)
        facts += [("tracker_target", op), ("tracker_target_value", value)]
    if args.every is not None:
        every, n = parse_every(args.every)
        facts += [("tracker_every", every), ("tracker_every_n", n)]
    if args.why is not None:
        facts.append(("tracker_why", text_field(args.why, "--why")))
    if args.state:
        if args.state not in STATES:
            raise ToolError(f"--state is {', '.join(STATES)}.")
        if not current:
            raise ToolError("A new tracker starts active.")
        if args.state != current["state"]:
            facts.append(("tracker_state", args.state))
            facts.append(("tracker_until", noon(now.date(), now.tzinfo) if args.state == "retired" else None))
            if args.state == "active" and not has_records:
                facts.append(("tracker_since", noon(now.date(), now.tzinfo)))
    sets = [{"subject": key, "predicate": p, "value": v, "valid_from": "now"} for p, v in facts if v is not None]
    closes = [{"subject": key, "predicate": p, "at": "now", "if_present": True} for p, v in facts if v is None]
    result = mem.write(args.by, args.source or f"Tracker {entity['name']}", entities=[entity], facts=sets,
                       **({"close": closes} if closes else {}))
    t = Journal(mem, now.tzinfo, now.date()).trackers[key]
    return {"ok": True, "created": not current, **tracker_view(j, t), "warnings": result.get("warnings", [])}


def cmd_trackers(mem: Memory, args, now: datetime) -> dict:
    j = Journal(mem, now.tzinfo, now.date())
    return {"ok": True, "trackers": [tracker_view(j, t) | {"streak": j.streak(t)} for t in j.ordered(args.all)]}


def cmd_log(mem: Memory, args, now: datetime) -> dict:
    j = Journal(mem, now.tzinfo, now.date())
    day = parse_day(args.date, "--date") if args.date else now.date()
    if day > now.date():
        raise ToolError(f"{day.isoformat()} hasn't happened yet: only today or past days can be recorded.")
    pairs = []
    for item in args.entry:
        if "=" not in item:
            raise ToolError(f"--entry is tracker=value, not {item!r}")
        ref, raw = item.split("=", 1)
        t = j.find(ref.strip())
        if t["state"] != "active":
            raise ToolError(f"{t['name']} is retired; reactivate it to record it.")
        if t["since"] and day < t["since"]:
            raise ToolError(f"{t['name']} exists since {t['since'].isoformat()}; it can't have a record before.")
        if any(p[0]["key"] == t["key"] for p in pairs):
            raise ToolError(f"{t['name']} appears twice in this call.")
        pairs.append((t, parse_value(t, raw)))
    events, voids, results = [], [], []
    late = (now.date() - day).days
    for t, value in pairs:
        prev = j.records.get(t["key"], {}).get(day)
        stem = f"LOG_{t['key'].split(':', 1)[1]}_{day.strftime('%Y%m%d')}"
        if prev and prev["value"] == value:
            results.append({"tracker": t["key"], "name": t["name"], "value": show(t, value), "unchanged": True})
            continue
        if prev and not args.correct:
            results.append({"tracker": t["key"], "name": t["name"], "value": show(t, prev["value"]), "conflict": True,
                            "new_value": show(t, value),
                            "message": "There is already a different record for this day; to replace it, --correct."})
            continue
        if prev:
            voids.append(prev["key"])
            stem += f"_c{now.strftime('%H%M%S')}"
        events.append({"key": stem, "type": "tracker_logged", "occurred_at": noon(day, now.tzinfo),
                       "summary": f"{t['name']}: {show(t, value)}",
                       "attributes": {"tracker_value": value, "late_days": late},
                       "links": [{"predicate": "about_tracker", "entity": t["key"]}]})
        results.append({"tracker": t["key"], "name": t["name"], "value": show(t, value),
                        "done": done(t, value), **({"corrected": True} if prev else {"created": True})})
    for key in voids:
        mem.run("void", "--event", key, "--reason", args.source or "Corrected by the owner", "--by", args.by)
    if events:
        mem.write(args.by, args.source or f"Record of {day.isoformat()}", events=events)
    after = Journal(mem, now.tzinfo, now.date())
    for r in results:
        r["streak"] = after.streak(after.trackers[r["tracker"]])
    return {"ok": True, "date": day.isoformat(), "weekday": WEEKDAYS[day.weekday()], "late_days": late,
            "entries": results, "conflicts": sum(1 for r in results if r.get("conflict"))}


def cmd_unlog(mem: Memory, args, now: datetime) -> dict:
    j = Journal(mem, now.tzinfo, now.date())
    t = j.find(args.tracker)
    day = parse_day(args.date, "--date")
    prev = j.records.get(t["key"], {}).get(day)
    if not prev:
        raise ToolError(f"{t['name']} has no record on {day.isoformat()}.")
    mem.run("void", "--event", prev["key"], "--reason", args.reason, "--by", args.by)
    return {"ok": True, "tracker": t["key"], "date": day.isoformat(), "voided": show(t, prev["value"])}


def cmd_day(mem: Memory, args, now: datetime) -> dict:
    j = Journal(mem, now.tzinfo, now.date())
    day = parse_day(args.date, "--date") if args.date else now.date()
    out = []
    for t in j.ordered(include_retired=True):
        if not j.window(t, day, day):
            continue
        r = j.records.get(t["key"], {}).get(day)
        out.append({"tracker": t["key"], "name": t["name"], "value": show(t, r["value"]) if r else None,
                    "done": done(t, r["value"]) if r else None, "written_later": r["late"] if r else None})
    return {"ok": True, "date": day.isoformat(), "weekday": WEEKDAYS[day.weekday()], "entries": out,
            "missing": [e["name"] for e in out if e["value"] is None]}


def month_of(args, now: datetime, default_previous: bool = False) -> tuple[str, date, date]:
    month = args.month or (previous_month(now.date()) if default_previous else now.strftime("%Y-%m"))
    first, last = parse_month(month)
    if first > now.date():
        raise ToolError(f"{month} hasn't started yet.")
    return month, first, last


def cmd_grid(mem: Memory, args, now: datetime) -> dict:
    month, first, last = month_of(args, now)
    j = Journal(mem, now.tzinfo, now.date(), as_of=min(last, now.date()))
    return {"ok": True, "month": month, **j.grid(first, last, args.lang)}


def stats_for(mem: Memory, now: datetime, month: str, first: date, last: date) -> dict:
    j = Journal(mem, now.tzinfo, now.date(), as_of=min(last, now.date()))
    trackers = [s for t in j.ordered(include_retired=True) if (s := j.month_stats(t, first, last))]
    p_month = previous_month(first)
    pf, pl = parse_month(p_month)
    pj = Journal(mem, now.tzinfo, now.date(), as_of=pl)
    before = {t["key"]: s.get("compliance_percent") for t in pj.ordered(include_retired=True)
              if (s := pj.month_stats(t, pf, pl))}
    for s in trackers:
        if s["tracker"] in before:
            s["previous_month_compliance_percent"] = before[s["tracker"]]
    return {"journal": j, "month": month, "complete": last < now.date(), "trackers": trackers,
            "writing": j.writing(first, last), "coincidences": j.coincidences(first, last),
            "coincidences_note": f"averages on days one tracker was done vs not done, with at least {MIN_SIDE} days "
                                 "on each side; they are coincidences in the record, not causes"}


def cmd_stats(mem: Memory, args, now: datetime) -> dict:
    month, first, last = month_of(args, now)
    s = stats_for(mem, now, month, first, last)
    s.pop("journal")
    return {"ok": True, **s}


def cmd_reflect(mem: Memory, args, now: datetime) -> dict:
    month, first, last = month_of(args, now, default_previous=True)
    if args.save:
        fields = {"went_well": text_field(args.went_well, "--went-well"),
                  "went_wrong": text_field(args.went_wrong, "--went-wrong"),
                  "intention": text_field(args.intention, "--intention")}
        if not any(fields.values()):
            raise ToolError("--save needs at least one of --went-well, --went-wrong, --intention.")
        j = Journal(mem, now.tzinfo, now.date())
        prev = j.reflections.get(month)
        key = f"REFLECT_{month.replace('-', '')}"
        if prev:
            mem.run("void", "--event", prev["key"], "--reason", args.source or "Reflection rewritten", "--by", args.by)
            key += f"_r{now.strftime('%Y%m%d%H%M%S')}"
        mem.write(args.by, args.source or f"Reflection of {month}", events=[{
            "key": key, "type": "month_reflected", "occurred_at": now.isoformat(timespec="seconds"),
            "summary": f"Reflection of {month}",
            "attributes": {"reflect_month": month, **{k: v for k, v in fields.items() if v}}}])
        return {"ok": True, "month": month, "saved": True, "rewritten": bool(prev)}
    s = stats_for(mem, now, month, first, last)
    j: Journal = s.pop("journal")
    return {"ok": True, **s, "grid": j.grid(first, last, args.lang),
            "previous_reflection": j.reflections.get(previous_month(first)),
            "already_reflected": j.reflections.get(month),
            "trackers_now": [tracker_view(j, t) for t in Journal(mem, now.tzinfo, now.date()).ordered()]}


def cmd_brief(mem: Memory, args, now: datetime) -> dict:
    try:
        j = Journal(mem, now.tzinfo, now.date())
    except ToolError as error:
        if error.code != MEMORY_ERROR:
            raise
        return {"ok": True, "today": now.date().isoformat(), "setup_needed": True,
                "message": "No memory or no bitacora settings here yet: start the memory, then TOOL setup."}
    if not j.trackers:
        return {"ok": True, "today": now.date().isoformat(), "empty": True}
    p_month = previous_month(now.date())
    pf, pl = parse_month(p_month)
    existed = any(t["since"] and t["since"] <= pl and (not t["until"] or t["until"] > pf) for t in j.trackers.values())
    written = j.written()
    last = max(written, default=None)
    return {"ok": True, "today": now.date().isoformat(), "weekday": WEEKDAY_NAMES[now.weekday()],
            "trackers": [{"name": t["name"], "goal": goal_text(t),
                          "today": show(t, j.records.get(t["key"], {}).get(now.date(), {}).get("value")),
                          "streak": j.streak(t)} for t in j.ordered()],
            "last_written": last.isoformat() if last else None,
            "reflection_due": p_month if existed and p_month not in j.reflections else None}


# -- CLI ------------------------------------------------------------------------------------
def main() -> None:
    p = argparse.ArgumentParser(prog="bitacora.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--version", action="version", version=f"bitacora.py {__version__}")
    p.add_argument("--mem", help="Path to project-memory's memory.py")
    p.add_argument("--db", help="Path to the memory (default: the current project's)")
    p.add_argument("--tz", default=os.environ.get("HOWWARE_TZ") or local_offset(), help="UTC offset, e.g. --tz=-06:00")
    p.add_argument("--now", default=os.environ.get("BITACORA_NOW"), help=argparse.SUPPRESS)  # fixed clock for tests
    sub = p.add_subparsers(dest="command", required=True)

    def cmd(name: str, by: bool = True, source: bool = True):
        s = sub.add_parser(name)
        if by:
            s.add_argument("--by", required=True, help="person:<id> of the owner")
        if source:
            s.add_argument("--source", help="The owner's literal words")
        return s

    cmd("setup", source=False)
    cmd("now", by=False, source=False)
    s = cmd("tracker")
    s.add_argument("--key", required=True, help="tracker:<slug> or a short name")
    s.add_argument("--name")
    s.add_argument("--kind", help=" | ".join(KINDS))
    s.add_argument("--unit", help="for quantity: the whole unit values are stored in (minute, glass, ml...)")
    s.add_argument("--target", help="at_least:N | at_most:N | yes | none")
    s.add_argument("--every", help="day | week:N | days:N | none")
    s.add_argument("--why", help="why the owner tracks it, in their words")
    s.add_argument("--state", help=" | ".join(STATES))
    s = cmd("trackers", by=False, source=False)
    s.add_argument("--all", action="store_true", help="include retired trackers")
    s = cmd("log")
    s.add_argument("--date", help="YYYY-MM-DD (today by default)")
    s.add_argument("--entry", required=True, action="append", help="tracker=value, repeatable")
    s.add_argument("--correct", action="store_true", help="replace a different record of the same day")
    s = cmd("unlog", source=False)
    s.add_argument("--tracker", required=True)
    s.add_argument("--date", required=True)
    s.add_argument("--reason", required=True, help="why, in the owner's words")
    s = cmd("day", by=False, source=False)
    s.add_argument("--date", help="YYYY-MM-DD (today by default)")
    for name in ("grid", "stats"):
        s = cmd(name, by=False, source=False)
        s.add_argument("--month", help="YYYY-MM (this month by default)")
        if name == "grid":
            s.add_argument("--lang", default="en", help="en | es: weekday initials of the grid")
    s = cmd("reflect", by=False)
    s.add_argument("--lang", default="en", help="en | es: weekday initials of the grid")
    s.add_argument("--by", help="person:<id> of the owner (needed with --save)")
    s.add_argument("--month", help="YYYY-MM (last month by default)")
    s.add_argument("--save", action="store_true", help="store the owner's answers")
    s.add_argument("--went-well")
    s.add_argument("--went-wrong")
    s.add_argument("--intention")
    cmd("brief", by=False, source=False)
    args = p.parse_args()

    commands = {"setup": cmd_setup, "now": cmd_now, "tracker": cmd_tracker, "trackers": cmd_trackers, "log": cmd_log,
                "unlog": cmd_unlog, "day": cmd_day, "grid": cmd_grid, "stats": cmd_stats, "reflect": cmd_reflect,
                "brief": cmd_brief}
    try:
        tz = parse_offset(args.tz)
        if args.now:
            try:
                now = datetime.fromisoformat(args.now).replace(tzinfo=tz)
            except ValueError:
                raise ToolError(f"--now must be YYYY-MM-DDTHH:MM, not {args.now!r}") from None
        else:
            now = datetime.now(tz).replace(microsecond=0)
        if args.command == "reflect" and args.save and not args.by:
            raise ToolError("reflect --save needs --by.")
        if args.command == "now":
            result, code = cmd_now(None, args, now), OK
        else:
            mem = Memory(find_helper(args.mem), args.db)
            mem.check_version()
            result, code = commands[args.command](mem, args, now), OK
    except ToolError as error:
        result, code = {"ok": False, "error": {"code": error.code, "message": str(error)}}, error.code
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(code)


if __name__ == "__main__":
    main()
