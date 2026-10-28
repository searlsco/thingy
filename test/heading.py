#!/usr/bin/env python3
"""Check heading errors without opening URLs or contacting Things."""
import os
import subprocess
from pathlib import Path

source = Path('lib/things_bridge.applescript').read_text()
pure = source.split('on bucketFor(')[0]
handler = source[source.index('on moveHeading('):source.index('end moveHeading') + len('end moveHeading')]
# Strip read-only identity validation and replace URL dispatch with a failure
# containing the token. Only local fixture code executes.
start = handler.index('\ttell application "Things3"')
end = handler.index('\tend tell', start) + len('\tend tell')
handler = handler[:start] + handler[end:]
handler = handler.replace('open location my headingUrl(taskId, projectId, headingTitle, authToken)',
                          'error "dispatch failure: " & authToken')
assert 'tell application' not in handler and 'open location' not in handler
fixture = pure + handler + '''
on run argv
    return my moveHeading(item 1 of argv, item 2 of argv, item 3 of argv)
end run
'''

def reject(args, token, expected):
    env = dict(os.environ, THINGS_AUTH_TOKEN="", THINGY_AUTH_TOKEN=token)
    result = subprocess.run(['/usr/bin/osascript', '-', *args], input=fixture,
                            text=True, capture_output=True, env=env)
    assert result.returncode != 0
    assert expected in result.stderr
    if token:
        assert token not in result.stdout + result.stderr

reject(['task', 'project', 'News'], '', 'requires THINGS_AUTH_TOKEN')
reject(['task', 'project', ''], 'secret-token-must-stay-private', 'must not be empty')
reject(['task', 'project', 'News'], 'secret-token-must-stay-private', 'could not submit heading move')
print('Passed: missing authorization and empty heading rejection, token-safe dispatch errors.')

# Return the selected token only in this isolated fixture, without dispatching it.
selection_fixture = fixture.replace('error "dispatch failure: " & authToken', 'return authToken')
for primary, legacy, expected in [
    ('primary-token', '', 'primary-token'),
    ('', 'legacy-token', 'legacy-token'),
    ('primary-token', 'legacy-token', 'primary-token'),
    (None, 'legacy-token', 'legacy-token'),
]:
    env = dict(os.environ, THINGY_AUTH_TOKEN=legacy)
    env.pop('THINGS_AUTH_TOKEN', None)
    if primary is not None:
        env['THINGS_AUTH_TOKEN'] = primary
    result = subprocess.run(['/usr/bin/osascript', '-', 'task', 'project', 'News'],
                            input=selection_fixture, text=True, capture_output=True, env=env)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == expected
print('Passed: primary token, legacy fallback, empty/unset fallback, and token precedence.')
