import json, os, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from interaction.lib import tokens

class Tokens(unittest.TestCase):
    def test_incremental_and_dedup(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as h:
            hp=Path(h); (hp/'.claude/projects/p').mkdir(parents=True); (hp/'.codex/sessions/2026/11/19').mkdir(parents=True)
            (hp/'.claude/projects/p/a.jsonl').write_text('\n'.join([
                json.dumps({'cwd':'/tmp','timestamp':'2026-11-19T00:00:00Z','uuid':'u','message':{'id':'m','model':'c','usage':{'input_tokens':2,'output_tokens':3}}}),
                json.dumps({'cwd':'/tmp','timestamp':'2026-11-19T00:00:00Z','uuid':'u','message':{'id':'m','model':'c','usage':{'input_tokens':2,'output_tokens':3}}}), 'bad'])+'\n')
            (hp/'.codex/sessions/2026/11/19/x.jsonl').write_text('\n'.join([json.dumps({'type':'session_meta','payload':{'id':'x','cwd':'/tmp','model':'g'}}),json.dumps({'timestamp':'2026-11-19T00:00:00Z','ordinal':1,'type':'event_msg','payload':{'type':'token_count','info':{'total_token_usage':{'input_tokens':99},'last_token_usage':{'input_tokens':4,'cached_input_tokens':1,'output_tokens':2}}}})])+'\n')
            with patch.object(tokens,'STATE',Path(d)), patch.dict(os.environ,{'HOME':h}):
                self.assertEqual(tokens.sync()['rows'],2); self.assertEqual(tokens.sync()['rows'],0)
                rows=tokens.read_rows(); self.assertEqual(sum(x['input'] for x in rows),6)

if __name__ == '__main__': unittest.main()
