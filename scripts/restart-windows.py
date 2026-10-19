"""Restart outdated, idle native Claude processes on Windows."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


def rpc(*args):
    raw = subprocess.check_output([os.environ.get('HERDR_BIN_PATH', 'herdr'), *args],
                                  encoding='utf-8', errors='replace', creationflags=subprocess.CREATE_NO_WINDOW)
    return json.loads(raw)['result']


def process_details(pid):
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return None
    try:
        size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        times = [wintypes.FILETIME() for _ in range(4)]
        if not kernel.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)) or not kernel.GetProcessTimes(handle, *[ctypes.byref(t) for t in times]):
            return None
        stamp = ((times[0].dwHighDateTime << 32) | times[0].dwLowDateTime) / 10_000_000 - 11644473600
        return buffer.value, stamp
    finally:
        kernel.CloseHandle(handle)


def outdated(details, latest, launcher, installed_at):
    image, started = details
    match = re.search(r'[\\/]versions[\\/](\d+\.\d+\.\d+(?:-[\w.-]+)?)(?:\.exe)?$', image)
    if match:
        return match.group(1) != latest
    # A running launcher can retain its old mapped image after installation.
    # Only identify it as outdated when it predates the new binary's creation.
    if os.path.normcase(os.path.abspath(image)) == os.path.normcase(os.path.abspath(launcher)):
        return started < installed_at
    return False


def terminate(pid, expected):
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x100000 | 0x1000 | 1, False, pid)
    if not handle:
        return False
    try:
        if process_details(pid) != expected:
            return False
        return bool(kernel.TerminateProcess(handle, 0)) and kernel.WaitForSingleObject(handle, 10000) == 0
    finally:
        kernel.CloseHandle(handle)


def main(only=''):
    launcher = shutil.which('claude') or str(Path.home() / '.local/bin/claude.exe')
    output = subprocess.check_output([launcher, '--version'], text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    latest = re.search(r'\d+\.\d+\.\d+(?:-[\w.-]+)?', output).group(0)
    binary = Path.home() / '.local/share/claude/versions' / latest
    installed_at = getattr(binary.stat(), 'st_birthtime', binary.stat().st_ctime) if binary.exists() else 0
    config = Path(os.environ.get('CLAUDE_CONFIG_DIR') or Path.home() / '.claude')
    done = failed = 0
    for agent in rpc('agent', 'list')['agents']:
        pane = agent['pane_id']
        if agent.get('agent') != 'claude' or agent.get('agent_status') != 'idle' or (only and pane != only):
            continue
        processes = rpc('pane', 'process-info', '--pane', pane)['process_info'].get('foreground_processes', [])
        if not processes:
            continue
        pid = int(processes[0]['pid'])
        details = process_details(pid)
        if not details or not outdated(details, latest, launcher, installed_at):
            continue
        session_file = config / 'sessions' / f'{pid}.json'
        try:
            sid = json.loads(session_file.read_text(encoding='utf-8')).get('sessionId', '')
        except (OSError, ValueError):
            sid = ''
        # Recheck agent state immediately before termination.
        current = rpc('agent', 'list')['agents']
        if not any(a.get('pane_id') == pane and a.get('agent') == 'claude' and a.get('agent_status') == 'idle' for a in current):
            continue
        if not terminate(pid, details):
            failed += 1
            continue
        command = 'claude'
        if re.fullmatch(r'[A-Za-z0-9-]+', sid) and any((config / 'projects').glob('*/' + sid + '.jsonl')):
            command += ' --resume ' + sid
        rpc('pane', 'run', pane, command)
        done += 1
    rpc('notification', 'show', 'Agent Restart', '--body', f'{done} restarted ({latest}), {failed} failed')
    print(f'{done} restarted; {failed} failed')
    return bool(failed)


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else ''))
