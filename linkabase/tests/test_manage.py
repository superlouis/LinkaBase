"""Lifecycle safety checks, using mocked processes (no real process is killed)."""
import _bootstrap
import unittest,tempfile,json,os
from pathlib import Path
from unittest.mock import patch,MagicMock
import manage
class LifecycleTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.runtime=Path(self.tmp.name)
  self.patches=[patch.object(manage,'RUNTIME',self.runtime),patch.object(manage,'STATE',self.runtime/'processes.json')]
  for p in self.patches:p.start()
 def tearDown(self):
  for p in self.patches:p.stop()
  self.tmp.cleanup()
 def test_pid_reuse_never_matches(self):
  proc=MagicMock();proc.create_time.return_value=123;proc.status.return_value='running'
  with patch.object(manage.psutil,'Process',return_value=proc):
   self.assertIsNone(manage.process({'pid':1234,'created':122}));self.assertIs(manage.process({'pid':1234,'created':123}),proc)
 def test_start_tracks_both_services(self):
  proc=MagicMock(pid=1234);identity=MagicMock();identity.create_time.return_value=42
  with patch.object(manage.subprocess,'Popen',return_value=proc) as popen,patch.object(manage.psutil,'Process',return_value=identity),patch.object(manage,'process',return_value=identity),patch.object(manage.time,'sleep'),patch.object(manage.socket,'socket'):
   manage.start_locked();self.assertEqual(popen.call_count,2);self.assertEqual(len(manage.records()),2)
   commands=[x.args[0] for x in popen.call_args_list];self.assertTrue(any('streamlit' in cmd for cmd in commands));self.assertTrue(any('uvicorn' in cmd for cmd in commands))
 def test_running_does_not_spawn_duplicates(self):
  manage.STATE.write_text(json.dumps({'app':{'pid':1,'created':1},'editor':{'pid':2,'created':2}}))
  with patch.object(manage,'process',return_value=MagicMock()),patch.object(manage.subprocess,'Popen') as popen:
   manage.start_locked();popen.assert_not_called()
 def test_stop_ignores_reused_pid(self):
  manage.STATE.write_text(json.dumps({'app':{'pid':1,'created':1}}))
  with patch.object(manage,'process',return_value=None),patch.object(manage.psutil,'wait_procs') as wait:
   manage.stop_locked();wait.assert_not_called();self.assertFalse(manage.STATE.exists())
if __name__=='__main__':unittest.main()
