# Stream Race Stats Design

## Goal

Add a public `!streamracestats` command that summarizes the current stream's races in one or two compact chat messages.

## Time Window

The command summarizes races from the stream-day noon cutoff through the time the command is run.

- Use the bot host's local timezone.
- If the command runs at or after local noon, use today's noon as the cutoff.
- If the command runs before local noon, use yesterday's noon as the cutoff.
- Select races by `started_at_utc >= cutoff`.
- Do not include the words "since noon" in chat output.

## Message 1

Message 1 is always sent. It reports race counts and a chronological winner list.

Format:

```text
Stream Race Stats 🏁 Races: 12 total / 10 completed / 1 pending / 1 skipped 🏆 Winners: 1️⃣ Alice #7 2️⃣ Bob #12 3️⃣ Alice #4 4️⃣ Cara #69
```

Rules:

- `total` is all races in the window.
- `completed` is races with completed winners.
- `pending` is races still pending.
- `skipped` combines skipped and unknown statuses.
- `Winners` lists completed race winners in chronological race order.
- Each winner entry uses the existing keycap rank markers.
- Each winner entry includes racer display name and winning display car number.
- If there are no completed winners, use `🏆 Winners: none`.

## Message 2

Message 2 is sent only when there is at least one completed winner in the window.

Format:

```text
Stream Leaders 🏆 Drivers: Alice 2W / Bob 1W / Cara 1W 🚗 Cars: #7 2W / #12 1W / #69 1W 🎯 Unique winners: 8
```

Rules:

- `Drivers` lists the top stream winners by wins descending, then name ascending.
- `Cars` lists the top stream winning car numbers by wins descending, then car number ascending.
- Keep each list compact, with slash separators.
- Cap each list at three entries.
- `Unique winners` counts distinct normalized winner names.

## Message Limit

The command sends no more than two chat messages.

If no races are found in the window, send one message:

```text
Stream Race Stats 🏁 Races: 0 total / 0 completed / 0 pending / 0 skipped 🏆 Winners: none
```

## Implementation Notes

Add stream-window aggregate helpers to `race_history.py` and keep chat formatting in `trackracerbot.py`. Reuse the existing leaderboard keycap marker helper for winner list numbering. Add tests for the noon cutoff, race status counts, winner list with car numbers, leader summaries, empty stream output, and command routing.
