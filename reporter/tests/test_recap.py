#!/usr/bin/env python3
"""recap: full text to Apple Notes, only the head pushed; Notes markup. Stubs only, nothing is sent."""
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MD = '# 11-13 回顾\n输入 1 分 · 输出 2 分\n\n## 时间线\n\n' + '\n'.join(
    f'**{h:02d}:00–{h:02d}:30 · 输入 · P** 第 {h} 段 <x>\n  - 学到：东西 {h}' for h in range(9, 21))


class Recap(unittest.TestCase):
    def run_recap(self, note_rc=0):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup); root = Path(tmp.name)
        module = root / 'reporter'
        for part in ('bin', 'lib'):
            shutil.copytree(ROOT / part, module / part, ignore=shutil.ignore_patterns('__pycache__'))
        pulse = root / 'pulse/bin/pulse'; pulse.parent.mkdir(parents=True)
        (root / 'md').write_text(MD)
        pulse.write_text(f'#!/bin/sh\ncat {root / "md"}\n'); pulse.chmod(0o755)
        calls = root / 'calls'
        (module / 'bin/notify').write_text(
            f'#!/bin/sh\nprintf "%s\\037" "$@" >> {calls}\nprintf "\\036" >> {calls}\n'
            f'[ "$1" = note ] && exit {note_rc}\nexit 0\n')
        r = subprocess.run([str(module / 'bin/recap')], stdin=subprocess.DEVNULL, capture_output=True,
                           text=True, timeout=20, env=dict(os.environ, TZ='Asia/Tokyo'))
        self.assertEqual(r.returncode, 0, r.stderr)
        return [call.split('\x1f')[:-1] for call in calls.read_text().split('\x1e')[:-1]]

    def test_full_text_to_notes_head_to_phone(self):
        note, alert = self.run_recap()
        self.assertEqual(note[:5], ['note', '--folder', 'PRTS 日报', '--title', note[4]])
        self.assertTrue(note[4].endswith(' 回顾')); self.assertEqual(note[-1], MD)
        self.assertEqual(alert[:3], ['alert', '--title', '输入 1 分 · 输出 2 分'])
        self.assertIn('mobilenotes://', alert)
        text = alert[-1]
        self.assertIn('第 9 段', text); self.assertNotIn('第 20 段', text)   # head only
        self.assertTrue(text.endswith('全文见备忘录 · PRTS 日报 · ' + note[4]))

    def test_notes_failure_points_to_file(self):
        _, alert = self.run_recap(note_rc=1)
        self.assertIn('备忘录写入失败', alert[-1])

    def test_notes_markup(self):
        to_html = runpy.run_path(str(ROOT / 'lib/channels/notes'))['to_html']
        out = to_html('2026-11-13 回顾', MD)
        self.assertTrue(out.startswith('<h1>2026-11-13 回顾</h1>'))
        self.assertNotIn('11-13 回顾</h1>\n<h1>', out)                   # Markdown H1 replaced
        self.assertIn('<h2>时间线</h2>', out)
        self.assertIn('<b>09:00–09:30 · 输入 · P</b> 第 9 段 &lt;x&gt;', out)
        self.assertIn('• 学到：东西 9', out)


if __name__ == '__main__':
    unittest.main()
