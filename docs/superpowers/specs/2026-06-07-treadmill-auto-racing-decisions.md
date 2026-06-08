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

Refinement: The loop now runs in multiple passes: force integration, global pack/seam pressure, repeated contact resolution, rail/front-wall enforcement, then event/status derivation. This is closer to a fluid-like pack simulation without committing to a full rigid-body engine yet.

Second refinement: Collision response should not feel slow-motion. Hard contacts now engage at lower thresholds, transfer more velocity/angular force, accumulate pileup pressure faster, and let disturbed rear-pack cars resolve into chain eliminations within a few seconds.

### Derive car statuses from physics

Decision: Treat car statuses as broadcast/event labels derived from continuous motion fields where possible, not as the primary finite-state machine for every physical change.

Reason: The physical behavior is event-driven. Wheel speed, traction, yaw, velocity, pileup pressure, and eliminated/side-hung flags should drive status labels, not the other way around.

### Make orientation part of the physics, not just the art

Decision: The car's yaw changes its effective drive. When a car rotates too far away from nose-down alignment, its wheels stop countering the belt well and the belt carries it upward/off the far end.

Reason: A sideways car should not float or crab-walk in place. It should lose useful rolling direction, slide with the belt, and either recover traction or get eliminated.

### Treat slots as starting positions, not lanes

Decision: The POC should use a narrower belt, larger cars, faint slot guides, and weak lateral centering so the field reads as a pack of cars side by side.

Reason: The real treadmill does not have strict lanes. Cars are close enough to bump, shove, and shift together, with the second row tight against the first row's bumpers.

Refinement: The pack is still exactly 15 cars wide. The second row sits close behind the first row without visual overlap; it should not push through the first row unless a front-row car falls back and opens/contact creates a real interaction.

### Make the side rails part of normal race behavior

Decision: The simulation should bias edge cars into hard side rails and let cars collect/stack at the sides before rare side-gap hangs.

Reason: Reference footage shows side pressure is a normal feature of the race, not only a rare special event. The center may open while side groups stay jammed.

Refinement: Rail stacks are supported up to four cars per side. High side-hang races can force a small side stack so the visual behavior appears in demo mode, while the cap prevents unlimited rail clutter.

### Treat the yellow line as the front boundary

Decision: The bottom yellow line is the near/front limit of the active belt area. Cars point toward it, but active car noses should not cross it.

Reason: The prior sim used the yellow line as the car center target, which let the rendered noses extend below the front boundary and into the track-direction label area.

### Add a track angle tuning knob

Decision: Demo mode accepts `trackAngleDeg`, defaulting to 6 degrees. The angle adds down-screen assist against the belt so stable cars do not immediately slide back at race start.

Reason: Hot Wheels rolling resistance is low, and the physical treadmill has a slight uphill angle near the exit. The sim needs a simple knob for that effect before the rest of the friction model is fully tuned.

### Ramp treadmill speed

Decision: Demo belt speed starts at 0mph, ramps to a 2mph-equivalent start speed, holds that through 60 seconds, then ramps toward a 10mph-equivalent value.

Reason: The real race has a startup transient as the treadmill comes up to speed. That startup load gives weak rollers and twitchier cars a believable chance to wobble or lose momentum before the later speed ramp.

### Add stable car traits

Decision: Each car gets stable rolling traits keyed to its racer/slot rather than the race seed: wheel speed, traction, stability, wobble, rolling resistance, yaw loss, and recovery.

Reason: Some real cars are naturally better or worse rollers. Race seeds should change incident timing and interaction patterns, but the same car should broadly feel like the same car across races.

### Allow bounded early pack incidents

Decision: During the 2mph hold, race-seeded severe stumbles can turn a front-row lost-momentum event into a real knockout and disturb adjacent row-two cars. The distribution is bounded so some races start clean and some produce early pack incidents.

Reason: The previous model had visible wobble but no real incidents until roughly 70-90 seconds. The segment needs a nonzero chance of early pack chaos without making every race collapse immediately.

### Separate parked bumper contact from real hits

Decision: Front/rear cars that are close and aligned should share/damp velocity instead of generating repeated damaging collision impulses. Chain-reaction callouts are delayed until a car has actually drifted back far enough for the contact to behave like a real incident.

Reason: The two rows are intentionally close together at the line. Treating that resting proximity as a collision every frame caused immediate pileups before any visible shift happened.

Refinement: Contact handling must include positional separation and active-belt boundary enforcement. Velocity-only collision response lets cars overlap visually even when the event logic thinks they collided.

Second refinement: Starting row spacing must be based on the rear car nose meeting the front car tail, not half-car center spacing. Bumper compression is capped to a few simulated pixels because metal bumpers do not squash deeply.

### Expose physics knobs in-scene

Decision: The POC scene shows a compact physics debug panel with current belt speed, startup ramp, track angle, angle assist, rolling resistance, yaw wheel-speed loss/recovery, bumper compression, contact bounce, seam shift, trait variance, early-upset chance, impact speed, chain spread, active/sliding/eliminated counts, average wheel speed, and average traction.

Reason: The physical model is still an approximation. Showing the knobs makes tuning conversations concrete and prevents hidden assumptions about friction, wheel speed, or collision surfaces.

Current limitation: The simulation does not model each wheel or metal material properties directly. It uses stable per-car traits, wheel speed, traction, yaw loss, rolling resistance, startup load, bumper compression caps, and contact damping as the tunable proxy.

### Deepen the camera perspective

Decision: Render the treadmill as a long perspective belt with a narrower far end, tapered rails, stronger distance scaling, and cars with visible front/nose profiles.

Reason: Reference footage is not a flat overhead track. The camera sees the near start line, a long belt receding away, rail depth, and the front profiles of staged cars.

### Make HUD copy phase-aware

Decision: "Speeding up for more chaos" appears only during the post-60-second ramp toward the next belt speed. Normal racing uses neutral copy, and active incidents use chaos/incident copy.

Reason: The text should describe what the belt is actually doing. Saying it is speeding up during the 2mph hold is misleading.

### Keep POC assets code-native

Decision: Use Pixi `Graphics` and text for placeholder art.

Reason: This avoids asset loading risk and keeps the first OBS proof lightweight. Real art and spritesheets can come after the race flow feels engaging.

### Keep notes uncommitted unless requested

Decision: Checkpoint commits are useful before major concept pivots.

Reason: The initial oval-style POC was committed as `5b2c5b1` before changing the model to true treadmill racing.
