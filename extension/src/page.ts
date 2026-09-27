// Page script (Cliniko workflow safeguards plan Task 6.3; D1, D13).
//
// It is a CUE and an input path, never the enforcing control: the app pauses
// the recording and refuses stale commands; this script only draws what the
// service worker's per-tab slice says and relays two things back. The page's
// own scripts or CSS can keep what it draws hidden or covered for as long as
// they like; the heartbeat only puts back an element that was removed.
//
// - INERT until its slice says the tab's host is allow-listed: before that it
//   says hello once (asking for its slice) and draws nothing. When the host
//   leaves the allow-list — or the app stops — it returns to inert: the
//   frame and the block are removed, the slice (with any patient name) is
//   dropped, and `location.href` reports stop.
// - It never reads Cliniko's page. It reads `location.href` (the SPA
//   backstop: the service worker stays the one `context` reporter and checks
//   the href against the tab's own host) and its own marker element.
// - It draws inside a CLOSED shadow root on its own element, styled through
//   the CSSOM (never an inline <style> the page's CSP could refuse). Every
//   string from the app is set with `textContent`, never parsed as HTML.
// - The block's buttons act only on trusted (user) clicks, carry the
//   `session_ref` and `state_rev` of the slice they were drawn from, and
//   Discard needs a second click within 15 s.
// - After an extension update the old copy is orphaned (its runtime is
//   gone); the re-injected copy removes the old copy's element and takes over,
//   and an orphaned copy tears itself down when it notices.

import type { PageBlock, PageSlice } from "./context";

export const MARKER = "data-cliniko-scribe";
export const HEARTBEAT_MS = 500;
export const DISARM_MS = 15_000;

const RED = "#c62828";
const AMBER = "#b26a00";

const REASONS: Readonly<Record<string, string>> = {
  note_changed: "This tab opened a different treatment note.",
  left_note: "The recording's tab left its treatment note.",
  tab_closed: "The recording's tab was closed.",
  other_note: "Another treatment note is open.",
  login: "Cliniko's login page is open.",
  pipe_lost: "Chrome disconnected from Clinic Scribe.",
  new_client: "Chrome reconnected to Clinic Scribe.",
  suspend: "The computer went to sleep.",
  locked: "The computer was locked.",
};

export function reasonText(reason: string): string {
  // Own entries only: `constructor` and the like are unknown codes (round 38 PR-LOW-211).
  return (Object.hasOwn(REASONS, reason) ? REASONS[reason] : undefined) ?? "The recording was paused.";
}

type BlockAction = "finish" | "resume_previous" | "discard";

export interface RuntimeLike {
  readonly id: string | undefined;
  sendMessage(message: unknown): Promise<unknown>;
  onMessage: {
    addListener(cb: (message: unknown, sender: { id?: string | undefined; tab?: unknown }) => unknown): void;
    removeListener(cb: (message: unknown, sender: { id?: string | undefined; tab?: unknown }) => unknown): void;
  };
}

export interface PageOptions {
  /** Whether a click was made by the user. Tests inject it; jsdom has no trusted events. */
  isTrusted?: (event: Event) => boolean;
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function optionalText(value: unknown): value is string | undefined {
  return value === undefined || typeof value === "string";
}

/** The slice as the worker sends it, or null for anything else. */
export function readSlice(message: unknown): PageSlice | null {
  if (!isObject(message) || message["kind"] !== "slice" || !isObject(message["slice"])) return null;
  const s = message["slice"];
  const frame = s["frame"];
  if (typeof s["active"] !== "boolean" || !(frame === null || frame === "recording" || frame === "paused")) return null;
  const slice: PageSlice = { active: s["active"], frame };
  const b = s["block"];
  if (b !== undefined) {
    if (
      !isObject(b) ||
      typeof b["session_ref"] !== "string" ||
      typeof b["state_rev"] !== "number" ||
      typeof b["reason"] !== "string" ||
      typeof b["same_clinic"] !== "boolean" ||
      typeof b["recording_clinic"] !== "string" ||
      !optionalText(b["previous_patient"]) ||
      !optionalText(b["this_patient"])
    ) {
      return null;
    }
    const block: PageBlock = {
      session_ref: b["session_ref"],
      state_rev: b["state_rev"],
      reason: b["reason"],
      same_clinic: b["same_clinic"],
      recording_clinic: b["recording_clinic"],
    };
    if (typeof b["previous_patient"] === "string") block.previous_patient = b["previous_patient"];
    if (typeof b["this_patient"] === "string") block.this_patient = b["this_patient"];
    slice.block = block;
  }
  return slice;
}

function style(el: HTMLElement, props: Record<string, string>): void {
  for (const [name, value] of Object.entries(props)) el.style.setProperty(name, value);
}

function node<K extends keyof HTMLElementTagNameMap>(
  doc: Document,
  tag: K,
  text?: string,
  props: Record<string, string> = {},
): HTMLElementTagNameMap[K] {
  const el = doc.createElement(tag);
  if (text !== undefined) el.textContent = text;
  style(el, props);
  return el;
}

const BUTTON = {
  font: "600 14px system-ui, sans-serif",
  padding: "8px 14px",
  "border-radius": "6px",
  border: "1px solid #5f6368",
  background: "#ffffff",
  color: "#202124",
  cursor: "pointer",
};

export class PageScript {
  private host: HTMLElement | null = null;
  private root: ShadowRoot | null = null;
  private slice: PageSlice | null = null;
  private lastHref: string;
  private timer: ReturnType<typeof setInterval> | null = null;
  private armedRef: string | null = null;
  private disarmTimer: ReturnType<typeof setTimeout> | null = null;
  private stopped = false;
  private readonly trusted: (event: Event) => boolean;
  private readonly listener = (message: unknown, sender: { id?: string | undefined; tab?: unknown }): false => {
    this.onMessage(message, sender);
    return false;
  };

  constructor(
    private readonly doc: Document,
    private readonly runtime: RuntimeLike,
    options: PageOptions = {},
  ) {
    this.trusted = options.isTrusted ?? ((event) => event.isTrusted);
    this.lastHref = doc.location.href;
  }

  /** For tests only: what the closed shadow root holds. */
  get shadowForTests(): ShadowRoot | null {
    return this.root;
  }

  get isActive(): boolean {
    return this.slice?.active === true;
  }

  start(): void {
    // Take over from a copy orphaned by an extension update.
    for (const stale of this.doc.querySelectorAll(`[${MARKER}]`)) stale.remove();
    this.runtime.onMessage.addListener(this.listener);
    this.send({ kind: "hello", href: this.doc.location.href });
  }

  /** Stop for good (orphaned): everything drawn is removed. */
  stop(): void {
    this.stopped = true;
    this.runtime.onMessage.removeListener(this.listener);
    this.goInert();
  }

  /** The heartbeat: report an href change, and re-attach a removed element (it never restyles one). */
  tick(): void {
    if (this.stopped) return;
    if (this.runtime.id === undefined) {
      this.stop();
      return;
    }
    if (!this.isActive) return; // inert: no reports
    const href = this.doc.location.href;
    if (href !== this.lastHref) {
      this.lastHref = href;
      this.send({ kind: "href", href });
    }
    if (this.host !== null && !this.host.isConnected) this.doc.documentElement.append(this.host);
  }

  private send(message: unknown): void {
    if (this.stopped) return;
    if (this.runtime.id === undefined) {
      this.stop();
      return;
    }
    try {
      this.runtime.sendMessage(message).catch(() => {
        if (this.runtime.id === undefined) this.stop();
      });
    } catch {
      this.stop(); // "Extension context invalidated": this copy is orphaned
    }
  }

  private onMessage(message: unknown, sender: { id?: string | undefined; tab?: unknown }): void {
    // Only this extension's service worker (never a tab) sends slices.
    if (this.stopped || sender.id !== this.runtime.id || sender.tab !== undefined) return;
    const slice = readSlice(message);
    if (slice === null) return;
    if (!slice.active) {
      this.goInert();
      return;
    }
    const wasActive = this.isActive;
    this.slice = slice;
    if (!wasActive) this.startHeartbeat();
    this.render();
  }

  private startHeartbeat(): void {
    this.lastHref = this.doc.location.href;
    this.timer ??= setInterval(() => this.tick(), HEARTBEAT_MS);
  }

  private goInert(): void {
    this.slice = null;
    this.disarm();
    if (this.timer !== null) {
      clearInterval(this.timer);
      this.timer = null;
    }
    this.host?.remove();
    this.host = null;
    this.root = null;
  }

  private disarm(): void {
    this.armedRef = null;
    if (this.disarmTimer !== null) {
      clearTimeout(this.disarmTimer);
      this.disarmTimer = null;
    }
  }

  private ensureRoot(): ShadowRoot {
    if (this.root !== null && this.host !== null) {
      if (!this.host.isConnected) this.doc.documentElement.append(this.host);
      return this.root;
    }
    const host = this.doc.createElement("div");
    host.setAttribute(MARKER, "");
    style(host, {
      all: "initial",
      position: "fixed",
      inset: "0",
      "pointer-events": "none",
      "z-index": "2147483647",
    });
    this.doc.documentElement.append(host);
    this.host = host;
    this.root = host.attachShadow({ mode: "closed" });
    return this.root;
  }

  private render(): void {
    const slice = this.slice;
    if (slice === null) return;
    if (slice.frame === null && slice.block === undefined) {
      this.host?.remove();
      this.host = null;
      this.root = null;
      return;
    }
    const root = this.ensureRoot();
    root.replaceChildren();
    if (slice.frame !== null) {
      const frame = node(this.doc, "div", undefined, {
        position: "fixed",
        inset: "0",
        border: `3px solid ${slice.frame === "recording" ? RED : AMBER}`,
        "box-sizing": "border-box",
        "pointer-events": "none",
      });
      frame.setAttribute("data-frame", slice.frame);
      root.append(frame);
    }
    if (slice.block !== undefined) {
      if (this.armedRef !== null && this.armedRef !== slice.block.session_ref) this.disarm();
      root.append(this.blockCard(slice.block));
    } else {
      this.disarm();
    }
  }

  private blockCard(block: PageBlock): HTMLElement {
    const doc = this.doc;
    const overlay = node(doc, "div", undefined, {
      position: "fixed",
      inset: "0",
      background: "rgba(32, 33, 36, 0.55)",
      display: "flex",
      "align-items": "center",
      "justify-content": "center",
      "pointer-events": "auto",
    });
    overlay.setAttribute("role", "alertdialog");
    overlay.setAttribute("aria-modal", "true");
    const card = node(doc, "div", undefined, {
      background: "#ffffff",
      color: "#202124",
      font: "14px/1.45 system-ui, sans-serif",
      "border-radius": "10px",
      "border-top": `6px solid ${AMBER}`,
      padding: "20px 24px",
      "max-width": "560px",
      width: "calc(100% - 48px)",
      "box-shadow": "0 8px 28px rgba(0, 0, 0, 0.3)",
    });
    const title = node(doc, "h2", "Recording paused", { margin: "0 0 6px", font: "600 18px system-ui, sans-serif" });
    title.setAttribute("data-part", "title");
    const reason = node(doc, "p", reasonText(block.reason), { margin: "0 0 14px" });
    reason.setAttribute("data-part", "reason");
    card.append(title, reason);

    const patients = node(doc, "div", undefined, { display: "flex", gap: "16px", margin: "0 0 16px" });
    const previous = block.same_clinic
      ? (block.previous_patient ?? "The patient being recorded")
      : `Recording belongs to a patient in ${block.recording_clinic}`;
    patients.append(
      this.column("Recording", previous, "previous"),
      this.column("On this tab", block.this_patient ?? "The patient on this tab", "current"),
    );
    card.append(patients);

    const armed = this.armedRef === block.session_ref;
    const buttons = node(doc, "div", undefined, { display: "flex", gap: "8px", "flex-wrap": "wrap" });
    buttons.append(
      this.button("Resume previous", "resume_previous", block),
      this.button("Finish previous", "finish", block),
      this.button(armed ? "Confirm discard" : "Discard previous", "discard", block),
    );
    card.append(buttons);
    if (armed) {
      const confirm = node(doc, "p", "Discard this recording? This cannot be undone. Press Confirm discard to delete it.", {
        margin: "10px 0 0",
        color: RED,
      });
      confirm.setAttribute("data-part", "confirm");
      card.append(confirm);
    }
    overlay.append(card);
    return overlay;
  }

  private column(label: string, value: string, part: string): HTMLElement {
    const col = node(this.doc, "div", undefined, { flex: "1 1 0", "min-width": "0" });
    const heading = node(this.doc, "div", label, { font: "600 12px system-ui, sans-serif", color: "#5f6368" });
    const text = node(this.doc, "div", value, { font: "600 15px system-ui, sans-serif", "overflow-wrap": "anywhere" });
    text.setAttribute("data-part", part);
    col.append(heading, text);
    return col;
  }

  private button(label: string, action: BlockAction, block: PageBlock): HTMLButtonElement {
    const button = node(this.doc, "button", label, BUTTON);
    button.type = "button";
    button.setAttribute("data-action", action);
    button.addEventListener("click", (event) => this.onClick(event, action, block));
    return button;
  }

  private onClick(event: Event, action: BlockAction, block: PageBlock): void {
    if (!this.trusted(event) || this.slice?.block?.session_ref !== block.session_ref) return;
    const message: Record<string, unknown> = {
      kind: "block",
      action,
      session_ref: block.session_ref,
      state_rev: block.state_rev,
    };
    if (action === "discard") {
      if (this.armedRef !== block.session_ref) {
        this.armedRef = block.session_ref;
        this.disarmTimer = setTimeout(() => {
          this.disarm();
          this.render();
        }, DISARM_MS);
        this.render();
        return;
      }
      message["confirmed"] = true;
    }
    this.disarm();
    this.send(message);
    this.render();
  }
}

/** Start the page script in this tab (the manifest's content script). */
export function boot(): PageScript | null {
  if (typeof chrome === "undefined" || chrome.runtime?.id === undefined) return null;
  const script = new PageScript(document, chrome.runtime);
  script.start();
  return script;
}

export const pageScript = boot();
