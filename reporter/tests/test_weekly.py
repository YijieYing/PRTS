"""Weekly delivery in a disposable tree; no real agents, mail, Bark or WeChat."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class Weekly(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.reporter = self.root / 'reporter'
        for part in ('bin', 'lib'):
            shutil.copytree(ROOT / 'reporter' / part, self.reporter / part)
        (self.reporter / 'config').mkdir()
        self.config = self.reporter / 'config/config.toml'
        self.config.write_text('email_to = "test@example.invalid"\nwechat_outbox = "unused"\n')
        self.state = self.root / 'state'
        self.calls = self.root / 'calls'
        self.env = dict(os.environ, HOME=str(self.root), PRTS_REPORTER_STATE=str(self.state),
                        TEST_CALLS=str(self.calls))
        stub = '''#!/usr/bin/env python3
import json, os, pathlib, sys
with open(os.environ['TEST_CALLS'], 'a') as f:
    f.write(json.dumps([pathlib.Path(sys.argv[0]).name, *sys.argv[1:]]) + '\\n')
sys.exit(int(os.environ.get('TEST_FAIL', '0')))
'''
        for channel in ('bark', 'wechat', 'macos'):
            self.executable(self.reporter / 'lib/channels' / channel, stub)
        self.weekly = self.root / '完整报告.md'
        self.weekly.write_text('# 一周总结\n证据\n')
        self.summary = self.root / 'summary.txt'
        self.summary.write_text('完成关键实验\n结果一\n结果二\n全文：旧路径\n')

    def executable(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        path.chmod(0o755)

    def deliver(self, *args, rc=0):
        result = subprocess.run([sys.executable, str(self.reporter / 'lib/deliver.py'),
                                 '--weekly', str(self.weekly), '--wechat', str(self.summary),
                                 '--no-email', *args], env=self.env, stdin=subprocess.DEVNULL,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, rc, result.stdout + result.stderr)

    def assert_phone(self):
        calls = [json.loads(line) for line in self.calls.read_text().splitlines()]
        self.assertEqual(len(calls), 1)
        channel, title, body = calls[0]
        self.assertEqual((channel, title), ('bark', '完成关键实验'))
        self.assertLessEqual(len(body.splitlines()), 5)
        self.assertEqual(body.splitlines()[-1], '全文：' + str(self.weekly))
        self.assertNotIn('旧路径', body)

    def test_default_dual_delivery(self):
        self.deliver()
        self.assert_phone()
        self.assertEqual((self.state / 'outbox/latest-wechat.txt').read_text(), self.summary.read_text())

    def test_outbox_disabled(self):
        with self.config.open('a') as f:
            f.write('weekly_outbox = false\n')
        self.deliver()
        self.assert_phone()
        self.assertFalse((self.state / 'outbox').exists())

    def test_bounded_body(self):
        self.summary.write_text('完成关键实验\n' + '摘要\n' * 12)
        self.deliver()
        self.assert_phone()

    def test_failure_keeps_outbox_and_report(self):
        self.env['TEST_FAIL'] = '7'
        self.deliver(rc=7)
        self.assertTrue(self.weekly.exists())
        self.assertEqual((self.state / 'outbox/latest-wechat.txt').read_text(), self.summary.read_text())
        rows = [json.loads(line) for line in (self.state / 'out/deliveries.jsonl').read_text().splitlines()]
        self.assertEqual([(r['channel'], r['status']) for r in rows], [('wechat', 'staged'), ('phone', 'failed')])

    def test_email_only_skips_phone_and_outbox(self):
        self.deliver('--email-only')
        self.assertFalse(self.calls.exists())
        self.assertFalse((self.state / 'outbox').exists())

    def test_weekly_pipeline(self):
        # Fake only collection, composition and mail; retain the real report/weekly/deliver/notify chain.
        (self.reporter / 'lib/collect.py').write_text('')
        self.executable(self.root / 'interaction/bin/dispatch', '''#!/usr/bin/env python3
import pathlib, re, sys
prompt = pathlib.Path(sys.argv[3]).read_text()
for index, content in [(1, '# 本周报告\\n证据\\n'), (2, '完成关键实验\\n已验证结果\\n')]:
    path = pathlib.Path(re.search(str(index) + r'\\. `([^`]+)`', prompt).group(1))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
''')
        self.executable(self.root / 'interaction/bin/status', '#!/bin/sh\necho \'{"event":"exit","rc":0}\'\n')
        self.executable(self.root / 'stubs/osascript', '#!/bin/sh\necho 1\n')
        self.env['PATH'] = str(self.root / 'stubs') + ':' + self.env['PATH']
        with self.config.open('a') as f:
            f.write('weekly_outbox = false\n')
        result = subprocess.run([str(self.reporter / 'bin/report'), 'weekly', '2026-11-13'],
                                env=self.env, stdin=subprocess.DEVNULL, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.weekly = self.root / 'PRTS/human/reports/weekly-2026-11-07_2026-11-13.md'
        self.assertTrue(self.weekly.exists())
        self.assert_phone()
        self.assertTrue((self.state / 'out/wechat-2026-11-13.txt').exists())
        self.assertFalse((self.state / 'outbox').exists())


if __name__ == '__main__':
    unittest.main()
