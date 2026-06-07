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

- Runs a self-contained demo race loop.
- Uses deterministic seeded race simulation.
- Shows registration, countdown, racing, callouts, photo finish, results, and reset.
- Uses code-native PixiJS placeholder art so no assets are required.
- Includes a `/control` placeholder documenting the future operator surface.

## Known Limitations

- `/control` is not wired to the scene or bot yet.
- `mode=local` and `mode=hosted` are labels only in this POC.
- The scene winner is browser-simulated in demo mode.
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
