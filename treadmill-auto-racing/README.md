# Treadmill Auto Racing POC

Browser-based OBS scene prototype for the Treadmill Auto Racing segment.

## Commands

```powershell
npm install
npm test
npm run build
npm run dev -- --port 5173
```

## URLs

```text
http://127.0.0.1:5173/scene?mode=demo
http://127.0.0.1:5173/control
```

Tuning URL:

```text
http://127.0.0.1:5173/scene?mode=demo&trackAngleDeg=6
```

OBS Browser Source starting point:

```text
http://127.0.0.1:5173/scene?mode=demo
```

Recommended OBS source size:

```text
Width: 1920
Height: 1080
FPS: 60
```

## Current POC

- Runs a self-contained demo treadmill loop.
- Uses deterministic seeded simulation for 30 starting slots in two close rows of 15.
- Shows registration, countdown, belt motion, grounded down-facing cars on the bottom yellow line, upward slide-offs, bumps, chain reactions, rare side hangs, callouts, one-survivor results, and reset.
- Models treadmill speed explicitly: the belt carries cars up-screen, wheel drive pushes down-screen when cars are aligned, and sideways cars lose drive efficiency.
- Uses a deeper perspective treadmill view with a long belt, tapered rails, stronger distance scaling, and cars with visible front/nose profiles.
- Uses larger cars on a narrower belt so the pack reads as side-by-side cars instead of strict lanes.
- Runs a multi-pass simulation step: belt/incline/wheel forces, global pack/seam pressure, repeated contact resolution, rail/front-wall enforcement, then event/status derivation.
- Uses an increased impact-response tuning path so hard contacts transfer force and chain through the pack in a few seconds instead of slowly over many frames.
- Allows rail-side stacks up to four cars per side in high side-hang races.
- Supports `trackAngleDeg` as a tuning knob for how much the slight treadmill incline helps cars resist early slide-back. Default is `6`.
- Ramps belt speed from 0mph to a 2mph-equivalent start speed, holds that through 60 seconds, then ramps toward a 10mph-equivalent speed.
- Gives each car stable rolling traits keyed to its racer/slot: wheel speed, traction, stability, wobble, rolling resistance, yaw loss, and recovery.
- Shows a physics debug panel with belt speed, startup ramp, track angle, rolling resistance, yaw wheel-speed loss/recovery, bumper compression, seam shift, trait variance, early-upset chance, impact speed, chain spread, active/sliding/eliminated counts, average wheel speed, and average traction.
- Uses code-native PixiJS placeholder art so no assets are required.
- Includes a `/control` placeholder documenting the future operator surface.

## Known Limitations

- `/control` is not wired to the scene or bot yet.
- `mode=local` and `mode=hosted` are labels only in this POC.
- The scene winner/status order is browser-simulated in demo mode.
- The physics model is simplified. It does not yet simulate each wheel or metal material properties directly; it approximates those effects with stable per-car traits, wheel speed, traction, yaw loss, low rolling resistance, hard bumper compression limits, startup load, and contact damping.
- Car statuses are broadcast/event labels derived from continuous motion fields where possible; they are not intended to be a hard finite-state machine for every small physical change.
- Real `trackracerbot` WebSocket integration is deferred to the next phase.
- Sound, custom branding, transparent compositing QA, and asset polish are deferred.

## Review Notes

Design notes:

- `../docs/superpowers/specs/2026-06-07-treadmill-auto-racing-design.md`
- `../docs/superpowers/specs/2026-06-07-treadmill-auto-racing-decisions.md`

Important implementation files:

- `src/main.ts`
- `src/scene/TreadmillScene.ts`
- `src/simulation/raceSimulation.ts`
- `src/simulation/raceSimulation.test.ts`
