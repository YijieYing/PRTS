import json
import os
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

PULSE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PULSE / 'lib'))
import focus
import study

DATE = '2026-11-23'   # a Monday


class Study(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.state = Path(tmp.name) / 'state'
        self.dir = Path(tmp.name) / 'reading'
        self.dir.mkdir()
        self.config = {
            'timezone': 'Asia/Tokyo', 'sources': {'system_apps': []}, 'mapping': [],
            'study': [
                dict(id='reading', title='读论文', days=['Mon', 'Sun'], start='21:00', minutes=45, mode='offline', dir=str(self.dir)),
                dict(id='french', title='法语', days=['Mon'], start='22:00', minutes=30, mode='any', on=['法语'], dir=str(self.dir)),
            ],
            'study_settings': dict(lead_minutes=10, nag_minutes=5, done_ratio=.6, makeup_start='23:30'),
        }
        self.sent = []
        self.busy = {}      # minute timestamp -> window title
        for target, name, value in (
                (study, '_notify', lambda title, text: self.sent.append((title, text)) or True),
                (study.computer_history, 'load', self.load),
                (study.computer_history, 'system_app', lambda row, config: row['app'] == 'Dock')):
            p = patch.object(target, name, value)
            p.start()
            self.addCleanup(p.stop)
        self.model = patch.object(focus, 'classify', side_effect=lambda contexts, *a: {
            c: {'category': 'off'} for c in contexts}).start()
        self.addCleanup(patch.stopall)

    def load(self, sources, start, end, state, warnings):
        return [dict(time=t, last=t + 50, active=True, app='Chrome', title=title, domain='', counts={})
                for t, title in self.busy.items() if start <= t < end], []

    def at(self, clock, date=DATE):
        return study._stamp(date, clock, self.config)

    def use(self, start, minutes, title='B站', date=DATE):
        for i in range(minutes):
            self.busy[self.at(start, date) + i * 60] = title

    def tick(self, clock, date=DATE):
        return study.tick(self.config, self.state, self.at(clock, date))

    def replay(self, start, end, step=300):
        t = self.at(*start)
        while t <= self.at(*end):
            study.tick(self.config, self.state, t)
            t += step

    def entry(self, ident='reading', date=DATE):
        return json.loads((self.state / f'study/days/{date}.json').read_text())['items'][ident]

    def status(self, clock, ident='reading', date=DATE, on=None):
        return study.status(self.config, self.state, date, self.at(clock, on or date))['items'][ident]['status']

    def log(self, ident='reading', minutes=0, date=DATE):
        item = next(x for x in self.config['study'] if x['id'] == ident)
        study._log(item, date, Namespace(title='X', note='一句', minutes=minutes), self.state)

    def titles(self):
        return [title for title, _ in self.sent]

    def test_no_config_changes_nothing(self):
        self.assertEqual(study.tick({'timezone': 'Asia/Tokyo'}, self.state, 0), {'disabled': True})
        self.assertFalse(self.state.exists())

    def test_weekday(self):
        self.tick('12:00', '2026-11-22')
        day = json.loads((self.state / 'study/days/2026-11-22.json').read_text())
        self.assertEqual(list(day['items']), ['reading'])
        self.tick('12:00', '2026-11-24')
        self.assertFalse((self.state / 'study/days/2026-11-24.json').exists())

    def test_validation_is_a_warning(self):
        for change in (dict(mode='x'), dict(days=['Foo']), dict(id='french'), dict(start='21:50'), dict(start='9')):
            bad = dict(self.config, study=[dict(self.config['study'][0], **change), self.config['study'][1]])
            self.assertIn('study 配置无效', study.tick(bad, self.state, self.at('21:00')).get('warning', ''), change)
        self.assertEqual(self.sent, [])
        self.assertIn('study 配置无效', (self.state / 'focus/checks.jsonl').read_text())

    def test_lead_and_start_once(self):
        for clock in ('20:49', '20:50', '20:55', '21:00', '21:05'):
            self.tick(clock)
        self.assertEqual(self.titles(), ['10 分钟后：读论文', '现在：读论文'])
        self.assertIn('合上电脑', self.sent[1][1])

    def test_late_wake_and_fully_missed(self):
        self.tick('21:30')
        self.assertEqual(self.titles(), ['现在：读论文'])
        self.sent.clear()
        self.tick('23:20', '2026-11-22')   # another day, slept through
        self.assertEqual(self.sent, [])

    def test_off_screen_counts_and_is_not_accumulated(self):
        self.use('21:00', 20)
        for clock in ('21:05', '21:30', '21:30', '21:45'):
            self.tick(clock)
        slot = self.entry()['slots'][0]
        self.assertEqual((slot['on'], slot['off'], slot['unknown']), (25, 20, 0))
        self.model.assert_not_called()

    def test_own_folder_and_single_glance(self):
        self.use('21:00', 5, str(self.dir) + '/queue.md')
        self.use('21:20', 1)
        self.tick('21:45')
        slot = self.entry()['slots'][0]
        self.assertEqual((slot['on'], slot['off'], slot['unknown']), (44, 0, 1))

    def test_any_mode(self):
        self.use('22:00', 10, '法语教材')
        self.use('22:10', 5, '微信')
        self.tick('22:30')
        slot = self.entry('french')['slots'][0]
        self.assertEqual((slot['on'], slot['off']), (25, 5))
        self.model.assert_called()

    def test_unreadable_history_is_unknown(self):
        with patch.object(study.computer_history, 'load', side_effect=OSError('x')):
            self.tick('21:45')
        self.assertEqual(self.entry()['slots'][0]['unknown'], 45)
        self.assertEqual(self.entry()['status'], 'missed')

    def test_nag_names_the_place_and_cools_down(self):
        self.use('21:00', 45)
        t = self.at('21:05')
        for i in range(0, 600, 60):
            study.tick(self.config, self.state, t + i)
        nags = [x for x in self.titles() if x.startswith('该读论文了')]
        self.assertEqual(nags, ['该读论文了，你还在：B站'] * 2)

    def test_end_states(self):
        self.assertEqual(self.status('20:00'), 'pending')
        self.tick('21:10')
        self.assertEqual(self.status('21:10'), 'active')
        self.tick('21:45')
        self.assertEqual(self.entry()['status'], 'partial')    # off the screen, nothing logged
        self.assertIn('离屏 45 分', self.sent[-1][1])
        self.assertNotIn('读了', ''.join(sum(self.sent, ())))
        self.log()
        self.assertEqual(self.status('22:00'), 'done')         # logged afterwards, off-screen minutes count

    def test_missed_and_log_only(self):
        self.use('21:00', 45)
        self.tick('21:45')
        self.assertEqual(self.entry()['status'], 'missed')
        self.log()
        self.assertEqual(self.status('21:50'), 'partial')
        self.log(minutes=30)
        self.assertEqual(self.status('21:50'), 'done')

    def test_done_earlier_in_the_day_is_quiet(self):
        self.log(minutes=45)
        self.replay(('20:45',), ('21:45',))
        self.assertEqual([x for x in self.titles() if '读论文' in x and not x.endswith('完成')], [])

    def test_skip_survives_the_end_and_gets_no_makeup(self):
        self.tick('21:05')
        study._skip(self.config['study'][0], DATE, '出差', self.config, self.state)
        self.sent.clear()
        self.assertFalse((self.state / 'focus/current.json').exists())
        self.replay(('21:10',), ('23:55',))
        self.assertEqual(self.entry()['status'], 'skip')
        self.assertEqual(len(self.entry()['slots']), 1)
        self.assertFalse([x for x in self.titles() if '读论文' in x])
        with self.assertRaises(ValueError):
            study._skip(self.config['study'][1], '2026-11-22', 'x', self.config, self.state)

    def test_makeup_chains_past_midnight_once(self):
        self.use('21:00', 45)
        self.use('22:00', 30)
        self.replay(('20:45',), ('01:00', '2026-11-24'))
        for ident, begin in (('reading', self.at('23:30')), ('french', self.at('00:15', '2026-11-24'))):
            slots = self.entry(ident)['slots']
            self.assertEqual([s['kind'] for s in slots], ['main', 'makeup'])
            self.assertEqual(slots[1]['start'], begin)
            self.assertTrue(slots[1]['closed'])
            self.assertEqual(self.entry(ident)['status'], 'partial')
        self.assertIn('现在：读论文（补）', self.titles())

    def test_full_evening_sequence(self):
        self.use('21:00', 15)
        self.replay(('20:45',), ('21:50',))
        self.log()
        self.replay(('21:55',), ('01:00', '2026-11-24'))
        self.assertEqual(self.titles(), [
            '10 分钟后：读论文', '现在：读论文', '该读论文了，你还在：B站', '该读论文了，你还在：B站',
            '该读论文了，你还在：B站', '读论文：完成一半', '10 分钟后：法语', '现在：法语', '法语：完成一半',
            '5 分钟后：法语（补）', '现在：法语（补）', '法语：完成一半'])
        self.assertEqual(self.status('01:00', on='2026-11-24'), 'done')

    def test_makeup_skipped_when_asleep(self):
        self.use('21:00', 45)
        self.replay(('21:00',), ('22:40',))
        self.tick('02:00', '2026-11-24')
        self.assertEqual(len(self.entry()['slots']), 1)

    def test_focus_conflicts(self):
        path = self.state / 'focus/current.json'
        path.parent.mkdir(parents=True)
        base = dict(goal='g', on=[], off=[], note='', start=self.at('20:00'), until=self.at('23:00'), rows=[], counts=focus.counts([]), reminders=[])
        focus.write(path, base)
        self.tick('21:05')
        self.assertEqual(focus.read(path, None)['goal'], 'g')     # manual stays
        focus.write(path, dict(base, source='dnd'))
        self.tick('21:10')
        self.assertEqual(focus.read(path, None)['source'], 'study')
        self.assertIn('"end_reason": "study"', (path.parent / 'log.jsonl').read_text())
        focus._start_dnd(self.config, self.state, self.at('21:11'))
        self.assertEqual(focus.read(path, None)['source'], 'study')
        for name in ('status', 'stop'):                            # must not classify or crash
            focus.command(Namespace(focus_command=name, reason='dnd-off'), self.config, self.state)
        self.tick('21:45')
        self.assertFalse(path.exists())

    def test_focus_check_runs_study_and_survives_it(self):
        args = Namespace(focus_command='check', at=datetime.fromtimestamp(self.at('21:00')).astimezone().isoformat(), dry=False)
        with patch.object(study, 'tick', side_effect=RuntimeError('boom')):
            self.assertEqual(focus.command(args, self.config, self.state), 0)
        self.assertIn('boom', (self.state / 'focus/checks.jsonl').read_text())
        focus.command(args, self.config, self.state)
        self.assertEqual(self.titles(), ['现在：读论文'])
        focus.command(Namespace(focus_command='check', at=args.at, dry=True), self.config, self.state)
        self.assertEqual(len(self.sent), 1)

    def test_day_section(self):
        self.tick('21:45')
        self.log()
        text = study.day(self.state, self.at('05:00'), self.at('05:00', '2026-11-24'), self.config)
        self.assertIn('读论文：完成；离屏或在学 45 分', text)
        self.assertIn('记录：X', text)
        self.assertEqual(study.day(self.state, self.at('05:00', '2026-11-25'), self.at('05:00', '2026-11-26'), self.config), '')

    def test_streak(self):
        for date, done in (('2026-11-16', True), ('2026-11-22', True)):
            self.log(minutes=45, date=date)
            self.tick('22:00', date)
        self.assertEqual(study.status(self.config, self.state, '2026-11-22', self.at('23:00', '2026-11-22'))['streak'], 1)

    def test_queue_pitch_and_pace(self):
        q = self.dir / 'queue.md'
        q.write_text('# q\n## P1 · 甲\n- 状态：读完\n- 晚数：1\n## P2 · 乙\n- 状态：待读\n- 晚数：2\n- 为什么读：因为有趣。\n## P3 · 丙\n- 晚数：1\n')
        self.config['study'][0]['queue'] = str(q)
        self.tick('20:50', '2026-11-22')
        self.assertEqual(self.sent[0][0], '10 分钟后读：P2 乙')
        self.assertIn('第 1 晚，预计 2 晚', self.sent[0][1])
        self.assertIn('为什么读：因为有趣。', self.sent[0][1])
        self.assertIn('比计划提前 1 篇', self.sent[0][1])      # nothing read yet in the plan, P1 already done
        self.tick('21:00', '2026-11-22')
        self.assertEqual(self.sent[1][0], '现在读：P2 乙')
        self.assertNotIn('为什么读', self.sent[1][1])           # the pitch came with the lead
        self.log(date='2026-11-22')
        study._log(self.config['study'][0], '2026-11-22', Namespace(title='P2 乙 前半', note='', minutes=0), self.state)
        self.tick('22:00', '2026-11-22')
        self.sent.clear()
        self.tick('21:00')                                      # slept through the lead: pitch comes with the start
        self.assertIn('第 2 晚，预计 2 晚', self.sent[0][1])
        self.assertIn('为什么读', self.sent[0][1])
        self.assertIn('按计划正好', self.sent[0][1])
        q.write_text(q.read_text().replace('- 状态：待读', '- 状态：读完').replace('## P3 · 丙', '## P3 · 丙\n- 状态：读完'))
        self.assertIsNone(study._paper(self.config['study'][0], self.state, DATE, self.config))

    def test_requests(self):
        directory = self.state / 'focus'
        directory.mkdir(parents=True)
        now = datetime.now().timestamp()
        lines = [dict(action='start-dnd', time=now - 3600), dict(action='start-dnd', time=now - 120), dict(action='stop-dnd', time=now - 60)]
        (directory / 'requests.jsonl').write_text('\n'.join(map(json.dumps, lines)) + '\nbroken\n')
        with patch.object(focus, 'infer_dnd', return_value=('g', [], [])), patch.object(focus, 'evaluate', return_value=([], [])):
            focus._consume_requests(directory, self.config, self.state, now)
        ended = [json.loads(x) for x in (directory / 'log.jsonl').read_text().splitlines()]
        self.assertEqual([(round(x['ended'] - x['start']), x['end_reason']) for x in ended], [(60, 'dnd-off')])
        log = (directory / 'dnd.log').read_text()
        self.assertIn('expired_request', log)
        self.assertIn('bad_request', log)
        self.assertFalse((directory / 'requests.jsonl').exists())

    def test_request_command_on_bare_path_reads_nothing(self):
        env = dict(PATH='/usr/bin:/bin', HOME=os.environ['HOME'], PULSE_STATE=str(self.state), PULSE_COMMAND_PREFIX='/usr/bin/true')
        r = subprocess.run([str(PULSE / 'bin/pulse'), 'focus', 'request', 'start-dnd'], env=env, capture_output=True, text=True)
        self.assertEqual((r.returncode, r.stderr), (0, ''))
        self.assertEqual(json.loads((self.state / 'focus/requests.jsonl').read_text())['action'], 'start-dnd')
        self.assertFalse((self.state / 'focus/current.json').exists())


if __name__ == '__main__':
    unittest.main()
