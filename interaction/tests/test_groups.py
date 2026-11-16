#!/usr/bin/env python3
"""Groups fixtures; CLI children have closed stdin via the shared test harness."""
import datetime as dt
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path
import unittest
from unittest.mock import patch
import test_threads
from interaction.lib.groups import groups, roadmap
from interaction.lib.sessions import reader, scan
from interaction.lib.projects import match
from pulse.lib.sources import project as pulse_project


class Groups(unittest.TestCase):
    def setUp(self):
        test_threads.Threads.setUp(self)
        self.scanner = patch('interaction.lib.groups.scan', return_value=[])
        self.scanner.start()
        self.addCleanup(self.scanner.stop)
    call = test_threads.Threads.call
    sub = test_threads.Threads.sub

    def test_cli_projects_roadmaps_and_legacy(self):
        table = self.root/'ROADMAP.md'
        table.write_text('| ID | 状态 | 标题 |\n| --- | --- | --- |\n'
                         '| R1 | ✅ | Done |\n| M1 | 🔨 | **Monitor** |\n' +
                         ''.join(f'| R{i} | 💤 | **Title {i}** | more |\n' for i in range(2, 9)))
        checklist = self.root/'TODO.md'
        checklist.write_text('```md\n- [ ] example\n```\n- [x] done\n- [ ] first\n  * [ ] second\n')
        self.projects.write_text(f'''[[project]]
name="A"
path="/a"
group="Second"
roadmap={json.dumps(str(table))}
roadmap_prefix="R"
[[project]]
name="Loose"
path="/loose"
[[project]]
name="B"
path="/b"
group="First"
roadmap={json.dumps(str(table))}
roadmap_prefix="M"
[[project]]
name="A"
path="/a2"
group="Second"
[[project]]
name="Tasks"
path="/tasks"
group="First"
roadmap={json.dumps(str(checklist))}
[[project]]
name="Missing"
path="/missing"
roadmap={json.dumps(str(self.root/'missing.md'))}
[[project]]
name="Outreach"
path="/outreach"
group="Outreach"
''')
        value = json.loads(self.call('bin/status', 'threads', '--json').stdout)
        self.assertEqual(value['threads'], [])
        self.assertEqual([g['name'] for g in value['groups']], ['Second', 'First', 'Outreach', '未分组'])
        projects = {p['name']: p for g in value['groups'] for p in g['projects']}
        self.assertEqual(projects['A']['paths'], ['/a', '/a2'])
        self.assertEqual([i['id'] for i in projects['A']['roadmap']['open']], ['R2','R3','R4','R5','R6'])
        self.assertEqual(projects['B']['roadmap']['open'], [dict(id='M1', status='🔨', title='Monitor')])
        self.assertEqual(projects['Tasks']['roadmap']['open'], [dict(id=None, status=None, title=t) for t in ('first','second')])
        self.assertTrue(projects['Missing']['roadmap']['error'])
        self.assertEqual(projects['Missing']['roadmap']['open'], [])
        self.assertEqual(projects['Outreach']['roadmap'], dict(path=None, open=[], error=None))
        self.assertEqual(projects['Outreach']['team'], [])
        for p in projects.values():
            self.assertEqual(set(p), {'name','thread','paths','roadmap','team','tasks_running','tasks_unreviewed','last_event_at'})
        checklist.write_text('ordinary prose')
        self.assertTrue(roadmap(dict(roadmap=str(checklist)))['error'])
        checklist.write_text('- [X] all done')
        self.assertEqual(roadmap(dict(roadmap=str(checklist)))['open'], [])
        self.assertIsNone(roadmap(dict(roadmap=str(checklist)))['error'])

    def test_team_window_dedupe_limits_counts(self):
        now = dt.datetime(2026, 11, 16, tzinfo=dt.timezone.utc)
        iso = lambda days: (now-dt.timedelta(days=days)).isoformat()
        rows = []
        def run(name, ident, days, caller=None, cwd='/repo', **extra):
            rows.extend([dict(name=name,event='start',t=iso(days),cwd=cwd,caller=caller,**extra),
                         dict(name=name,event='thread',t=iso(days),thread=ident)])
        for i in range(12): run(str(i), f'id{i}', i/10)
        run('repeat', 'id0', 2)
        run('old', 'old', 15)
        run('future', 'future', -1)
        run('caller', 'child', 1, dict(kind='claude',id='cli-uuid'))
        run('worktree', 'worktree', 0, cwd='/elsewhere', worktree=dict(repo='/repo'))
        # Start resets IDs even when the new run has no thread/caller yet.
        rows.append(dict(name='caller', event='start', t=iso(0), cwd='/elsewhere'))
        rows.append(dict(name='caller', event='exit', t=iso(0), rc=0))
        subs = [dict(thread_key='project:Canonical',to='codex:id0',paused=False),
                dict(project='Canonical',to='codex:id0',paused=False),
                dict(project='Canonical',to='claude:local_sub',paused=False),
                dict(project='Canonical',to='codex:paused',paused=True),
                dict(thread_key='gh:owner/repo#1',project='Canonical',to='codex:pr',paused=False)]
        threads = {'project:Canonical': dict(tasks=[dict(status='running',reviewed=False),
                   dict(status='done',reviewed=False),dict(status='failed',reviewed=False),
                   dict(status='done',reviewed=True)],last_event_at=iso(0))}
        with patch('interaction.lib.groups.mapping',return_value=[dict(name='Canonical',path='/repo')]):
            p = groups(threads, subs, rows, iso(0))[0]['projects'][0]
        team = p['team']; by_id = {m['id']: m for m in team}
        self.assertEqual(len(team), len(by_id))
        self.assertEqual(len([m for m in team if not m['subscribed']]), 10)
        self.assertTrue(by_id['codex:id0']['subscribed'])
        self.assertEqual(by_id['codex:id0']['last_active'],iso(0))
        self.assertIsNone(by_id['claude:local_sub']['last_active'])
        self.assertIn('codex:worktree',by_id)
        for ident in ('codex:old','codex:future','codex:paused','codex:pr'):
            self.assertNotIn(ident,by_id)
        self.assertEqual(p['tasks_running'],1)
        self.assertEqual(p['tasks_unreviewed'],2)
        self.assertEqual(p['last_event_at'],iso(0))
        self.assertTrue(all(m['subscribed'] for m in team[:2]))
        recent = [m['last_active'] for m in team if not m['subscribed']]
        self.assertEqual(recent, sorted(recent, reverse=True))
        # Inclusive 14-day boundary, CLI Claude identity, no child-completion activity for caller.
        rows = []
        run('boundary','boundary',14,dict(kind='claude',id='cli-uuid'))
        rows.append(dict(name='boundary',event='exit',t=iso(0),rc=0))
        run('outside','outside',14.001)
        with patch('interaction.lib.groups.mapping',return_value=[dict(name='Canonical',path='/repo')]):
            team = groups({}, [], rows, iso(0))[0]['projects'][0]['team']
        self.assertEqual({m['id'] for m in team}, {'claude:cli-uuid','codex:boundary'})
        self.assertEqual(next(m for m in team if m['kind']=='claude')['last_active'], iso(14))


    def test_desktop_files_and_database(self):
        module = reader()
        if module is None:
            self.skipTest('optional AgentConsole checkout is not installed')
        module.HOME = str(self.root)
        now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
        epoch = now.timestamp()
        iso = lambda days: (now-dt.timedelta(days=days)).isoformat()
        transcripts = self.root/'.claude/projects/repo'
        transcripts.mkdir(parents=True)
        metadata = self.root/'Library/Application Support/Claude/claude-code-sessions/account'
        metadata.mkdir(parents=True)
        def claude(sid, cwd, days=0, archived=False, local=None):
            path = transcripts/(sid+'.jsonl')
            path.write_text(json.dumps(dict(cwd=cwd, type='user', uuid=sid,
                                           message=dict(content='prompt')))+'\n')
            os.utime(path, (epoch-days*86400, epoch-days*86400))
            local = local or 'local_'+sid
            (metadata/(local+'.json')).write_text(json.dumps(dict(sessionId=local,
                cliSessionId=sid, title='Desktop '+sid, isArchived=archived)))
        claude('cli', '/repo/deep/child', 1)
        claude('archived', '/repo/deep', archived=True)
        claude('home', str(self.root))
        claude('old', '/repo/deep', 15)
        claude('edge', '/repo/deep', 14)
        claude('future', '/repo/deep', -1)
        claude('sibling', '/repository')
        db = self.root/'.codex/state_5.sqlite'
        db.parent.mkdir()
        with closing(sqlite3.connect(db)) as con:
            con.execute('CREATE TABLE threads (id, rollout_path, cwd, name, title, preview, source, updated_at_ms, archived, model, agent_role, model_provider)')
            con.execute('CREATE TABLE thread_spawn_edges (child_thread_id, parent_thread_id)')
            for i in range(12):
                con.execute('INSERT INTO threads VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                    (f'c{i}', '/missing', '/repo', '', f'Codex {i}', '', 'desktop',
                     int((epoch-i*60)*1000), 0, '', '', ''))
            for sid, days, archived in [('old',15,0), ('archived',0,1), ('future',-1,0), ('edge',14,0)]:
                con.execute('INSERT INTO threads VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
                    (sid, '/missing', '/repo/deep', '', sid, '', 'desktop', int((epoch-days*86400)*1000), archived, '', '', ''))
            con.commit()
        items = [dict(name='Home', path=str(self.root)), dict(name='A', path='/repo'),
                 dict(name='Deep', path='/repo/deep')]
        rows = [dict(name='dispatch', event='start', t=iso(2), cwd='/repo/deep', caller=dict(kind='claude',id='cli')),
                dict(name='archived', event='start', t=iso(0), cwd='/repo/deep', caller=dict(kind='claude',id='archived')),
                dict(name='codex', event='start', t=iso(1), cwd='/repo'),
                dict(name='codex', event='thread', t=iso(1), thread='c0')]
        subs = [dict(project='Deep', to='claude:cli'), dict(project='Deep', to='claude:local_cli')]
        with patch('interaction.lib.groups.scan', side_effect=lambda: scan(module)), \
             patch('interaction.lib.groups.mapping', return_value=items), \
             patch('time.time', return_value=epoch), patch('pathlib.Path.home', return_value=self.root):
            projects = {p['name']:p for g in groups({}, subs, rows, iso(0)) for p in g['projects']}
            self.assertIsNone(match(str(self.root), items))
            self.assertIsNone(match(str(self.root/'unknown'), items))
            self.assertIsNone(match('/repository', items))
            self.assertEqual(match('/repo/deep/child', items), 'Deep')
            self.assertEqual(pulse_project('/repo/deep/child', items), 'Deep')
            self.assertEqual(pulse_project(str(self.root), items), '未归属')
            self.assertEqual(pulse_project('/unregistered', items), 'unregistered')
            self.assertIsNone(match('/repo/child', [dict(name='Exact',path='/repo',exact=True)]))
        self.assertEqual(projects['Home']['team'], [])
        deep = projects['Deep']['team']
        self.assertEqual([m['id'] for m in deep], ['claude:local_cli', 'claude:local_edge', 'codex:edge'])
        self.assertTrue(deep[0]['subscribed'])
        self.assertEqual(deep[0]['title'], 'Desktop cli')
        self.assertEqual(deep[0]['last_active'], iso(1))
        team = projects['A']['team']
        self.assertEqual(len(team), 10)
        self.assertEqual([m['id'] for m in team], [f'codex:c{i}' for i in range(10)])
        self.assertTrue(all(not m['subscribed'] for m in team))
        self.assertEqual(team[0]['title'], 'Codex 0')

if __name__ == '__main__': unittest.main(verbosity=2)
