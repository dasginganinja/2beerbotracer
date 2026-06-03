# Track Racer Bot Response Bank

Draft response copy for chat messages. Templates use:

- `{author}` for the user who entered.
- `{position}` for their car number in the queue.
- `{lineup}` for the comma-separated race lineup, rendered lowercase in chat responses.

## Successful Entry

Each successful entry response should tell the user their car number.

1. `You're in, {author}. You're car #{position}.`
2. `Locked in, {author}. You're car #{position}.`
3. `Added to the grid, {author}. You're car #{position}.`
4. `You're on the list, {author}. Car #{position} is yours.`
5. `Registered, {author}. You've got car #{position}.`
6. `Welcome to the queue, {author}. You're car #{position}.`
7. `Got you, {author}. You're in car #{position}.`
8. `Grid slot claimed, {author}. You're car #{position}.`

## Start

Each start response should introduce the lineup without changing the actual names included.

1. `Starting grid locked: {lineup}`
2. `Rolling out with: {lineup}`
3. `Race lineup is set: {lineup}`
4. `Sending these racers: {lineup}`
5. `On the line: {lineup}`
6. `Next race is ready for: {lineup}`
7. `Grid is live: {lineup}`
8. `Race call: {lineup}`

## Duplicate Entry

Each duplicate entry response should remind the user that they are already registered and tell them their car number.

1. `You're already in, {author}. You're car #{position}.`
2. `You're on the grid already, {author}. Car #{position} is yours.`
3. `Hold tight, {author}. You're already car #{position}.`
4. `Already got you, {author}. You're in car #{position}.`
5. `No need to re-enter, {author}. You're car #{position}.`
6. `You're still locked in, {author}. Car #{position} is set.`
7. `Duplicate ignored, {author}. You're already car #{position}.`
8. `You're covered, {author}. Car #{position} is yours.`

## Closed Registration

Used after `!start` locks the race. This response should avoid telling the user they entered and point them to `!entries` instead.

1. `Grid is locked, {author}. Use !entries to check the lineup.`

## Open Entries

Used when a mod runs `!openentries` to reopen registration without clearing the current queue.

1. `Entries are open.`

## Close Entries

Used when a mod runs `!closeentries` to close registration without clearing the current queue.

1. `entries closed`

## Other Engagement Opportunities

These are good candidates for later response variation.

1. Full list: currently tells the user the list is full. This could add a short "try next race" variation.
2. `!clearentries`: currently has one mod-facing confirmation. This could mention that registration is open again.
3. Entry-list-filled stats: currently reports timing and Twitch percentage. This could add one celebratory lead-in.
4. `!commands`: currently reads like a system response. This could be friendlier while staying short.
