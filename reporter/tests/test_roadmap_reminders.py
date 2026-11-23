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

    def run_sync(self, items, reminders, mapping):
        calls, marks = [], []
        def fake_osa(script, *args):
            calls.append((script, args))
            if script is todo.GET_ITEMS:
                return "".join(f"{r['id']}\t{r['title']}\t{r['due']}\t{str(r['done']).lower()}\n" for r in reminders)
            return "new-id"
        with tempfile.TemporaryDirectory() as d, patch.object(todo, "STATE", Path(d)), \
             patch.object(todo, "osa", side_effect=fake_osa), \
             patch.object(todo, "roadmap_items", return_value=items), \
             patch.object(todo, "roadmap_mark", side_effect=lambda p, i, s: marks.append((i, s))), \
             patch.object(todo.subprocess, "run", return_value=type("R", (), {"returncode": 0})()):
            (Path(d)/"outreach-reminders.jsonl").write_text("".join(json.dumps(m)+"\n" for m in mapping))
            todo.sync_locked(self.rule(), False, False, "2026-11-23", Path(d)/"day")
            saved = [json.loads(x) for x in (Path(d)/"outreach-reminders.jsonl").read_text().splitlines()]
        return [(c[0], c[1]) for c in calls if c[0] is not todo.GET_ITEMS], marks, saved

    def test_existing_reminders_follow_the_table(self):
        items = [{"id":"S01","title":"新文字","status":"💤","ddl":"2026-12-05","kind":"提交"},
                 {"id":"S02","title":"发邮件（仅当 S32 没有课题）","status":"💤","ddl":"2026-12-01","kind":"提交"},
                 {"id":"S03","title":"做完了","status":"✅","ddl":"2026-12-01","kind":"提交"},
                 {"id":"S04","title":"手机勾了","status":"💤","ddl":"2026-12-01","kind":"提交"},
                 {"id":"S05","title":"被删了","status":"💤","ddl":"2026-12-01","kind":"提交"}]
        reminders = [dict(id="r1", title="[S01] 旧文字", due="2026-12-01T14:00:00", done=False),
                     dict(id="r2", title="[S02] 发邮件", due="2026-12-01T14:00:00", done=False),
                     dict(id="r3", title="[S03] 做完了", due="2026-12-01T14:00:00", done=False),
                     dict(id="r4", title="[S04] 手机勾了", due="2026-12-01T14:00:00", done=True)]
        mapping = [dict(id=f"S0{i}", reminder=f"r{i}") for i in range(1, 6)]
        writes, marks, saved = self.run_sync(items, reminders, mapping)
        self.assertIn((todo.UPDATE, ("r1", "[S01] 新文字", "2026-12-05T14:00")), writes)
        self.assertIn((todo.UPDATE, ("r2", "[S02] 发邮件（仅当 S32 没有课题）", "2026-12-01T14:00")), writes)   # conditional: kept up to date
        self.assertIn((todo.DONE, ("r3",)), writes)
        self.assertEqual(marks, [("S04", "✅")])
        self.assertNotIn(todo.ADD, [w[0] for w in writes])                                             # S05 deleted on the phone: not rebuilt
        self.assertTrue(next(m for m in saved if m["id"] == "S05").get("deleted"))

if __name__ == "__main__": unittest.main()
