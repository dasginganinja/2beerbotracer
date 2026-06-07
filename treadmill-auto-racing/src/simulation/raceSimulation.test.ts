import { describe, expect, it } from "vitest";
import {
  createDemoRace,
  getAllowedTransition,
  simulateRace,
  type Racer,
  type RaceState,
} from "./raceSimulation";

const racers: Racer[] = [
  { id: "r1", displayName: "Alpha", color: "#f94144" },
  { id: "r2", displayName: "Bravo", color: "#f3722c" },
  { id: "r3", displayName: "Charlie", color: "#f9c74f" },
  { id: "r4", displayName: "Delta", color: "#90be6d" },
];

describe("race simulation", () => {
  it("creates a demo race with enough named racers for an OBS proof", () => {
    const race = createDemoRace(1234);

    expect(race.raceId).toBe("demo-1234");
    expect(race.state).toBe("REGISTRATION_OPEN");
    expect(race.racers.length).toBeGreaterThanOrEqual(8);
    expect(race.racers.length).toBeLessThanOrEqual(12);
    expect(new Set(race.racers.map((racer) => racer.id)).size).toBe(race.racers.length);
  });

  it("produces deterministic final results for a seed and racer list", () => {
    const first = simulateRace({ seed: 42, racers, durationMs: 45_000 });
    const second = simulateRace({ seed: 42, racers, durationMs: 45_000 });

    expect(first.results).toEqual(second.results);
    expect(first.results.map((result) => result.place)).toEqual([1, 2, 3, 4]);
    expect(new Set(first.results.map((result) => result.racerId)).size).toBe(racers.length);
    expect(first.timeline.some((event) => event.type === "chaos")).toBe(true);
  });

  it("keeps sampled progress between 0 and 1 until the race has finished", () => {
    const race = simulateRace({ seed: 7, racers, durationMs: 30_000 });

    for (const frame of race.frames) {
      for (const car of frame.cars) {
        expect(car.progress).toBeGreaterThanOrEqual(0);
        expect(car.progress).toBeLessThanOrEqual(1);
      }
    }
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
