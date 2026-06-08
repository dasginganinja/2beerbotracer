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
  type PhysicsTuning,
  type RaceFrame,
  type RaceState,
  type Racer,
  type SimulatedRace,
} from "../simulation/raceSimulation";

const WIDTH = 1920;
const HEIGHT = 1080;
const CENTER_X = 960;
const DEMO_RACE_SAFETY_MS = 120_000;
const BELT_WIDTH = 1300;
const BELT_X = (WIDTH - BELT_WIDTH) / 2;
const BELT_Y = 120;
const BELT_HEIGHT = 790;
const BELT_TOP_WIDTH_RATIO = 0.58;
const BELT_LEFT_BOTTOM = BELT_X;
const BELT_RIGHT_BOTTOM = BELT_X + BELT_WIDTH;
const BELT_LEFT_TOP = CENTER_X - (BELT_WIDTH * BELT_TOP_WIDTH_RATIO) / 2;
const BELT_RIGHT_TOP = CENTER_X + (BELT_WIDTH * BELT_TOP_WIDTH_RATIO) / 2;
const SLOT_COLUMNS = 15;
const CAR_SCALE = 0.92;
const ROW_CENTER_SPACING = 105;
const CAR_NOSE_TO_CENTER = 66 * CAR_SCALE;
const CAR_BASE_ROTATION = Math.PI / 2;
const DEFAULT_BELT_SPEED_MPH = 2;
const DEFAULT_DEBUG_METRICS = {
  active: 0,
  sliding: 0,
  eliminated: 0,
  averageWheelSpeed: 0,
  averageTraction: 0,
};
const DEFAULT_PHYSICS_TUNING: PhysicsTuning = {
  beltStartMph: 2,
  beltFullMph: 10,
  beltStartupRampMs: 9_000,
  beltHoldMs: 60_000,
  beltRampMs: 60_000,
  trackAngleDeg: 6,
  trackAngleAssistPxPerSecPerDeg: 8,
  rollingResistancePerSecond: 0.012,
  yawWheelLossPerSecond: 0.22,
  yawRecoverPerSecond: 0.08,
  maxBumperCompressionPx: 5,
  contactRestitution: 0.18,
  seamShiftPx: 18,
  carTraitVariance: 1,
  earlyUpsetChance: 0.26,
};

type CarView = {
  racer: Racer;
  root: Container;
  body: Graphics;
  shadow: Graphics;
  roofNumber: Text;
  lastProgress: number;
  lastOffset: number;
  lastStatus: string;
};

type ProjectedPoint = {
  x: number;
  y: number;
  depthScale: number;
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
  private readonly debugLayer = new Container();
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
  private trackAngleDeg = 6;
  private lastHudKey = "";
  private lastLeaderboardKey = "";
  private lastDebugKey = "";
  private calloutUntilMs = 0;
  private calloutText = "";
  private beltScroll = 0;
  private titleText!: Text;
  private phaseText!: Text;
  private promptText!: Text;
  private leaderboardText!: Text;
  private debugText!: Text;
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
    this.trackAngleDeg = this.readTrackAngle();
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
    this.root.addChild(this.trackLayer, this.carLayer, this.fxLayer, this.hudLayer, this.debugLayer, this.resultsLayer);

    this.drawTrack();
    this.createHud();
    this.createDebugPanel();
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
      durationMs: DEMO_RACE_SAFETY_MS,
      trackAngleDeg: this.trackAngleDeg,
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

    const finalFrameTimeMs = this.simulatedRace.frames.at(-1)?.timeMs ?? DEMO_RACE_SAFETY_MS;
    if (this.raceElapsedMs >= finalFrameTimeMs) {
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
      .rect(0, 855, WIDTH, 225)
      .fill(0x121722);

    const railInsetBottom = 88;
    const railInsetTop = 48;
    const deck = new Graphics()
      .poly([
        BELT_LEFT_TOP - railInsetTop,
        BELT_Y - 42,
        BELT_RIGHT_TOP + railInsetTop,
        BELT_Y - 42,
        BELT_RIGHT_BOTTOM + railInsetBottom,
        BELT_Y + BELT_HEIGHT + 36,
        BELT_LEFT_BOTTOM - railInsetBottom,
        BELT_Y + BELT_HEIGHT + 36,
      ], true)
      .fill(0x151922)
      .stroke({ width: 8, color: 0x353b47 });

    const belt = new Graphics()
      .poly([
        BELT_LEFT_TOP,
        BELT_Y,
        BELT_RIGHT_TOP,
        BELT_Y,
        BELT_RIGHT_BOTTOM,
        BELT_Y + BELT_HEIGHT,
        BELT_LEFT_BOTTOM,
        BELT_Y + BELT_HEIGHT,
      ], true)
      .fill(0x2d333f)
      .stroke({ width: 5, color: 0x596273 });

    this.beltStripeLayer.removeChildren();
    for (let i = -2; i < 26; i += 1) {
      const y = BELT_Y + 28 + i * 34;
      const normalizedY = Math.max(0, Math.min(1, (y - BELT_Y) / BELT_HEIGHT));
      const left = this.projectBeltPoint(0.035, normalizedY).x;
      const right = this.projectBeltPoint(0.965, normalizedY).x;
      const stripe = new Graphics()
        .rect(left, y, right - left, 11)
        .fill({ color: 0x3a414e, alpha: 0.36 });
      this.beltStripeLayer.addChild(stripe);
    }

    const rails = new Graphics()
      .poly([
        BELT_LEFT_TOP - 36,
        BELT_Y - 3,
        BELT_LEFT_TOP - 5,
        BELT_Y - 3,
        BELT_LEFT_BOTTOM + 28,
        BELT_Y + BELT_HEIGHT,
        BELT_LEFT_BOTTOM - 34,
        BELT_Y + BELT_HEIGHT,
      ], true)
      .fill(0x0d0f14)
      .stroke({ width: 5, color: 0xf0ebe1 })
      .poly([
        BELT_RIGHT_TOP + 5,
        BELT_Y - 3,
        BELT_RIGHT_TOP + 36,
        BELT_Y - 3,
        BELT_RIGHT_BOTTOM + 34,
        BELT_Y + BELT_HEIGHT,
        BELT_RIGHT_BOTTOM - 28,
        BELT_Y + BELT_HEIGHT,
      ], true)
      .fill(0x0d0f14)
      .stroke({ width: 5, color: 0xf0ebe1 })
      .rect(BELT_LEFT_BOTTOM + 36, BELT_Y + BELT_HEIGHT - 12, BELT_WIDTH - 72, 8)
      .fill({ color: 0xffcf33, alpha: 0.7 });

    const sideGaps = new Graphics()
      .poly([
        BELT_LEFT_TOP + 18,
        BELT_Y + 65,
        BELT_LEFT_TOP + 36,
        BELT_Y + 65,
        BELT_LEFT_BOTTOM + 72,
        BELT_Y + BELT_HEIGHT - 110,
        BELT_LEFT_BOTTOM + 42,
        BELT_Y + BELT_HEIGHT - 110,
      ], true)
      .fill(0x050608)
      .poly([
        BELT_RIGHT_TOP - 36,
        BELT_Y + 65,
        BELT_RIGHT_TOP - 18,
        BELT_Y + 65,
        BELT_RIGHT_BOTTOM - 42,
        BELT_Y + BELT_HEIGHT - 110,
        BELT_RIGHT_BOTTOM - 72,
        BELT_Y + BELT_HEIGHT - 110,
      ], true)
      .fill(0x050608);

    const slots = new Graphics();
    for (let column = 0; column < SLOT_COLUMNS; column += 1) {
      const normalizedX = column / SLOT_COLUMNS;
      const top = this.projectBeltPoint(normalizedX, 0.12);
      const bottom = this.projectBeltPoint(normalizedX, 0.84);
      slots.moveTo(top.x, top.y).lineTo(bottom.x, bottom.y).stroke({ width: 1, color: 0xffffff, alpha: 0.025 });
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
    beltDirection.position.set(BELT_X + BELT_WIDTH - 205, BELT_Y + BELT_HEIGHT - 48);

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
    label.position.set(CENTER_X, 975);

    this.trackLayer.addChild(background, deck, belt, this.beltStripeLayer, rails, sideGaps, slots, beltDirection, label);
  }

  private updateBeltAnimation(deltaMs: number): void {
    const beltSpeedMph = this.getCurrentBeltSpeedMph();
    this.beltScroll = (this.beltScroll - deltaMs * (0.08 + beltSpeedMph * 0.018)) % 34;
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

  private createDebugPanel(): void {
    const panel = new Graphics()
      .roundRect(18, 612, 430, 435, 12)
      .fill({ color: 0x05070a, alpha: 0.76 })
      .stroke({ width: 2, color: 0x596273, alpha: 0.75 });

    this.debugText = new Text({
      text: "",
      style: {
        fontFamily: "Consolas, monospace",
        fontSize: 20,
        fill: 0xd8dde8,
        lineHeight: 25,
      },
    });
    this.debugText.position.set(36, 630);
    this.debugLayer.addChild(panel, this.debugText);
  }

  private setRacers(racers: Racer[]): void {
    this.carLayer.removeChildren();
    this.carViews.clear();

    racers.forEach((racer) => {
      const root = new Container({ label: racer.id });
      const shadow = new Graphics()
        .ellipse(0, 37, 64, 16)
        .fill({ color: 0x000000, alpha: 0.38 });
      const car = new Graphics()
        .roundRect(-49, -31, 98, 62, 11)
        .fill(Number.parseInt(racer.color.slice(1), 16))
        .stroke({ width: 4, color: 0x111111 })
        .roundRect(31, -27, 21, 54, 8)
        .fill(0x101010)
        .rect(42, -19, 10, 38)
        .fill({ color: 0xf1f4f8, alpha: 0.82 })
        .circle(-31, 34, 9)
        .fill(0x050505)
        .circle(31, 34, 9)
        .fill(0x050505)
        .roundRect(-30, -22, 26, 17, 4)
        .fill({ color: 0xffffff, alpha: 0.6 })
        .roundRect(4, -22, 27, 17, 4)
        .fill({ color: 0xffffff, alpha: 0.7 })
        .poly([47, -28, 68, -18, 72, 0, 68, 18, 47, 28], true)
        .fill(Number.parseInt(racer.color.slice(1), 16))
        .stroke({ width: 3, color: 0x111111 })
        .rect(62, -13, 7, 26)
        .fill(0x111111)
        .circle(66, -17, 4)
        .fill(0xf7f1d0)
        .circle(66, 17, 4)
        .fill(0xf7f1d0);

      const roofNumber = new Text({
        text: String(racer.slot),
        style: {
          fontFamily: "Arial Black, Impact, sans-serif",
          fontSize: 23,
          fill: 0xffffff,
          stroke: { color: 0x000000, width: 5 },
        },
      });
      roofNumber.anchor.set(0.5);
      roofNumber.position.set(-3, 1);
      roofNumber.rotation = -Math.PI / 2;

      root.addChild(shadow, car, roofNumber);
      root.scale.set(CAR_SCALE);
      this.carLayer.addChild(root);

      const view = {
        racer,
        root,
        body: car,
        shadow,
        roofNumber,
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
    const slotCenterX = (view.racer.column + 0.5) / SLOT_COLUMNS;
    const yellowLineY = BELT_Y + BELT_HEIGHT - 12;
    const frontRowY = yellowLineY - CAR_NOSE_TO_CENTER;
    const fallbackY = view.racer.row === 0 ? frontRowY : frontRowY - ROW_CENTER_SPACING;
    const fallbackNormalizedY = (fallbackY - BELT_Y) / BELT_HEIGHT;
    const projected = this.projectBeltPoint(
      normalizedX === undefined ? slotCenterX : normalizedX,
      normalizedY === undefined ? fallbackNormalizedY : normalizedY,
    );
    const activeAngle = Math.max(-0.72, Math.min(0.72, angle));
    const statusAngle = status === "knocked-out" || status === "self-spun"
      ? Math.max(-1.05, Math.min(1.05, angle))
      : activeAngle;

    view.root.position.set(projected.x, projected.y);
    view.root.rotation = CAR_BASE_ROTATION + statusAngle;
    view.root.alpha = status === "knocked-out" ? 0.55 : 1;
    view.root.scale.set(CAR_SCALE * renderScale * projected.depthScale);
    view.root.zIndex = Math.round(projected.y);
    view.shadow.rotation = -view.root.rotation;
    view.shadow.alpha = status === "knocked-out" ? 0.22 : 0.38;
  }

  private projectBeltPoint(normalizedX: number, normalizedY: number): ProjectedPoint {
    const y = BELT_Y + normalizedY * BELT_HEIGHT;
    const widthAtY = BELT_WIDTH * (BELT_TOP_WIDTH_RATIO + (1 - BELT_TOP_WIDTH_RATIO) * normalizedY);
    const leftAtY = CENTER_X - widthAtY / 2;
    const x = leftAtY + normalizedX * widthAtY;
    return {
      x,
      y,
      depthScale: 0.62 + normalizedY * 0.52,
    };
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

    const debug = this.buildDebugPanel();
    if (force || debug !== this.lastDebugKey) {
      this.debugText.text = debug;
      this.lastDebugKey = debug;
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
    if (this.state === "RACING") {
      const speedMph = this.getCurrentBeltSpeedMph();
      const tuning = this.getPhysicsTuning();
      const isSpeedRamp = this.raceElapsedMs >= tuning.beltHoldMs && speedMph < tuning.beltFullMph - 0.05;
      const isChaotic = this.elapsedMs < this.calloutUntilMs;
      const message = isChaotic
        ? "incident on the belt"
        : isSpeedRamp
          ? "speeding up for more chaos"
          : "cars are fighting the belt";
      return `${progressSeconds}s | track ${speedMph.toFixed(1)} mph | angle ${this.trackAngleDeg.toFixed(1)}deg | ${message}`;
    }
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

  private buildDebugPanel(): string {
    const frame = this.state === "RACING" ? this.getInterpolatedFrame(this.raceElapsedMs) : undefined;
    const metrics = frame?.metrics ?? DEFAULT_DEBUG_METRICS;
    const tuning = this.getPhysicsTuning();

    return [
      "PHYSICS DEBUG",
      `belt mph       ${this.getCurrentBeltSpeedMph().toFixed(1)}`,
      `startup ramp   ${(tuning.beltStartupRampMs / 1000).toFixed(1)}s`,
      `track angle    ${tuning.trackAngleDeg.toFixed(1)} deg`,
      `angle assist   ${tuning.trackAngleAssistPxPerSecPerDeg.toFixed(1)} px/s/deg`,
      `rolling loss   ${tuning.rollingResistancePerSecond.toFixed(3)} /s`,
      `yaw wheel loss ${tuning.yawWheelLossPerSecond.toFixed(2)} /s`,
      `yaw recovery   ${tuning.yawRecoverPerSecond.toFixed(2)} /s`,
      `bumper crush   ${tuning.maxBumperCompressionPx.toFixed(1)} px`,
      `contact bounce ${tuning.contactRestitution.toFixed(2)}`,
      `seam shift     ${tuning.seamShiftPx.toFixed(1)} px`,
      `trait variance ${tuning.carTraitVariance.toFixed(2)}`,
      `early upset    ${tuning.earlyUpsetChance.toFixed(2)}`,
      `active         ${metrics.active}`,
      `sliding/wobble ${metrics.sliding}`,
      `eliminated     ${metrics.eliminated}`,
      `avg wheels     ${metrics.averageWheelSpeed.toFixed(2)}`,
      `avg traction   ${metrics.averageTraction.toFixed(2)}`,
    ].join("\n");
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
      return { timeMs, beltSpeedMph: DEFAULT_BELT_SPEED_MPH, metrics: DEFAULT_DEBUG_METRICS, cars: [] };
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
    const frameSpanMs = Math.max(1, next.timeMs - previous.timeMs);
    const t = (timeMs - previous.timeMs) / frameSpanMs;
    return {
      timeMs,
      beltSpeedMph: previous.beltSpeedMph + (next.beltSpeedMph - previous.beltSpeedMph) * t,
      metrics: {
        active: next.metrics.active,
        sliding: next.metrics.sliding,
        eliminated: next.metrics.eliminated,
        averageWheelSpeed:
          previous.metrics.averageWheelSpeed +
          (next.metrics.averageWheelSpeed - previous.metrics.averageWheelSpeed) * t,
        averageTraction:
          previous.metrics.averageTraction +
          (next.metrics.averageTraction - previous.metrics.averageTraction) * t,
      },
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
          stackIndex: nextCar?.stackIndex ?? car.stackIndex,
        };
      }),
    };
  }

  private getCurrentBeltSpeedMph(): number {
    if (this.state !== "RACING") {
      return DEFAULT_BELT_SPEED_MPH;
    }
    return this.getInterpolatedFrame(this.raceElapsedMs).beltSpeedMph;
  }

  private getPhysicsTuning(): PhysicsTuning {
    return this.simulatedRace?.tuning ?? { ...DEFAULT_PHYSICS_TUNING, trackAngleDeg: this.trackAngleDeg };
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

  private readTrackAngle(): number {
    const raw = Number(this.params.get("trackAngleDeg") ?? "6");
    return Number.isFinite(raw) ? Math.max(-4, Math.min(8, raw)) : 6;
  }
}
