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
const DEMO_RACE_MS = 45_000;
const BELT_X = 250;
const BELT_Y = 300;
const BELT_WIDTH = 1420;
const BELT_HEIGHT = 520;
const SLOT_COLUMNS = 15;
const SLOT_WIDTH = BELT_WIDTH / SLOT_COLUMNS;
const CAR_SCALE = 0.72;
const CAR_BASE_ROTATION = Math.PI / 2;

type CarView = {
  racer: Racer;
  root: Container;
  shadow: Graphics;
  nameplate: Text;
  lastProgress: number;
  lastOffset: number;
  lastStatus: string;
};

export class TreadmillScene {
  private readonly host: HTMLElement;
  private readonly params: URLSearchParams;
  private readonly app = new Application();
  private readonly root = new Container({ sortableChildren: true });
  private readonly trackLayer = new Container();
  private readonly beltStripeLayer = new Container();
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
  private beltScroll = 0;
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
    this.updateBeltAnimation(deltaMs);

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
      this.placeCar(view, car.x, car.y, car.angle, car.status, car.scale);
      view.lastProgress = car.progress;
      view.lastOffset = car.trackOffset;
      view.lastStatus = car.status;
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
          this.placeCar(view, undefined, undefined, 0, result.status);
          view.lastStatus = result.status;
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
      .rect(0, 805, WIDTH, 275)
      .fill(0x121722);

    const deck = new Graphics()
      .roundRect(185, 245, 1550, 640, 42)
      .fill(0x151922)
      .stroke({ width: 8, color: 0x353b47 })
      .roundRect(BELT_X, BELT_Y, BELT_WIDTH, BELT_HEIGHT, 26)
      .fill(0x222936)
      .stroke({ width: 6, color: 0xffcf33 });

    const belt = new Graphics()
      .roundRect(BELT_X + 28, BELT_Y + 38, BELT_WIDTH - 56, BELT_HEIGHT - 76, 18)
      .fill(0x2d333f)
      .stroke({ width: 4, color: 0x596273 });

    this.beltStripeLayer.removeChildren();
    for (let i = -2; i < 16; i += 1) {
      const stripe = new Graphics()
        .rect(BELT_X + 48, BELT_Y + 55 + i * 34, BELT_WIDTH - 96, 11)
        .fill({ color: 0x3a414e, alpha: 0.36 });
      this.beltStripeLayer.addChild(stripe);
    }

    const rails = new Graphics()
      .rect(BELT_X + 18, BELT_Y + 30, 22, BELT_HEIGHT - 60)
      .fill(0x0d0f14)
      .rect(BELT_X + BELT_WIDTH - 40, BELT_Y + 30, 22, BELT_HEIGHT - 60)
      .fill(0x0d0f14)
      .rect(BELT_X + 40, BELT_Y + BELT_HEIGHT - 74, BELT_WIDTH - 80, 6)
      .fill({ color: 0xffcf33, alpha: 0.55 });

    const sideGaps = new Graphics()
      .roundRect(BELT_X + 38, BELT_Y + 80, 30, BELT_HEIGHT - 160, 10)
      .fill(0x050608)
      .roundRect(BELT_X + BELT_WIDTH - 68, BELT_Y + 80, 30, BELT_HEIGHT - 160, 10)
      .fill(0x050608);

    const slots = new Graphics();
    for (let column = 0; column < SLOT_COLUMNS; column += 1) {
      const x = BELT_X + column * SLOT_WIDTH;
      slots.rect(x, BELT_Y + 105, 1, BELT_HEIGHT - 210).fill({ color: 0xffffff, alpha: 0.055 });
    }

    const beltDirection = new Text({
      text: "BELT DIRECTION UP",
      style: {
        fontFamily: "Arial Black, Impact, sans-serif",
        fontSize: 30,
        fill: 0xb8bfcc,
        stroke: { color: 0x000000, width: 5 },
      },
    });
    beltDirection.anchor.set(0.5);
    beltDirection.position.set(BELT_X + BELT_WIDTH - 200, BELT_Y + BELT_HEIGHT - 68);

    const label = new Text({
      text: "TREADMILL RACING: 30 CARS / LAST SURVIVOR WINS",
      style: {
        fontFamily: "Arial Black, Impact, sans-serif",
        fontSize: 34,
        fill: 0xffcf33,
        stroke: { color: 0x000000, width: 6 },
      },
    });
    label.anchor.set(0.5);
    label.position.set(CENTER_X, 900);

    this.trackLayer.addChild(background, deck, belt, this.beltStripeLayer, rails, sideGaps, slots, beltDirection, label);
  }

  private updateBeltAnimation(deltaMs: number): void {
    this.beltScroll = (this.beltScroll - deltaMs * 0.14) % 34;
    this.beltStripeLayer.y = this.beltScroll;
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
    this.leaderboardText.position.set(1500, 75);

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

    racers.forEach((racer) => {
      const root = new Container({ label: racer.id });
      const shadow = new Graphics()
        .ellipse(0, 30, 54, 13)
        .fill({ color: 0x000000, alpha: 0.38 });
      const car = new Graphics()
        .roundRect(-42, -20, 84, 40, 10)
        .fill(Number.parseInt(racer.color.slice(1), 16))
        .stroke({ width: 4, color: 0x111111 })
        .circle(-24, 22, 8)
        .fill(0x050505)
        .circle(24, 22, 8)
        .fill(0x050505)
        .rect(8, -14, 24, 11)
        .fill({ color: 0xffffff, alpha: 0.7 })
        .poly([42, 0, 58, -10, 58, 10], true)
        .fill(Number.parseInt(racer.color.slice(1), 16))
        .stroke({ width: 3, color: 0x111111 });

      const nameplate = new Text({
        text: `#${racer.slot} ${racer.displayName}`,
        style: {
          fontFamily: "Arial, sans-serif",
          fontSize: 17,
          fill: 0xffffff,
          stroke: { color: 0x000000, width: 4 },
        },
      });
      nameplate.anchor.set(0.5);
      nameplate.position.set(0, -37);

      root.addChild(shadow, car, nameplate);
      root.scale.set(CAR_SCALE);
      this.carLayer.addChild(root);

      const view = {
        racer,
        root,
        shadow,
        nameplate,
        lastProgress: 0.5,
        lastOffset: 0,
        lastStatus: "running",
      };
      this.carViews.set(racer.id, view);
      this.placeCar(view, undefined, undefined, 0, "running");
    });
  }

  private placeCar(
    view: CarView,
    normalizedX?: number,
    normalizedY?: number,
    angle: number = 0,
    status: string = "running",
    renderScale: number = 1,
  ): void {
    const slotCenterX = BELT_X + view.racer.column * SLOT_WIDTH + SLOT_WIDTH / 2;
    const yellowLineY = BELT_Y + BELT_HEIGHT - 74;
    const fallbackY = view.racer.row === 0 ? yellowLineY - 42 : yellowLineY - 90;
    const x = normalizedX === undefined ? slotCenterX : BELT_X + normalizedX * BELT_WIDTH;
    const y = normalizedY === undefined ? fallbackY : BELT_Y + normalizedY * BELT_HEIGHT;
    const activeAngle = Math.max(-0.72, Math.min(0.72, angle));
    const statusAngle = status === "knocked-out" || status === "self-spun"
      ? Math.max(-1.05, Math.min(1.05, angle))
      : activeAngle;

    view.root.position.set(x, y);
    view.root.rotation = CAR_BASE_ROTATION + statusAngle;
    view.root.alpha = status === "knocked-out" ? 0.55 : 1;
    view.root.scale.set(CAR_SCALE * renderScale);
    view.root.zIndex = Math.round(y);
    view.shadow.rotation = -view.root.rotation;
    view.shadow.alpha = status === "knocked-out" ? 0.22 : 0.38;
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
    if (this.state === "RACING") return `${progressSeconds}s / ${DEMO_RACE_MS / 1000}s | lose momentum and the belt carries you up`;
    if (this.state === "PHOTO_FINISH") return "Race control is counting survivors and side-gap victims";
    if (this.state === "RESULTS") return "Resetting for the next grid soon";
    return "";
  }

  private buildLeaderboard(): string {
    const ordered = [...this.carViews.values()].sort((a, b) => {
      if (a.lastStatus === "running" && b.lastStatus !== "running") return -1;
      if (a.lastStatus !== "running" && b.lastStatus === "running") return 1;
      return b.lastProgress - a.lastProgress;
    });
    const header = "SURVIVAL BOARD";
    const rows = ordered.slice(0, 12).map((view, index) => {
      const place = String(index + 1).padStart(2, " ");
      const status = view.lastStatus === "running" ? "OK" : view.lastStatus.toUpperCase();
      return `${place}. #${String(view.racer.slot).padStart(2, "0")} ${view.racer.displayName} ${status}`;
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
      .map((result) => {
        const status = result.status === "running" ? "survived" : result.status.replace("-", " ");
        return `${result.place}. #${result.slot} ${result.displayName}  ${status}`;
      });

    this.resultsText = new Text({
      text: `TREADMILL SURVIVORS\n\n${lines.join("\n")}`,
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
          trackOffset: car.trackOffset + ((nextCar?.trackOffset ?? car.trackOffset) - car.trackOffset) * t,
          angle: car.angle + ((nextCar?.angle ?? car.angle) - car.angle) * t,
          status: nextCar?.status ?? car.status,
          x: car.x + ((nextCar?.x ?? car.x) - car.x) * t,
          y: car.y + ((nextCar?.y ?? car.y) - car.y) * t,
          scale: car.scale + ((nextCar?.scale ?? car.scale) - car.scale) * t,
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
