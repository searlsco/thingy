# Thingy

A command-line interface to Things 3 on macOS. Data commands print JSON and use
Things' supported AppleScript interface and URL scheme, never its private database.

## Install

```sh
brew install searlsco/tap/thingy
thingy --version
thingy inbox
```

Things 3 must be installed. On the first data command, macOS may request
permission for the calling application to automate Things. Run data commands
in the signed-in user's session.

## Commands

```text
thingy inbox
thingy today
thingy project ID
thingy selected
thingy search QUERY
thingy containers
thingy show ID
thingy apply ID KIND DEST_ID WHEN DEADLINE
thingy move-heading ID PROJECT_ID HEADING
thingy complete ID
thingy cancel ID
thingy append-notes ID TEXT
thingy create TITLE NOTES KIND DEST_ID WHEN
thingy create-empty TITLE
thingy configure-created ID NOTES KIND DEST_ID WHEN
thingy create-project TITLE NOTES AREA_ID
```

`KIND` is `project`, `area`, or `standalone`. `DEST_ID` is an exact container id,
or an empty string for standalone tasks. `WHEN` is `today`, `inbox`, `anytime`,
`someday`, or `YYYY-MM-DD`. `DEADLINE` is `YYYY-MM-DD`, `none` to clear it, or an
empty string to preserve it. `AREA_ID` may be an empty string for no area.
Use `thingy help` for the command reference.

Before changing a task, read it with `show` and address it by exact id. Mutation
commands return JSON; `create-empty` and `configure-created` return the id,
which can be verified with `show`. The two-step creation commands let a caller
save the new id before configuring the task, so it can retry configuration
without creating duplicates.

`project` reads open tasks by exact project id. `selected` reads the tasks
currently selected in the Things UI, including a selected range. Neither
command includes heading membership: Things' supported AppleScript interface
does not expose headings.

`move-heading` uses the [Things URL scheme](https://culturedcode.com/things/support/articles/2803573/)
to move a task to an existing heading title in an exact project. Enable Things
URLs in Things Settings → General and obtain the token under Manage. Provide
it through the `THINGY_AUTH_TOKEN` environment variable. The token is never
passed in process arguments or printed by Thingy.

The command returns a JSON submission receipt with `submitted: true`, not a
verified placement. URL handling is asynchronous; invalid authorization can
be rejected by Things, and a missing heading is silently ignored. Verify the
heading and result in the Things UI. Heading creation and heading reads are
not supported by these commands.

## Update

```sh
brew update
brew upgrade searlsco/tap/thingy
```

These commands can run in a nightly update job. Updating needs no reboot.

## Development and releases

Run `script/test` for CLI checks using a fake AppleScript runner and pure
JSON/date handler checks (Python 3 required), and
`osacompile -o /tmp/thingy.scpt lib/things_bridge.applescript` on a Mac with
Things installed to check AppleScript compilation. Live read verification can
use `bin/thingy containers`; tests do not change real tasks.

`VERSION` is the version source. For a release, update it, run the checks,
commit, tag `v<VERSION>`, and push the branch and tag. Publish a GitHub release,
then update `Formula/thingy.rb` in the tap with the tag archive URL and SHA-256.
Install the formula and verify `thingy --version` and `brew test thingy`.
