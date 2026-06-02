# Agent Rules

## IP Address Handling

- Do not commit personal or external IPv4 addresses in tracked source, docs, tests, or generated fixtures.
- Use `localhost`, `127.0.0.1`, environment variables, config files ignored by git, or generated files in ignored directories instead.
- Before committing or pushing, scan tracked files for IPv4-shaped literals:
  - `git grep -n -E "\b([0-9]{1,3}\.){3}[0-9]{1,3}\b"`
- Investigate every match before committing. `0.0.0.0` is acceptable as a server bind address when clearly documented.
- `browsersource.js` is legacy tracked content and may be left alone unless the user explicitly asks to change it.
- Widget exports that need a deployment IP must be generated into `widget-exports/`, which is ignored by git.

## Widget Source Defaults

- Committed widget HTML should default WebSocket URLs to `ws://localhost:64209`.
- Do not modify committed widget source files to point at an external IP for deployment.
- Use `scripts/update_widget_ip.py` to create deployment-specific widget copies.
