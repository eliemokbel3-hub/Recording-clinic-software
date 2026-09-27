// The side panel (Cliniko workflow safeguards plan Task 6.4; D1).
//
// It draws `panelModel`'s layout from the worker's view and turns clicks into
// commands the worker relays to the app. Every string is set with
// `textContent` (never parsed as HTML), nothing is written to
// `chrome.storage`, and nothing is logged. The consent tick is never
// pre-ticked, is cleared whenever the note it was given for changes or the
// Ready layout goes away, and is cleared by every Start press. Discard (in
// the Blocked layout) needs a second click within 15 s.
//
// The panel opens from the toolbar icon (`setPanelBehavior` in the worker).
// Its port to the worker drops when the worker restarts; the panel then
// shows "Connecting…" and reconnects, and the worker answers with its
// current view.

import type { PanelView, ToPanel } from "./hub";
import { PANEL_PORT } from "./hub";
import type { BlockedModel, LiveModel, PanelModel, ReadyModel } from "./panel-view";
import { CONNECTING, CONSENT_TEXT, DISCARD_CONFIRM, panelModel } from "./panel-view";

export const RECONNECT_MS = 1000;
export const DISARM_MS = 15_000;

export interface PanelPort {
  postMessage(message: unknown): void;
  onMessage: { addListener(cb: (message: unknown) => void): void };
  onDisconnect: { addListener(cb: () => void): void };
}

export interface PanelRuntime {
  connect(info: { name: string }): PanelPort;
}

function isView(message: unknown): message is ToPanel {
  if (typeof message !== "object" || message === null) return false;
  const m = message as Record<string, unknown>;
  const view = m["view"] as Record<string, unknown> | undefined;
  return m["kind"] === "view" && typeof view === "object" && view !== null && typeof view["connection"] === "string";
}

export class Panel {
  private port: PanelPort | null = null;
  private view: PanelView | null = null;
  private lastViewText = "";
  private consentKey: string | null = null;
  private consentTicked = false;
  private armedRef: string | null = null;
  private disarmTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(
    private readonly doc: Document,
    private readonly mount: HTMLElement,
    private readonly runtime: PanelRuntime,
  ) {}

  start(): void {
    this.render();
    this.connect();
  }

  private connect(): void {
    let port: PanelPort;
    try {
      port = this.runtime.connect({ name: PANEL_PORT });
    } catch {
      setTimeout(() => this.connect(), RECONNECT_MS);
      return;
    }
    this.port = port;
    port.onMessage.addListener((message) => {
      if (port !== this.port || !isView(message)) return;
      const text = JSON.stringify(message.view);
      if (text === this.lastViewText) return;
      this.lastViewText = text;
      this.view = message.view;
      this.render();
    });
    port.onDisconnect.addListener(() => {
      if (port !== this.port) return;
      this.port = null;
      this.view = null;
      this.lastViewText = "";
      this.render();
      setTimeout(() => this.connect(), RECONNECT_MS);
    });
  }

  private send(command: Record<string, unknown>): void {
    try {
      this.port?.postMessage({ kind: "command", ...command });
    } catch {
      // The port closed under the click; the reconnect re-renders.
    }
  }

  // --- drawing -------------------------------------------------------------------

  private el<K extends keyof HTMLElementTagNameMap>(tag: K, text?: string, part?: string): HTMLElementTagNameMap[K] {
    const el = this.doc.createElement(tag);
    if (text !== undefined) el.textContent = text;
    if (part !== undefined) el.setAttribute("data-part", part);
    return el;
  }

  private button(label: string, action: string, onClick: () => void, primary = false): HTMLButtonElement {
    const button = this.el("button", label);
    button.type = "button";
    button.setAttribute("data-action", action);
    if (primary) button.classList.add("primary");
    button.addEventListener("click", onClick);
    return button;
  }

  render(): void {
    const model: PanelModel =
      this.view === null ? { layout: { kind: "message", text: CONNECTING }, warnings: [] } : panelModel(this.view);
    const layout = model.layout;
    if (layout.kind !== "ready" || layout.key !== this.consentKey) {
      // A different note, or no Ready at all: the tick never carries over.
      this.consentTicked = false;
      this.consentKey = layout.kind === "ready" ? layout.key : null;
    }
    if (layout.kind !== "blocked" || layout.session_ref !== this.armedRef) this.disarm();

    const section = this.el("section");
    section.setAttribute("data-layout", layout.kind);
    if (model.banner !== undefined) section.append(this.banner(model.banner));
    switch (layout.kind) {
      case "message": {
        section.append(this.el("p", layout.text, "message"));
        if (layout.hint !== undefined) section.append(this.el("p", layout.hint, "hint"));
        break;
      }
      case "checking":
        section.append(this.el("p", "Checking with Cliniko…", "message"));
        if (layout.clinic !== undefined) section.append(this.el("p", layout.clinic, "clinic"));
        break;
      case "ready":
        this.ready(section, layout);
        break;
      case "live":
        this.live(section, layout);
        break;
      case "blocked":
        this.blocked(section, layout);
        break;
    }
    if (model.queued !== undefined) section.append(this.el("p", model.queued, "queued"));
    for (const warning of model.warnings) section.append(this.el("p", warning, "warning"));
    if (model.refusal !== undefined) {
      const refusal = this.el("p", model.refusal, "refusal");
      refusal.setAttribute("role", "alert");
      section.append(refusal);
    }
    this.mount.replaceChildren(section);
  }

  private banner(banner: NonNullable<PanelModel["banner"]>): HTMLElement {
    const box = this.el("div", undefined, "banner");
    box.append(
      this.el("p", banner.text, "banner-text"),
      this.button("Open for review", "open_review", () =>
        this.send({ action: "open_review", state_rev: banner.state_rev, session_ref: banner.session_ref }),
      ),
    );
    return box;
  }

  private ready(section: HTMLElement, layout: ReadyModel): void {
    section.append(
      this.el("h1", layout.patient, "patient"),
      this.el("p", layout.appointment, "appointment"),
      this.el("p", layout.clinic, "clinic"),
      this.el("p", layout.verification, "verification"),
    );
    const label = this.el("label", undefined, "consent");
    const box = this.el("input");
    box.type = "checkbox";
    box.checked = this.consentTicked;
    label.append(box, this.doc.createTextNode(` ${CONSENT_TEXT}`));
    const start = this.button("Start", "start", () => {
      if (!this.consentTicked) return;
      this.consentTicked = false; // every Start clears the tick
      this.send({ action: "start", state_rev: layout.state_rev, consent: true, target: layout.target });
      this.render();
    }, true);
    start.disabled = !this.consentTicked;
    box.addEventListener("change", () => {
      this.consentTicked = box.checked;
      start.disabled = !box.checked;
    });
    section.append(label, start);
  }

  private live(section: HTMLElement, layout: LiveModel): void {
    section.append(this.el("h1", layout.title, "title"));
    if (layout.timer !== undefined) section.append(this.el("p", layout.timer, "timer"));
    section.append(this.el("p", layout.patient, "patient"));
    if (layout.clinic !== undefined) section.append(this.el("p", layout.clinic, "clinic"));
    section.append(this.el("p", layout.consent, "consent-at"));
    for (const line of layout.hands_free ?? []) section.append(this.el("p", line, "hands-free"));
    const ref = { state_rev: layout.state_rev, session_ref: layout.session_ref };
    const row = this.el("div", undefined, "buttons");
    if (layout.phase === "recording") {
      row.append(this.button("Pause", "pause", () => this.send({ action: "pause", ...ref })));
    }
    if (layout.phase === "paused") {
      row.append(this.button("Resume", "resume", () => this.send({ action: "resume", ...ref }), true));
    }
    if (layout.phase !== "finishing") {
      row.append(this.button("Finish consultation", "finish", () => this.send({ action: "finish", ...ref })));
    }
    section.append(row);
  }

  private blocked(section: HTMLElement, layout: BlockedModel): void {
    section.append(this.el("h1", "Recording paused", "title"), this.el("p", layout.reason, "reason"));
    const people = this.el("div", undefined, "patients");
    const previous = this.el("div");
    previous.append(
      this.el("div", "Recording", "label"),
      this.el("div", layout.previous, "previous"),
      this.el("div", layout.previous_clinic, "previous-clinic"),
    );
    const current = this.el("div");
    current.append(this.el("div", "On screen", "label"), this.el("div", layout.current, "current"));
    people.append(previous, current);
    section.append(people);
    const ref = { state_rev: layout.state_rev, session_ref: layout.session_ref };
    const armed = this.armedRef === layout.session_ref;
    const row = this.el("div", undefined, "buttons");
    row.append(
      this.button("Resume previous", "resume_previous", () => this.send({ action: "resume_previous", ...ref }), true),
      this.button("Finish previous", "finish", () => this.send({ action: "finish", ...ref })),
      this.button(armed ? "Confirm discard" : "Discard previous", "discard", () => {
        if (this.armedRef !== layout.session_ref) {
          this.armedRef = layout.session_ref;
          this.disarmTimer = setTimeout(() => {
            this.disarm();
            this.render();
          }, DISARM_MS);
          this.render();
          return;
        }
        this.disarm();
        this.send({ action: "discard", confirmed: true, ...ref });
        this.render();
      }),
    );
    section.append(row);
    if (armed) section.append(this.el("p", DISCARD_CONFIRM, "confirm"));
  }

  private disarm(): void {
    this.armedRef = null;
    if (this.disarmTimer !== null) {
      clearTimeout(this.disarmTimer);
      this.disarmTimer = null;
    }
  }
}

/** Start the panel on its page. */
export function boot(): Panel | null {
  const mount = typeof document !== "undefined" ? document.getElementById("panel") : null;
  if (mount === null || typeof chrome === "undefined") return null;
  const panel = new Panel(document, mount, chrome.runtime);
  panel.start();
  return panel;
}

export const panel = boot();
