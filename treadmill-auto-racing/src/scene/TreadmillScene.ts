import {
  Application,
  Container,
  Graphics,
  Text,
  type Ticker,
} from "pixi.js";
import {
  createDemoRace,
  simulateRace,
  type DemoRace,
  type RaceFrame,
  type RaceState,
  type Racer,
  type SimulatedRace,
} from "../simulation/raceSimulation";

const WIDTH = 1920;
const HEIGHT = 1080;
const CENTER_X = 960;
const CENTER_Y = 575;
const TRACK_RADIUS_X = 660;
const TRACK_RADIUS_Y = 250;
const DEMO_RACE_MS = 45_000;

type CarView = {
  racer: Racer;
  root: Container;
  nameplate: Text;
  lastProgress: number;
};

export class TreadmillScene {
  private readonly host: HTMLElement;
  private readonly params: URLSearchParams;
  private readonly app = new Application();
  private readonly root = new Container({ sortableChildren: true });
  private readonly trackLayer = new Container();
  private readonly carLayer = new Container({ sortableChildren: true });
  private readonly fxLayer = new Container();
  private readonly hudLayer = new Container();
  private readonly resultsLayer = new Container();
  private readonly carViews = new Map<string, CarView>();
  private mode: "demo" | "local" | "hosted" = "demo";
  private race: DemoRace = createDemoRace(20260607);
  private simulatedRace: SimulatedRace | null = null;
  private state: RaceState = "BOOT";
  private elapsedMs = 0;
  private stateElapsedMs = 0;
  private raceElapsedMs = 0;
  private seed = 20260607;
  private lastHudKey = "";
  private lastLeaderboardKey = "";
  private calloutUntilMs = 0;
  private calloutText = "";
  private titleText!: Text;
  private phaseText!: Text;
  private promptText!: Text;
  private leaderboardText!: Text;
  private calloutBanner!: Container;
  private calloutLabel!: Text;
  private resultsText!: Text;

  public constructor(host: HTMLElement, params: URLSearchParams) {
    this.host = host;
    this.params = params;
  }

  public async start(): Promise<void> {
    this.mode = this.readMode();
    this.seed = Number(this.params.get("seed") ?? Date.now() % 1_000_000);
    this.race = createDemoRace(this.seed);
    this.state = "REGISTRATION_OPEN";

    await this.app.init({
      width: WIDTH,
      height: HEIGHT,
      resolution: 1,
      antialias: true,
      backgroundAlpha: this.params.get("transparent") === "1" ? 0 : 1,
      backgroundColor: 0x08090d,
    });

    this.host.appendChild(this.app.canvas);
    this.app.stage.addChild(this.root);
    this.root.addChild(this.trackLayer, this.carLayer, this.fxLayer, this.hudLayer, this.resultsLayer);

    this.drawTrack();
    this.createHud();
    this.setRacers(this.race.racers);
    this.updateHud(true);

    this.app.ticker.add(this.update, this);
  }

  private update(ticker: Ticker): void {
    const deltaMs = Math.min(ticker.deltaMS, 100);
    this.elapsedMs += deltaMs;
    this.stateElapsedMs += deltaMs;

    if (this.state === "REGISTRATION_OPEN" && this.stateElapsedMs > 4_000) {
      this.transitionTo("REGISTRATION_CLOSED");
    } else if (this.state === "REGISTRATION_CLOSED" && this.stateElapsedMs > 1_000) {
      this.transitionTo("COUNTDOWN");
    } else if (this.state === "COUNTDOWN" && this.stateElapsedMs > 4_000) {
      this.startRace();
    } else if (this.state === "RACING") {
      this.updateRace(deltaMs);
    } else if (this.state === "PHOTO_FINISH" && this.stateElapsedMs > 3_000) {
      this.transitionTo("RESULTS");
      this.showResults();
    } else if (this.state === "RESULTS" && this.stateElapsedMs > 10_000) {
      this.resetDemo();
    }

    this.updateHud(false);
  }

  private transitionTo(next: RaceState): void {
    this.state = next;
    this.stateElapsedMs = 0;
  }

  private startRace(): void {
    this.simulatedRace = simulateRace({
      seed: this.seed,
      racers: this.race.racers,
      durationMs: DEMO_RACE_MS,
    });
    this.raceElapsedMs = 0;
    this.resultsLayer.removeChildren();
    this.transitionTo("RACING");
  }

  private updateRace(deltaMs: number): void {
    if (!this.simulatedRace) {
      return;
    }

    this.raceElapsedMs += deltaMs;
    const frame = this.getInterpolatedFrame(this.raceElapsedMs);
    for (const car of frame.cars) {
      const view = this.carViews.get(car.racerId);
      if (!view) {
        continue;
      }
      this.placeCar(view, car.progress);
      view.lastProgress = car.progress;
    }

    const event = this.simulatedRace.timeline.find(
      (candidate) =>
        this.raceElapsedMs >= candidate.timeMs &&
        this.raceElapsedMs - deltaMs < candidate.timeMs,
    );
    if (event) {
      this.calloutText = event.message;
      this.calloutUntilMs = this.elapsedMs + 3_000;
      this.pulseCar(event.racerId);
    }

    if (this.raceElapsedMs >= DEMO_RACE_MS) {
      for (const result of this.simulatedRace.results) {
        const view = this.carViews.get(result.racerId);
        if (view) {
          this.placeCar(view, 1);
        }
      }
      this.transitionTo("PHOTO_FINISH");
    }
  }

  private resetDemo(): void {
    this.seed += 1;
    this.race = createDemoRace(this.seed);
    this.simulatedRace = null;
    this.raceElapsedMs = 0;
    this.resultsLayer.removeChildren();
    this.setRacers(this.race.racers);
    this.transitionTo("REGISTRATION_OPEN");
  }

  private drawTrack(): void {
    const background = new Graphics()
      .rect(0, 0, WIDTH, HEIGHT)
      .fill(0x08090d)
      .rect(0, 720, WIDTH, 360)
      .fill(0x121722);

    const treadmill = new Graphics()
      .roundRect(210, 250, 1500, 650, 42)
      .fill(0x151922)
      .stroke({ width: 8, color: 0x353b47 })
      .roundRect(260, 300, 1400, 550, 32)
      .fill(0x20252f);

    const belt = new Graphics()
      .ellipse(CENTER_X, CENTER_Y, TRACK_RADIUS_X + 95, TRACK_RADIUS_Y + 95)
      .stroke({ width: 118, color: 0x2b303b })
      .ellipse(CENTER_X, CENTER_Y, TRACK_RADIUS_X + 15, TRACK_RADIUS_Y + 15)
      .stroke({ width: 10, color: 0xffcf33 })
      .ellipse(CENTER_X, CENTER_Y, TRACK_RADIUS_X - 85, TRACK_RADIUS_Y - 85)
      .stroke({ width: 4, color: 0x596273, alpha: 0.7 });

    const finish = new Graphics()
      .rect(CENTER_X - 18, CENTER_Y - TRACK_RADIUS_Y - 112, 36, 190)
      .fill(0xf7f7fb)
      .rect(CENTER_X - 18, CENTER_Y - TRACK_RADIUS_Y - 112, 18, 24)
      .fill(0x111111)
      .rect(CENTER_X, CENTER_Y - TRACK_RADIUS_Y - 88, 18, 24)
      .fill(0x111111)
      .rect(CENTER_X - 18, CENTER_Y - TRACK_RADIUS_Y - 64, 18, 24)
      .fill(0x111111)
      .rect(CENTER_X, CENTER_Y - TRACK_RADIUS_Y - 40, 18, 24)
      .fill(0x111111);

    const label = new Text({
      text: "TREADMILL AUTO RACING",
      style: {
        fontFamily: "Arial Black, Impact, sans-serif",
        fontSize: 40,
        fill: 0xffcf33,
        stroke: { color: 0x000000, width: 6 },
      },
    });
    label.anchor.set(0.5);
    label.position.set(CENTER_X, 930);

    this.trackLayer.addChild(background, treadmill, belt, finish, label);
  }

  private createHud(): void {
    this.titleText = new Text({
      text: "",
      style: {
        fontFamily: "Arial Black, Impact, sans-serif",
        fontSize: 54,
        fill: 0xffffff,
        stroke: { color: 0x000000, width: 8 },
      },
    });
    this.titleText.position.set(48, 34);

    this.phaseText = new Text({
      text: "",
      style: {
        fontFamily: "Arial Black, Impact, sans-serif",
        fontSize: 96,
        fill: 0xffcf33,
        stroke: { color: 0x000000, width: 10 },
      },
    });
    this.phaseText.anchor.set(0.5);
    this.phaseText.position.set(CENTER_X, 140);

    this.promptText = new Text({
      text: "",
      style: {
        fontFamily: "Arial, sans-serif",
        fontSize: 34,
        fill: 0xf7f7fb,
        stroke: { color: 0x000000, width: 5 },
      },
    });
    this.promptText.anchor.set(0.5);
    this.promptText.position.set(CENTER_X, 220);

    this.leaderboardText = new Text({
      text: "",
      style: {
        fontFamily: "Consolas, monospace",
        fontSize: 28,
        fill: 0xf7f7fb,
        lineHeight: 38,
      },
    });
    this.leaderboardText.position.set(1515, 90);

    this.calloutBanner = new Container();
    const calloutBg = new Graphics()
      .roundRect(-430, -42, 860, 84, 16)
      .fill({ color: 0xffcf33, alpha: 0.96 })
      .stroke({ width: 4, color: 0x111111 });
    this.calloutLabel = new Text({
      text: "",
      style: {
        fontFamily: "Arial Black, Impact, sans-serif",
        fontSize: 30,
        fill: 0x111111,
      },
    });
    this.calloutLabel.anchor.set(0.5);
    this.calloutBanner.addChild(calloutBg, this.calloutLabel);
    this.calloutBanner.position.set(CENTER_X, 820);
    this.calloutBanner.visible = false;

    this.hudLayer.addChild(
      this.titleText,
      this.phaseText,
      this.promptText,
      this.leaderboardText,
      this.calloutBanner,
    );
  }

  private setRacers(racers: Racer[]): void {
    this.carLayer.removeChildren();
    this.carViews.clear();

    racers.forEach((racer, index) => {
      const root = new Container({ label: racer.id });
      const car = new Graphics()
        .roundRect(-34, -18, 68, 36, 10)
        .fill(Number.parseInt(racer.color.slice(1), 16))
        .stroke({ width: 4, color: 0x111111 })
        .circle(-20, 20, 8)
        .fill(0x050505)
        .circle(20, 20, 8)
        .fill(0x050505)
        .rect(4, -13, 20, 10)
        .fill({ color: 0xffffff, alpha: 0.7 });

      const nameplate = new Text({
        text: racer.displayName,
        style: {
          fontFamily: "Arial, sans-serif",
          fontSize: 20,
          fill: 0xffffff,
          stroke: { color: 0x000000, width: 4 },
        },
      });
      nameplate.anchor.set(0.5);
      nameplate.position.set(0, -38);

      root.addChild(car, nameplate);
      this.carLayer.addChild(root);

      const view = { racer, root, nameplate, lastProgress: index / racers.length };
      this.carViews.set(racer.id, view);
      this.placeCar(view, index / racers.length);
    });
  }

  private placeCar(view: CarView, progress: number): void {
    const laneOffset = (Number(view.racer.id.replace(/\D/g, "")) % 5 - 2) * 16;
    const angle = -Math.PI / 2 + progress * Math.PI * 2;
    const radiusX = TRACK_RADIUS_X + laneOffset;
    const radiusY = TRACK_RADIUS_Y + laneOffset * 0.35;
    const x = CENTER_X + Math.cos(angle) * radiusX;
    const y = CENTER_Y + Math.sin(angle) * radiusY;

    view.root.position.set(x, y);
    view.root.rotation = angle + Math.PI / 2;
    view.root.zIndex = Math.round(y);
    view.nameplate.rotation = -view.root.rotation;
  }

  private updateHud(force: boolean): void {
    const countdown = Math.max(0, Math.ceil((4_000 - this.stateElapsedMs) / 1000));
    const progressSeconds = Math.floor(this.raceElapsedMs / 1000);
    const title = `Treadmill Auto Racing  |  ${this.mode.toUpperCase()} MODE`;
    const phase = this.getPhaseLabel(countdown);
    const prompt = this.getPromptLabel(progressSeconds);
    const hudKey = `${title}|${phase}|${prompt}`;

    if (force || hudKey !== this.lastHudKey) {
      this.titleText.text = title;
      this.phaseText.text = phase;
      this.promptText.text = prompt;
      this.lastHudKey = hudKey;
    }

    const leaderboard = this.buildLeaderboard();
    if (force || leaderboard !== this.lastLeaderboardKey) {
      this.leaderboardText.text = leaderboard;
      this.lastLeaderboardKey = leaderboard;
    }

    this.calloutBanner.visible = this.elapsedMs < this.calloutUntilMs;
    if (this.calloutBanner.visible && this.calloutLabel.text !== this.calloutText) {
      this.calloutLabel.text = this.calloutText;
    }
  }

  private getPhaseLabel(countdown: number): string {
    if (this.state === "REGISTRATION_OPEN") return "REGISTRATION OPEN";
    if (this.state === "REGISTRATION_CLOSED") return "LOCKING GRID";
    if (this.state === "COUNTDOWN") return countdown > 0 ? String(countdown) : "GO";
    if (this.state === "RACING") return "RACING";
    if (this.state === "PHOTO_FINISH") return "PHOTO FINISH";
    if (this.state === "RESULTS") return "RESULTS";
    return this.state;
  }

  private getPromptLabel(progressSeconds: number): string {
    if (this.state === "REGISTRATION_OPEN") return "Type !race to join the next treadmill disaster";
    if (this.state === "REGISTRATION_CLOSED") return `${this.race.racers.length} cars staged`;
    if (this.state === "COUNTDOWN") return "Hands off the belt. Physics is booting.";
    if (this.state === "RACING") return `${progressSeconds}s / ${DEMO_RACE_MS / 1000}s`;
    if (this.state === "PHOTO_FINISH") return "Race control is pretending that was measurable";
    if (this.state === "RESULTS") return "Resetting for the next grid soon";
    return "";
  }

  private buildLeaderboard(): string {
    const ordered = [...this.carViews.values()].sort((a, b) => b.lastProgress - a.lastProgress);
    const header = "POSITION TOWER";
    const rows = ordered.slice(0, 10).map((view, index) => {
      const place = String(index + 1).padStart(2, " ");
      return `${place}. ${view.racer.displayName}`;
    });
    return [header, ...rows].join("\n");
  }

  private showResults(): void {
    if (!this.simulatedRace) {
      return;
    }

    const panel = new Graphics()
      .roundRect(460, 245, 1000, 590, 18)
      .fill({ color: 0x10141c, alpha: 0.94 })
      .stroke({ width: 5, color: 0xffcf33 });

    const lines = this.simulatedRace.results
      .slice(0, 10)
      .map((result) => `${result.place}. ${result.displayName}  ${formatTime(result.finishTimeMs)}`);

    this.resultsText = new Text({
      text: `OFFICIAL ENOUGH RESULTS\n\n${lines.join("\n")}`,
      style: {
        fontFamily: "Arial Black, Impact, sans-serif",
        fontSize: 34,
        fill: 0xffffff,
        lineHeight: 48,
        stroke: { color: 0x000000, width: 5 },
      },
    });
    this.resultsText.position.set(520, 300);
    this.resultsLayer.addChild(panel, this.resultsText);
  }

  private getInterpolatedFrame(timeMs: number): RaceFrame {
    if (!this.simulatedRace) {
      return { timeMs, cars: [] };
    }

    const frames = this.simulatedRace.frames;
    const nextIndex = frames.findIndex((frame) => frame.timeMs >= timeMs);
    if (nextIndex <= 0) {
      return frames[0];
    }
    if (nextIndex === -1) {
      return frames[frames.length - 1];
    }

    const previous = frames[nextIndex - 1];
    const next = frames[nextIndex];
    const t = (timeMs - previous.timeMs) / (next.timeMs - previous.timeMs);
    return {
      timeMs,
      cars: previous.cars.map((car) => {
        const nextCar = next.cars.find((candidate) => candidate.racerId === car.racerId);
        return {
          racerId: car.racerId,
          progress: car.progress + ((nextCar?.progress ?? car.progress) - car.progress) * t,
        };
      }),
    };
  }

  private pulseCar(racerId: string): void {
    const view = this.carViews.get(racerId);
    if (!view) {
      return;
    }
    view.root.scale.set(1.25);
    setTimeout(() => view.root.scale.set(1), 350);
  }

  private readMode(): "demo" | "local" | "hosted" {
    const mode = this.params.get("mode");
    if (mode === "local" || mode === "hosted") {
      return mode;
    }
    return "demo";
  }
}

function formatTime(ms: number): string {
  return `${(ms / 1000).toFixed(2)}s`;
}
