import "./styles.css";
import { TreadmillScene } from "./scene/TreadmillScene";

const appRoot = document.querySelector<HTMLDivElement>("#app");

if (!appRoot) {
  throw new Error("Missing #app root");
}

const path = window.location.pathname;

if (path.startsWith("/control")) {
  renderControlPanel(appRoot);
} else {
  appRoot.classList.add("scene-root");
  const scene = new TreadmillScene(appRoot, new URLSearchParams(window.location.search));
  scene.start().catch((error: unknown) => {
    appRoot.innerHTML = `<pre class="fatal-error">${String(error)}</pre>`;
  });
}

function renderControlPanel(root: HTMLDivElement): void {
  root.classList.add("control-root");
  root.innerHTML = `
    <main class="control-panel">
      <section>
        <p class="eyebrow">Treadmill Auto Racing</p>
        <h1>Race Control POC</h1>
        <p class="muted">The first proof is browser-demo only. These controls document the operator surface and will wire to the bot bridge in a later phase.</p>
      </section>
      <section class="control-grid">
        <button>Open Registration</button>
        <button>Close Registration</button>
        <button>Start Countdown</button>
        <button>Start Race</button>
        <button>Trigger Chaos</button>
        <button class="danger">Emergency Reset</button>
      </section>
      <section class="status-card">
        <h2>Planned State</h2>
        <dl>
          <div><dt>Mode</dt><dd>demo/local/hosted</dd></div>
          <div><dt>Connection</dt><dd>WebSocket snapshot + events</dd></div>
          <div><dt>Safety</dt><dd>Reset requires confirmation once live control is connected</dd></div>
        </dl>
      </section>
    </main>
  `;
}
