import json, subprocess, unittest, sys, importlib.util
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'lib'))
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('pulse_impl',Path(__file__).resolve().parents[1]/'lib/pulse.py'); pulse=importlib.util.module_from_spec(spec); spec.loader.exec_module(pulse)

class PulseTokenSection(unittest.TestCase):
    def setUp(self):
        self.c=pulse.config(); self.segment={'start':0,'end':60,'intervals':[[0,60]],'held_candidates':[],'source':'computer','session':'s','project':None,'category':'input','summary':'x','reason':'x','learned':[],'produced':[],'messages':[],'active_seconds':60,'held_seconds':0}
    def _result(self,text,rc=0):
        return subprocess.CompletedProcess([],rc,stdout=text,stderr='')
    def test_data(self):
        value=json.dumps([{'group':'claude','total':1000,'cache_read':500,'input':400,'cache_write':0,'output':100,'reasoning':10}])
        with patch.dict('os.environ',{'PULSE_TOKENS':'stub'}), patch.object(pulse,'run',return_value=self._result(value)):
            self.assertIn('## token',pulse.render({'segments':[self.segment.copy()],'warnings':[]},'2026-11-19',self.c))
    def test_no_data(self):
        with patch.object(pulse,'run',return_value=self._result('[]')):
            self.assertNotIn('## token',pulse.render({'segments':[self.segment.copy()],'warnings':[]},'2026-11-19',self.c))
    def test_failure(self):
        with patch.object(pulse,'run',return_value=self._result('',1)):
            self.assertNotIn('## token',pulse.render({'segments':[self.segment.copy()],'warnings':[]},'2026-11-19',self.c))
