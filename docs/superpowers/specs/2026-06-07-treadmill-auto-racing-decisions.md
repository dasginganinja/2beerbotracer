# Treadmill Auto Racing Decision Log

## 2026-06-07

### Build a browser scene, not a bot rewrite

Decision: The POC lives in a new `treadmill-auto-racing/` frontend folder. The existing Python bot remains unchanged.

Reason: The current bot already handles chat entries, moderator commands, local WebSocket overlays, and race history. The fastest useful proof is the OBS scene.

### Use PixiJS with Vite and TypeScript

Decision: Use Vite + TypeScript + PixiJS v8 for `/scene`.

Reason: The scene is a 2D animated broadcast package. Pixi gives direct control over cars, overlays, particles, and frame timing without the heavier assumptions of Phaser.

### Use deterministic browser simulation for demo mode

Decision: `/scene?mode=demo` decides race order locally from seed and entrants.

Reason: Demo mode must work without backend dependencies. The simulation will be isolated and tested so it can later be replaced or guided by server-authoritative results.

### Choose treadmill oval visual metaphor

Decision: Cars race on a treadmill-shaped oval with broadcast overlays.

Reason: It keeps the treadmill joke visible while making position changes, finish line, and leaderboard updates easy to read.

### Keep POC assets code-native

Decision: Use Pixi `Graphics` and text for placeholder art.

Reason: This avoids asset loading risk and keeps the first OBS proof lightweight. Real art and spritesheets can come after the race flow feels engaging.

### Keep notes uncommitted unless requested

Decision: Write docs and code locally, but do not commit automatically.

Reason: The user asked for reviewable morning notes, not a git commit. If a commit is requested later, scan tracked files for IPv4 literals first per `AGENTS.md`.
