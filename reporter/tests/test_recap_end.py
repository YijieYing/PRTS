"""Isolated command-chain fixtures. No production state or delivery channels."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class End(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        shutil.copytree(ROOT/'bin', self.root/'reporter/bin')
        shutil.copytree(ROOT/'lib', self.root/'reporter/lib')
        (self.root/'pulse/bin').mkdir(parents=True)
        self.status = dict(day='2026-11-16', previous='2026-11-15', eligible=True, idle=True)
        self.state = self.root/'state'; self.state.mkdir()
        (self.state/'recap-sent.json').write_text(json.dumps({'2026-11-15': {'sent': True}}))
        self.stub(self.root/'pulse/bin/pulse', '''import json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]
with (root/'calls').open('a') as f: f.write(' '.join(sys.argv[1:])+'\\n')
if sys.argv[1]=='recap-status': print((root/'status').read_text())
elif sys.argv[1]=='day': print('# '+sys.argv[2]+' 回顾\\n总计\\n'+'全文内容'*2000)
elif sys.argv[1]=='now': print('{"quiet":true}')
''')
        self.stub(self.root/'reporter/bin/notify', '''import json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]
with (root/'sent').open('a') as f: f.write(json.dumps(sys.argv[1:])+'\\n')
''')
        self.stub(self.root/'reporter/bin/ask', '''import sys
assert sys.argv[1]!='due', 'quiet must not deliver questions'
''')

    def stub(self, path, body):
        path.write_text('#!/usr/bin/env python3\n'+body); path.chmod(0o755)

    def run_entry(self, *args, entry='recap'):
        (self.root/'status').write_text(json.dumps(self.status))
        result = subprocess.run([str(self.root/'reporter/bin'/entry), *args],
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=20,
            env=dict(os.environ, PRTS_REPORTER_STATE=str(self.state)))
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def sent(self):
        path = self.root/'sent'
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def test_active_or_too_early(self):
        for key in ('idle', 'eligible'):
            self.status[key] = False
            self.run_entry('--auto')
            self.assertEqual(self.sent(), [])
            self.status[key] = True

    def test_idle_and_idempotent_then_manual(self):
        self.run_entry('--auto'); self.run_entry('--auto')
        self.assertEqual(len(self.sent()), 2)
        self.assertIn('2026-11-16 回顾', self.sent()[0])
        self.assertGreater(len(self.sent()[0][-1]), 4000)
        self.run_entry('2026-11-16')
        self.assertEqual(len(self.sent()), 4)

    def test_partial_failure_retries_only_failed_channel(self):
        self.stub(self.root/'reporter/bin/notify', """import json,sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]
with (root/'sent').open('a') as f: f.write(json.dumps(sys.argv[1:])+'\\n')
if sys.argv[1]=='note' and not (root/'failed').exists():
    (root/'failed').touch(); sys.exit(1)
""")
        self.run_entry('--auto'); self.run_entry('--auto'); self.run_entry('--auto')
        self.assertEqual([call[0] for call in self.sent()], ['note', 'alert', 'note'])

    def test_fallback(self):
        self.status.update(day='2026-11-17', previous='2026-11-16', eligible=False, idle=False)
        self.run_entry('--auto')
        self.assertIn('2026-11-16 回顾', self.sent()[0])

    def test_dry_read_only(self):
        before = (self.state/'recap-sent.json').read_bytes()
        result = self.run_entry('--dry', '2026-11-16')
        self.assertGreater(len(result.stdout), 4000)
        self.assertEqual(self.sent(), [])
        self.assertEqual((self.root/'calls').read_text(), 'day 2026-11-16 --dry\n')
        self.assertEqual((self.state/'recap-sent.json').read_bytes(), before)

    def test_quiet_remind_delivers_recap_only(self):
        self.run_entry(entry='remind')
        self.assertEqual(len(self.sent()), 2)
        commands = (self.root/'calls').read_text().splitlines()
        self.assertEqual(commands[0], 'ear sync --no-notify')
        self.assertEqual(commands.count('ear sync --no-notify'), 1)
