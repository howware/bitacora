"""Tests of the tool against a real, temporary memory. Synthetic data only.

The memory helper is found in HOWWARE_MEMORY_HELPER or in the installed project-memory skill. The clock is fixed
with BITACORA_NOW so dates, streaks and months are reproducible.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "skill" / "bitacora" / "scripts" / "bitacora.py"
BY = "person:test"


def find_helper() -> Path | None:
    for c in (os.environ.get("HOWWARE_MEMORY_HELPER"), Path.home() / ".claude/skills/project-memory/scripts/memory.py",
              ROOT.parent / "long-term-memory-for-AI" / "db" / "memory.py"):
        if c and Path(c).is_file():
            return Path(c)
    return None


HELPER = find_helper()


def run(*args: str, now: str = "2026-09-01T09:00", db: str | None = None, code: int = 0, test=None) -> dict:
    env = {**os.environ, "BITACORA_NOW": now, "PYTHONIOENCODING": "utf-8"}
    cmd = [sys.executable, str(TOOL)] + (["--mem", str(HELPER), "--db", db] if db else []) + ["--tz=-06:00", *args]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env=env)
    test.assertEqual(proc.returncode, code, proc.stdout + proc.stderr)
    return json.loads(proc.stdout)


@unittest.skipUnless(HELPER, "project-memory is not installed")
class ToolTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "memory.sqlite")
        subprocess.run([sys.executable, str(HELPER), "--db", self.db, "init", "--owner-name", "Test",
                        "--owner-key", BY], check=True, capture_output=True)
        self.assertTrue(self.tool("setup", "--by", BY)["ok"])

    def tearDown(self):
        self.tmp.cleanup()

    def tool(self, *args: str, now: str = "2026-09-01T09:00", code: int = 0) -> dict:
        return run(*args, now=now, db=self.db, code=code, test=self)

    def trackers(self):
        self.tool("tracker", "--key", "sleep", "--name", "Sleep", "--kind", "quantity", "--unit", "minute",
                  "--target", "at_least:420", "--by", BY, "--source", "dormir 7 horas o más")
        self.tool("tracker", "--key", "gym", "--name", "Gym", "--kind", "yesno", "--every", "week:3", "--by", BY)
        self.tool("tracker", "--key", "water", "--name", "Plants", "--kind", "yesno", "--every", "days:3", "--by", BY)
        self.tool("tracker", "--key", "mood", "--name", "Mood", "--kind", "scale", "--by", BY)

    def log(self, day: str, *entries: str, now: str | None = None, code: int = 0) -> dict:
        args = ["log", "--date", day, "--by", BY]
        for e in entries:
            args += ["--entry", e]
        return self.tool(*args, now=now or f"{day}T21:00", code=code)

    # -- brief and setup ---------------------------------------------------------------
    def test_brief_without_trackers(self):
        self.assertTrue(self.tool("brief")["empty"])

    def test_brief_without_memory_says_setup(self):
        other = str(Path(self.tmp.name) / "none.sqlite")
        self.assertTrue(run("brief", db=other, test=self)["setup_needed"])

    # -- trackers ------------------------------------------------------------------------
    def test_tracker_goal_text_and_refusals(self):
        self.trackers()
        names = {t["name"]: t for t in self.tool("trackers")["trackers"]}
        self.assertEqual(names["Sleep"]["goal"], "at least 7 h 00 min, every day")
        self.assertEqual(names["Gym"]["goal"], "done, 3 days a week")
        self.assertEqual(names["Plants"]["goal"], "done, at least every 3 days")
        self.assertIsNone(names["Mood"]["goal"])
        self.tool("tracker", "--key", "steps", "--name", "Steps", "--kind", "quantity", "--by", BY, code=2)
        self.tool("tracker", "--key", "x", "--name", "X", "--kind", "scale", "--target", "at_least:9", "--by", BY,
                  code=2)
        self.tool("tracker", "--key", "y", "--name", "Y", "--kind", "yesno", "--target", "at_least:2", "--by", BY,
                  code=2)
        self.tool("tracker", "--key", "z", "--name", "Z", "--kind", "yesno", "--every", "week:9", "--by", BY, code=2)

    def test_kind_and_unit_are_locked_once_there_are_records(self):
        self.trackers()
        self.log("2026-09-01", "sleep=400")
        self.tool("tracker", "--key", "sleep", "--kind", "scale", "--by", BY, code=2)
        self.tool("tracker", "--key", "sleep", "--unit", "hour", "--by", BY, code=2)
        changed = self.tool("tracker", "--key", "sleep", "--target", "at_least:450", "--by", BY)
        self.assertEqual(changed["target_value"], 450)
        cleared = self.tool("tracker", "--key", "sleep", "--target", "none", "--by", BY)
        self.assertIsNone(cleared["goal"])

    def test_retired_tracker_keeps_history_and_refuses_records(self):
        self.trackers()
        self.log("2026-09-01", "gym=yes")
        retired = self.tool("tracker", "--key", "gym", "--state", "retired", "--by", BY, now="2026-09-03T09:00")
        self.assertEqual(retired["state"], "retired")
        self.log("2026-09-03", "gym=yes", code=2)
        self.assertNotIn("Gym", [t["name"] for t in self.tool("trackers")["trackers"]])
        self.assertIn("Gym", [t["name"] for t in self.tool("trackers", "--all")["trackers"]])
        self.assertEqual(self.tool("day", "--date", "2026-09-01")["entries"][1]["value"], "yes")

    # -- log -----------------------------------------------------------------------------
    def test_log_is_idempotent_and_corrections_are_explicit(self):
        self.trackers()
        first = self.log("2026-09-01", "sleep=390", "gym=sí", "mood=4")
        self.assertEqual([e["value"] for e in first["entries"]], ["6 h 30 min", "yes", "4/5"])
        self.assertFalse(first["entries"][0]["done"])
        again = self.log("2026-09-01", "sleep=390")
        self.assertTrue(again["entries"][0]["unchanged"])
        conflict = self.log("2026-09-01", "sleep=450")
        self.assertEqual(conflict["conflicts"], 1)
        self.assertEqual(self.tool("day", "--date", "2026-09-01")["entries"][0]["value"], "6 h 30 min")
        fixed = self.tool("log", "--date", "2026-09-01", "--entry", "sleep=450", "--correct", "--by", BY,
                          now="2026-09-01T22:00")
        self.assertTrue(fixed["entries"][0]["corrected"])
        self.assertTrue(fixed["entries"][0]["done"])
        self.assertEqual(self.tool("day", "--date", "2026-09-01")["entries"][0]["value"], "7 h 30 min")

    def test_log_refuses_bad_values_and_dates(self):
        self.trackers()
        self.log("2026-09-02", "sleep=6.5", code=2)          # 6.5 what? hours must say h
        self.log("2026-09-02", "sleep=6.51h", code=2)        # not whole minutes
        self.log("2026-09-02", "sleep=2000", code=2)         # more than a day
        self.log("2026-09-02", "mood=7", code=2)
        self.log("2026-09-02", "gym=maybe", code=2)
        self.log("2026-09-02", "nothing=1", code=2)
        self.log("2026-09-02", "gym=yes", "gym=no", code=2)
        self.log("2026-09-05", "gym=yes", now="2026-09-02T10:00", code=2)   # future
        self.log("2026-08-30", "gym=yes", now="2026-09-02T10:00", code=2)   # before the tracker existed

    def test_minutes_take_hours(self):
        self.trackers()
        self.assertEqual(self.log("2026-09-01", "sleep=6:30")["entries"][0]["value"], "6 h 30 min")
        self.assertEqual(self.log("2026-09-02", "sleep=7.25h")["entries"][0]["value"], "7 h 15 min")
        self.log("2026-09-03", "sleep=6:75", code=2)

    def test_unlog_voids_the_record(self):
        self.trackers()
        self.log("2026-09-01", "gym=yes")
        self.tool("unlog", "--tracker", "Gym", "--date", "2026-09-01", "--reason", "fue otro día", "--by", BY)
        self.assertEqual(self.tool("day", "--date", "2026-09-01")["missing"], ["Sleep", "Gym", "Plants", "Mood"])
        self.tool("unlog", "--tracker", "gym", "--date", "2026-09-01", "--reason", "x", "--by", BY, code=2)

    # -- streaks and stats ---------------------------------------------------------------
    def test_daily_streak_today_does_not_break_it(self):
        self.trackers()
        for day, minutes in (("2026-09-01", 300), ("2026-09-02", 430), ("2026-09-03", 440), ("2026-09-04", 425)):
            self.log(day, f"sleep={minutes}")
        trackers = self.tool("trackers", now="2026-09-05T08:00")["trackers"]
        self.assertEqual(trackers[0]["streak"], {"unit": "days", "current": 3, "best": 3})
        trackers = self.tool("trackers", now="2026-09-06T08:00")["trackers"]   # 09-05 had no record: broken
        self.assertEqual(trackers[0]["streak"]["current"], 0)

    def test_weekly_goal_compliance(self):
        self.trackers()
        # Week of 09-07: 3 gym days (met). Week of 09-14: 2 (not met). 09-01 is a Tuesday: its week began before
        # the tracker existed and doesn't count.
        for day in ("2026-09-02", "2026-09-07", "2026-09-09", "2026-09-11", "2026-09-15", "2026-09-17"):
            self.log(day, "gym=yes")
        self.log("2026-09-16", "gym=no")
        stats = self.tool("stats", "--month", "2026-09", now="2026-10-01T09:00")
        gym = next(t for t in stats["trackers"] if t["name"] == "Gym")
        self.assertEqual([(w["week_of"], w["done"], w["met"]) for w in gym["weeks"]],
                         [("2026-09-07", 3, True), ("2026-09-14", 2, False), ("2026-09-21", 0, False)])
        self.assertEqual(gym["compliance_percent"], 33)
        self.assertEqual(gym["done_days"], 6)
        self.assertEqual(gym["not_done_days"], 1)

    def test_every_n_days_gaps_and_next(self):
        self.trackers()
        for day in ("2026-09-01", "2026-09-04", "2026-09-10", "2026-09-12"):
            self.log(day, "water=yes")
        stats = self.tool("stats", "--month", "2026-09", now="2026-09-13T09:00")
        plants = next(t for t in stats["trackers"] if t["name"] == "Plants")
        self.assertEqual(plants["longest_gap_days"], 6)
        self.assertEqual(plants["gaps_over_goal"], 1)
        self.assertEqual(plants["compliance_percent"], 67)
        self.assertEqual(plants["streak"]["current"], 2)
        self.assertEqual(plants["streak"]["next_by"], "2026-09-15")

    def test_daily_compliance_ignores_days_without_data(self):
        self.trackers()
        self.log("2026-09-01", "sleep=430", "mood=2")
        self.log("2026-09-02", "sleep=300", "mood=4")
        stats = self.tool("stats", "--month", "2026-09", now="2026-09-04T09:00")
        sleep, mood = stats["trackers"][0], stats["trackers"][3]
        self.assertEqual((sleep["days"], sleep["logged"], sleep["no_data"]), (4, 2, 2))
        self.assertEqual(sleep["compliance_percent"], 50)
        self.assertEqual(sleep["average"], "6 h 05 min")
        self.assertEqual(mood["average"], "3.0/5")
        self.assertNotIn("compliance_percent", mood)

    def test_writing_counts_days_written_later(self):
        self.trackers()
        self.log("2026-09-01", "mood=3")
        self.log("2026-09-02", "mood=3", now="2026-09-04T09:00")
        writing = self.tool("stats", "--month", "2026-09", now="2026-09-04T10:00")["writing"]
        self.assertEqual((writing["days"], writing["written"], writing["on_the_day"], writing["filled_in_later"],
                          writing["not_written"]), (4, 2, 1, 1, 2))

    def test_coincidences_need_days_on_both_sides(self):
        self.trackers()
        for i in range(1, 9):
            self.log(f"2026-09-{i:02d}", f"gym={'yes' if i % 2 else 'no'}", f"mood={5 if i % 2 else 2}")
        found = self.tool("stats", "--month", "2026-09", now="2026-09-09T09:00")["coincidences"]
        self.assertEqual(found[0]["when"], "Gym")
        self.assertEqual(found[0]["measure"], "Mood")
        self.assertEqual(found[0]["difference"], "+3.0/5")
        self.assertEqual((found[0]["days_done"], found[0]["days_not"]), (4, 4))
        self.tool("unlog", "--tracker", "gym", "--date", "2026-09-08", "--reason", "x", "--by", BY,
                  now="2026-09-09T09:00")
        self.assertEqual(self.tool("stats", "--month", "2026-09", now="2026-09-09T09:00")["coincidences"], [])

    def test_grid(self):
        self.trackers()
        self.log("2026-09-01", "sleep=430", "gym=yes", "mood=4")
        self.log("2026-09-02", "sleep=300", "gym=no")
        self.log("2026-09-03", "mood=2", now="2026-09-05T09:00")
        grid = self.tool("grid", "--month", "2026-09", now="2026-09-05T09:00")["text"].splitlines()
        self.assertEqual(grid[0].split()[0][:5], "12345")
        rows = {line.split()[0]: line[len(grid[2]) - 30:] for line in grid[2:]}
        self.assertEqual(rows["Sleep"][:6], "●○···" + " ")
        self.assertEqual(rows["Gym"][:5], "●○···")
        self.assertEqual(rows["Mood"][:5], "4·2··")
        self.assertEqual(rows["written"][:6], "●●◐·· ")

    # -- reflection --------------------------------------------------------------------
    def test_reflection_due_save_and_rewrite(self):
        self.trackers()
        self.log("2026-09-10", "gym=yes")
        self.assertIsNone(self.tool("brief", now="2026-09-20T09:00")["reflection_due"])
        self.assertEqual(self.tool("brief", now="2026-10-01T09:00")["reflection_due"], "2026-09")
        data = self.tool("reflect", now="2026-10-01T09:00")
        self.assertEqual(data["month"], "2026-09")
        self.assertTrue(data["complete"])
        self.assertIn("text", data["grid"])
        self.tool("reflect", "--save", "--by", BY, now="2026-10-01T09:00", code=2)          # nothing to save
        self.tool("reflect", "--save", "--went-well", "x", now="2026-10-01T09:00", code=2)  # no --by
        saved = self.tool("reflect", "--save", "--went-well", "constancia", "--intention", "regar más", "--by", BY,
                          now="2026-10-01T09:00")
        self.assertFalse(saved["rewritten"])
        self.assertIsNone(self.tool("brief", now="2026-10-01T09:05")["reflection_due"])
        again = self.tool("reflect", "--save", "--intention", "regar cada 3 días", "--by", BY, now="2026-10-01T10:00")
        self.assertTrue(again["rewritten"])
        october = self.tool("reflect", "--month", "2026-10", now="2026-10-02T09:00")
        self.assertEqual(october["previous_reflection"]["intention"], "regar cada 3 días")
        self.assertIsNone(october["previous_reflection"]["went_well"])


class ContractTest(unittest.TestCase):
    def test_version(self):
        out = subprocess.run([sys.executable, str(TOOL), "--version"], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0)
        self.assertIn(".py ", out.stdout)

    def test_now_needs_no_memory(self):
        now = run("now", now="2026-10-12T08:30", test=self)
        self.assertEqual((now["today"], now["weekday"], now["month"], now["yesterday"]),
                         ("2026-10-12", "monday", "2026-10", "2026-10-11"))

    def test_bad_month(self):
        if HELPER:
            with tempfile.TemporaryDirectory() as tmp:
                db = str(Path(tmp) / "m.sqlite")
                subprocess.run([sys.executable, str(HELPER), "--db", db, "init", "--owner-name", "T",
                                "--owner-key", BY], check=True, capture_output=True)
                run("setup", "--by", BY, db=db, test=self)
                run("stats", "--month", "2026-13", db=db, code=2, test=self)
                run("stats", "--month", "2027-01", db=db, code=2, test=self)


if __name__ == "__main__":
    unittest.main()
