#!/usr/bin/env python3
"""Check mutation ordering with all application event targets removed."""
import subprocess
from pathlib import Path

source = Path('lib/things_bridge.applescript').read_text().split('on run argv')[0]
for handler in ('applyChange', 'configureCreatedTask', 'createTask'):
    start = source.index('on ' + handler + '(')
    end = source.index('end ' + handler, start)
    body = source[start:end]
    boundary = 'tell application "Things3"'
    assert boundary in body, 'missing mutation boundary: ' + handler
    body = body.replace(boundary, 'error "mutation boundary reached"\n\t' + boundary, 1)
    source = source[:start] + body + source[end:]

# Dictionary terminology is available at compilation, but every target is the
# fixture itself. A regression can reach a sentinel, never a real application.
source = source.replace('tell application "Things3"',
                        'using terms from application "Things3"\n\ttell me')
source = source.replace('end tell', 'end tell\n\tend using terms from')
assert 'tell application' not in source

checks = '''
on rejectInput(caseName)
    try
        if caseName is "apply-date" then
            my applyChange("unused", "standalone", "", "2026-02-30", "")
        else if caseName is "apply-deadline" then
            my applyChange("unused", "standalone", "", "inbox", "2026-02-30")
        else if caseName is "configure-date" then
            my configureCreatedTask("unused", "notes", "standalone", "", "2026-02-30")
        else if caseName is "create-date" then
            my createTask("title", "notes", "standalone", "", "2026-02-30")
        else if caseName is "create-kind" then
            my createTask("title", "notes", "invalid", "", "inbox")
        end if
    on error messageText
        if messageText contains "invalid date" or messageText contains "destination kind must" then return
        error caseName & ": " & messageText
    end try
    error "input accepted: " & caseName
end rejectInput
on run
    repeat with caseName in {"apply-date", "apply-deadline", "configure-date", "create-date", "create-kind"}
        my rejectInput(caseName as text)
    end repeat
    return "Passed: invalid inputs rejected before mutation boundaries."
end run
'''
result = subprocess.run(['/usr/bin/osascript', '-'], input=source + checks,
                        text=True, capture_output=True)
if result.returncode:
    raise RuntimeError(result.stderr)
print(result.stdout.strip())
