#!/usr/bin/env python3
"""Linux regression: /proc version wins over the foreground comm name."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest

SCRIPT = Path(__file__).with_name('restart-all.sh')


@unittest.skipUnless(Path('/proc/self/exe').exists() and shutil.which('cc'), 'needs Linux /proc and a C compiler')
class RestartTests(unittest.TestCase):
    def run_case(self, version, status='idle', resume=False):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            binary = home / version
            source = home / 'wait.c'
            source.write_text('#include <unistd.h>\nint main(void) { for (;;) pause(); }\n')
            subprocess.run(['cc', str(source), '-o', str(binary)], check=True, capture_output=True)
            proc = subprocess.Popen([str(binary)])
            # Reap promptly so the script's kill -0 polling observes exit.
            threading.Thread(target=proc.wait, daemon=True).start()
            try:
                bin_dir = home / 'bin'
                bin_dir.mkdir()
                (bin_dir / 'claude').symlink_to(home / '2.1.303')
                sessions = home / '.claude/sessions'
                sessions.mkdir(parents=True)
                (sessions / f'{proc.pid}.json').write_text(json.dumps({'sessionId': 'fixture-session'}))
                if resume:
                    projects = home / '.claude/projects/fixture'
                    projects.mkdir(parents=True)
                    (projects / 'fixture-session.jsonl').write_text('{}\n')
                mock = bin_dir / 'herdr'
                mock.write_text('''#!/usr/bin/python3
import json,os,sys
from pathlib import Path
a=sys.argv[1:]
if a[:2]==['agent','list']:
 print(json.dumps({'result':{'agents':[{'agent':'claude','agent_status':os.environ['TEST_STATUS'],'pane_id':'fixture'}]}}))
elif a[:2]==['pane','process-info']:
 print(json.dumps({'result':{'process_info':{'foreground_processes':[{'pid':int(os.environ['TEST_PID']),'name':'claude'}]}}}))
else:
 with (Path(os.environ['HOME'])/'calls').open('a') as f: f.write(json.dumps(a)+'\\n')
''')
                mock.chmod(0o700)
                env = dict(os.environ, HOME=str(home), PATH=str(bin_dir)+':/usr/bin:/bin', HERDR_BIN_PATH=str(mock), TEST_PID=str(proc.pid), TEST_STATUS=status)
                result = subprocess.run(['sh', str(SCRIPT)], env=env, capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
                calls = [json.loads(line) for line in (home/'calls').read_text().splitlines()]
                restarted = [a for a in calls if a[:2] == ['pane','run']]
                return restarted, proc.poll()
            finally:
                if proc.poll() is None:
                    proc.terminate()
                proc.wait()

    def test_old_linux_binary_resumes_its_session(self):
        calls, status = self.run_case('2.1.302', resume=True)
        self.assertEqual(calls, [['pane','run','fixture','claude --resume fixture-session']])
        self.assertIsNotNone(status)

    def test_current_binary_is_not_restarted(self):
        calls, status = self.run_case('2.1.303')
        self.assertEqual(calls, [])
        self.assertIsNone(status)

    def test_unknown_binary_is_not_terminated(self):
        calls, status = self.run_case('unknown-binary')
        self.assertEqual(calls, [])
        self.assertIsNone(status)

    def test_busy_binary_is_not_terminated(self):
        calls, status = self.run_case('2.1.302', status='working')
        self.assertEqual(calls, [])
        self.assertIsNone(status)


if __name__ == '__main__':
    unittest.main()
