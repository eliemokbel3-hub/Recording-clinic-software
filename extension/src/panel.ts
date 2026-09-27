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
// A snapshot that changes only the timer or a `state_rev` (a recording's
// every second) updates the timer's text in place: the buttons stay the same
// nodes, so keyboard focus and a mouse press survive, and each button reads
// its session and revision from the model on screen when clicked. Any other
// change redraws, and focus returns to the same action for the same session
// only (round 60 PR-MED-330).
//
// The panel opens from the toolbar icon (`setPanelBehavior` in the worker).
// Its port to the worker drops when the worker restarts; the panel then
// shows "Connecting…" and reconnects, and the worker answers with its
// current view.

import type { PanelView, ToPanel } from "./hub";
import { PANEL_PORT } from "./hub";
import type { BlockedModel, Layout, LiveModel, PanelModel, ReadyModel } from "./panel-view";
import { CHECKING, CONNECTING, CONSENT_TEXT, DISCARD_CONFIRM, panelModel } from "./panel-view";

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

/** The session a model's buttons act on (Live, Blocked), else null. */
function sessionOf(model: PanelModel): string | null {
  const layout = model.layout;
  return layout.kind === "live" || layout.kind === "blocked" ? layout.session_ref : null;
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
  // Round 60 PR-MED-330: the model now on screen (buttons read their ref and
  // `state_rev` from it at click time) and what the drawn DOM depends on.
  private model: PanelModel | null = null;
  private drawnKey: string | null = null;

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

  /**
   * What the drawn DOM depends on, minus what may change in place: the
   * timer's text and the `state_rev`s, which a recording advances about once
   * a second (round 60 PR-MED-330). The local tick and Discard arming are in
   * it, so their changes redraw.
   */
  private structureKey(model: PanelModel): string {
    const layout: Record<string, unknown> = { ...model.layout };
    delete layout.timer;
    delete layout.state_rev;
    const banner = model.banner === undefined ? undefined : { text: model.banner.text, session_ref: model.banner.session_ref };
    return JSON.stringify([layout, banner, model.queued, model.refusal, model.warnings, this.consentTicked, this.armedRef]);
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

    const previous = this.model;
    this.model = model;
    const key = this.structureKey(model);
    if (key === this.drawnKey) {
      // Only the timer or a revision moved: update the timer's text in place,
      // so the buttons stay the same nodes — keyboard focus and a mouse press
      // survive (a rebuild once a second dropped both).
      const timerEl = this.mount.querySelector('[data-part="timer"]');
      if (timerEl !== null && layout.kind === "live" && layout.timer !== undefined) timerEl.textContent = layout.timer;
      return;
    }
    this.drawnKey = key;
    // A rebuild keeps focus on the same action for the SAME session only.
    const active = this.doc.activeElement;
    const focusedAction = active !== null && this.mount.contains(active) ? active.getAttribute("data-action") : null;
    const sameSession = previous !== null && sessionOf(previous) !== null && sessionOf(previous) === sessionOf(model);

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
        section.append(this.el("p", CHECKING, "message"));
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
    if (focusedAction !== null && sameSession) {
      section.querySelector<HTMLElement>(`button[data-action="${focusedAction}"]`)?.focus();
    }
  }

  /** The layout now on screen, if it is of `kind` (a button's click-time read). */
  private current<K extends Layout["kind"]>(kind: K): Extract<Layout, { kind: K }> | null {
    const layout = this.model?.layout;
    return layout !== undefined && layout.kind === kind ? (layout as Extract<Layout, { kind: K }>) : null;
  }

  private banner(banner: NonNullable<PanelModel["banner"]>): HTMLElement {
    const box = this.el("div", undefined, "banner");
    box.append(
      this.el("p", banner.text, "banner-text"),
      this.button("Open for review", "open_review", () => {
        const now = this.model?.banner;
        if (now === undefined) return;
        this.send({ action: "open_review", state_rev: now.state_rev, session_ref: now.session_ref });
      }),
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
      const now = this.current("ready");
      if (!this.consentTicked || now === null) return;
      this.consentTicked = false; // every Start clears the tick
      this.send({ action: "start", state_rev: now.state_rev, consent: true, target: now.target });
      this.render();
    }, true);
    start.disabled = !this.consentTicked;
    box.addEventListener("change", () => {
      this.consentTicked = box.checked;
      start.disabled = !box.checked;
      // The DOM already shows the tick: record it as drawn, so the next
      // snapshot of the same note does not redraw under the practitioner's
      // focus (round 60 PR-MED-330's sibling on Ready).
      this.drawnKey = this.model !== null ? this.structureKey(this.model) : null;
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
    // The ref and revision are read when clicked: the timer updates in place.
    const act = (action: string) => (): void => {
      const now = this.current("live");
      if (now !== null) this.send({ action, state_rev: now.state_rev, session_ref: now.session_ref });
    };
    const row = this.el("div", undefined, "buttons");
    if (layout.phase === "recording") row.append(this.button("Pause", "pause", act("pause")));
    if (layout.phase === "paused") row.append(this.button("Resume", "resume", act("resume"), true));
    if (layout.phase !== "finishing") row.append(this.button("Finish consultation", "finish", act("finish")));
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
    const armed = this.armedRef === layout.session_ref;
    const act = (action: string) => (): void => {
      const now = this.current("blocked");
      if (now !== null) this.send({ action, state_rev: now.state_rev, session_ref: now.session_ref });
    };
    const row = this.el("div", undefined, "buttons");
    row.append(
      this.button("Resume previous", "resume_previous", act("resume_previous"), true),
      this.button("Finish previous", "finish", act("finish")),
      this.button(armed ? "Confirm discard" : "Discard previous", "discard", () => {
        const now = this.current("blocked");
        if (now === null) return;
        if (this.armedRef !== now.session_ref) {
          this.armedRef = now.session_ref;
          this.disarmTimer = setTimeout(() => {
            this.disarm();
            this.render();
          }, DISARM_MS);
          this.render();
          return;
        }
        this.disarm();
        this.send({ action: "discard", confirmed: true, state_rev: now.state_rev, session_ref: now.session_ref });
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
