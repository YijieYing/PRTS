#!/usr/bin/env python3
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
class RunTests(unittest.TestCase):
    def test_read_only_and_stdin(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            fake=p/'codex'; fake.write_text('''#!/usr/bin/env python3
import json,sys,os
from pathlib import Path
assert sys.stdin.read()==''
Path(os.environ['ARGS']).write_text(json.dumps(sys.argv[1:]))
Path(sys.argv[sys.argv.index('-o')+1]).write_text('{"ok":true}')
'''); fake.chmod(0o755)
            (p/'prompt').write_text('classify fixture'); (p/'schema').write_text('{}')
            env=dict(os.environ,PATH=tmp+os.pathsep+os.environ['PATH'],ARGS=str(p/'args'))
            r=subprocess.run([str(ROOT/'interaction/bin/run'),str(p/'prompt'),'--output-schema',str(p/'schema'),'-o',str(p/'out')],env=env,stdin=subprocess.DEVNULL,text=True,capture_output=True)
            self.assertEqual(r.returncode,0,r.stderr); self.assertEqual(json.loads(r.stdout),{'ok':True})
            args=json.loads((p/'args').read_text()); self.assertIn('read-only',args); self.assertNotIn('workspace-write',args); self.assertIn('--output-schema',args)
    def test_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp); fake=p/'codex'; fake.write_text('#!/bin/sh\nexit 7\n'); fake.chmod(0o755); (p/'prompt').write_text('x')
            r=subprocess.run([str(ROOT/'interaction/bin/run'),str(p/'prompt')],env=dict(os.environ,PATH=tmp+os.pathsep+os.environ['PATH']),stdin=subprocess.DEVNULL,capture_output=True)
            self.assertEqual(r.returncode,7)
if __name__=='__main__':unittest.main()
