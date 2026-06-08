import { describe, expect, it } from "vitest";
import {
  createDemoRace,
  getStableCarTraits,
  getAllowedTransition,
  simulateRace,
  type Racer,
  type RaceState,
} from "./raceSimulation";

const racers: Racer[] = [
  { id: "r1", displayName: "Alpha", color: "#f94144", slot: 1, row: 0, column: 0 },
  { id: "r2", displayName: "Bravo", color: "#f3722c", slot: 2, row: 0, column: 1 },
  { id: "r3", displayName: "Charlie", color: "#f9c74f", slot: 16, row: 1, column: 0 },
  { id: "r4", displayName: "Delta", color: "#90be6d", slot: 17, row: 1, column: 1 },
];

describe("race simulation", () => {
  it("creates a demo race with enough named racers for an OBS proof", () => {
    const race = createDemoRace(1234);

    expect(race.raceId).toBe("demo-1234");
    expect(race.state).toBe("REGISTRATION_OPEN");
    expect(race.racers).toHaveLength(30);
    expect(new Set(race.racers.map((racer) => racer.id)).size).toBe(race.racers.length);
    expect(race.racers[0]).toMatchObject({ slot: 1, row: 0, column: 0 });
    expect(race.racers[14]).toMatchObject({ slot: 15, row: 0, column: 14 });
    expect(race.racers[15]).toMatchObject({ slot: 16, row: 1, column: 0 });
    expect(race.racers[29]).toMatchObject({ slot: 30, row: 1, column: 14 });
  });

  it("stages exactly two non-overlapping rows of fifteen cars", () => {
    const demo = createDemoRace(1235);
    const race = simulateRace({ seed: 1235, racers: demo.racers, durationMs: 1_000, trackAngleDeg: 6 });
    const firstFrame = race.frames[0];
    const columns = new Set(demo.racers.map((racer) => racer.column));
    const row0Y =
      firstFrame.cars
        .filter((car) => Number(car.racerId.replace("demo-racer-", "")) <= 15)
        .reduce((sum, car) => sum + car.y, 0) / 15;
    const row1Y =
      firstFrame.cars
        .filter((car) => Number(car.racerId.replace("demo-racer-", "")) > 15)
        .reduce((sum, car) => sum + car.y, 0) / 15;

    expect(columns.size).toBe(15);
    expect(row0Y - row1Y).toBeGreaterThan(0.19);
    expect(row0Y - row1Y).toBeLessThan(0.23);
  });

  it("produces deterministic final results for a seed and racer list", () => {
    const first = simulateRace({ seed: 42, racers, durationMs: 45_000 });
    const second = simulateRace({ seed: 42, racers, durationMs: 45_000 });

    expect(first.results).toEqual(second.results);
    expect(first.results.map((result) => result.place)).toEqual([1, 2, 3, 4]);
    expect(new Set(first.results.map((result) => result.racerId)).size).toBe(racers.length);
    expect(first.timeline.some((event) => event.type === "chaos")).toBe(true);
  });

  it("keeps car rolling traits stable across race seeds", () => {
    const firstRace = createDemoRace(5001);
    const secondRace = createDemoRace(5002);

    expect(getStableCarTraits(firstRace.racers[0])).toEqual(getStableCarTraits(secondRace.racers[0]));
    expect(getStableCarTraits(firstRace.racers[0])).not.toEqual(getStableCarTraits(firstRace.racers[1]));
  });

  it("keeps sampled treadmill positions bounded near the belt", () => {
    const race = simulateRace({ seed: 7, racers, durationMs: 30_000 });

    for (const frame of race.frames) {
      for (const car of frame.cars) {
        expect(car.progress).toBeGreaterThanOrEqual(-1);
        expect(car.progress).toBeLessThanOrEqual(1);
        expect(car.trackOffset).toBeGreaterThanOrEqual(-1);
        expect(car.trackOffset).toBeLessThanOrEqual(1);
      }
    }
  });

  it("keeps active cars behind the bottom yellow line", () => {
    const race = simulateRace({ seed: 2031, racers: createDemoRace(2031).racers, durationMs: 30_000 });

    for (const frame of race.frames) {
      for (const car of frame.cars) {
        if (car.status === "running" || car.status === "recovering" || car.status === "wobbling") {
          expect(car.y).toBeLessThanOrEqual(0.76);
          expect(car.x).toBeGreaterThanOrEqual(0.07);
          expect(car.x).toBeLessThanOrEqual(0.93);
        }
      }
    }
  });

  it("keeps the active car nose behind the bottom yellow line", () => {
    const race = simulateRace({ seed: 2033, racers: createDemoRace(2033).racers, durationMs: 30_000 });
    const noseToCenter = 66 / 520;
    const frontLine = 446 / 520;

    for (const frame of race.frames) {
      for (const car of frame.cars) {
        if (car.status === "running" || car.status === "recovering" || car.status === "wobbling") {
          expect(car.y + Math.cos(car.angle) * noseToCenter).toBeLessThanOrEqual(frontLine + 0.004);
        }
      }
    }
  });

  it("keeps second-row noses near rear bumpers instead of deep inside front cars", () => {
    const race = simulateRace({ seed: 2035, racers: createDemoRace(2035).racers, durationMs: 20_000, trackAngleDeg: 6 });
    const noseToCenter = 66 / 520;
    const tailToCenter = 48 / 520;
    const maxCompression = 5 / 520;

    for (const frame of race.frames.filter((candidate) => candidate.timeMs < 10_000)) {
      for (let column = 0; column < 15; column += 1) {
        const front = frame.cars.find((car) => car.racerId === `demo-racer-${column + 1}`);
        const rear = frame.cars.find((car) => car.racerId === `demo-racer-${column + 16}`);
        if (!front || !rear || front.status !== "running" || rear.status !== "running") {
          continue;
        }
        const rearNose = rear.y + Math.cos(rear.angle) * noseToCenter;
        const frontTail = front.y - Math.cos(front.angle) * tailToCenter;

        expect(rearNose - frontTail).toBeLessThanOrEqual(maxCompression + 0.012);
      }
    }
  });

  it("separates same-row active cars instead of letting them stack", () => {
    const race = simulateRace({ seed: 2032, racers: createDemoRace(2032).racers, durationMs: 20_000 });
    const activeStatuses = new Set(["running", "recovering", "wobbling", "sliding-up"]);

    for (const frame of race.frames.filter((candidate) => candidate.timeMs < 12_000)) {
      for (const rowStart of [1, 16]) {
        const rowCars = frame.cars
          .filter((car) => activeStatuses.has(car.status))
          .filter((car) => {
            const slot = Number(car.racerId.replace("demo-racer-", ""));
            return slot >= rowStart && slot < rowStart + 15;
          })
          .sort((a, b) => a.x - b.x);

        for (let index = 1; index < rowCars.length; index += 1) {
          expect(rowCars[index].x - rowCars[index - 1].x).toBeGreaterThan(0.035);
        }
      }
    }
  });

  it("models treadmill-specific chaos events and car statuses", () => {
    const race = simulateRace({ seed: 99, racers, durationMs: 45_000 });
    const eventTypes = new Set(race.timeline.map((event) => event.chaosType));

    expect(eventTypes.has("bump")).toBe(true);
    expect(eventTypes.has("knockout") || eventTypes.has("chain-reaction")).toBe(true);
    expect(race.results.some((result) => result.status !== "running")).toBe(true);
  });

  it("runs as an elimination race until exactly one car survives", () => {
    const race = simulateRace({ seed: 2026, racers, durationMs: 45_000 });
    const survivors = race.results.filter((result) => result.status === "running");
    const finalFrame = race.frames.at(-1);

    expect(survivors).toHaveLength(1);
    expect(survivors[0].place).toBe(1);
    expect(finalFrame?.cars.filter((car) => car.status === "running")).toHaveLength(1);
    expect(race.results.filter((result) => result.status !== "running")).toHaveLength(racers.length - 1);
    expect(race.timeline.filter((event) => event.chaosType !== "bump").length).toBeGreaterThanOrEqual(1);
  });

  it("holds the survivor near the bottom start line while eliminated cars move upward", () => {
    const race = simulateRace({ seed: 2027, racers, durationMs: 45_000 });
    const finalFrame = race.frames.at(-1);
    const survivor = race.results.find((result) => result.status === "running");
    const survivorCar = finalFrame?.cars.find((car) => car.racerId === survivor?.racerId);
    const eliminatedCars = finalFrame?.cars.filter((car) => car.status !== "running") ?? [];

    expect(survivorCar?.progress).toBeGreaterThan(0.69);
    expect(survivorCar?.progress).toBeLessThanOrEqual(0.76);
    expect(Math.abs(survivorCar?.angle ?? 0)).toBeLessThan(0.35);
    expect(eliminatedCars.length).toBeGreaterThan(0);
    for (const car of eliminatedCars) {
      expect(car.progress).toBeLessThan(survivorCar?.progress ?? 0);
      expect(car.y).toBeLessThan(survivorCar?.y ?? 1);
      expect(car.scale).toBeLessThanOrEqual(survivorCar?.scale ?? 0);
    }
  });

  it("uses track angle to help cars resist early upward belt drift", () => {
    const flatRace = simulateRace({ seed: 2028, racers, durationMs: 20_000, trackAngleDeg: 0 });
    const angledRace = simulateRace({ seed: 2028, racers, durationMs: 20_000, trackAngleDeg: 4 });
    const flatFrame = flatRace.frames.find((frame) => frame.timeMs === 8_000);
    const angledFrame = angledRace.frames.find((frame) => frame.timeMs === 8_000);
    const averageY = (frame: NonNullable<typeof flatFrame>) =>
      frame.cars.reduce((sum, car) => sum + car.y, 0) / frame.cars.length;

    expect(angledFrame).toBeDefined();
    expect(flatFrame).toBeDefined();
    expect(averageY(angledFrame!)).toBeGreaterThan(averageY(flatFrame!));
  });

  it("does not turn resting bumper proximity into immediate pileups", () => {
    const race = simulateRace({
      seed: 2030,
      racers: createDemoRace(2030).racers,
      durationMs: 20_000,
      trackAngleDeg: 6,
    });
    const earlyMajorIncidents = race.timeline.filter(
      (event) => event.timeMs < 6_000 && event.chaosType !== "bump",
    );
    const frameAtFiveSeconds = race.frames.find((frame) => frame.timeMs === 5_000);

    expect(earlyMajorIncidents.length).toBeLessThanOrEqual(2);
    expect(frameAtFiveSeconds?.metrics.active).toBeGreaterThanOrEqual(24);
    expect(frameAtFiveSeconds?.metrics.eliminated).toBe(0);
  });

  it("does not force demo races to finish at the old 45 second mark", () => {
    const race = simulateRace({
      seed: 2029,
      racers: createDemoRace(2029).racers,
      durationMs: 120_000,
      trackAngleDeg: 6,
    });
    const finalFrame = race.frames.at(-1);

    expect(finalFrame?.timeMs).toBeGreaterThan(45_000);
    expect(finalFrame?.timeMs).toBeLessThanOrEqual(120_000);
    expect(finalFrame?.cars.filter((car) => car.status === "running")).toHaveLength(1);
  });

  it("ramps from 0mph to 2mph at startup before holding and later speeding up", () => {
    const race = simulateRace({
      seed: 2034,
      racers: createDemoRace(2034).racers,
      durationMs: 120_000,
      trackAngleDeg: 6,
    });
    const atStart = race.frames.find((frame) => frame.timeMs === 0);
    const afterStartup = race.frames.find((frame) => frame.timeMs === 9_000);
    const atOneMinute = race.frames.find((frame) => frame.timeMs === 60_000);
    const atNinetySeconds = race.frames.find((frame) => frame.timeMs === 90_000);

    expect(atStart?.beltSpeedMph).toBe(0);
    expect(afterStartup?.beltSpeedMph).toBe(2);
    expect(atOneMinute?.beltSpeedMph).toBe(2);
    expect(atNinetySeconds?.beltSpeedMph).toBeCloseTo(6);
  });

  it("allows occasional real incidents during the 2mph hold without making every seed explode", () => {
    const races = Array.from({ length: 18 }, (_, index) =>
      simulateRace({
        seed: 4100 + index,
        racers: createDemoRace(4100 + index).racers,
        durationMs: 120_000,
        trackAngleDeg: 6,
      }),
    );
    const racesWithEarlyIncidents = races.filter((race) =>
      race.timeline.some((event) => event.timeMs < 60_000 && event.chaosType !== "bump"),
    );

    expect(racesWithEarlyIncidents.length).toBeGreaterThanOrEqual(3);
    expect(racesWithEarlyIncidents.length).toBeLessThanOrEqual(12);
  });

  it("keeps side-gap hangs uncommon across seeded demo races", () => {
    const sideHangRaces = Array.from({ length: 20 }, (_, index) =>
      simulateRace({ seed: 3000 + index, racers: createDemoRace(3000 + index).racers, durationMs: 45_000 }),
    ).filter((race) => race.results.some((result) => result.status === "side-hung"));

    expect(sideHangRaces.length).toBeGreaterThanOrEqual(2);
    expect(sideHangRaces.length).toBeLessThanOrEqual(8);
  });

  it("allows only explicit race state transitions", () => {
    expect(getAllowedTransition("REGISTRATION_OPEN", "COUNTDOWN")).toBe(false);
    expect(getAllowedTransition("REGISTRATION_OPEN", "REGISTRATION_CLOSED")).toBe(true);
    expect(getAllowedTransition("COUNTDOWN", "RACING")).toBe(true);
    expect(getAllowedTransition("RESULTS", "REGISTRATION_OPEN")).toBe(false);
    expect(getAllowedTransition("RESETTING", "IDLE")).toBe(true);
  });
});

describe("race state type", () => {
  it("includes the broadcast states needed by the POC", () => {
    const states: RaceState[] = [
      "BOOT",
      "IDLE",
      "REGISTRATION_OPEN",
      "REGISTRATION_CLOSED",
      "COUNTDOWN",
      "RACING",
      "PHOTO_FINISH",
      "RESULTS",
      "RESETTING",
      "ERROR",
    ];

    expect(states).toContain("RACING");
  });
});
