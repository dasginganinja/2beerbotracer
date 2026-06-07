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

### Correct visual metaphor to physical treadmill racing

Decision: Cars stage near the front/bottom, closest-to-camera side of the treadmill in two rows of 15 on a wide belt, not an oval track.

Reason: The real segment assigns users to one of 30 cars. The treadmill speed generally holds cars on the yellow line closest to the camera until they bump, slow down, spin, get knocked out, or wedge near a side gap. The scene should recreate that format instead of implying circuit racing. Cars should point down toward the bottom of the scene, the belt should move toward the top, and failed cars should slide toward the top/off the far end. Side-gap hangs should be uncommon, while pileups and chain reactions should be common enough to sell the chaos.

### Treat result order as survival/status

Decision: The demo simulation ranks cars by survival and stability, with exactly one final `running` survivor and the rest ending as `knocked-out`, `side-hung`, or `self-spun`.

Reason: Treadmill racing continues until only one car remains viable on the belt, not until cars complete laps.

### Move from scripted outcomes to fixed-step friction logic

Decision: The simulation should run a deterministic fixed-step loop with explicit belt speed, wheel drive speed, traction, friction/damping, collision impulses, recovery chance, pileup pressure, and rare side-gap checks.

Reason: The real race behavior comes from cars losing or recovering momentum while the belt carries them toward the front. Scripted preassigned outcomes were too artificial and could not represent cars speeding back up, pileups, or front-row failures taking out cars behind them.

### Make orientation part of the physics, not just the art

Decision: The car's yaw changes its effective drive. When a car rotates too far away from nose-down alignment, its wheels stop countering the belt well and the belt carries it upward/off the far end.

Reason: A sideways car should not float or crab-walk in place. It should lose useful rolling direction, slide with the belt, and either recover traction or get eliminated.

### Keep POC assets code-native

Decision: Use Pixi `Graphics` and text for placeholder art.

Reason: This avoids asset loading risk and keeps the first OBS proof lightweight. Real art and spritesheets can come after the race flow feels engaging.

### Keep notes uncommitted unless requested

Decision: Checkpoint commits are useful before major concept pivots.

Reason: The initial oval-style POC was committed as `5b2c5b1` before changing the model to true treadmill racing.
