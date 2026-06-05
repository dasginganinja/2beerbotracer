# Leaderboard Keycap Ranks Design

## Goal

Make public leaderboard chat output easier to scan by replacing plain numeric rank prefixes with Unicode keycap rank markers.

## Commands

Apply the formatting to both public leaderboard commands:

- `!leaderboard`
- `!carleaderboard`

## Output Format

Use Unicode keycap markers for ranks 1 through 5.

Regular leaderboard example:

```text
Top winners: 1️⃣ Alice 4W/9R 44.4% 2️⃣ Bob 3W/8R 37.5% 3️⃣ Cara 2W/6R 33.3%.
```

Car leaderboard example:

```text
Top cars: 1️⃣ #7 3W/42R 7.1% 2️⃣ #12 2W/38R 5.3% 3️⃣ #69 2W/40R 5.0%.
```

Entries should be separated by a single space. Do not keep semicolons between entries; the keycap markers provide the visual break.

## Unchanged Behavior

Empty-state messages stay unchanged:

```text
No completed winners yet.
No completed car winners yet.
```

Leaderboard ranking, limits, database queries, command names, and command permissions stay unchanged.

## Implementation Notes

Add a small shared rank marker helper in `trackracerbot.py` and use it from both `build_leaderboard_response()` and `build_car_leaderboard_response()`. Update formatter and command tests to assert the new output.
