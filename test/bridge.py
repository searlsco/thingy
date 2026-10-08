#!/usr/bin/env python3
"""Exercise pure bridge handlers without sending commands to Things."""
import json
import subprocess
from pathlib import Path

source = Path('lib/things_bridge.applescript').read_text().split('on bucketFor(')[0]
# Make the clock deterministic at a month boundary without a production test hook.
source = source.replace('set parsedDate to current date', '''set parsedDate to current date
    set day of parsedDate to 1
    set year of parsedDate to 2026
    set month of parsedDate to 1
    set day of parsedDate to 31''')
checks = '''
set textValue to "Quotes " & quote & " slash " & character id 92 & return & linefeed & tab
repeat with codePoint from 0 to 31
    set textValue to textValue & character id codePoint
end repeat
set valuesJson to "[" & my jsonString(textValue)
repeat with dateText in {"2026-02-28", "2026-04-30", "2028-02-29", "2026-12-01"}
    set valuesJson to valuesJson & "," & my dateOnly(my parseIsoDate(dateText as text))
end repeat
repeat with dateText in {"2026-02-29", "2026-04-31", "2026-13-01", "2026-00-01", "2026-01-00", "2026-1-01", "not-a-date"}
    set rejected to false
    try
        my parseIsoDate(dateText as text)
    on error
        set rejected to true
    end try
    if not rejected then error "accepted invalid date: " & dateText
end repeat
return valuesJson & "]"
'''
result = subprocess.run(['/usr/bin/osascript', '-'], input=source + checks,
                        text=True, capture_output=True)
if result.returncode:
    raise RuntimeError(result.stderr)
values = json.loads(result.stdout)
assert values[0] == 'Quotes " slash \\' + '\n\n\t' + ''.join('\n' if c == 13 else chr(c) for c in range(32))
assert values[1:] == ['2026-02-28', '2026-04-30', '2028-02-29', '2026-12-01']
print('Passed: JSON control-character round trip, month-boundary dates, invalid dates.')
