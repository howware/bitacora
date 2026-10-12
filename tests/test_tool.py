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

    def test_a_voided_day_can_be_recorded_again(self):
        self.trackers()
        for value in ("yes", "no"):
            self.log("2026-09-01", "gym=yes")
            self.tool("unlog", "--tracker", "gym", "--date", "2026-09-01", "--reason", "x", "--by", BY,
                      now="2026-09-01T21:00")
            self.log("2026-09-01", f"gym={value}")
            self.assertEqual(self.tool("day", "--date", "2026-09-01")["entries"][1]["value"], value)
            self.tool("unlog", "--tracker", "gym", "--date", "2026-09-01", "--reason", "x", "--by", BY,
                      now="2026-09-01T21:00")

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

    # -- notes (0.2) -----------------------------------------------------------------------
    def note(self, day: str, kind: str, text: str, now: str | None = None, code: int = 0) -> dict:
        return self.tool("note", "--date", day, "--type", kind, "--text", text, "--by", BY,
                         now=now or f"{day}T21:00", code=code)

    def test_setup_creates_default_note_types_once(self):
        types = self.tool("note-types")["note_types"]
        self.assertEqual([(t["symbol"], t["key"]) for t in types],
                         [("–", "note_type:note"), ("○", "note_type:event"), ("!", "note_type:idea"),
                          ("*", "note_type:important"), ("•", "note_type:task")])
        self.tool("note-type", "--key", "idea", "--name", "Ocurrencia", "--symbol", "¡", "--by", BY)
        self.assertEqual(self.tool("setup", "--by", BY)["note_types_created"], [])
        idea = next(t for t in self.tool("note-types")["note_types"] if t["key"] == "note_type:idea")
        self.assertEqual((idea["name"], idea["symbol"]), ("Ocurrencia", "¡"))

    def test_note_types_are_the_owners(self):
        made = self.tool("note-type", "--key", "gratitude", "--name", "Gratitud", "--symbol", "♡",
                         "--purpose", "algo por lo que estoy agradecido", "--by", BY)
        self.assertTrue(made["created"])
        self.tool("note-type", "--key", "x", "--name", "X", "--symbol", "♡", "--purpose", "p", "--by", BY, code=2)
        self.tool("note-type", "--key", "y", "--name", "Y", "--by", BY, code=2)        # symbol and purpose needed
        self.tool("note-type", "--key", "task", "--state", "retired", "--by", BY)
        self.note("2026-09-01", "task", "llamar al plomero", code=2)
        self.assertEqual(self.note("2026-09-01", "♡", "la comida con mi mamá")["notes"][0]["type"], "Gratitud")

    def test_notes_idempotent_search_retype_and_unnote(self):
        first = self.note("2026-09-01", "event", "Fue la boda de mi primo en Guanajuato")["notes"][0]
        self.assertTrue(first["created"])
        again = self.note("2026-09-01", "note", "fue la boda de mi  primo en guanajuato")["notes"][0]
        self.assertTrue(again["unchanged"])
        self.assertIn("retype", again["message"])
        self.note("2026-09-02", "idea", "Un jardín vertical")
        found = self.tool("notes", "--search", "JARDIN vertical")
        self.assertEqual((found["total"], found["notes"][0]["symbol"]), (1, "!"))
        self.assertEqual(self.tool("notes", "--type", "○")["total"], 1)
        self.assertEqual(self.tool("notes", "--month", "2026-09")["total"], 2)
        moved = self.tool("retype", "--key", first["key"], "--type", "important", "--by", BY)
        self.assertEqual(moved["symbol"], "*")
        self.assertEqual(self.tool("notes", "--date", "2026-09-01")["notes"][0]["type"], "Important")
        gone = self.tool("unnote", "--key", moved["key"], "--reason", "me equivoqué", "--by", BY)
        self.assertIn("stays in the memory file", gone["note"])
        self.assertEqual(self.tool("notes", "--date", "2026-09-01")["total"], 0)
        self.tool("unnote", "--key", moved["key"], "--reason", "x", "--by", BY, code=2)

    def test_a_removed_or_retyped_note_said_again(self):
        key = self.note("2026-09-01", "note", "hola")["notes"][0]["key"]
        self.tool("unnote", "--key", key, "--reason", "x", "--by", BY)
        again = self.note("2026-09-01", "note", "Hola")["notes"][0]
        self.assertTrue(again["created"])
        self.assertNotEqual(again["key"], key)
        self.assertEqual(self.tool("notes", "--date", "2026-09-01")["total"], 1)
        self.tool("retype", "--key", again["key"], "--type", "idea", "--by", BY)
        third = self.note("2026-09-01", "note", "hola")["notes"][0]
        self.assertTrue(third["unchanged"])
        self.assertEqual(third["type"], "Idea")
        self.assertEqual(self.tool("notes", "--date", "2026-09-01")["total"], 1)

    def test_notes_refusals_and_bulk(self):
        self.note("2026-09-05", "note", "x", now="2026-09-02T09:00", code=2)     # future
        self.note("2026-09-01", "nothing", "x", code=2)
        self.note("2026-09-01", "note", "   ", code=2)
        self.note("2026-09-01", "note", "a" * 4001, code=2)
        path = Path(self.tmp.name) / "notes.json"
        path.write_text(json.dumps([{"type": "event", "text": "Viaje a Oaxaca"}, {"type": "idea", "text": "Huerto"},
                                    {"type": "event", "text": "Viaje a Oaxaca"}], ensure_ascii=False), encoding="utf-8")
        bulk = self.tool("note", "--date", "2026-09-03", "--file", str(path), "--by", BY, now="2026-09-03T20:00")
        self.assertEqual(len(bulk["notes"]), 2)
        path.write_text('{"type": "idea"}', encoding="utf-8")
        self.tool("note", "--file", str(path), "--by", BY, code=2)

    def test_notes_count_as_writing_and_show_in_the_day(self):
        self.trackers()
        self.note("2026-09-01", "note", "Día tranquilo")
        self.note("2026-09-02", "note", "Llovió", now="2026-09-04T09:00")
        writing = self.tool("stats", "--month", "2026-09", now="2026-09-04T10:00")["writing"]
        self.assertEqual((writing["written"], writing["on_the_day"], writing["filled_in_later"]), (2, 1, 1))
        day = self.tool("day", "--date", "2026-09-01", now="2026-09-04T10:00")
        self.assertEqual(day["notes"][0]["text"], "Día tranquilo")

    # -- collections (0.2) ------------------------------------------------------------------
    def books(self):
        return self.tool("collection", "--key", "books", "--name", "Libros", "--statuses", "por leer, leyendo, leído",
                         "--done", "leído", "--rating", "yes", "--by", BY, "--source", "quiero llevar mis libros")

    def item(self, *args: str, now: str = "2026-09-10T09:00", code: int = 0) -> dict:
        return self.tool("item", "--collection", "books", *args, "--by", BY, now=now, code=code)

    def test_collection_definition_and_refusals(self):
        self.assertEqual(self.books()["statuses"], ["por leer", "leyendo", "leído"])
        self.tool("collection", "--key", "x", "--name", "X", "--statuses", "a", "--done", "a", "--by", BY, code=2)
        self.tool("collection", "--key", "x", "--name", "X", "--statuses", "a, b", "--done", "c", "--by", BY, code=2)
        self.tool("collection", "--key", "x", "--name", "X", "--done", "a", "--by", BY, code=2)
        ideas = self.tool("collection", "--key", "ideas", "--name", "Ideas de negocio", "--by", BY)
        self.assertEqual((ideas["statuses"], ideas["rating"]), ([], False))
        self.item("--title", "Rayuela")
        self.item("--key", "item:books-rayuela", "--status", "leyendo")
        self.tool("collection", "--key", "books", "--statuses", "pendiente, leído", "--done", "leído", "--by", BY,
                  code=2)                                           # Rayuela would be left with a lost status
        names = [c["name"] for c in self.tool("collections")["collections"]]
        self.assertEqual(names, ["Libros", "Ideas de negocio"])
        self.tool("collection", "--key", "books", "--statuses", "none", "--by", BY, code=2)    # Rayuela has one
        self.tool("collection", "--key", "ideas", "--statuses", "a, b", "--done", "b", "--by", BY)
        cleared = self.tool("collection", "--key", "ideas", "--statuses", "none", "--by", BY)
        self.assertEqual((cleared["statuses"], cleared["done_status"]), ([], None))

    def test_items_status_finish_date_rating_and_counts(self):
        self.books()
        added = self.item("--title", "Cien años de soledad")
        self.assertEqual((added["status"], added["added_on"]), ("por leer", "2026-09-10"))
        self.assertTrue(self.item("--title", "cien años de soledad")["unchanged"])
        done = self.item("--title", "Cien años de soledad", "--status", "Leido", "--rating", "5", now="2026-09-20T09:00")
        self.assertEqual((done["status"], done["finished_on"], done["rating"], done["finished"]),
                         ("leído", "2026-09-20", "5/5", True))
        self.item("--title", "Pedro Páramo", "--status", "leído", "--date", "2026-08-30", "--rating", "4")
        self.item("--title", "Rayuela", "--status", "leyendo")
        self.item("--title", "Rayuela", "--date", "2026-09-01", code=2)        # a date only with the finished status
        self.item("--title", "Rayuela", "--rating", "6", code=2)
        self.item("--title", "Rayuela", "--status", "abandonado", code=2)
        self.item("--title", "Ficciones", "--status", "leído", "--date", "2026-09-30", now="2026-09-20T09:00", code=2)
        september = self.tool("items", "--collection", "books", "--month", "2026-09", now="2026-09-21T09:00")
        self.assertEqual([i["title"] for i in september["items"]], ["Cien años de soledad"])
        year = self.tool("items", "--collection", "books", "--year", "2026", now="2026-09-21T09:00")
        self.assertEqual(year["finished_in_period"]["count"], 2)
        self.assertEqual(year["finished_in_period"]["average_rating"], "4.5/5")
        self.assertEqual(year["by_status"], {"por leer": 0, "leyendo": 1, "leído": 2})
        back = self.item("--title", "Cien años de soledad", "--status", "leyendo", now="2026-09-22T09:00")
        self.assertIsNone(back["finished_on"])                         # no longer finished

    def test_removed_items_stop_showing_and_can_come_back(self):
        self.books()
        self.item("--title", "Rayuela")
        self.item("--title", "Rayuela", "--remove", "--reason", "ya no me interesa")
        listing = self.tool("items", "--collection", "books")
        self.assertEqual((listing["shown"], listing["items"]), (0, []))
        self.assertEqual(self.tool("items", "--collection", "books", "--all")["items"][0]["removed"], True)
        self.assertNotIn("removed", self.item("--title", "Rayuela"))
        self.item("--title", "Nada", "--remove", code=2)

    # -- reflection with notes and collections (0.2) -------------------------------------------
    def test_reflection_brings_notes_collections_and_highlights(self):
        self.books()
        self.note("2026-09-03", "event", "Viaje a Oaxaca")
        self.note("2026-09-15", "note", "Terminé el huerto")
        self.item("--title", "Rayuela", "--status", "leído", now="2026-09-12T09:00")
        data = self.tool("reflect", now="2026-10-01T09:00")
        self.assertEqual(data["notes"]["total"], 2)
        self.assertEqual(data["collections"], [{"collection": "Libros", "added": ["Rayuela"], "finished": ["Rayuela"]}])
        self.assertEqual([n["text"] for n in data["month_notes"]], ["Viaje a Oaxaca", "Terminé el huerto"])
        self.assertEqual(self.tool("brief", now="2026-10-01T09:00")["reflection_due"], "2026-09")   # notes count
        self.tool("reflect", "--save", "--highlight", "Viaje a Oaxaca", "--highlight", "El huerto", "--by", BY,
                  now="2026-10-01T09:30")
        october = self.tool("reflect", "--month", "2026-10", now="2026-10-02T09:00")
        self.assertEqual(october["previous_reflection"]["highlights"], ["Viaje a Oaxaca", "El huerto"])

    # -- sharing a memory with todo, and moving a journal (0.2) ---------------------------------
    def test_brief_says_whether_todo_is_here(self):
        self.trackers()
        self.assertFalse(self.tool("brief")["todo_here"])
        subprocess.run([sys.executable, str(HELPER), "--db", self.db, "define-event-type", "--type", "task_captured",
                        "--high-volume", "--by", BY], check=True, capture_output=True)
        self.assertTrue(self.tool("brief")["todo_here"])

    def test_copy_from_another_memory_is_exact_and_idempotent(self):
        self.trackers()
        self.books()
        for i in range(1, 6):
            self.log(f"2026-09-{i:02d}", f"sleep={400 + i * 10}", f"gym={'yes' if i % 2 else 'no'}")
        self.note("2026-09-02", "event", "Viaje a Oaxaca")
        self.note("2026-09-03", "idea", "Huerto", now="2026-09-05T09:00")
        self.item("--title", "Rayuela", "--status", "leído", "--rating", "4")
        self.tool("reflect", "--save", "--month", "2026-09", "--intention", "leer más", "--by", BY,
                  now="2026-10-01T09:00")
        target = str(Path(self.tmp.name) / "shared.sqlite")
        subprocess.run([sys.executable, str(HELPER), "--db", target, "init", "--owner-name", "Test", "--owner-key", BY],
                       check=True, capture_output=True)
        run("setup", "--by", BY, db=target, test=self)
        copied = run("copy-from", "--from-db", self.db, "--by", BY, db=target, now="2026-10-01T10:00", test=self)
        self.assertEqual(copied["copied"], {"tracker": 4, "collection": 1, "item": 1, "tracker_logged": 10,
                                            "note_written": 2, "month_reflected": 1})
        again = run("copy-from", "--from-db", self.db, "--by", BY, db=target, now="2026-10-01T10:05", test=self)
        self.assertEqual(again["copied"], {})
        here = self.tool("stats", "--month", "2026-09", now="2026-10-01T11:00")
        there = run("stats", "--month", "2026-09", db=target, now="2026-10-01T11:00", test=self)
        self.assertEqual(here, there)
        self.assertEqual(run("items", "--collection", "books", db=target, test=self)["items"][0]["rating"], "4/5")
        run("copy-from", "--from-db", str(Path(self.tmp.name) / "nope.sqlite"), "--by", BY, db=target, code=2,
            test=self)
        run("copy-from", "--from-db", target, "--by", BY, db=target, code=2, test=self)


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
