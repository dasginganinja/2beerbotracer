export type RaceState =
  | "BOOT"
  | "IDLE"
  | "REGISTRATION_OPEN"
  | "REGISTRATION_CLOSED"
  | "COUNTDOWN"
  | "RACING"
  | "PHOTO_FINISH"
  | "RESULTS"
  | "RESETTING"
  | "ERROR";

export type Racer = {
  id: string;
  displayName: string;
  color: string;
  slot: number;
  row: 0 | 1;
  column: number;
};

export type DemoRace = {
  raceId: string;
  state: RaceState;
  racers: Racer[];
};

export type RaceResult = {
  racerId: string;
  displayName: string;
  slot: number;
  place: number;
  finishTimeMs: number;
  status: CarStatus;
};

export type RaceFrame = {
  timeMs: number;
  cars: Array<{
    racerId: string;
    progress: number;
    trackOffset: number;
    angle: number;
    status: CarStatus;
    x: number;
    y: number;
    scale: number;
  }>;
};

export type RaceTimelineEvent = {
  type: "chaos";
  chaosType: ChaosType;
  timeMs: number;
  racerId: string;
  message: string;
};

export type SimulatedRace = {
  results: RaceResult[];
  frames: RaceFrame[];
  timeline: RaceTimelineEvent[];
};

type SimulateRaceInput = {
  seed: number;
  racers: Racer[];
  durationMs: number;
  trackAngleDeg?: number;
};

export type CarStatus =
  | "running"
  | "wobbling"
  | "sliding-up"
  | "recovering"
  | "spinning"
  | "pileup"
  | "knocked-out"
  | "side-hung"
  | "self-spun";

export type ChaosType = "bump" | "knockout" | "side-hang" | "self-spin" | "chain-reaction";

type CarRuntime = {
  racer: Racer;
  index: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
  angle: number;
  angularVelocity: number;
  wheelSpeed: number;
  traction: number;
  stability: number;
  mass: number;
  status: CarStatus;
  eliminated: boolean;
  eliminatedAtMs?: number;
  finishScore: number;
  lastChaosType: ChaosType;
  lastChaosAtMs: number;
  pileupContacts: number;
  sideHangEligible: boolean;
};

const SIM_WIDTH = 1210;
const SIM_HEIGHT = 520;
const SIM_SLOT_COLUMNS = 15;
const SIM_SLOT_WIDTH = SIM_WIDTH / SIM_SLOT_COLUMNS;
const SIM_START_HOLD_Y = 446;
const SIM_ROW_SPACING = 70;
const SIM_START_Y = [SIM_START_HOLD_Y, SIM_START_HOLD_Y - SIM_ROW_SPACING] as const;
const SIM_LEFT_SAFE_X = 62;
const SIM_RIGHT_SAFE_X = SIM_WIDTH - 62;
const SIM_OFF_FRONT_Y = -36;
const SIM_STEP_MS = 100;
const SIM_STEP_SECONDS = SIM_STEP_MS / 1000;
const BELT_SPEED_PX_PER_SEC = 132;
const MAX_DRIVE_SPEED_PX_PER_SEC = 148;
const MAX_RECOVERY_SPEED_PX_PER_SEC = 42;
const MAX_LATERAL_SPEED_PX_PER_SEC = 24;
const TRACK_ANGLE_ASSIST_PX_PER_SEC_PER_DEG = 8;
const ACTIVE_YAW_LIMIT_RAD = 0.72;
const SLIDING_YAW_LIMIT_RAD = 0.52;

const DEMO_NAMES = [
  "Natmar",
  "Hotdogman",
  "Judy",
  "Shrek",
  "Ohyeah",
  "GoodVibes",
  "PitBoss",
  "TreadHead",
  "Skidmark",
  "Boosty",
  "ConeDodger",
  "LapSnack",
  "WallTap",
  "BeltBandit",
  "SideGap",
  "NoseWedge",
  "LooseAxle",
  "FloorIt",
  "RumbleStrip",
  "Clipper",
  "SpinCycle",
  "DraftTax",
  "OilPan",
  "Twitchy",
  "LeftHook",
  "RightHook",
  "ChaosMod",
  "LastSlot",
  "Bumper",
  "Wiggle",
];

const DEMO_COLORS = [
  "#f94144",
  "#f3722c",
  "#f8961e",
  "#f9c74f",
  "#90be6d",
  "#43aa8b",
  "#4d908e",
  "#577590",
  "#277da1",
  "#9b5de5",
  "#f15bb5",
  "#00bbf9",
];

const ALLOWED_TRANSITIONS: Record<RaceState, RaceState[]> = {
  BOOT: ["IDLE", "ERROR"],
  IDLE: ["REGISTRATION_OPEN", "ERROR"],
  REGISTRATION_OPEN: ["REGISTRATION_CLOSED", "RESETTING", "ERROR"],
  REGISTRATION_CLOSED: ["COUNTDOWN", "RESETTING", "ERROR"],
  COUNTDOWN: ["RACING", "RESETTING", "ERROR"],
  RACING: ["PHOTO_FINISH", "RESETTING", "ERROR"],
  PHOTO_FINISH: ["RESULTS", "RESETTING", "ERROR"],
  RESULTS: ["RESETTING", "ERROR"],
  RESETTING: ["IDLE", "REGISTRATION_OPEN", "ERROR"],
  ERROR: ["RESETTING"],
};

export function createDemoRace(seed: number): DemoRace {
  const racers = DEMO_NAMES.slice(0, 30).map((name, index) => {
    const slot = index + 1;
    return {
      id: `demo-racer-${index + 1}`,
      displayName: name,
      color: DEMO_COLORS[index % DEMO_COLORS.length],
      slot,
      row: (slot <= 15 ? 0 : 1) as 0 | 1,
      column: (slot - 1) % 15,
    };
  });

  return {
    raceId: `demo-${seed}`,
    state: "REGISTRATION_OPEN",
    racers,
  };
}

export function simulateRace({ seed, racers, durationMs, trackAngleDeg = 2.5 }: SimulateRaceInput): SimulatedRace {
  const random = createRandom(seed);
  const raceAllowsSideHangs = seed % 4 === 0;
  const sideHangLimit = raceAllowsSideHangs ? 1 + (seed % 12 === 0 ? 1 : 0) : 0;
  const trackAngleAssistVelocity = clamp(trackAngleDeg, -4, 8) * TRACK_ANGLE_ASSIST_PX_PER_SEC_PER_DEG;
  let sideHangs = 0;
  const cars = racers.map<CarRuntime>((racer, index) => {
    const slotX = racer.column * SIM_SLOT_WIDTH + SIM_SLOT_WIDTH / 2;
    const rowStagger = racer.row === 0 ? -6 : 6;
    return {
      racer,
      index,
      x: slotX + (random() - 0.5) * 14,
      y: SIM_START_Y[racer.row],
      vx: (random() - 0.5) * 4,
      vy: (random() - 0.5) * 3,
      angle: Math.PI / 2 + (random() - 0.5) * 0.08,
      angularVelocity: 0,
      wheelSpeed: 0.9 + random() * 0.32 + rowStagger / 500,
      traction: 0.72 + random() * 0.24,
      stability: 0.52 + random() * 0.42,
      mass: 0.85 + random() * 0.35,
      status: "running",
      eliminated: false,
      finishScore: 0,
      lastChaosType: "bump",
      lastChaosAtMs: -10_000,
      pileupContacts: 0,
      sideHangEligible: raceAllowsSideHangs && (racer.column <= 1 || racer.column >= 13 || random() > 0.88),
    };
  });
  const frames: RaceFrame[] = [];
  const timeline: RaceTimelineEvent[] = [];
  let lastRunningCount = cars.length;
  let raceEndTimeMs = durationMs;

  for (let timeMs = 0; timeMs <= durationMs; timeMs += SIM_STEP_MS) {
    const runningCars = cars.filter((car) => !car.eliminated);
    if (runningCars.length <= 1 && timeMs > durationMs * 0.2) {
      raceEndTimeMs = timeMs;
      break;
    }

    for (const car of cars) {
      if (car.eliminated || car.status === "side-hung") {
        continue;
      }

      const yawError = normalizeAngle(car.angle - Math.PI / 2);
      const yawEfficiency = clamp(Math.cos(Math.abs(yawError) * 1.8), 0, 1);
      const beltVelocity = -BELT_SPEED_PX_PER_SEC;
      const driveVelocity = MAX_DRIVE_SPEED_PX_PER_SEC * car.wheelSpeed * car.traction * yawEfficiency;
      const holdCorrection = clamp((SIM_START_HOLD_Y - car.y) * 1.45, -MAX_RECOVERY_SPEED_PX_PER_SEC, MAX_RECOVERY_SPEED_PX_PER_SEC);
      const seamPhase = timeMs / 2_700 + seed * 0.01;
      const railBias = car.racer.column <= 2 ? -10 : car.racer.column >= 12 ? 10 : 0;
      const packDrift =
        Math.sin(seamPhase) * 18 +
        Math.sign(Math.sin(seamPhase)) * 6 +
        Math.sin(timeMs / 4_600 + car.racer.row * 0.8) * 5 +
        Math.sin(timeMs / 3_700 + car.racer.column * 0.42) * 4 +
        railBias;
      const lateralCenter = car.racer.column * SIM_SLOT_WIDTH + SIM_SLOT_WIDTH / 2 + packDrift;
      const lateralVelocity = clamp((lateralCenter - car.x) * 0.22 * car.stability, -MAX_LATERAL_SPEED_PX_PER_SEC, MAX_LATERAL_SPEED_PX_PER_SEC);
      const jitterVelocity = (random() - 0.5) * 5;
      const targetVy = beltVelocity + trackAngleAssistVelocity + driveVelocity + holdCorrection;
      const targetVx = lateralVelocity + jitterVelocity + Math.sin(yawError) * driveVelocity * 0.12;

      car.vy += (targetVy - car.vy) * 0.2;
      car.vx += (targetVx - car.vx) * 0.18;
      car.angularVelocity += -yawError * car.stability * 0.45 * SIM_STEP_SECONDS;
      car.angularVelocity *= 0.84;
      car.x += car.vx * SIM_STEP_SECONDS;
      car.y += car.vy * SIM_STEP_SECONDS;
      car.angle += car.angularVelocity * SIM_STEP_SECONDS;

      if (car.x < SIM_LEFT_SAFE_X || car.x > SIM_RIGHT_SAFE_X) {
        const side = car.x < SIM_LEFT_SAFE_X ? -1 : 1;
        car.x = side < 0 ? Math.max(28, car.x) : Math.min(SIM_WIDTH - 28, car.x);
        car.vx -= side * Math.min(Math.abs(car.vx) * 0.55 + 4, 22);
        car.angularVelocity += side * 0.08;
        car.traction = clamp(car.traction - 0.006, 0.05, 1);
      }

      const maxYaw = car.status === "spinning" || car.status === "self-spun" ? 1.05 : ACTIVE_YAW_LIMIT_RAD;
      car.angle = Math.PI / 2 + clamp(normalizeAngle(car.angle - Math.PI / 2), -maxYaw, maxYaw);

      const tractionShock = random() < (1 - car.stability) * 0.006 ? 0.07 : 0;
      if (tractionShock > 0) {
        car.traction = clamp(car.traction - tractionShock, 0.08, 1);
        car.status = "wobbling";
        car.angularVelocity += (random() - 0.5) * 0.28;
      } else if (car.status === "wobbling" && random() < car.stability * 0.12) {
        car.status = "recovering";
        car.traction = clamp(car.traction + 0.14, 0, 1);
      } else if ((car.status === "recovering" || car.status === "wobbling") && car.traction > 0.45) {
        car.status = "running";
      }

      if (Math.abs(yawError) > SLIDING_YAW_LIMIT_RAD) {
        car.traction = clamp(car.traction - 0.055, 0.04, 1);
        car.wheelSpeed = clamp(car.wheelSpeed - 0.035, 0.08, 1.35);
        car.status = car.status === "running" ? "sliding-up" : car.status;
      }

      if (car.y < SIM_START_HOLD_Y - 112 && car.vy < -58 && car.status === "running") {
        car.status = "sliding-up";
      }
      if (car.status === "sliding-up" && random() < car.stability * Math.max(car.traction, 0.2) * 0.08) {
        car.status = "recovering";
        car.wheelSpeed = clamp(car.wheelSpeed + 0.16, 0, 1.35);
        car.traction = clamp(car.traction + 0.22, 0, 1);
      }
    }

    for (let i = 0; i < cars.length; i += 1) {
      for (let j = i + 1; j < cars.length; j += 1) {
        resolveContact(cars[i], cars[j], timeMs, random, timeline);
      }
    }

    for (const car of cars) {
      if (car.eliminated) {
        continue;
      }

      car.x = clamp(car.x, 28, SIM_WIDTH - 28);
      const nearSide = car.x < SIM_LEFT_SAFE_X || car.x > SIM_RIGHT_SAFE_X;
      if (
        nearSide &&
        car.sideHangEligible &&
        sideHangs < sideHangLimit &&
        car.y < SIM_START_HOLD_Y - 120 &&
        car.vy < -44 &&
        random() < 0.22
      ) {
        car.status = "side-hung";
        car.eliminated = true;
        car.eliminatedAtMs = timeMs;
        car.lastChaosType = "side-hang";
        sideHangs += 1;
        pushChaos(timeline, car, timeMs, "side-hang");
      }

      if (car.y < SIM_OFF_FRONT_Y && timeMs > 3_500) {
        const stillRunning = cars.filter((candidate) => !candidate.eliminated).length;
        if (stillRunning > 1) {
          car.status = car.pileupContacts >= 2 ? "pileup" : car.angularVelocity > 0.007 ? "self-spun" : "knocked-out";
          car.eliminated = true;
          car.eliminatedAtMs = timeMs;
          car.lastChaosType = car.pileupContacts >= 2 ? "chain-reaction" : statusToChaosType(car.status);
          pushChaos(timeline, car, timeMs, car.lastChaosType);
        }
      }
    }

    const runningCount = cars.filter((car) => !car.eliminated).length;
    if (runningCount < lastRunningCount - 1) {
      const clusterCar = cars.find((car) => car.lastChaosAtMs === timeMs);
      if (clusterCar) {
        pushChaos(timeline, clusterCar, timeMs, "chain-reaction");
      }
    }
    lastRunningCount = runningCount;

    frames.push(toFrame(timeMs, cars));
  }

  const survivor = cars
    .filter((car) => !car.eliminated)
    .sort((a, b) => b.stability + b.traction - (a.stability + a.traction))[0];
  if (sideHangLimit > 0 && sideHangs === 0) {
    const sideHangCandidate = cars
      .filter((car) => car !== survivor && (car.racer.column <= 1 || car.racer.column >= 13))
      .sort((a, b) => (a.eliminatedAtMs ?? durationMs) - (b.eliminatedAtMs ?? durationMs))[0];
    if (sideHangCandidate) {
      sideHangCandidate.status = "side-hung";
      sideHangCandidate.eliminated = true;
      sideHangCandidate.eliminatedAtMs = Math.min(sideHangCandidate.eliminatedAtMs ?? raceEndTimeMs, raceEndTimeMs * 0.82);
      sideHangCandidate.x = sideHangCandidate.racer.column <= 1 ? SIM_LEFT_SAFE_X - 18 : SIM_RIGHT_SAFE_X + 18;
      sideHangCandidate.y = Math.min(sideHangCandidate.y, SIM_START_HOLD_Y - 150);
      sideHangCandidate.lastChaosType = "side-hang";
      pushChaos(timeline, sideHangCandidate, sideHangCandidate.eliminatedAtMs, "side-hang");
    }
  }
  for (const car of cars) {
    if (car !== survivor && !car.eliminated) {
      car.status = "knocked-out";
      car.eliminated = true;
      car.eliminatedAtMs = raceEndTimeMs;
      car.lastChaosType = "knockout";
      car.y = Math.min(car.y, SIM_OFF_FRONT_Y - 8);
      pushChaos(timeline, car, raceEndTimeMs, "knockout");
    }
  }
  if (survivor) {
    survivor.status = "running";
    survivor.eliminated = false;
    survivor.y = Math.max(survivor.y, SIM_START_HOLD_Y - 18);
    survivor.vy = Math.max(survivor.vy, 0);
    survivor.angle = Math.PI / 2 + clamp(normalizeAngle(survivor.angle - Math.PI / 2), -0.28, 0.28);
  }

  frames.push(toFrame(raceEndTimeMs, cars));

  const orderedCars = [...cars].sort((a, b) => {
    if (!a.eliminated && b.eliminated) return -1;
    if (a.eliminated && !b.eliminated) return 1;
    if ((b.eliminatedAtMs ?? raceEndTimeMs) !== (a.eliminatedAtMs ?? raceEndTimeMs)) {
      return (b.eliminatedAtMs ?? raceEndTimeMs) - (a.eliminatedAtMs ?? raceEndTimeMs);
    }
    return b.stability + b.traction - (a.stability + a.traction);
  });
  const results = orderedCars.map((car, index) => ({
    racerId: car.racer.id,
    displayName: car.racer.displayName,
    slot: car.racer.slot,
    place: index + 1,
    finishTimeMs: Math.round(car.eliminatedAtMs ?? raceEndTimeMs),
    status: car.status === "pileup" ? "knocked-out" : finalStatus(car.status),
  }));

  return { results, frames, timeline };
}

export function getAllowedTransition(from: RaceState, to: RaceState): boolean {
  return ALLOWED_TRANSITIONS[from].includes(to);
}

function createRandom(seed: number): () => number {
  let state = seed >>> 0;
  return () => {
    state += 0x6d2b79f5;
    let value = state;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function normalizeAngle(value: number): number {
  let angle = value;
  while (angle > Math.PI) angle -= Math.PI * 2;
  while (angle < -Math.PI) angle += Math.PI * 2;
  return angle;
}

function statusToChaosType(status: CarStatus): ChaosType {
  if (status === "knocked-out" || status === "pileup") return "knockout";
  if (status === "side-hung") return "side-hang";
  if (status === "self-spun" || status === "spinning") return "self-spin";
  return "bump";
}

function finalStatus(status: CarStatus): CarStatus {
  if (status === "wobbling" || status === "recovering" || status === "sliding-up") return "knocked-out";
  if (status === "spinning") return "self-spun";
  if (status === "pileup") return "knocked-out";
  return status;
}

function resolveContact(
  a: CarRuntime,
  b: CarRuntime,
  timeMs: number,
  random: () => number,
  timeline: RaceTimelineEvent[],
): void {
  if (a.eliminated || b.eliminated || a.status === "side-hung" || b.status === "side-hung") {
    return;
  }

  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const minX = 66;
  const minY = 74;
  if (Math.abs(dx) > minX || Math.abs(dy) > minY) {
    return;
  }

  const overlapX = minX - Math.abs(dx);
  const overlapY = minY - Math.abs(dy);
  const impulse = (overlapX + overlapY) / (minX + minY);
  const directionX = dx === 0 ? (random() > 0.5 ? 1 : -1) : Math.sign(dx);
  const directionY = dy === 0 ? (random() > 0.5 ? 1 : -1) : Math.sign(dy);
  const relativeSpeed = Math.hypot(b.vx - a.vx, b.vy - a.vy);
  const relativeYaw = Math.abs(normalizeAngle(a.angle - b.angle));
  const lateralCompression = Math.abs(dx) > 24 && overlapX > 36;
  const restingBumperContact =
    a.racer.row !== b.racer.row &&
    a.racer.column === b.racer.column &&
    Math.abs(dx) < 44 &&
    Math.abs(dy) > 52 &&
    relativeSpeed < 26 &&
    relativeYaw < 0.24;
  const hardContact = impulse > 0.72 && (relativeSpeed > 40 || relativeYaw > 0.42 || lateralCompression);

  if (restingBumperContact) {
    const sharedVx = (a.vx + b.vx) / 2;
    const sharedVy = (a.vy + b.vy) / 2;
    a.vx = a.vx * 0.7 + sharedVx * 0.3;
    b.vx = b.vx * 0.7 + sharedVx * 0.3;
    a.vy = a.vy * 0.7 + sharedVy * 0.3;
    b.vy = b.vy * 0.7 + sharedVy * 0.3;
    return;
  }

  if (!hardContact) {
    const softImpulse = impulse * 1.8;
    a.vx -= directionX * softImpulse / a.mass;
    b.vx += directionX * softImpulse / b.mass;
    a.vy -= directionY * softImpulse * 0.45 / a.mass;
    b.vy += directionY * softImpulse * 0.45 / b.mass;
    if (impulse > 0.58 && timeMs - a.lastChaosAtMs > 3_000 && timeMs - b.lastChaosAtMs > 3_000) {
      pushChaos(timeline, impulse > 0.68 ? a : b, timeMs, "bump");
    }
    return;
  }

  if (timeMs < 6_000) {
    const earlyImpulse = impulse * 3.2;
    a.vx -= directionX * earlyImpulse / a.mass;
    b.vx += directionX * earlyImpulse / b.mass;
    a.vy -= directionY * earlyImpulse * 0.55 / a.mass;
    b.vy += directionY * earlyImpulse * 0.55 / b.mass;
    a.angularVelocity -= directionX * impulse * 0.06;
    b.angularVelocity += directionX * impulse * 0.06;
    if (impulse > 0.78 && timeMs - a.lastChaosAtMs > 3_000 && timeMs - b.lastChaosAtMs > 3_000) {
      pushChaos(timeline, impulse > 0.84 ? a : b, timeMs, "bump");
    }
    return;
  }

  a.vx -= directionX * impulse * 12 / a.mass;
  b.vx += directionX * impulse * 12 / b.mass;
  a.vy -= directionY * impulse * 9 / a.mass;
  b.vy += directionY * impulse * 9 / b.mass;
  a.angularVelocity -= directionX * impulse * 0.34;
  b.angularVelocity += directionX * impulse * 0.34;

  a.traction = clamp(a.traction - impulse * (0.025 + random() * 0.045), 0.05, 1);
  b.traction = clamp(b.traction - impulse * (0.025 + random() * 0.045), 0.05, 1);
  a.wheelSpeed = clamp(a.wheelSpeed - impulse * 0.035, 0.1, 1.35);
  b.wheelSpeed = clamp(b.wheelSpeed - impulse * 0.035, 0.1, 1.35);

  a.pileupContacts += impulse > 0.72 ? 1 : 0.45;
  b.pileupContacts += impulse > 0.72 ? 1 : 0.45;
  a.status = timeMs > 6_000 && a.pileupContacts > 6 && impulse > 0.72 ? "pileup" : "wobbling";
  b.status = timeMs > 6_000 && b.pileupContacts > 6 && impulse > 0.72 ? "pileup" : "wobbling";

  const front = a.racer.row === 0 && b.racer.row === 1 ? a : b.racer.row === 0 && a.racer.row === 1 ? b : undefined;
  const rear = front === a ? b : front === b ? a : undefined;
  if (
    front &&
    rear &&
    timeMs > 6_000 &&
    rear.y < SIM_START_HOLD_Y - SIM_ROW_SPACING + 16 &&
    Math.abs(front.racer.column - rear.racer.column) <= 1 &&
    impulse > 0.66 &&
    relativeSpeed > 16 &&
    random() < 0.08 + impulse * 0.14
  ) {
    rear.traction = clamp(rear.traction - 0.14, 0.04, 1);
    rear.wheelSpeed = clamp(rear.wheelSpeed - 0.1, 0.08, 1.35);
    rear.status = "sliding-up";
    rear.vy -= 18 + impulse * 14;
    pushChaos(timeline, rear, timeMs, "chain-reaction");
  } else if (impulse > 0.42 && timeMs - a.lastChaosAtMs > 2200 && timeMs - b.lastChaosAtMs > 2200) {
    const chaosType = timeMs > 6_000 && impulse > 0.72 ? "chain-reaction" : "bump";
    pushChaos(timeline, impulse > 0.72 ? a : b, timeMs, chaosType);
  }
}

function pushChaos(
  timeline: RaceTimelineEvent[],
  car: CarRuntime,
  timeMs: number,
  chaosType: ChaosType,
): void {
  if (timeMs - car.lastChaosAtMs < 900 && car.lastChaosType === chaosType) {
    return;
  }

  car.lastChaosAtMs = timeMs;
  car.lastChaosType = chaosType;
  timeline.push({
    type: "chaos",
    chaosType,
    timeMs: Math.round(timeMs),
    racerId: car.racer.id,
    message: buildChaosMessage(car.racer.displayName, chaosType),
  });
}

function toFrame(timeMs: number, cars: CarRuntime[]): RaceFrame {
  return {
    timeMs,
    cars: cars.map((car) => ({
      racerId: car.racer.id,
      progress: clamp(car.y / SIM_HEIGHT, -1, 1),
      trackOffset: clamp((car.x - (car.racer.column * SIM_SLOT_WIDTH + SIM_SLOT_WIDTH / 2)) / 84, -1, 1),
      angle: car.angle - Math.PI / 2,
      status: car.eliminated ? finalStatus(car.status) : car.status,
      x: car.x / SIM_WIDTH,
      y: car.y / SIM_HEIGHT,
      scale: clamp(0.82 + car.y / SIM_HEIGHT * 0.22, 0.82, 1.08),
    })),
  };
}

function buildChaosMessage(displayName: string, chaosType: ChaosType): string {
  if (chaosType === "chain-reaction") return `${displayName} got swept into a pileup`;
  if (chaosType === "knockout") return `${displayName} got taken out on the belt`;
  if (chaosType === "side-hang") return `${displayName} wedged a nose in the side gap`;
  if (chaosType === "self-spin") return `${displayName} spun without needing help`;
  return `${displayName} traded paint and somehow stayed pointed forward`;
}
