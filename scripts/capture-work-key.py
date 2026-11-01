#!/usr/bin/env python3
"""Explicit local capture for the configured running clone; no signing or login."""
import argparse
import json
import os
from pathlib import Path
import plistlib
import shlex
import subprocess

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-debug-scan', action='store_true')
    args = parser.parse_args()
    if not args.confirm_debug_scan:
        parser.error('This may pause or crash the selected clone. Confirm explicitly before running.')
    target = json.loads((ROOT / 'runtime/line-target.json').read_text())
    app = Path(target['app_path']).resolve(strict=True)
    info = plistlib.loads((app / 'Contents/Info.plist').read_bytes())
    if info['CFBundleIdentifier'] != target['bundle_id']:
        raise RuntimeError('Configured clone identity changed')
    executable = str(app / 'Contents/MacOS' / info['CFBundleExecutable'])
    rows = subprocess.check_output(['/bin/ps', '-axo', 'pid=,comm='], text=True).splitlines()
    pids = [line.strip().split(None, 1)[0] for line in rows if len(line.strip().split(None, 1)) == 2 and line.strip().split(None, 1)[1] == executable]
    if len(pids) != 1:
        raise RuntimeError('Expected exactly one configured clone main process')
    os.umask(0o077)
    capture = ROOT / 'runtime/key-capture'
    capture.mkdir(mode=0o700, parents=True, exist_ok=True)
    capture.chmod(0o700)
    candidate = capture / 'candidates.txt'
    status = capture / 'scan-status.json'
    log = capture / 'lldb.log'
    if any(p.exists() for p in (candidate, status, log)):
        raise RuntimeError('Previous private capture artifacts exist; review them before retrying')
    helper = ROOT / 'runtime/bin/keychain-store'
    if not helper.is_file():
        raise RuntimeError('Compile the Keychain helper first')
    env = dict(os.environ, LINE_KEY_CANDIDATES_PATH=str(candidate), LINE_KEY_SCAN_STATUS_PATH=str(status))
    scanner = ROOT / 'src/key-capture/lldb_scan.py'
    signature = subprocess.check_output(['/usr/bin/codesign', '-dv', str(app)], stderr=subprocess.STDOUT)
    try:
        with log.open('w') as output:
            result = subprocess.run(['/usr/bin/lldb', '--no-lldbinit', '--batch', '--attach-pid', pids[0], '-o', 'command script import ' + shlex.quote(str(scanner)), '-o', 'line_scan', '-o', 'detach'], env=env, stdout=output, stderr=subprocess.STDOUT)
        if status.is_file():
            scan = json.loads(status.read_text())
            print(json.dumps({k: scan[k] for k in ('candidateCount', 'bytesScanned', 'timeLimitReached', 'byteLimitReached') if k in scan}), flush=True)
        if result.returncode:
            print(json.dumps({'ok': False, 'error': 'debug_scan_failed', 'appSignatureChanged': False}))
            return 1
        # Validator opens a stable copy of the explicitly configured DB and stores
        # only a verified key through the existing Login Keychain helper.
        return subprocess.run([str(ROOT / '.venv/bin/python3'), str(ROOT / 'src/key-capture/validate_candidates.py'), str(candidate)]).returncode
    finally:
        for path in (candidate, status, log):
            path.unlink(missing_ok=True)
        after = subprocess.check_output(['/usr/bin/codesign', '-dv', str(app)], stderr=subprocess.STDOUT)
        if after != signature:
            raise RuntimeError('App signature changed unexpectedly')


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        print(json.dumps({'ok': False, 'error': type(error).__name__}))
        raise SystemExit(1)
