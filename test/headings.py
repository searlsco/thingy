#!/usr/bin/env python3
"""Check project-scoped heading validation and confirmed placement."""
import base64
import importlib.util
import os
import subprocess
from pathlib import Path
from unittest.mock import patch

import sys
sys.dont_write_bytecode = True

spec = importlib.util.spec_from_file_location('headings', 'lib/headings.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
name = 'Mail & café\nSecond line'
row = 'heading-id\t' + base64.b64encode(name.encode()).decode()
with patch.object(m, 'shortcut', return_value=[row]), patch.object(m.subprocess, 'run'):
    assert m.heading_list('project-id') == [{'id': 'heading-id', 'name': name}]

receipt = {'id': 'task-id', 'project': {'id': 'project-id'},
           'heading': {'id': 'heading-id', 'name': name}}
with patch.dict(os.environ, THINGY_AUTH_TOKEN='fixture-secret'), \
     patch.object(m, 'heading_list', return_value=[receipt['heading']]), \
     patch.object(m, 'placement', return_value=receipt), \
     patch.object(m.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'Thingy Headings\nThingy Heading\n')) as dispatch:
    assert m.move('task-id', 'project-id', 'heading-id') == dict(receipt, verified=True)
    assert dispatch.call_args.args[0][-1] == name
    assert 'fixture-secret' not in repr(dispatch.call_args)

for headings, requested in [([], 'heading-id'),
                           ([{'id': 'one', 'name': 'Same'}, {'id': 'two', 'name': 'Same'}], 'one')]:
    with patch.dict(os.environ, THINGY_AUTH_TOKEN='fixture-secret'), \
         patch.object(m, 'heading_list', return_value=headings), \
         patch.object(m.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'Thingy Headings\nThingy Heading\n')) as dispatch:
        try:
            m.move('task-id', 'project-id', requested)
            raise AssertionError('invalid heading was accepted')
        except ValueError:
            pass
        assert all(call.args[0][:2] == ['shortcuts', 'list'] for call in dispatch.call_args_list)

with patch.dict(os.environ, THINGY_AUTH_TOKEN='fixture-secret'), \
     patch.object(m, 'heading_list', return_value=[receipt['heading']]), \
     patch.object(m, 'placement', return_value=dict(receipt, heading={'id': 'wrong', 'name': 'Wrong'})), \
     patch.object(m.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'Thingy Headings\nThingy Heading\n')), patch.object(m.time, 'sleep'):
    try:
        m.move('task-id', 'project-id', 'heading-id')
        raise AssertionError('unconfirmed move was accepted')
    except ValueError as error:
        assert 'did not confirm' in str(error)
print('Passed: heading Unicode output, exact project membership, ambiguous title rejection, verified move receipt, unconfirmed move failure.')

# Missing output and malformed output must never turn into a valid empty list.
for payload in [None, '', 'wrong marker\n', m.OUTPUT_MARKER + '\n']:
    def runner(args, **kwargs):
        if payload is not None:
            Path(args[args.index('--output-path') + 1]).write_text(payload)
        return subprocess.CompletedProcess(args, 0)
    with patch.object(m.subprocess, 'run', side_effect=runner):
        if payload == m.OUTPUT_MARKER + '\n':
            assert m.shortcut('Thingy Headings', 'project-id') == []
        else:
            try:
                m.shortcut('Thingy Headings', 'project-id')
                raise AssertionError('invalid output was accepted')
            except ValueError:
                pass

with patch.dict(os.environ, THINGY_AUTH_TOKEN='fixture-secret'), \
     patch.object(m, 'heading_list', return_value=[receipt['heading']]), \
     patch.object(m, 'placement', return_value=receipt) as read_task, \
     patch.object(m.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'Thingy Headings\nThingy Heading\n')) as runner:
    assert m.validate_move('task-id', 'project-id', 'heading-id') == receipt['heading']
    read_task.assert_called_once_with('task-id')
    assert runner.call_args.args[0] == ['shortcuts', 'list']

with patch.dict(os.environ, THINGY_AUTH_TOKEN='fixture-secret'), \
     patch.object(m, 'heading_list') as read_headings, \
     patch.object(m.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'Thingy Headings\n')):
    try:
        m.validate_move('task-id', 'project-id', 'heading-id')
        raise AssertionError('missing verifier was accepted')
    except ValueError:
        pass
    read_headings.assert_not_called()
print('Passed: explicit empty-result marker, missing/malformed output rejection, read-only preflight and missing bridge rejection.')
