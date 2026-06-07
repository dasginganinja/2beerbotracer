# Treadmill Auto Racing Browser Scene Design

## Product Brief

Treadmill Auto Racing is a browser-based OBS scene for a livestream race segment. Viewers enter through chat commands handled by `trackracerbot`, then OBS shows a broadcast-style animated race with named cars, position changes, chaos events, a finish, and results.

The first proof should be fun without backend work: `/scene?mode=demo` runs fake entrants, race flow, simulation, callouts, leaderboard, and reset locally in the browser. Later modes can connect to the existing bot WebSocket and then a richer hosted backend.

## Recommended Visual Direction

Use a treadmill-shaped oval: tiny toy race cars loop around a treadmill belt with exaggerated broadcast overlays. This gives the segment a distinct identity, supports position changes cleanly, and reads well at 1920x1080.

Rejected alternatives:

- Straight treadmill lanes: very readable, but finish and position changes feel less dynamic.
- Full NASCAR fake broadcast: polished, but loses the treadmill joke.
- Serious simulator: wrong tone for a chat minigame.

## Recommended Architecture

Frontend:

- Vite + TypeScript.
- PixiJS v8 for the scene canvas.
- Plain DOM/CSS for `/control` where form controls matter more than canvas animation.
- A small state machine and deterministic demo race simulation outside Pixi so it can be tested.

Backend/bot:

- Existing `trackracerbot.py` continues to own Twitch chat, entry commands, registration, race history, and moderator commands.
- Existing `ws://localhost:64209` remains the compatibility target.
- A future bridge can translate current `send_queue` / `latest_winner` responses into richer scene events.

Modes:

- `demo`: no backend, fake entrants and timed race loop.
- `local`: connect to `ws://localhost:64209`, initially through compatibility polling.
- `hosted`: connect to channel-specific scene/control backend later.

## OBS Scene Specification

Target:

- 1920x1080, 60fps.
- Browser Source URL: `/scene?mode=demo` for POC.
- No permissions required.
- Optional transparent mode later via `?transparent=1`.

Pixi rendering layers:

- Background: treadmill belt, stage, lane/track markings.
- Race world: cars, nameplates, skid/smoke/confetti.
- Broadcast HUD: title, registration prompt, countdown, lap/segment, current leader.
- Position tower: live ordering.
- Callouts: chaos and announcer banners.
- Results: podium and finish order.
- Debug overlay: hidden by default, enabled with `?debug=1`.

State machine:

- `BOOT`
- `IDLE`
- `REGISTRATION_OPEN`
- `REGISTRATION_CLOSED`
- `COUNTDOWN`
- `RACING`
- `PHOTO_FINISH`
- `RESULTS`
- `RESETTING`
- `ERROR`

The POC can skip `WAITING_FOR_BOT` in demo mode and use it only for local/hosted connection modes.

Reload/reconnect:

- Demo mode starts from a clean loop on reload.
- Local/hosted mode should request a full snapshot after reconnect.
- If disconnected during a race, the scene should continue visual playback when it has enough local state and show a small connection badge, not hard-fail the broadcast.

## Control Panel Specification

The POC may include a minimal `/control` page shell after the demo scene exists. Required eventual controls:

- Open registration.
- Close registration.
- Start countdown.
- Start race.
- Reset scene.
- Add/remove test racer.
- Trigger chaos event.
- Replay finish.
- Emergency stop/reset.

State display:

- Connection state.
- Current race ID.
- Current scene state.
- Entrants.
- Last event.

Safety:

- Reset and emergency stop should be visually distinct.
- Destructive controls should require a second click or short confirmation once real bot control is connected.

## Race Lifecycle Specification

Registration:

- Show `Type !race to join`.
- Display entrants on a starting grid.
- Demo mode auto-populates 8-12 racers.

Countdown:

- Close registration.
- Show big countdown lights and text.
- Cars idle with slight movement.

Race:

- Cars move around the treadmill oval.
- Simulation decides progress, speed, boost/slip events, and final order.
- Position tower updates live.
- Callout banners appear for chaos events.

Finish:

- Slow down near the line.
- Emphasize winner and close battles.
- Freeze or briefly replay the finish.

Results:

- Show podium/top 3 and full finish order.
- Keep readable for OBS.
- Reset automatically in demo mode after a delay, with manual reset later.

## Event Protocol v0

Use envelope messages so versioning and snapshots are clean:

```ts
type SceneEnvelope =
  | { v: 0; type: "scene.hello"; channel?: string; mode: "demo" | "local" | "hosted" }
  | { v: 0; type: "scene.snapshot"; race: RaceSnapshotDto }
  | { v: 0; type: "registration.opened"; raceId: string }
  | { v: 0; type: "registration.closed"; raceId: string }
  | { v: 0; type: "racer.joined"; raceId: string; racer: RacerDto }
  | { v: 0; type: "racer.removed"; raceId: string; racerId: string }
  | { v: 0; type: "race.countdown.started"; raceId: string; seconds: number }
  | { v: 0; type: "race.started"; raceId: string; seed: number; results?: ResultDto[] }
  | { v: 0; type: "race.chaos"; raceId: string; chaosType: ChaosType; targetRacerId?: string }
  | { v: 0; type: "race.finished"; raceId: string; results: ResultDto[] }
  | { v: 0; type: "scene.reset"; raceId?: string }
  | { v: 0; type: "scene.error"; code: string; message: string; recoverable: boolean };
```

For MVP demo mode, the frontend decides results from seed and entrants. For competitive rewards or persistent standings, the server should eventually send authoritative results and the frontend should animate toward them.

## MVP Implementation Plan

Milestone 1: Project shell and docs

- Add `treadmill-auto-racing/` Vite/Pixi app.
- Add design/decision docs.
- Add test setup for deterministic simulation.

Milestone 2: Demo simulation

- Define scene states and transitions.
- Generate fake racers.
- Deterministically simulate progress and final results from seed.
- Emit chaos callouts.

Milestone 3: Pixi scene

- Render 1920x1080 treadmill oval.
- Render cars/nameplates.
- Render HUD, countdown, leaderboard, callouts, results.
- Run `/scene?mode=demo`.

Milestone 4: Control shell

- Add `/control` route with state display and disabled/fake controls.
- Wire demo reset/start actions if time allows.

Milestone 5: Verification

- Unit tests for simulation/state rules.
- Production build.
- Browser smoke check if local server can run.

## Risk Register

- OBS refresh: reload loses local demo state; acceptable for POC, needs snapshot for real mode.
- OBS browser lifecycle: source shutdown can break persistent races; document recommended settings.
- Performance: too much dynamic `Text` or redrawn `Graphics` can hurt 60fps; update text only on value changes and keep graphics stable.
- Bot disconnects: scene should show degraded connection state and keep rendering current race.
- Fairness: demo/browser authority is fine for entertainment, not rewards.
- Asset loading: POC uses vector placeholder art to avoid startup downloads.
- Scope creep: defer accounts, hosted auth, betting, persistent progression, custom assets, and sound.

## Open Questions

- Should the real segment winner come from the physical treadmill race, the bot, or the browser animation?
- Should the first live version use `!start` as race start, or add separate open/close/countdown commands?
- How long should one race run on stream: 30, 45, or 60 seconds?
- Should registration remain tied to the existing 30-entry queue, or should the animated race cap entrants lower for readability?
- Should the visual theme be 2Beer-branded immediately, or stay generic until the mechanic is proven?
