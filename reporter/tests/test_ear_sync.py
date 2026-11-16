"""Exercise both scheduled entry points with disposable command stubs."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

class EarSync(unittest.TestCase):
    def test_scheduled_sync_order_and_failure_isolation(self):
        for entry, flags, next_call in [('remind',' --no-notify', 'check'),('recap',' --no-notify','day')]:
            for rc in (0,1):
                with self.subTest(entry=entry,rc=rc), tempfile.TemporaryDirectory() as tmp:
                    root=Path(tmp)
                    for directory in ('reporter/bin','pulse/bin'): (root/directory).mkdir(parents=True)
                    shutil.copy(ROOT/'bin'/entry,root/'reporter/bin'/entry)
                    shutil.copytree(ROOT/'lib',root/'reporter/lib')
                    if entry=='remind':
                        (root/'reporter/bin/recap').write_text('#!/bin/sh\nexit 0\n')
                        (root/'reporter/bin/recap').chmod(0o755)
                    calls=root/'calls'
                    def stub(path,body):
                        path.write_text('#!/bin/bash\n'+body);path.chmod(0o755)
                    stub(root/'pulse/bin/pulse', f"""echo "$*" >> "{calls}"
if [ "$1" = ear ]; then [ -z "$(cat)" ] || exit 99; exit {rc}; fi
[ "$1" = now ] && echo '{{"quiet":false}}'
[ "$1" = day ] && printf '# 日报\\n总计\\n内容\\n'
exit 0
""")
                    stub(root/'reporter/bin/ask','exit 0\n')
                    stub(root/'reporter/bin/notify','exit 0\n')
                    result=subprocess.run([str(root/'reporter/bin'/entry), *(['2026-11-16'] if entry=='recap' else [])],stdin=subprocess.DEVNULL,
                                          capture_output=True,text=True,timeout=10)
                    self.assertEqual(result.returncode,0,result.stderr)
                    commands=calls.read_text().splitlines()
                    self.assertEqual(commands[0],'ear sync'+flags)
                    self.assertEqual(len(commands),3 if entry=='remind' else 2)
                    self.assertTrue(commands[1].startswith(next_call))
                    if rc: self.assertIn('warning',result.stderr)
