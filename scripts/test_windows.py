import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('restart', Path(__file__).with_name('restart-windows.py'))
restart = importlib.util.module_from_spec(spec)
spec.loader.exec_module(restart)


class RestartTests(unittest.TestCase):
    def test_idle_session_resumes_and_busy_session_is_skipped(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'CLAUDE_CONFIG_DIR': directory}):
            root = Path(directory)
            (root/'sessions').mkdir()
            (root/'sessions/123.json').write_text('{"sessionId":"fixture-session"}')
            (root/'projects/repo').mkdir(parents=True)
            (root/'projects/repo/fixture-session.jsonl').write_text('{}')
            for status, expected in [('working', False), ('blocked', False), ('idle', True)]:
                calls = []
                def rpc(*args):
                    calls.append(args)
                    if args == ('agent', 'list'):
                        return {'agents': [{'pane_id':'fixture','agent':'claude','agent_status':status}]}
                    if args[:2] == ('pane', 'process-info'):
                        return {'process_info': {'foreground_processes': [{'pid':123}]}}
                    return {}
                with patch.object(restart, 'rpc', side_effect=rpc), patch.object(restart.subprocess, 'check_output', return_value='2.1.303 (Claude Code)'), patch.object(restart, 'process_details', return_value=(r'C:\test\versions\2.1.302', 10)), patch.object(restart, 'terminate', return_value=True) as terminate:
                    self.assertFalse(restart.main())
                    self.assertEqual(terminate.called, expected)
                    if expected:
                        self.assertIn(('pane','run','fixture','claude --resume fixture-session'), calls)

    def test_versioned_binaries_and_launcher_installation_time(self):
        launcher = r'C:\Users\test\.local\bin\claude.exe'
        self.assertTrue(restart.outdated((r'C:\Users\test\.local\share\claude\versions\2.1.302', 10), '2.1.303', launcher, 20))
        self.assertFalse(restart.outdated((r'C:\Users\test\.local\share\claude\versions\2.1.303.exe', 10), '2.1.303', launcher, 20))
        self.assertTrue(restart.outdated((launcher, 10), '2.1.303', launcher, 20))
        self.assertFalse(restart.outdated((launcher, 30), '2.1.303', launcher, 20))
        self.assertFalse(restart.outdated((r'C:\unrelated.exe', 10), '2.1.303', launcher, 20))

    @unittest.skipUnless(os.name == 'nt', 'Windows process API')
    def test_native_identity_and_disposable_process_termination(self):
        child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'], creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            details = restart.process_details(child.pid)
            self.assertIsNotNone(details)
            self.assertEqual(os.path.normcase(details[0]), os.path.normcase(sys.executable))
            self.assertFalse(restart.terminate(child.pid, ('different-process', 0)))
            self.assertIsNone(child.poll())
            self.assertTrue(restart.terminate(child.pid, details))
            child.wait(timeout=5)
        finally:
            if child.poll() is None:
                child.terminate()
            child.wait()


if __name__ == '__main__':
    unittest.main()
