#!/usr/bin/env python3
"""Read headings through the installed, supported Things Shortcuts actions."""
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent.parent


def shortcut(name, item_id):
    with tempfile.TemporaryDirectory(prefix='thingy-') as directory:
        source = Path(directory) / 'input.txt'
        output = Path(directory) / 'output.txt'
        source.write_text(item_id)
        result = subprocess.run(['shortcuts', 'run', name, '--input-path', str(source),
                                 '--output-path', str(output)], capture_output=True, timeout=30)
        if result.returncode:
            raise ValueError(f'{name} could not run; import the bundled shortcut with thingy install-headings')
        if not output.exists():
            return []
        return output.read_text().rstrip('\n').splitlines()


def heading_list(project_id):
    # Resolve exact project before querying its headings.
    subprocess.run(['osascript', str(ROOT / 'lib/things_bridge.applescript'),
                    'project', project_id], check=True, stdout=subprocess.DEVNULL, timeout=30)
    headings = []
    for line in shortcut('Thingy Headings', project_id):
        if not line:
            continue
        fields = line.split('\t')
        if len(fields) != 2 or not fields[0]:
            raise ValueError('invalid output from Thingy Headings shortcut')
        headings.append({'id': fields[0], 'name': base64.b64decode(fields[1], validate=True).decode()})
    return headings


def placement(task_id):
    rows = shortcut('Thingy Heading', task_id)
    if len(rows) != 1:
        raise ValueError('task heading placement could not be read')
    fields = rows[0].split('\t')
    if len(fields) != 4 or fields[0] != task_id:
        raise ValueError('invalid output from Thingy Heading shortcut')
    return {'id': fields[0], 'project': {'id': fields[1]},
            'heading': {'id': fields[2], 'name': base64.b64decode(fields[3], validate=True).decode()}}


def move(task_id, project_id, heading_id):
    if not os.environ.get('THINGY_AUTH_TOKEN'):
        raise ValueError('move-heading-id requires THINGY_AUTH_TOKEN from Things URL settings')
    headings = heading_list(project_id)
    chosen = next((h for h in headings if h['id'] == heading_id), None)
    if not chosen:
        raise ValueError('heading does not exist in the selected project')
    if sum(h['name'] == chosen['name'] for h in headings) != 1:
        raise ValueError('heading title is ambiguous in the selected project')
    subprocess.run(['osascript', str(ROOT / 'lib/things_bridge.applescript'),
                    'move-heading', task_id, project_id, chosen['name']], check=True,
                   stdout=subprocess.DEVNULL, timeout=30)
    # URL delivery is asynchronous. A bounded read-after-write verifies placement.
    for attempt in range(3):
        current = placement(task_id)
        if current['project']['id'] == project_id and current['heading']['id'] == heading_id:
            return dict(current, verified=True)
        if attempt < 2:
            time.sleep(0.3)
    raise ValueError('Things did not confirm the requested heading placement')


def main(argv):
    if argv == ['install-headings']:
        for name in ['Thingy Headings', 'Thingy Heading']:
            subprocess.run(['open', str(ROOT / 'shortcuts' / f'{name}.shortcut')], check=True)
        return
    if len(argv) == 2 and argv[0] == 'headings' and argv[1]:
        result = heading_list(argv[1])
    elif len(argv) == 2 and argv[0] == 'heading' and argv[1]:
        result = placement(argv[1])
    elif len(argv) == 4 and argv[0] == 'move-heading-id' and all(argv[1:]):
        result = move(*argv[1:])
    else:
        raise ValueError('usage: thingy headings PROJECT_ID | heading ID | move-heading-id ID PROJECT_ID HEADING_ID | install-headings')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except (ValueError, subprocess.SubprocessError, OSError) as error:
        print(f'thingy: {error}', file=sys.stderr)
        sys.exit(1)
