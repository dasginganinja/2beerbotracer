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
};

export type DemoRace = {
  raceId: string;
  state: RaceState;
  racers: Racer[];
};

export type RaceResult = {
  racerId: string;
  displayName: string;
  place: number;
  finishTimeMs: number;
};

export type RaceFrame = {
  timeMs: number;
  cars: Array<{
    racerId: string;
    progress: number;
  }>;
};

export type RaceTimelineEvent = {
  type: "chaos";
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
};

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
  const random = createRandom(seed);
  const racerCount = 8 + Math.floor(random() * 5);
  const racers = DEMO_NAMES.slice(0, racerCount).map((name, index) => ({
    id: `demo-racer-${index + 1}`,
    displayName: name,
    color: DEMO_COLORS[index % DEMO_COLORS.length],
  }));

  return {
    raceId: `demo-${seed}`,
    state: "REGISTRATION_OPEN",
    racers,
  };
}

export function simulateRace({ seed, racers, durationMs }: SimulateRaceInput): SimulatedRace {
  const random = createRandom(seed);
  const profiles = racers.map((racer, index) => {
    const baseSpeed = 0.86 + random() * 0.22;
    const wobble = 0.025 + random() * 0.05;
    const phase = random() * Math.PI * 2;
    const boostAtMs = durationMs * (0.18 + random() * 0.62);
    const boostSize = 0.035 + random() * 0.065;
    const slipAtMs = durationMs * (0.25 + random() * 0.52);
    const slipSize = 0.015 + random() * 0.055;

    return {
      racer,
      index,
      baseSpeed,
      wobble,
      phase,
      boostAtMs,
      boostSize,
      slipAtMs,
      slipSize,
      finishScore: baseSpeed + boostSize - slipSize + random() * 0.08,
    };
  });

  const orderedProfiles = [...profiles].sort((a, b) => {
    if (b.finishScore !== a.finishScore) {
      return b.finishScore - a.finishScore;
    }
    return a.index - b.index;
  });

  const results = orderedProfiles.map((profile, index) => ({
    racerId: profile.racer.id,
    displayName: profile.racer.displayName,
    place: index + 1,
    finishTimeMs: Math.round(durationMs + index * 420 + random() * 180),
  }));

  const frames: RaceFrame[] = [];
  for (let timeMs = 0; timeMs <= durationMs; timeMs += 250) {
    const raceT = timeMs / durationMs;
    frames.push({
      timeMs,
      cars: profiles.map((profile) => {
        const finishRank = results.find((result) => result.racerId === profile.racer.id)?.place ?? racers.length;
        const rankBonus = (racers.length - finishRank) / Math.max(racers.length, 1) * 0.1;
        const boost = smoothStep(profile.boostAtMs, profile.boostAtMs + 4000, timeMs) * profile.boostSize;
        const slip = smoothStep(profile.slipAtMs, profile.slipAtMs + 3000, timeMs) * profile.slipSize;
        const wobble = Math.sin(raceT * Math.PI * 8 + profile.phase) * profile.wobble;
        const progress = clamp(raceT * (0.9 + rankBonus) + boost - slip + wobble * (1 - raceT), 0, 1);

        return {
          racerId: profile.racer.id,
          progress: timeMs >= durationMs ? 1 : progress,
        };
      }),
    });
  }

  const timeline = orderedProfiles.slice(0, Math.min(3, orderedProfiles.length)).map((profile, index) => ({
    type: "chaos" as const,
    timeMs: Math.round(durationMs * (0.25 + index * 0.18)),
    racerId: profile.racer.id,
    message: buildChaosMessage(profile.racer.displayName, index),
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

function smoothStep(edge0: number, edge1: number, value: number): number {
  const x = clamp((value - edge0) / (edge1 - edge0), 0, 1);
  return x * x * (3 - 2 * x);
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function buildChaosMessage(displayName: string, index: number): string {
  const templates = [
    `${displayName} found the mystery boost lane`,
    `${displayName} survived a belt wobble`,
    `${displayName} got aero help from absolutely nowhere`,
  ];
  return templates[index % templates.length];
}
