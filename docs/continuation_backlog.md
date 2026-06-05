# Continuation Backlog

Use this file for follow-up changes that should not be rushed live.

## Planned Soon

### Add cooldown for `!streamracestats`

Goal: keep `!streamracestats` public while preventing chat spam.

Initial design notes:

- Add a public-command cooldown for `!streamracestats`.
- Suggested cooldown: 60-120 seconds.
- Moderators should bypass the cooldown.
- Cooldown should suppress duplicate output quietly or reply with a short remaining-time message. Decide before implementation.
- Tests should cover viewer cooldown, moderator bypass, and no cooldown interaction with other commands.

## Bugs To Investigate

### `entries-widget-1col.html` finished animation may not show

Observed concern: the one-column widget may not display the finished/full animation correctly.

Investigation notes:

- Compare finished/full-state logic between `entries-widget.html` and `entries-widget-1col.html`.
- Check whether CSS classes, animation keyframes, and DOM IDs match the JavaScript state changes.
- Verify with the in-app browser or Playwright-style screenshot/pixel checks if available.
- Add a targeted widget test if the existing Node test can cover the finished-state transition.

## Current Branch Context

Recent related work is on `codex/car-stats-leaderboard`:

- `!carstats <number>`
- `!carleaderboard`
- keycap rank markers for leaderboards
- `!streamracestats`
