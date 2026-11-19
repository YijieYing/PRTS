import argparse, json, os, tempfile, unittest
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
            (hp/'.codex/sessions/2026/11/19/x.jsonl').write_text('\n'.join([json.dumps({'type':'session_meta','payload':{'id':'x','cwd':'/tmp','model':'g'}}),json.dumps({'timestamp':'2026-11-19T00:00:00Z','ordinal':1,'type':'event_msg','payload':{'type':'token_count','info':{'total_token_usage':{'input_tokens':4,'cached_input_tokens':1,'output_tokens':2},'last_token_usage':{'input_tokens':4,'cached_input_tokens':1,'output_tokens':2}}}}),json.dumps({'timestamp':'2026-11-19T00:00:01Z','ordinal':2,'type':'event_msg','payload':{'type':'token_count','info':{'total_token_usage':{'input_tokens':9,'cached_input_tokens':2,'output_tokens':3},'last_token_usage':{'input_tokens':5,'cached_input_tokens':1,'output_tokens':1}}}}),json.dumps({'timestamp':'2026-11-19T00:00:02Z','ordinal':3,'type':'event_msg','payload':{'type':'token_count','info':{'total_token_usage':{'input_tokens':9,'cached_input_tokens':2,'output_tokens':3},'last_token_usage':{'input_tokens':0,'cached_input_tokens':0,'output_tokens':0}}}})])+'\n')
            with patch.object(tokens,'STATE',Path(d)), patch.dict(os.environ,{'HOME':h}):
                self.assertEqual(tokens.sync()['rows'],3); self.assertEqual(tokens.sync()['rows'],0)
                rows=tokens.read_rows(); self.assertEqual(sum(x['input'] for x in rows),9); self.assertEqual(sum(x['cache_read'] for x in rows),2)

    def test_child_parent_title_and_cross_file_copy(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as h:
            hp=Path(h); base=hp/'.claude/projects/p/s1'; (base/'subagents').mkdir(parents=True)
            rec={'cwd':'/tmp','type':'user','message':{'content':'A long user question for title'}}
            use={'cwd':'/tmp','type':'assistant','message':{'id':'same','model':'c','usage':{'input_tokens':1,'output_tokens':2}}}
            (base/'subagents/a.jsonl').write_text(json.dumps(rec)+'\n'+json.dumps(use)+'\n')
            (hp/'.claude/projects/p/z.jsonl').write_text(json.dumps(use)+'\n')
            with patch.object(tokens,'STATE',Path(d)), patch.dict(os.environ,{'HOME':h}):
                self.assertEqual(tokens.sync()['rows'],1)
                row=tokens.read_rows()[0]; self.assertEqual(row['parent_session'],'s1'); self.assertEqual(row['title'],'A long user question for title')

    def test_append_truncate_rebuild_and_tags(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as h:
            hp=Path(h); p=hp/'.claude/projects/p'; p.mkdir(parents=True)
            f=p/'x.jsonl'; f.write_text(json.dumps({'type':'assistant','message':{'id':'1','usage':{'input_tokens':1,'output_tokens':1}}})+'\n')
            with patch.object(tokens,'STATE',Path(d)), patch.dict(os.environ,{'HOME':h}):
                self.assertEqual(tokens.sync()['rows'],1); self.assertEqual(tokens.sync()['rows'],0)
                with f.open('a') as out: out.write(json.dumps({'type':'assistant','message':{'id':'2','usage':{'input_tokens':2,'output_tokens':1}}})+'\n')
                self.assertEqual(tokens.sync()['rows'],1)
                f.write_text(json.dumps({'type':'assistant','message':{'id':'3','usage':{'input_tokens':3,'output_tokens':1}}})+'\n')
                self.assertEqual(tokens.sync()['rows'],1)
                tokens.main(['tag','3','arm=raw']); tokens.main(['tag','3','arm=formatted','exp=yes'])
                self.assertEqual(tokens._load('tags.json',{})['3']['arm'],'formatted')

    def test_summary_definition_and_multidimensional(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(tokens,'STATE',Path(d)):
                Path(d).mkdir(parents=True,exist_ok=True)
                Path(d,'ledger.jsonl').write_text('\n'.join(json.dumps({'time':'2026-11-19T00:00:00+00:00','agent':'codex','model':'g','session':'s','project':'P','task':'T','tags':{'arm':'a'},'input':4,'cache_write':1,'cache_read':2,'output':3,'reasoning':2}) for _ in range(2))+'\n')
                a=argparse.Namespace(since='2026-11-18',until='2026-11-20',by=['agent','tag:arm'],tag=None,logical_day=False,no_sync=True)
                row=tokens.summary(a)[0]; self.assertEqual(row['total'],20); self.assertEqual(row['without_cache_read'],16); self.assertEqual(row['runs'],2); self.assertEqual(row['mean']['total'],10)

    def test_codex_reset_uses_last_and_project_task(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as h, tempfile.TemporaryDirectory() as state:
            hp=Path(h); p=hp/'.codex/sessions/2026/11/19'; p.mkdir(parents=True)
            (Path(state)/'registry.jsonl').write_text(json.dumps({'event':'start','name':'job','tags':{'arm':'raw'}})+'\n'+json.dumps({'event':'thread','name':'job','thread':'cx'})+'\n')
            (p/'x.jsonl').write_text('\n'.join([json.dumps({'type':'session_meta','payload':{'id':'cx','cwd':'/tmp','model':'g'}}),json.dumps({'type':'event_msg','payload':{'type':'token_count','info':{'total_token_usage':{'input_tokens':10,'output_tokens':5},'last_token_usage':{'input_tokens':10,'output_tokens':5}}}}),json.dumps({'type':'event_msg','payload':{'type':'token_count','info':{'total_token_usage':{'input_tokens':2,'output_tokens':1},'last_token_usage':{'input_tokens':2,'output_tokens':1}}}})])+'\n')
            with patch.object(tokens,'STATE',Path(d)), patch.dict(os.environ,{'HOME':h,'PRTS_INTERACTION_STATE':state}):
                self.assertEqual(tokens.sync()['rows'],2); rows=tokens.read_rows(); self.assertEqual(sum(x['input']+x['output'] for x in rows),18); self.assertEqual(rows[-1]['task'],'job')

if __name__ == '__main__': unittest.main()
