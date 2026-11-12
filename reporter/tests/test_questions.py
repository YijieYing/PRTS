#!/usr/bin/env python3
"""Public CLI tests: disposable installation, state, pulse and closed stdin."""
import concurrent.futures
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Questions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.module = self.root / 'reporter'
        for part in ('bin', 'lib', 'config'):
            shutil.copytree(ROOT / part, self.module / part, ignore=shutil.ignore_patterns('__pycache__'))
        self.env = dict(os.environ, PRTS_REPORTER_STATE=str(self.root / 'data'), TZ='Asia/Tokyo')
        self.log = self.root / 'data/questions.jsonl'
        self.ask = self.module / 'bin/ask'
        self.pulse = self.root / 'pulse/bin/pulse'
        self.pulse.parent.mkdir(parents=True)
        self.stub('false')

    def stub(self, value):
        self.pulse.write_text('#!/bin/sh\nread line && exit 9\nprintf \'{"quiet":' + value + '}\\n\'\n')
        self.pulse.chmod(0o755)

    def run_cmd(self, *args, rc=0):
        r = subprocess.run([str(self.ask), *args], env=self.env, stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, timeout=10)
        self.assertEqual(r.returncode, rc, r.stdout + r.stderr)
        return r.stdout.strip()

    def add(self, urgency='blocking', key=None, *extra):
        key = key or str(len(self.events()))
        return self.run_cmd('add', '问题 ' + key, '--why', '原因', '--default', '默认',
                            '--urgency', urgency, '--source', 'test', '--dedupe', key, *extra)

    def events(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def due(self, now):
        return self.run_cmd('due', '--channel', 'claude', '--now', now)

    def remind(self):
        notify = self.module / 'bin/notify'
        calls = self.root / 'notify-calls'
        notify.write_text('#!/bin/sh\nprintf "%s|" "$@" >> ' + str(calls) + '\necho >> ' + str(calls) + '\n')
        r = subprocess.run([str(self.module / 'bin/remind')], env=self.env, stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, timeout=10)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return calls.read_text() if calls.exists() else ''

    def test_remind_pushes_only_when_something_is_due(self):
        self.assertEqual(self.remind(), '')                  # empty queue: silent
        q = self.add('timely', 'remind-one').strip()
        sent = self.remind()
        self.assertIn('alert|--title|PRTS 提醒|--text|', sent)
        self.assertIn(q, sent)
        self.assertEqual(self.remind(), sent)                # timely is not repeated: no second push

    def test_timely_pushes_once_and_respects_quiet(self):
        self.stub('true')
        q = self.add('timely', 'quiet-one').strip()
        self.assertEqual(self.due('2026-11-12T10:00:00+09:00'), '')     # quiet: held back
        self.stub('false')
        self.assertIn(q, self.due('2026-11-12T10:05:00+09:00'))          # pushed at the next due run
        self.assertEqual(self.due('2026-11-12T11:00:00+09:00'), '')     # never repeated

    def test_fold_dedupe_concurrency(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            ids = list(pool.map(lambda _: self.add(key='same'), range(16)))
        self.assertEqual(set(ids), {'Q1'})
        self.assertEqual(len(self.events()), 1)
        self.run_cmd('close', 'Q1', 'superseded')
        self.assertEqual(self.add(key='same'), 'Q2')
        rows = json.loads(self.run_cmd('list', '--json'))
        self.assertEqual(rows[0]['outcome'], 'superseded')
        self.assertEqual([q['qid'] for q in json.loads(self.run_cmd('list', '--open', '--json'))], ['Q2'])
        self.assertTrue(all({'qid', 't', 'event'} <= e.keys() for e in self.events()))

    def test_order_caps_and_render(self):
        for urgency in ('whenever', 'soon', 'blocking', 'blocking', 'blocking'):
            self.add(urgency)
        out = self.run_cmd('next', '--max', '99')
        self.assertEqual([l.split(' · ')[0] for l in out.splitlines() if ' · ' in l], ['Q3', 'Q4', 'Q5'])
        self.assertEqual(self.run_cmd('next', '--max', '1').count(' · '), 1)
        self.assertEqual(len(self.events()), 5)  # next/render are previews
        self.assertIn('Q1 · ', self.run_cmd('render'))
        out = self.due('2099-01-01T19:00:00+09:00')
        self.assertEqual(out.count(' · '), 3)
        sent = [e for e in self.events() if e['event'] == 'delivered']
        self.assertEqual({e['batch_size'] for e in sent}, {3})
        self.assertEqual(len({e['batch_id'] for e in sent}), 1)
        self.assertIn('Q2 · ', self.due('2099-01-01T19:01:00+09:00'))

    def test_interval_daily_cap_and_reset(self):
        self.add()
        self.assertIn('Q1 · ', self.due('2099-01-01T10:00:00+09:00'))
        self.assertEqual(self.due('2099-01-01T10:29:59+09:00'), '')
        self.assertIn('Q1 · ', self.due('2099-01-01T10:30:00+09:00'))
        for hour in range(11, 15):
            self.assertIn('Q1 · ', self.due(f'2099-01-01T{hour}:00:00+09:00'))
        self.assertEqual(self.due('2099-01-01T15:00:00+09:00'), '')
        self.assertIn('Q1 · ', self.due('2099-01-02T00:00:00+09:00'))

    def test_soon_quiet_fallback(self):
        self.add('soon')
        self.add('whenever')
        self.assertEqual(self.due('2099-01-01T17:59:59+09:00'), '')
        self.stub('true')
        self.assertEqual(self.due('2099-01-01T18:00:00+09:00'), '')
        self.add('blocking')
        self.assertIn('Q3 · ', self.due('2099-01-01T18:00:00+09:00'))
        self.pulse.write_text('#!/bin/sh\nexit 1\n')
        self.assertIn('Q1 · ', self.due('2099-01-01T18:01:00+09:00'))
        self.assertEqual(self.due('2099-01-01T18:02:00+09:00'), '')
        self.run_cmd('close', 'Q3', 'rejected')
        self.pulse.unlink()
        out = self.due('2099-01-02T18:00:00+09:00')
        self.assertIn('Q1 · ', out)
        self.assertNotIn('Q2 · ', out)

    def test_reply_and_defaults(self):
        for _ in range(4):
            self.add()
        self.run_cmd('reply', 'Q1 可以，按这个做')
        self.assertEqual(self.run_cmd('reply', 'Q2 你定'), '默认')
        self.run_cmd('reply', 'Q3 以后')
        self.run_cmd('reply', 'Q4 别问')
        rows = json.loads(self.run_cmd('list', '--json'))
        self.assertEqual([q['outcome'] for q in rows], ['answered', 'delegated', 'deferred', 'rejected'])
        self.assertEqual(rows[0]['via'], 'claude')
        self.assertIsNone(rows[0]['latency_s'])
        self.run_cmd('answer', 'Q2', '改成别的', '--via', 'file')
        self.assertFalse(json.loads(self.run_cmd('list', '--json'))[1]['default_ok'])
        self.run_cmd('reply', '没有编号', rc=2)
        self.run_cmd('reply', 'Q99 同意', rc=2)
        self.run_cmd('reply', 'Q3 同意', rc=2)
        self.add()
        self.run_cmd('default-used', 'Q5')
        self.run_cmd('default-ok', 'Q5', 'true')
        self.assertTrue(json.loads(self.run_cmd('list', '--json'))[-1]['default_ok'])

    def test_expire(self):
        for _ in range(3):
            self.add('blocking', None, '--expires', '2099-01-01T12:00:00+09:00')
        config = self.module / 'config/questions.toml'
        config.write_text(config.read_text().replace('max_batch = 3', 'max_batch = 2'))
        self.due('2099-01-01T11:00:00+09:00')
        self.run_cmd('opened', 'Q2', '--channel', 'claude')
        self.assertEqual(self.due('2099-01-01T12:00:00+09:00'), '')
        self.assertEqual(self.run_cmd('expire', '--now', '2099-01-01T12:00:00+09:00'), 'Q1\nQ2\nQ3')
        self.assertEqual([q['outcome'] for q in json.loads(self.run_cmd('list', '--json'))],
                         ['expired_unseen', 'expired_seen', 'expired_unseen'])
        self.assertEqual(self.run_cmd('expire', '--now', '2099-01-02T00:00:00+09:00'), '')

    def test_latency_and_wait(self):
        self.add()
        now = datetime.now().astimezone()
        self.due((now - timedelta(hours=1)).isoformat())
        self.due((now - timedelta(minutes=20)).isoformat())
        p = subprocess.Popen([str(self.ask), 'wait', 'Q1', '--poll', '0.02'], env=self.env,
                             stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            time.sleep(0.1)
            self.assertIsNone(p.poll())
            self.run_cmd('answer', 'Q1', '答案', '--via', 'session')
            stdout, stderr = p.communicate(timeout=5)
            self.assertEqual((p.returncode, stdout.strip(), stderr), (0, '答案', ''))
        finally:
            if p.poll() is None:
                p.kill()
                p.communicate()
        row = json.loads(self.run_cmd('list', '--json'))[0]
        self.assertGreaterEqual(row['latency_s'], 3600)
        self.assertLess(row['latency_s'], 3610)
        self.add()
        self.run_cmd('close', 'Q2', 'deferred')
        self.assertEqual(self.run_cmd('wait', 'Q2'), '')
        self.run_cmd('wait', 'Q99', rc=2)
        self.run_cmd('wait', 'Q2', '--poll', '0', rc=2)

    def test_soon_batch_order_and_local_day(self):
        for _ in range(4):
            self.add('soon')
        out = self.due('2099-01-01T09:00:00Z')  # 18:00 JST
        self.assertEqual([l.split(' · ')[0] for l in out.splitlines() if ' · ' in l], ['Q1', 'Q2', 'Q3'])
        out = self.due('2099-01-01T09:01:00Z')
        self.assertEqual([l.split(' · ')[0] for l in out.splitlines() if ' · ' in l], ['Q4'])
        self.assertEqual(self.due('2099-01-02T08:59:59Z'), '')
        self.assertEqual(self.due('2099-01-02T09:00:00Z').count(' · '), 3)

    def test_invalid_input_and_corrupt_history(self):
        self.run_cmd('add', '问题', '--why', '原因', '--default', '', '--urgency', 'soon',
                     '--source', 'test', '--dedupe', 'key', rc=2)
        self.assertFalse(self.log.exists())
        self.add()
        with self.log.open('a') as f:
            f.write('{broken')
        before = self.log.read_bytes()
        self.run_cmd('close', 'Q1', 'rejected', rc=2)
        self.assertEqual(self.log.read_bytes(), before)

    def test_concurrent_due_and_append_only(self):
        self.add()
        before = self.log.read_bytes()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            outputs = list(pool.map(lambda _: self.due('2099-01-01T12:00:00+09:00'), range(4)))
        self.assertEqual(sum(bool(out) for out in outputs), 1)
        self.assertTrue(self.log.read_bytes().startswith(before))
        self.run_cmd('close', 'Q1', 'answered', rc=2)
        self.assertEqual(len(self.events()), 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
