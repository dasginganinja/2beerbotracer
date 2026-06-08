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
  beltSpeedMph: number;
  metrics: RaceFrameMetrics;
  cars: Array<{
    racerId: string;
    progress: number;
    trackOffset: number;
    angle: number;
    status: CarStatus;
    x: number;
    y: number;
    scale: number;
    stackIndex?: number;
  }>;
};

export type RaceFrameMetrics = {
  active: number;
  sliding: number;
  eliminated: number;
  averageWheelSpeed: number;
  averageTraction: number;
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
  tuning: PhysicsTuning;
};

export type PhysicsTuning = {
  beltStartMph: number;
  beltFullMph: number;
  beltStartupRampMs: number;
  beltHoldMs: number;
  beltRampMs: number;
  trackAngleDeg: number;
  trackAngleAssistPxPerSecPerDeg: number;
  rollingResistancePerSecond: number;
  yawWheelLossPerSecond: number;
  yawRecoverPerSecond: number;
  maxBumperCompressionPx: number;
  contactRestitution: number;
  seamShiftPx: number;
  carTraitVariance: number;
  earlyUpsetChance: number;
  collisionImpulseMultiplier: number;
  chainSpreadChance: number;
  chainReactionThreshold: number;
};

export type StableCarTraits = {
  baseWheelSpeed: number;
  traction: number;
  stability: number;
  wobble: number;
  rollingResistance: number;
  yawLoss: number;
  recovery: number;
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
  traits: StableCarTraits;
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
  earlyUpsetAtMs?: number;
  earlyUpsetUsed: boolean;
  earlyUpsetCanEliminate: boolean;
  boggedUntilMs: number;
  sideStackIndex?: number;
};

const SIM_WIDTH = 1210;
const SIM_HEIGHT = 520;
const SIM_SLOT_COLUMNS = 15;
const SIM_SLOT_WIDTH = SIM_WIDTH / SIM_SLOT_COLUMNS;
const SIM_FRONT_LINE_Y = 446;
const SIM_CAR_NOSE_TO_CENTER = 66;
const SIM_CAR_TAIL_TO_CENTER = 48;
const SIM_START_HOLD_Y = SIM_FRONT_LINE_Y - SIM_CAR_NOSE_TO_CENTER;
const SIM_MAX_BUMPER_COMPRESSION = 5;
const SIM_ROW_SPACING = SIM_CAR_NOSE_TO_CENTER + SIM_CAR_TAIL_TO_CENTER - SIM_MAX_BUMPER_COMPRESSION;
const SIM_START_Y = [SIM_START_HOLD_Y, SIM_START_HOLD_Y - SIM_ROW_SPACING] as const;
const SIM_LEFT_SAFE_X = 62;
const SIM_RIGHT_SAFE_X = SIM_WIDTH - 62;
const SIM_SIDE_RAIL_PADDING = 24;
const SIM_OFF_FRONT_Y = -150;
const SIM_STEP_MS = 50;
const SIM_STEP_SECONDS = SIM_STEP_MS / 1000;
const SIM_STEP_CHANCE_SCALE = SIM_STEP_MS / 100;
const MPH_TO_PX_PER_SEC = 36;
const BELT_START_MPH = 2;
const BELT_FULL_MPH = 10;
const BELT_STARTUP_RAMP_MS = 9_000;
const BELT_HOLD_MS = 60_000;
const BELT_RAMP_MS = 60_000;
const MAX_DRIVE_SPEED_PX_PER_SEC = 152;
const MAX_RECOVERY_SPEED_PX_PER_SEC = 42;
const MAX_LATERAL_SPEED_PX_PER_SEC = 24;
const TRACK_ANGLE_ASSIST_PX_PER_SEC_PER_DEG = 8;
const ACTIVE_YAW_LIMIT_RAD = 0.72;
const SLIDING_YAW_LIMIT_RAD = 0.52;
const DEFAULT_PHYSICS_TUNING_BASE = {
  beltStartMph: BELT_START_MPH,
  beltFullMph: BELT_FULL_MPH,
  beltStartupRampMs: BELT_STARTUP_RAMP_MS,
  beltHoldMs: BELT_HOLD_MS,
  beltRampMs: BELT_RAMP_MS,
  trackAngleAssistPxPerSecPerDeg: TRACK_ANGLE_ASSIST_PX_PER_SEC_PER_DEG,
  rollingResistancePerSecond: 0.012,
  yawWheelLossPerSecond: 0.22,
  yawRecoverPerSecond: 0.08,
  maxBumperCompressionPx: SIM_MAX_BUMPER_COMPRESSION,
  contactRestitution: 0.18,
  seamShiftPx: 18,
  carTraitVariance: 1,
  earlyUpsetChance: 0.26,
  collisionImpulseMultiplier: 1.38,
  chainSpreadChance: 0.48,
  chainReactionThreshold: 4.2,
} as const;

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

export function getStableCarTraits(racer: Pick<Racer, "id" | "slot">): StableCarTraits {
  const random = createRandom(hashString(`${racer.id}:${racer.slot}`));
  const weakRoller = random() < 0.18;
  const twitchy = random() < 0.22;
  const smooth = random() < 0.18;
  const baseWheelSpeed = 0.78 + random() * 0.42 - (weakRoller ? 0.22 : 0) + (smooth ? 0.08 : 0);
  const stability = 0.46 + random() * 0.48 - (twitchy ? 0.13 : 0) + (smooth ? 0.08 : 0);
  const wobble = 0.45 + random() * 0.9 + (twitchy ? 0.45 : 0) + (weakRoller ? 0.18 : 0);

  return {
    baseWheelSpeed: clamp(baseWheelSpeed, 0.46, 1.32),
    traction: clamp(0.64 + random() * 0.28 - (weakRoller ? 0.08 : 0), 0.46, 0.96),
    stability: clamp(stability, 0.34, 0.98),
    wobble: clamp(wobble, 0.25, 1.8),
    rollingResistance: clamp(0.75 + random() * 0.65 + (weakRoller ? 0.38 : 0), 0.65, 1.95),
    yawLoss: clamp(0.75 + random() * 0.75 + (twitchy ? 0.45 : 0), 0.65, 2.05),
    recovery: clamp(0.65 + random() * 0.7 + (smooth ? 0.3 : 0) - (weakRoller ? 0.22 : 0), 0.42, 1.75),
  };
}

export function simulateRace({ seed, racers, durationMs, trackAngleDeg = 6 }: SimulateRaceInput): SimulatedRace {
  const random = createRandom(seed);
  const tuning: PhysicsTuning = {
    ...DEFAULT_PHYSICS_TUNING_BASE,
    trackAngleDeg: clamp(trackAngleDeg, -4, 8),
  };
  const raceAllowsSideHangs = seed % 4 === 0;
  const sideHangLimit = raceAllowsSideHangs ? 2 + (seed % 12 === 0 ? 2 : 0) : 0;
  const trackAngleAssistVelocity = tuning.trackAngleDeg * tuning.trackAngleAssistPxPerSecPerDeg;
  let sideHangs = 0;
  const cars = racers.map<CarRuntime>((racer, index) => {
    const slotX = racer.column * SIM_SLOT_WIDTH + SIM_SLOT_WIDTH / 2;
    const rowStagger = racer.row === 0 ? -6 : 6;
    const traits = getStableCarTraits(racer);
    const raceCarRandom = createRandom(hashString(`${seed}:${racer.id}:${racer.slot}`));
    const earlyCandidate =
      racer.row === 0 &&
      raceCarRandom() <
        tuning.earlyUpsetChance * clamp((traits.wobble + traits.rollingResistance - traits.recovery + 0.5) / 2.1, 0.28, 1.35);
    const severeEarlyUpset = earlyCandidate && raceCarRandom() < 0.28;
    return {
      racer,
      index,
      traits,
      x: slotX + (random() - 0.5) * 14,
      y: SIM_START_Y[racer.row],
      vx: (random() - 0.5) * 4,
      vy: (random() - 0.5) * 3,
      angle: Math.PI / 2 + (random() - 0.5) * 0.08 * traits.wobble,
      angularVelocity: 0,
      wheelSpeed: traits.baseWheelSpeed + rowStagger / 500,
      traction: traits.traction,
      stability: traits.stability,
      mass: 0.85 + random() * 0.35,
      status: "running",
      eliminated: false,
      finishScore: 0,
      lastChaosType: "bump",
      lastChaosAtMs: -10_000,
      pileupContacts: 0,
      sideHangEligible: raceAllowsSideHangs && (racer.column <= 1 || racer.column >= 13 || random() > 0.88),
      earlyUpsetAtMs: earlyCandidate ? 12_000 + raceCarRandom() * 42_000 : undefined,
      earlyUpsetUsed: false,
      earlyUpsetCanEliminate: severeEarlyUpset,
      boggedUntilMs: 0,
      sideStackIndex: undefined,
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
      if (car.eliminated) {
        advanceEliminatedCar(car, timeMs);
        continue;
      }
      if (car.status === "side-hung") {
        continue;
      }

      const yawError = normalizeAngle(car.angle - Math.PI / 2);
      const yawEfficiency = clamp(Math.cos(Math.abs(yawError) * 1.8), 0, 1);
      const beltVelocity = -getBeltSpeedPxPerSec(timeMs);
      const driveVelocity = MAX_DRIVE_SPEED_PX_PER_SEC * car.wheelSpeed * car.traction * yawEfficiency;
      const rawHoldCorrection = clamp(
        (SIM_START_HOLD_Y - car.y) * 1.45,
        -MAX_RECOVERY_SPEED_PX_PER_SEC,
        MAX_RECOVERY_SPEED_PX_PER_SEC,
      );
      const usableRollingGrip = clamp(car.wheelSpeed * car.traction * yawEfficiency * 1.25, 0.12, 1);
      const holdCorrection = rawHoldCorrection * usableRollingGrip;
      const slidingGrip = car.status === "sliding-up" ? clamp(usableRollingGrip, 0.05, 0.65) : 1;
      const beltSlipVelocity = car.status === "sliding-up" ? beltVelocity * (1.12 - slidingGrip * 0.32) : beltVelocity;
      const effectiveAngleAssist =
        car.status === "sliding-up" ? trackAngleAssistVelocity * clamp(slidingGrip * 0.75, 0.08, 0.42) : trackAngleAssistVelocity;
      const effectiveHoldCorrection =
        car.status === "sliding-up"
          ? holdCorrection * clamp(slidingGrip - 0.16, 0, 0.38)
          : car.status === "recovering"
            ? holdCorrection * 1.42
            : holdCorrection;
      const effectiveDriveVelocity = car.status === "recovering" ? driveVelocity * 1.28 : driveVelocity;
      const seamPhase = timeMs / 2_700 + seed * 0.01;
      const railBias = car.racer.column <= 2 ? -10 : car.racer.column >= 12 ? 10 : 0;
      const traitWobblePhase = timeMs / (1_900 + car.racer.slot * 37) + hashString(car.racer.id) * 0.0001;
      const traitWobble = Math.sin(traitWobblePhase) * car.traits.wobble;
      const packDrift =
        Math.sin(seamPhase) * tuning.seamShiftPx +
        Math.sign(Math.sin(seamPhase)) * 6 +
        Math.sin(timeMs / 4_600 + car.racer.row * 0.8) * 5 +
        Math.sin(timeMs / 3_700 + car.racer.column * 0.42) * 4 +
        traitWobble * 4 +
        railBias;
      const lateralCenter = car.racer.column * SIM_SLOT_WIDTH + SIM_SLOT_WIDTH / 2 + packDrift;
      const lateralVelocity = clamp((lateralCenter - car.x) * 0.22 * car.stability, -MAX_LATERAL_SPEED_PX_PER_SEC, MAX_LATERAL_SPEED_PX_PER_SEC);
      const jitterVelocity = (random() - 0.5) * 5;
      const targetVy = beltSlipVelocity + effectiveAngleAssist + effectiveDriveVelocity + effectiveHoldCorrection;
      const targetVx = lateralVelocity + jitterVelocity + Math.sin(yawError) * driveVelocity * 0.12;

      const velocityResponse = car.status === "recovering" ? 0.3 : car.status === "sliding-up" ? 0.26 : 0.19;
      car.vy += (targetVy - car.vy) * velocityResponse;
      car.vx += (targetVx - car.vx) * 0.16;
      const yawSpring = car.status === "recovering" ? 1.18 : car.status === "sliding-up" ? 0.72 : 0.48;
      car.angularVelocity += -yawError * car.stability * yawSpring * SIM_STEP_SECONDS;
      car.angularVelocity += traitWobble * 0.018 * SIM_STEP_SECONDS;
      car.angularVelocity *= car.status === "recovering" ? 0.84 : 0.91;
      const yawLoss = Math.abs(yawError) * tuning.yawWheelLossPerSecond * car.traits.yawLoss * SIM_STEP_SECONDS;
      const rollingLoss = tuning.rollingResistancePerSecond * car.traits.rollingResistance * SIM_STEP_SECONDS;
      car.wheelSpeed = clamp(car.wheelSpeed - yawLoss - rollingLoss, 0.02, 1.35);
      const accelerationLoad = getBeltAccelerationLoad(timeMs);
      if (accelerationLoad > 0) {
        const startupGripLoss =
          accelerationLoad * (1 - car.stability) * car.traits.rollingResistance * car.traits.wobble * 0.018;
        car.wheelSpeed = clamp(car.wheelSpeed - startupGripLoss, 0.02, 1.35);
        car.angularVelocity +=
          Math.sin(traitWobblePhase * 1.7) * accelerationLoad * car.traits.wobble * (1 - car.stability) * 0.055;
        if (startupGripLoss > 0.006 && car.status === "running") {
          car.status = "wobbling";
        }
      }
      if (Math.abs(yawError) < 0.16 && car.traction > 0.38) {
        car.wheelSpeed = clamp(
          car.wheelSpeed + tuning.yawRecoverPerSecond * car.traits.recovery * SIM_STEP_SECONDS,
          0.02,
          1.35,
        );
      }
      if (timeMs < car.boggedUntilMs) {
        car.wheelSpeed = Math.min(car.wheelSpeed, 0.12 + car.traits.recovery * 0.035);
        car.traction = Math.min(car.traction, 0.22 + car.traits.recovery * 0.04);
        car.vy -= (14 + car.traits.wobble * 5) * SIM_STEP_SECONDS;
        car.status = "sliding-up";
      }
      if (Math.abs(yawError) > 0.42 && random() < (0.002 + Math.abs(yawError) * 0.002) * SIM_STEP_CHANCE_SCALE) {
        car.wheelSpeed = clamp(car.wheelSpeed - 0.18 - random() * 0.18, 0.02, 1.35);
        if (car.wheelSpeed < 0.18) {
          car.status = "sliding-up";
        }
      }
      car.x += car.vx * SIM_STEP_SECONDS;
      car.y += car.vy * SIM_STEP_SECONDS;
      car.angle += car.angularVelocity * SIM_STEP_SECONDS;

      if (!car.earlyUpsetUsed && car.earlyUpsetAtMs !== undefined && timeMs >= car.earlyUpsetAtMs) {
        car.earlyUpsetUsed = true;
        car.wheelSpeed = clamp(car.wheelSpeed - 0.5 * car.traits.rollingResistance, 0.02, 1.35);
        car.traction = clamp(car.traction - 0.28 * car.traits.yawLoss, 0.04, 1);
        car.angularVelocity += (car.racer.column % 2 === 0 ? -1 : 1) * (0.28 + car.traits.wobble * 0.08);
        car.vy -= 52 + car.traits.wobble * 12;
        car.status = "sliding-up";
        car.boggedUntilMs = timeMs + 3_500 + car.traits.rollingResistance * 1_400;
        pushChaos(timeline, car, timeMs, "bump");
      }

      compressAgainstFrontBarrier(car);

      if (car.x < SIM_LEFT_SAFE_X || car.x > SIM_RIGHT_SAFE_X) {
        const side = car.x < SIM_LEFT_SAFE_X ? -1 : 1;
        car.x = side < 0 ? Math.max(28, car.x) : Math.min(SIM_WIDTH - 28, car.x);
        car.vx -= side * Math.min(Math.abs(car.vx) * 0.55 + 4, 22);
        car.angularVelocity += side * 0.08;
        car.traction = clamp(car.traction - 0.006, 0.05, 1);
      }
      enforceActiveBounds(car);

      const maxYaw = car.status === "spinning" || car.status === "self-spun" ? 1.05 : ACTIVE_YAW_LIMIT_RAD;
      car.angle = Math.PI / 2 + clamp(normalizeAngle(car.angle - Math.PI / 2), -maxYaw, maxYaw);

      const tractionShock = random() < (1 - car.stability) * 0.005 * car.traits.wobble * SIM_STEP_CHANCE_SCALE ? 0.07 : 0;
      if (tractionShock > 0) {
        car.traction = clamp(car.traction - tractionShock, 0.08, 1);
        car.status = "wobbling";
        car.angularVelocity += (random() - 0.5) * 0.28;
      } else if (car.status === "wobbling" && random() < car.stability * 0.12 * SIM_STEP_CHANCE_SCALE) {
        car.status = "recovering";
        car.traction = clamp(car.traction + 0.14, 0, 1);
      } else if ((car.status === "recovering" || car.status === "wobbling") && car.traction > 0.45) {
        car.status = "running";
      }

      if (Math.abs(yawError) > SLIDING_YAW_LIMIT_RAD) {
        car.traction = clamp(car.traction - 0.055, 0.04, 1);
        car.wheelSpeed = clamp(car.wheelSpeed - 0.035, 0.08, 1.35);
        if (car.wheelSpeed < 0.22 || car.y < SIM_START_HOLD_Y - 70) {
          car.status = car.status === "running" ? "sliding-up" : car.status;
        }
      }

      if (car.y < SIM_START_HOLD_Y - 112 && car.vy < -58 && car.status === "running") {
        car.status = "sliding-up";
      }
      if (car.status === "sliding-up" && random() < car.stability * Math.max(car.traction, 0.2) * 0.08 * SIM_STEP_CHANCE_SCALE) {
        car.status = "recovering";
        car.wheelSpeed = clamp(car.wheelSpeed + 0.16, 0, 1.35);
        car.traction = clamp(car.traction + 0.22, 0, 1);
      }
    }

    applyGlobalPackPressure(cars, timeMs, seed);
    for (let pass = 0; pass < 2; pass += 1) {
      for (let i = 0; i < cars.length; i += 1) {
        for (let j = i + 1; j < cars.length; j += 1) {
          resolveContact(cars[i], cars[j], timeMs, random, timeline, tuning);
        }
      }
      settleContacts(cars);
    }

    for (const car of cars) {
      if (car.eliminated) {
        continue;
      }

      enforceActiveBounds(car);
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
        car.sideStackIndex = getNextSideStackIndex(cars, car);
        placeSideStack(car);
        sideHangs += 1;
        pushChaos(timeline, car, timeMs, "side-hang");
      }

      if (
        timeMs > 10_000 &&
        timeMs < BELT_HOLD_MS &&
        car.racer.row === 0 &&
        car.status === "sliding-up" &&
        (
          (
            car.y < SIM_START_HOLD_Y - SIM_ROW_SPACING - 18 &&
            car.wheelSpeed < 0.28 &&
            car.traction < 0.42
          ) ||
          (
            car.earlyUpsetCanEliminate &&
            car.earlyUpsetAtMs !== undefined &&
            timeMs > car.earlyUpsetAtMs + 3_500 &&
            car.wheelSpeed < 0.24
          )
        )
      ) {
        const stillRunning = cars.filter((candidate) => !candidate.eliminated).length;
        if (stillRunning > 1) {
          car.status = car.pileupContacts >= 1.5 ? "pileup" : "knocked-out";
          car.eliminated = true;
          car.eliminatedAtMs = timeMs;
          car.lastChaosType = car.status === "pileup" ? "chain-reaction" : "knockout";
          car.vy -= 36;
          pushChaos(timeline, car, timeMs, car.lastChaosType);
          disturbRearPack(cars, car, timeMs, random, timeline, tuning);
        }
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
  const forcedSideHangMinimum = sideHangLimit >= 4 ? 2 : sideHangLimit > 0 ? 1 : 0;
  while (sideHangs < forcedSideHangMinimum) {
    const sideHangCandidate = cars
      .filter((car) => car !== survivor && car.status !== "side-hung" && (car.racer.column <= 1 || car.racer.column >= 13))
      .sort((a, b) => (a.eliminatedAtMs ?? durationMs) - (b.eliminatedAtMs ?? durationMs))[0];
    if (sideHangCandidate) {
      sideHangCandidate.status = "side-hung";
      sideHangCandidate.eliminated = true;
      sideHangCandidate.eliminatedAtMs = Math.min(sideHangCandidate.eliminatedAtMs ?? raceEndTimeMs, raceEndTimeMs * 0.82);
      sideHangCandidate.sideStackIndex = getNextSideStackIndex(cars, sideHangCandidate);
      placeSideStack(sideHangCandidate);
      sideHangCandidate.lastChaosType = "side-hang";
      sideHangs += 1;
      pushChaos(timeline, sideHangCandidate, sideHangCandidate.eliminatedAtMs, "side-hang");
    } else {
      break;
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
    survivor.wheelSpeed = Math.max(survivor.wheelSpeed, 0.62);
    survivor.traction = Math.max(survivor.traction, 0.62);
    survivor.pileupContacts = 0;
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

  return { results, frames, timeline, tuning };
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

function hashString(value: string): number {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
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

function getBeltSpeedPxPerSec(timeMs: number): number {
  return getBeltSpeedMph(timeMs) * MPH_TO_PX_PER_SEC;
}

function getBeltSpeedMph(timeMs: number): number {
  if (timeMs < BELT_STARTUP_RAMP_MS) {
    return BELT_START_MPH * clamp(timeMs / BELT_STARTUP_RAMP_MS, 0, 1);
  }
  const ramp = clamp((timeMs - BELT_HOLD_MS) / BELT_RAMP_MS, 0, 1);
  return BELT_START_MPH + (BELT_FULL_MPH - BELT_START_MPH) * ramp;
}

function getBeltAccelerationLoad(timeMs: number): number {
  if (timeMs > BELT_STARTUP_RAMP_MS + 2_000) {
    return 0;
  }
  const fade = clamp(1 - timeMs / (BELT_STARTUP_RAMP_MS + 2_000), 0, 1);
  return fade;
}

function getNoseY(car: CarRuntime): number {
  return car.y + Math.sin(car.angle) * SIM_CAR_NOSE_TO_CENTER;
}

function getTailY(car: CarRuntime): number {
  return car.y - Math.sin(car.angle) * SIM_CAR_TAIL_TO_CENTER;
}

function compressAgainstFrontBarrier(car: CarRuntime): void {
  const noseOverflow = getNoseY(car) - SIM_FRONT_LINE_Y;
  if (noseOverflow <= 0) {
    return;
  }

  car.y -= noseOverflow;
  if (car.vy > 0) {
    car.vy *= -0.08;
  }
  car.angularVelocity *= 0.82;
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

function deriveFrameStatus(car: CarRuntime): CarStatus {
  if (car.eliminated) {
    return finalStatus(car.status);
  }
  if (car.status === "side-hung" || car.status === "pileup" || car.status === "self-spun" || car.status === "spinning") {
    return car.status;
  }
  const yawError = Math.abs(normalizeAngle(car.angle - Math.PI / 2));
  if (car.pileupContacts > DEFAULT_PHYSICS_TUNING_BASE.chainReactionThreshold) {
    return "pileup";
  }
  if (car.y < SIM_START_HOLD_Y - 90 || car.wheelSpeed < 0.18 || yawError > 0.58) {
    return "sliding-up";
  }
  if (car.traction < 0.42 || yawError > 0.28 || Math.abs(car.angularVelocity) > 0.065) {
    return "wobbling";
  }
  if (car.status === "recovering") {
    return "recovering";
  }
  return "running";
}

function resolveContact(
  a: CarRuntime,
  b: CarRuntime,
  timeMs: number,
  random: () => number,
  timeline: RaceTimelineEvent[],
  tuning: PhysicsTuning,
): void {
  if (a.eliminated || b.eliminated || a.status === "side-hung" || b.status === "side-hung") {
    return;
  }

  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const minX = 66;
  const minY = SIM_CAR_NOSE_TO_CENTER + SIM_CAR_TAIL_TO_CENTER;
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
  const front = a.racer.row === 0 && b.racer.row === 1 ? a : b.racer.row === 0 && a.racer.row === 1 ? b : undefined;
  const rear = front === a ? b : front === b ? a : undefined;
  const bumperCompression = front && rear ? getNoseY(rear) - getTailY(front) : -Infinity;
  if (
    front &&
    rear &&
    Math.abs(front.racer.column - rear.racer.column) <= 1 &&
    Math.abs(dx) < 58 &&
    bumperCompression > -4
  ) {
    resolveBumperContact(front, rear, bumperCompression, impulse, relativeSpeed, relativeYaw, timeMs, random, timeline);
    return;
  }
  const restingBumperContact =
    front !== undefined &&
    rear !== undefined &&
    Math.abs(front.racer.column - rear.racer.column) <= 1 &&
    Math.abs(dx) < 50 &&
    getNoseY(rear) >= getTailY(front) - 8 &&
    getNoseY(rear) <= getTailY(front) + SIM_MAX_BUMPER_COMPRESSION &&
    relativeSpeed < 26 &&
    relativeYaw < 0.24;
  const hardContact = impulse > 0.62 && (relativeSpeed > 30 || relativeYaw > 0.34 || lateralCompression);
  const canSeparateX =
    Math.abs(dx) > 0.001 &&
    (a.racer.row === b.racer.row || Math.abs(dy) < SIM_ROW_SPACING * 0.62);
  const canSeparateY =
    Math.abs(dy) > 0.001 &&
    (a.racer.row !== b.racer.row || Math.abs(dx) < minX * 0.35);
  const separateOnX = canSeparateX && (!canSeparateY || overlapX < overlapY * 0.9);

  separateCars(a, b, separateOnX, separateOnX ? overlapX : overlapY, directionX, directionY, hardContact ? 0.94 : 0.58);
  enforceActiveBounds(a);
  enforceActiveBounds(b);

  if (restingBumperContact) {
    compressNoseToTail(front, rear);
    const sharedVx = (a.vx + b.vx) / 2;
    const sharedVy = (a.vy + b.vy) / 2;
    a.vx = a.vx * 0.7 + sharedVx * 0.3;
    b.vx = b.vx * 0.7 + sharedVx * 0.3;
    a.vy = a.vy * 0.7 + sharedVy * 0.3;
    b.vy = b.vy * 0.7 + sharedVy * 0.3;
    return;
  }

  if (!hardContact) {
    const softImpulse = impulse * 2.35 * tuning.collisionImpulseMultiplier;
    a.vx -= directionX * softImpulse / a.mass;
    b.vx += directionX * softImpulse / b.mass;
    a.vy -= directionY * softImpulse * 0.45 / a.mass;
    b.vy += directionY * softImpulse * 0.45 / b.mass;
    if (impulse > 0.54 && timeMs - a.lastChaosAtMs > 1_800 && timeMs - b.lastChaosAtMs > 1_800) {
      pushChaos(timeline, impulse > 0.68 ? a : b, timeMs, "bump");
    }
    return;
  }

  if (timeMs < 6_000) {
    const earlyImpulse = impulse * 4.1 * tuning.collisionImpulseMultiplier;
    a.vx -= directionX * earlyImpulse / a.mass;
    b.vx += directionX * earlyImpulse / b.mass;
    a.vy -= directionY * earlyImpulse * 0.55 / a.mass;
    b.vy += directionY * earlyImpulse * 0.55 / b.mass;
    a.angularVelocity -= directionX * impulse * 0.06;
    b.angularVelocity += directionX * impulse * 0.06;
    if (impulse > 0.7 && timeMs - a.lastChaosAtMs > 1_800 && timeMs - b.lastChaosAtMs > 1_800) {
      pushChaos(timeline, impulse > 0.84 ? a : b, timeMs, "bump");
    }
    return;
  }

  a.vx -= directionX * impulse * 15 * tuning.collisionImpulseMultiplier / a.mass;
  b.vx += directionX * impulse * 15 * tuning.collisionImpulseMultiplier / b.mass;
  a.vy -= directionY * impulse * 12 * tuning.collisionImpulseMultiplier / a.mass;
  b.vy += directionY * impulse * 12 * tuning.collisionImpulseMultiplier / b.mass;
  a.angularVelocity -= directionX * impulse * 0.46 * tuning.collisionImpulseMultiplier;
  b.angularVelocity += directionX * impulse * 0.46 * tuning.collisionImpulseMultiplier;

  a.traction = clamp(a.traction - impulse * (0.035 + random() * 0.06), 0.05, 1);
  b.traction = clamp(b.traction - impulse * (0.035 + random() * 0.06), 0.05, 1);
  a.wheelSpeed = clamp(a.wheelSpeed - impulse * 0.052, 0.08, 1.35);
  b.wheelSpeed = clamp(b.wheelSpeed - impulse * 0.052, 0.08, 1.35);

  a.pileupContacts += (impulse > 0.62 ? 1.45 : 0.72) * SIM_STEP_CHANCE_SCALE;
  b.pileupContacts += (impulse > 0.62 ? 1.45 : 0.72) * SIM_STEP_CHANCE_SCALE;
  a.status = timeMs > 6_000 && a.pileupContacts > tuning.chainReactionThreshold && impulse > 0.62 ? "pileup" : "wobbling";
  b.status = timeMs > 6_000 && b.pileupContacts > tuning.chainReactionThreshold && impulse > 0.62 ? "pileup" : "wobbling";

  if (
    front &&
    rear &&
    timeMs > 6_000 &&
    rear.y < SIM_START_HOLD_Y - SIM_ROW_SPACING + 16 &&
    Math.abs(front.racer.column - rear.racer.column) <= 1 &&
    impulse > 0.52 &&
    relativeSpeed > 12 &&
    random() < (0.16 + impulse * 0.22) * SIM_STEP_CHANCE_SCALE
  ) {
    rear.traction = clamp(rear.traction - 0.14, 0.04, 1);
    rear.wheelSpeed = clamp(rear.wheelSpeed - 0.1, 0.08, 1.35);
    rear.status = "sliding-up";
    rear.vy -= 28 + impulse * 24 * tuning.collisionImpulseMultiplier;
    pushChaos(timeline, rear, timeMs, "chain-reaction");
  } else if (impulse > 0.38 && timeMs - a.lastChaosAtMs > 1_400 && timeMs - b.lastChaosAtMs > 1_400) {
    pushChaos(timeline, impulse > 0.72 ? a : b, timeMs, "bump");
  }
}

function resolveBumperContact(
  front: CarRuntime,
  rear: CarRuntime,
  compression: number,
  impulse: number,
  relativeSpeed: number,
  relativeYaw: number,
  timeMs: number,
  random: () => number,
  timeline: RaceTimelineEvent[],
): void {
  compressNoseToTail(front, rear);

  const sharedVy = (front.vy + rear.vy) / 2;
  front.vy = front.vy * 0.72 + sharedVy * 0.28;
  rear.vy = rear.vy * 0.72 + sharedVy * 0.28;
  const excessCompression = Math.max(0, compression - SIM_MAX_BUMPER_COMPRESSION);
  if (excessCompression > 0) {
    rear.vy -= excessCompression * 0.16;
    front.vy += excessCompression * 0.04;
  }

  const yawKick = impulse * 0.045 + relativeYaw * 0.035;
  front.angularVelocity += (random() - 0.5) * yawKick;
  rear.angularVelocity += (random() - 0.5) * yawKick;

  if (relativeSpeed > 42 || relativeYaw > 0.38 || compression > SIM_MAX_BUMPER_COMPRESSION + 10) {
    front.traction = clamp(front.traction - impulse * 0.018, 0.06, 1);
    rear.traction = clamp(rear.traction - impulse * 0.034, 0.05, 1);
    rear.wheelSpeed = clamp(rear.wheelSpeed - impulse * 0.05, 0.02, 1.35);
    front.status = front.status === "running" ? "wobbling" : front.status;
    rear.status = "wobbling";
    if (timeMs - front.lastChaosAtMs > 2_200 && timeMs - rear.lastChaosAtMs > 2_200) {
      pushChaos(timeline, relativeYaw > 0.38 ? rear : front, timeMs, "bump");
    }
  }
}

function compressNoseToTail(front: CarRuntime, rear: CarRuntime): void {
  const compression = getNoseY(rear) - getTailY(front);
  if (compression < -4) {
    return;
  }

  const correction = Math.max(0, compression - SIM_MAX_BUMPER_COMPRESSION);
  front.y = Math.min(SIM_START_HOLD_Y, front.y + correction * 0.08);
  rear.y -= correction * 0.92;
  const sharedVy = (front.vy + rear.vy) / 2;
  front.vy = front.vy * 0.82 + sharedVy * 0.18;
  rear.vy = rear.vy * 0.82 + sharedVy * 0.18;
  compressAgainstFrontBarrier(front);
  compressAgainstFrontBarrier(rear);
}

function settleContacts(cars: CarRuntime[]): void {
  for (let pass = 0; pass < 3; pass += 1) {
    for (let i = 0; i < cars.length; i += 1) {
      for (let j = i + 1; j < cars.length; j += 1) {
        settleContact(cars[i], cars[j]);
      }
    }
  }
}

function applyGlobalPackPressure(cars: CarRuntime[], timeMs: number, seed: number): void {
  const seamPulse = Math.max(0, Math.sin(timeMs / 2_700 + seed * 0.01));
  for (const car of cars) {
    if (car.eliminated || car.status === "side-hung") {
      continue;
    }

    const neighbors = cars.filter(
      (candidate) =>
        candidate !== car &&
        !candidate.eliminated &&
        Math.abs(candidate.x - car.x) < 95 &&
        Math.abs(candidate.y - car.y) < 130,
    );
    const pressure = clamp(neighbors.length / 5, 0, 1);
    if (pressure <= 0) {
      continue;
    }

    car.vx += Math.sin(timeMs / 1_400 + car.racer.slot) * pressure * seamPulse * 1.8;
    car.angularVelocity += Math.sin(timeMs / 1_100 + car.racer.column) * pressure * seamPulse * 0.012;
    car.traction = clamp(car.traction - pressure * seamPulse * 0.0018, 0.04, 1);
    if (pressure > 0.65 && seamPulse > 0.75) {
      car.pileupContacts += 0.08;
    }
  }
}

function settleContact(a: CarRuntime, b: CarRuntime): void {
  if (a.eliminated || b.eliminated || a.status === "side-hung" || b.status === "side-hung") {
    return;
  }

  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const minX = 66;
  const minY = SIM_CAR_NOSE_TO_CENTER + SIM_CAR_TAIL_TO_CENTER;
  if (Math.abs(dx) > minX || Math.abs(dy) > minY) {
    return;
  }

  const overlapX = minX - Math.abs(dx);
  const overlapY = minY - Math.abs(dy);
  const directionX = dx === 0 ? 1 : Math.sign(dx);
  const directionY = dy === 0 ? 1 : Math.sign(dy);
  const separateOnX =
    Math.abs(dx) > 0.001 &&
    (a.racer.row === b.racer.row || Math.abs(dy) < SIM_ROW_SPACING * 0.62) &&
    overlapX < overlapY * 0.95;

  separateCars(a, b, separateOnX, separateOnX ? overlapX : overlapY, directionX, directionY, 0.62);
  enforceActiveBounds(a);
  enforceActiveBounds(b);
}

function getNextSideStackIndex(cars: CarRuntime[], car: CarRuntime): number {
  const onLeft = car.x < SIM_WIDTH / 2;
  const used = new Set(
    cars
      .filter((candidate) => candidate.status === "side-hung" && candidate.sideStackIndex !== undefined)
      .filter((candidate) => (onLeft ? candidate.x < SIM_WIDTH / 2 : candidate.x >= SIM_WIDTH / 2))
      .map((candidate) => candidate.sideStackIndex),
  );

  for (let index = 0; index < 4; index += 1) {
    if (!used.has(index)) {
      return index;
    }
  }
  return 3;
}

function placeSideStack(car: CarRuntime): void {
  const stackIndex = car.sideStackIndex ?? 0;
  const onLeft = car.x < SIM_WIDTH / 2 || car.racer.column <= 1;
  const xBase = onLeft ? SIM_LEFT_SAFE_X - 18 : SIM_RIGHT_SAFE_X + 18;
  const xStack = onLeft ? xBase - stackIndex * 13 : xBase + stackIndex * 13;
  car.x = xStack;
  car.y = Math.min(car.y, SIM_START_HOLD_Y - 125 - stackIndex * 24);
  car.angle = Math.PI / 2 + (onLeft ? -0.32 : 0.32) + stackIndex * 0.07;
  car.vx = 0;
  car.vy = 0;
  car.angularVelocity = 0;
}

function disturbRearPack(
  cars: CarRuntime[],
  frontCar: CarRuntime,
  timeMs: number,
  random: () => number,
  timeline: RaceTimelineEvent[],
  tuning: PhysicsTuning,
): void {
  for (const candidate of cars) {
    if (
      candidate.eliminated ||
      candidate.racer.row !== 1 ||
      Math.abs(candidate.racer.column - frontCar.racer.column) > 1
    ) {
      continue;
    }

    const severity = 0.42 + random() * 0.42;
    candidate.traction = clamp(candidate.traction - severity * candidate.traits.yawLoss, 0.04, 1);
    candidate.wheelSpeed = clamp(candidate.wheelSpeed - severity * candidate.traits.rollingResistance, 0.02, 1.35);
    candidate.angularVelocity += (random() - 0.5) * (0.28 + candidate.traits.wobble * 0.14);
    candidate.vy -= 48 + severity * 62 * tuning.collisionImpulseMultiplier;
    candidate.pileupContacts += 1.8 + severity;
    candidate.status = "sliding-up";
    candidate.boggedUntilMs = Math.max(candidate.boggedUntilMs, timeMs + 2_200 + severity * 2_200);

    if (candidate.pileupContacts > tuning.chainReactionThreshold && random() < tuning.chainSpreadChance) {
      const stillRunning = cars.filter((car) => !car.eliminated).length;
      if (stillRunning > 1) {
        candidate.status = "pileup";
        candidate.eliminated = true;
        candidate.eliminatedAtMs = timeMs + 400;
        candidate.lastChaosType = "chain-reaction";
        pushChaos(timeline, candidate, candidate.eliminatedAtMs, "chain-reaction");
        continue;
      }
    }

    if (random() < tuning.chainSpreadChance && timeMs - candidate.lastChaosAtMs > 1_200) {
      pushChaos(timeline, candidate, timeMs, "bump");
    }
  }
}

function separateCars(
  a: CarRuntime,
  b: CarRuntime,
  separateOnX: boolean,
  overlap: number,
  directionX: number,
  directionY: number,
  strength: number,
): void {
  const correction = Math.max(0, overlap) * strength * 0.5;
  if (correction <= 0) {
    return;
  }

  if (separateOnX) {
    a.x -= directionX * correction;
    b.x += directionX * correction;
  } else {
    a.y -= directionY * correction;
    b.y += directionY * correction;
  }
}

function advanceEliminatedCar(car: CarRuntime, timeMs: number): void {
  if (car.status === "side-hung") {
    return;
  }

  const beltVelocity = -getBeltSpeedPxPerSec(timeMs);
  const slideTarget = beltVelocity * 1.18 - 18;
  car.vy += (slideTarget - car.vy) * 0.24;
  car.vx *= 0.92;
  car.angularVelocity *= 0.94;
  car.x += car.vx * SIM_STEP_SECONDS;
  car.y += car.vy * SIM_STEP_SECONDS;
  car.angle += car.angularVelocity * SIM_STEP_SECONDS;
  car.y = Math.max(car.y, SIM_OFF_FRONT_Y - 95);
}

function enforceActiveBounds(car: CarRuntime): void {
  if (car.eliminated || car.status === "side-hung") {
    return;
  }

  const minX = SIM_LEFT_SAFE_X + SIM_SIDE_RAIL_PADDING;
  const maxX = SIM_RIGHT_SAFE_X - SIM_SIDE_RAIL_PADDING;
  if (car.x < minX) {
    car.x = minX;
    car.vx = Math.max(0, car.vx) * 0.35;
  } else if (car.x > maxX) {
    car.x = maxX;
    car.vx = Math.min(0, car.vx) * 0.35;
  }

  if (car.y > SIM_START_HOLD_Y) {
    car.y = SIM_START_HOLD_Y;
    car.vy = Math.min(0, car.vy) * 0.35;
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
  const activeCars = cars.filter((car) => !car.eliminated);
  const sliding = cars.filter((car) => {
    const status = deriveFrameStatus(car);
    return status === "sliding-up" || status === "wobbling" || status === "spinning" || status === "pileup";
  }).length;
  return {
    timeMs,
    beltSpeedMph: getBeltSpeedMph(timeMs),
    metrics: {
      active: activeCars.length,
      sliding,
      eliminated: cars.length - activeCars.length,
      averageWheelSpeed: activeCars.length
        ? activeCars.reduce((sum, car) => sum + car.wheelSpeed, 0) / activeCars.length
        : 0,
      averageTraction: activeCars.length
        ? activeCars.reduce((sum, car) => sum + car.traction, 0) / activeCars.length
        : 0,
    },
    cars: cars.map((car) => ({
      racerId: car.racer.id,
      progress: clamp(car.y / SIM_HEIGHT, -1, 1),
      trackOffset: clamp((car.x - (car.racer.column * SIM_SLOT_WIDTH + SIM_SLOT_WIDTH / 2)) / 84, -1, 1),
      angle: car.angle - Math.PI / 2,
      status: deriveFrameStatus(car),
      x: car.x / SIM_WIDTH,
      y: car.y / SIM_HEIGHT,
      scale: clamp(0.66 + car.y / SIM_HEIGHT * 0.46, 0.62, 1.16),
      stackIndex: car.sideStackIndex,
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
