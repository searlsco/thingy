# Thingy

Thingy is a macOS CLI for Things 3. Keep commands and JSON compatible with the
existing interface. Use only the supported AppleScript interface and Things URL scheme; never read
or write Things' private database. Address existing tasks by exact id.

The CLI is `bin/thingy`, its bridge is `lib/things_bridge.applescript`, and
`VERSION` owns the release version. Homebrew installs the complete tree in
libexec and exposes the CLI through an executable wrapper.

Run `script/test` after CLI changes. Check bridge compilation with
`osacompile` on a Mac with Things installed. Live verification should read
containers or existing tasks, never mutate personal tasks just to test.

This is a public repository. Do not name private consumers or include private
paths or personal configuration in code, documentation, commits, or releases.
See README.md for release steps.
