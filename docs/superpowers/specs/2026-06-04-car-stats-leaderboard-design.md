# Car Stats Leaderboard Design

## Goal

Add public chat commands that report whether specific car numbers perform better than others across recorded races.

## Commands

`!carstats <number>` reports aggregate performance for one display car number. The command uses `race_entries.display_number`, so car `#69` is treated as the displayed slot already stored for position 29.

Example:

```text
Car #7: 3W / 42R / 7.1%. Best driver: Alice 2W. Last win: Bob.
```

`!carleaderboard` reports the top five display car numbers.

Example:

```text
Top cars: 1. #7 3W/42R 7.1%; 2. #12 2W/38R 5.3%; 3. #69 2W/40R 5.0%.
```

Both commands are public and should appear in `!commands`, `README.md`, and `BOT_DOCUMENTATION.md`.

## Data Semantics

Car stats are not racer stats. They aggregate by car display number across all stored race snapshots:

- `total_races`: number of races where that display car number appeared.
- `wins`: number of completed races won by an entry with that display car number.
- `win_percentage`: `wins / total_races * 100`, rounded to one decimal place.
- `best_driver`: racer name with the most wins from that car number, if any.
- `best_driver_wins`: number of wins for `best_driver`.
- `last_win`: most recent racer name to win from that car number, if any.

Cars with appearances but no wins should still be reportable by `!carstats <number>`.

## Ranking

`!carleaderboard` ranks cars by:

1. wins descending
2. win percentage descending
3. display car number ascending

The leaderboard includes only cars with at least one completed win. If no completed races have winners, the response is:

```text
No completed car winners yet.
```

## Error Handling

If no number is provided:

```text
Usage: !carstats <number>
```

If the argument is not a positive integer:

```text
Usage: !carstats <number>
```

If the car has never appeared in a recorded race:

```text
No races recorded for car #7.
```

## Implementation Notes

Add aggregate query helpers to `race_history.py` and keep chat formatting in `trackracerbot.py`, matching the existing split for racer stats and leaderboard commands. Add focused tests for the database helpers, command routing, fixture replay, and command help text.
