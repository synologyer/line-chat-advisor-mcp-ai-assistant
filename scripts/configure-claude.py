#!/usr/bin/env python3
"""Preview or save an explicit LINE Desktop/clone target and Claude MCP entry."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent


def private_json(path, value):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.new')
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
            f.write('\n')
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def desktop_config(existing, node, root):
    result = dict(existing)
    entries = dict(result.get('mcpServers', {}))
    entries['work-line-readonly'] = {'command': str(node), 'args': [str(root / 'bin/line-context-relay.mjs')]}
    result['mcpServers'] = entries
    return result


def choose_database(directory, explicit=None, opened=()):
    candidates = [p for p in directory.glob('qw*.edb') if p.is_file() and '_' not in p.name]
    if explicit:
        p = directory / explicit
        if p.name != explicit or p not in candidates:
            raise ValueError('--db-file must be the exact basename of a main database in the selected container')
        return p
    active = [p for p in candidates if str(p) in opened]
    if len(active) == 1:
        return active[0]
    if len(candidates) == 1:
        return candidates[0]
    raise ValueError('Account database is ambiguous. Open the chosen app/account, or explicitly provide --db-file. No account selected.')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--app', type=Path, required=True, help='Exact LINE app or clone path')
    ap.add_argument('--db-file', help='Exact database basename, only needed for ambiguity')
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    app = args.app.expanduser().resolve(strict=True)
    info = plistlib.loads((app / 'Contents/Info.plist').read_bytes())
    bundle = info['CFBundleIdentifier']
    exe = str(app / 'Contents/MacOS' / info['CFBundleExecutable'])
    directory = Path.home() / 'Library/Containers' / bundle / 'Data/Library/Containers/jp.naver.line/Data/db'
    if not directory.is_dir():
        ap.error('The selected app has no supported local LINE database directory.')
    opened = set()
    rows = subprocess.check_output(['/bin/ps', '-axo', 'pid=,comm='], text=True).splitlines()
    for row in rows:
        parts = row.strip().split(None, 1)
        if len(parts) == 2 and parts[1] == exe:
            files = subprocess.run(['/usr/sbin/lsof', '-p', parts[0], '-Fn'], capture_output=True, text=True)
            opened.update(line[1:] for line in files.stdout.splitlines() if line.startswith('n'))
    try:
        selected = choose_database(directory, args.db_file, opened)
    except ValueError as error:
        ap.error(str(error))
    target = dict(app_path=str(app), bundle_id=bundle, db_dir=str(directory), db_filename=selected.name, passive_only=True)
    runtime = ROOT / 'runtime'
    target_file = runtime / 'line-target.json'
    if target_file.exists():
        previous = json.loads(target_file.read_text())
        if any(previous.get(k) != target[k] for k in ('bundle_id', 'db_dir', 'db_filename')):
            ap.error('Another account is already configured here. Use a separate private project installation for the new account.')
    node = shutil.which('node')
    if not node or not (ROOT / '.venv/bin/python3').is_file():
        ap.error('Install Node and run scripts/bootstrap first.')
    config = Path.home() / 'Library/Application Support/Claude/claude_desktop_config.json'
    existing = json.loads(config.read_text()) if config.exists() else {}
    merged = desktop_config(existing, Path(node), ROOT)
    if not args.apply:
        print(json.dumps({'preview': True, 'target': target, 'mcp': merged['mcpServers']['work-line-readonly']}, ensure_ascii=False, indent=2))
        print('Use --apply to save. This never captures keys, signs apps, or sends messages.')
        return
    os.umask(0o077)
    runtime.mkdir(mode=0o700, exist_ok=True)
    runtime.chmod(0o700)
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    for path in (target_file, config):
        if path.exists():
            private_json(runtime / (path.name + '.backup-' + stamp), json.loads(path.read_text()))
    private_json(target_file, target)
    private_json(config, merged)
    print('Configured. Restart Claude Desktop. No key capture, signing or LINE restart performed.')


if __name__ == '__main__':
    main()
