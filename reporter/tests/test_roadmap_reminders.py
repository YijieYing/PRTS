"""Roadmap reminder synchronization uses replaceable external boundaries."""
import importlib.machinery, importlib.util, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch

BIN = Path(__file__).resolve().parents[1] / "bin" / "todo"
spec = importlib.util.spec_from_loader("todo_bin", importlib.machinery.SourceFileLoader("todo_bin", str(BIN)))
todo = importlib.util.module_from_spec(spec); spec.loader.exec_module(todo)

class RoadmapReminders(unittest.TestCase):
    def rule(self):
        return [{"project":"Outreach", "map":"outreach-reminders.jsonl", "time":"14:00",
                 "skip_kinds":["检查"], "conditional":"仅当", "before":["python3","build.py"]}]

    def test_first_build_skips_non_action_items(self):
        def fake_osa(script, *args):
            return "" if script is todo.GET_ITEMS else "new-id"
        with tempfile.TemporaryDirectory() as d, patch.object(todo, "STATE", Path(d)), \
             patch.object(todo, "osa", side_effect=fake_osa), \
             patch.object(todo, "roadmap_items", return_value=[
                 {"id":"S01","title":"提交申请","status":"","ddl":"2026-12-01","kind":"提交"},
                 {"id":"S02","title":"检查材料","status":"","ddl":"2026-12-01","kind":"检查"},
                 {"id":"S03","title":"仅当有名额","status":"","ddl":"2026-12-01","kind":"准备"},
                 {"id":"S04","title":"无日期","status":"","ddl":"","kind":"准备"},
             ]):
            # The initial batch read is empty; build is allowed to fail and sync continues.
            todo.sync_locked(self.rule(), False, False, "2026-11-23", Path(d)/"day")
            rows=(Path(d)/"outreach-reminders.jsonl").read_text().splitlines()
            self.assertEqual(len(rows), 1); self.assertEqual(json.loads(rows[0])["id"], "S01")

    def test_dry_run_does_not_write_mapping(self):
        with tempfile.TemporaryDirectory() as d, patch.object(todo, "STATE", Path(d)), \
             patch.object(todo, "osa", return_value=""), \
             patch.object(todo, "roadmap_items", return_value=[{"id":"S01","title":"提交","status":"","ddl":"2026-12-01","kind":"提交"}]):
            self.assertEqual(todo.sync_locked(self.rule(), True, False, "2026-11-23", Path(d)/"day"), 0)
            self.assertFalse((Path(d)/"outreach-reminders.jsonl").exists())

    def test_read_failure_does_not_write_mapping(self):
        with tempfile.TemporaryDirectory() as d, patch.object(todo, "STATE", Path(d)), \
             patch.object(todo, "osa", side_effect=RuntimeError("permission")):
            self.assertEqual(todo.sync_locked(self.rule(), False, False, "2026-11-23", Path(d)/"day"), 1)
            self.assertFalse((Path(d)/"outreach-reminders.jsonl").exists())

if __name__ == "__main__": unittest.main()
