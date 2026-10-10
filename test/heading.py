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
    env = dict(os.environ, THINGY_AUTH_TOKEN=token)
    result = subprocess.run(['/usr/bin/osascript', '-', *args], input=fixture,
                            text=True, capture_output=True, env=env)
    assert result.returncode != 0
    assert expected in result.stderr
    if token:
        assert token not in result.stdout + result.stderr

reject(['task', 'project', 'News'], '', 'requires THINGY_AUTH_TOKEN')
reject(['task', 'project', ''], 'secret-token-must-stay-private', 'must not be empty')
reject(['task', 'project', 'News'], 'secret-token-must-stay-private', 'could not submit heading move')
print('Passed: missing authorization and empty heading rejection, token-safe dispatch errors.')
