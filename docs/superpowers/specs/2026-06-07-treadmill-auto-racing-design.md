# Treadmill Auto Racing Browser Scene Design

## Product Brief

Treadmill Auto Racing is a browser-based OBS scene for a livestream race segment. Viewers enter through chat commands handled by `trackracerbot`, then OBS shows a broadcast-style recreation of the treadmill race: 30 small cars staged in two close-packed rows of 15, held roughly in place by treadmill speed while bumps, self-spins, knockouts, and side-gap hangs continue until only one car survives.

The first proof should be fun without backend work: `/scene?mode=demo` runs fake entrants, race flow, simulation, callouts, survival board, and reset locally in the browser. Later modes can connect to the existing bot WebSocket and then a richer hosted backend.

## Recommended Visual Direction

Use the real treadmill format: a belt with two close rows of 15 numbered cars staged on the yellow line at the bottom/closest-to-camera side of the treadmill. Cars point down toward the bottom of the scene, the belt direction is toward the top of the scene, and the second row sits close behind the first row's bumpers rather than in a clearly separated lane. The starting slots are only staging positions; during the race the cars should read as a tight pack that can drift, bump, and shift together. Belt motion is shown with horizontal stripes scrolling upward. As cars get knocked, slow down, or catch the belt friction, they naturally slide toward the top/off the far end of the belt. That can take out individual cars, small groups, or large swaths when cars catch on each other.

Rejected alternatives:

- Oval/circuit racing: visually familiar, but wrong for the actual segment.
- Full NASCAR fake broadcast: polished, but loses the treadmill mechanism.
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

- Background: treadmill belt, stage, side gaps, subtle slot markings, belt direction.
- Belt texture: horizontal stripes scroll upward to show treadmill motion toward the top of the screen.
- Race world: cars, nameplates, skid/smoke/confetti.
- Broadcast HUD: title, registration prompt, countdown, race timer, survivor count.
- Survival board: live status ordering.
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
- Demo mode auto-populates 30 racers across two rows of 15.

Countdown:

- Close registration.
- Show big countdown lights and text.
- Cars idle with slight movement.

Race:

- Cars start on the yellow line at the bottom/closest-to-camera side and jitter around their assigned slots while belt speed holds them roughly in place.
- Failed cars slide toward the top/off the far end as their wheels slow or catch belt friction.
- The simulation uses explicit screen-space speeds: belt speed carries cars up-screen, wheel drive pushes cars back down-screen only while the car is pointed nose-down, and a hold correction keeps stable cars near the yellow line.
- A `trackAngleDeg` tuning knob adds down-screen assist to model the slight physical treadmill incline and low Hot Wheels rolling resistance.
- Yaw matters: a car that gets too sideways loses drive efficiency and is carried upward unless traction and wheel speed recover.
- Cars scale down as they move toward the top/far end of the treadmill.
- Slot guides are faint and lateral centering is weak; the field should move like a dense pack, not 15 strict lanes.
- Incidents can chain through nearby cars, producing small pileups or large group knockouts.
- Side-gap hangs are rare probability events, not a normal outcome every race.
- Demo simulation now uses a deterministic fixed-step model with per-car wheel speed, traction, stability, velocity, angular velocity, and contact impulses.
- Simulation decides survival, bumps, self-spins, side hangs, knockouts, and final result order until one survivor remains.
- Survival board updates live.
- Callout banners appear for chaos events.

Finish:

- Freeze the belt and emphasize the sole survivor versus knocked-out or hung cars.
- Show callouts for the decisive incidents.

Results:

- Show the sole survivor and incident statuses.
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

DTO additions for the treadmill format:

```ts
type RacerDto = {
  id: string;
  displayName: string;
  slot: number; // 1-30
  row: 0 | 1;
  column: number; // 0-14
  color?: string;
  avatarUrl?: string;
  source?: "twitch" | "bot" | "test";
};

type CarStatus = "running" | "knocked-out" | "side-hung" | "self-spun";
type ChaosType = "bump" | "knockout" | "side-hang" | "self-spin";

type ResultDto = {
  racerId: string;
  place: number;
  slot: number;
  displayName: string;
  status: CarStatus;
  finishTimeMs?: number;
};
```

For MVP demo mode, the frontend decides survival/results from seed and entrants, with exactly one final survivor. For real stream operation, the bot or operator should eventually send authoritative winner/status information when the scene needs to match the physical treadmill result.

## MVP Implementation Plan

Milestone 1: Project shell and docs

- Add `treadmill-auto-racing/` Vite/Pixi app.
- Add design/decision docs.
- Add test setup for deterministic simulation.

Milestone 2: Demo simulation

- Define scene states and transitions.
- Generate 30 fake racers with fixed slots.
- Deterministically simulate treadmill drift, bumps, side hangs, knockouts, self-spins, and one-survivor final results from seed.
- Emit treadmill-specific chaos callouts.

Milestone 3: Pixi scene

- Render 1920x1080 treadmill belt with 30 slots in two rows.
- Use larger cars on a narrower belt so side-by-side spacing reads clearly in OBS.
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
- Physical/result matching: demo/browser authority is fine for entertainment, but real mode should be able to accept operator/bot results from the actual treadmill.
- Asset loading: POC uses vector placeholder art to avoid startup downloads.
- Scope creep: defer accounts, hosted auth, betting, persistent progression, custom assets, and sound.

## Open Questions

- Should the real segment winner/statuses come from the physical treadmill race, the bot, an operator control panel, or browser animation?
- Should the first live version use `!start` as race start, or add separate open/close/countdown commands?
- How long should one treadmill run last on stream: 30, 45, or 60 seconds?
- Should all 30 entrants always render, or should empty slots remain visibly empty when fewer viewers join?
- Should the visual theme be 2Beer-branded immediately, or stay generic until the mechanic is proven?
