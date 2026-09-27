// What Chrome tells the app about Cliniko tabs, and what each tab is told
// back (Cliniko workflow safeguards plan D2, D5, D13; Task 6.2).
//
// REPORTS. `ContextReporter` is the ONE producer of `context` reports. It is
// inert until the app's first `state` gives it the allow-list. From then on a
// tab is reported only while it shows a page on an allow-listed host (a note,
// the login page or another Cliniko page); a tab it has reported that then
// leaves the allow-list — its URL becomes unreadable once it leaves Cliniko,
// because the extension holds no `tabs` permission — is reported ONCE as
// `not_cliniko` with no host and no URL and is no longer tracked; a tracked
// tab that closes is reported `closed`. A tab that was never on an
// allow-listed host is never reported at all. `focused` is "the active tab of
// the last-focused Chrome window": Chrome losing focus to another program
// (`WINDOW_ID_NONE`) changes nothing. Each report is sent only when what it
// says changed, under a `seq` that only rises; the app decides everything
// from the reports (Constraint 3).
//
// SLICES. `sliceFor` is the only place a tab's view of `state` is made: the
// frame colour, and the block scoped to the tab's own host (D2). A patient's
// name reaches a tab only when that patient belongs to the tab's own clinic;
// a block for another clinic's recording names that clinic by label only and
// carries none of that patient's name or ids (D1).

import type { ContextPayload, StatePayload } from "./protocol";
import { HOST_PATTERN, ID_PATTERN } from "./protocol";

export type PageView =
  | { page: "note"; host: string; patient_id: string; note_id: string }
  | { page: "login" | "other_cliniko"; host: string }
  | { page: "not_cliniko" };

// The note page (plan External findings): /patients/<id>/treatment_notes/<id>/edit.
const NOTE_PATH = /^\/patients\/([^/]+)\/treatment_notes\/([^/]+)\/edit\/?$/;
// Cliniko's sign-in page. UNVERIFIED on a live account (the morning smoke
// checks it): any other path on the host reads as `other_cliniko`, and the
// bound tab leaving its note pauses either way.
const LOGIN_PATH = /^\/users\/sign_in\/?$/;

/** The URL's host when it is a Cliniko web-app host (https, no port or login), else null. */
export function clinikoHost(url: string | undefined): string | null {
  if (url === undefined) return null;
  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    return null;
  }
  if (parsed.protocol !== "https:" || parsed.port !== "" || parsed.username !== "" || parsed.password !== "") {
    return null;
  }
  const host = parsed.hostname;
  return HOST_PATTERN.test(host) ? host : null;
}

/** What a tab shows, judged against the allow-list. Never reads the page. */
export function classifyUrl(url: string | undefined, allowList: readonly string[]): PageView {
  const host = clinikoHost(url);
  if (host === null || url === undefined || !allowList.includes(host)) return { page: "not_cliniko" };
  const path = new URL(url).pathname;
  const note = NOTE_PATH.exec(path);
  if (note) {
    const [, patientId, noteId] = note;
    if (patientId !== undefined && noteId !== undefined && ID_PATTERN.test(patientId) && ID_PATTERN.test(noteId)) {
      return { page: "note", host, patient_id: patientId, note_id: noteId };
    }
    return { page: "other_cliniko", host };
  }
  if (LOGIN_PATH.test(path)) return { page: "login", host };
  return { page: "other_cliniko", host };
}

/**
 * The note page's URL, built ONLY from an allow-listed host and two ids of
 * the protocol's id shape (D5: "Resume previous" carries ids only). Null if
 * any part fails.
 */
export function noteUrl(
  host: string | undefined,
  patientId: string | undefined,
  noteId: string | undefined,
  allowList: readonly string[],
): string | null {
  if (host === undefined || patientId === undefined || noteId === undefined) return null;
  if (!HOST_PATTERN.test(host) || !allowList.includes(host)) return null;
  if (!ID_PATTERN.test(patientId) || !ID_PATTERN.test(noteId)) return null;
  return `https://${host}/patients/${patientId}/treatment_notes/${noteId}/edit`;
}

/** The note a page view names, as one comparable key (null when not a note). */
export function noteKey(view: PageView): string | null {
  return view.page === "note" ? `${view.host}|${view.patient_id}|${view.note_id}` : null;
}

export interface TabSnapshot {
  id: number;
  windowId: number;
  active: boolean;
  url?: string | undefined;
}

interface TabRecord {
  windowId: number;
  active: boolean;
  url: string | undefined;
}

const MAX_SEQ = Number.MAX_SAFE_INTEGER;

export class ContextReporter {
  private allowList: readonly string[] | null = null;
  private readonly tabs = new Map<number, TabRecord>();
  // Tracked tabs: tab id -> the report last SENT for it.
  private readonly reported = new Map<number, string>();
  private focusedWindow: number | null = null;
  private seq = 0;

  constructor(private readonly send: (payload: ContextPayload) => boolean) {}

  get allowed(): readonly string[] {
    return this.allowList ?? [];
  }

  /** The active tab of the last-focused window, if known. */
  focusedTab(): number | null {
    for (const [id, tab] of this.tabs) {
      if (tab.active && tab.windowId === this.focusedWindow) return id;
    }
    return null;
  }

  url(tabId: number): string | undefined {
    return this.tabs.get(tabId)?.url;
  }

  snapshot(tabId: number): TabSnapshot | null {
    const tab = this.tabs.get(tabId);
    return tab ? { id: tabId, windowId: tab.windowId, active: tab.active, url: tab.url } : null;
  }

  view(tabId: number): PageView {
    const tab = this.tabs.get(tabId);
    return classifyUrl(tab?.url, this.allowed);
  }

  /** Every known tab id whose URL is on a Cliniko host (allow-listed or not). */
  clinikoTabs(): number[] {
    return [...this.tabs].filter(([, tab]) => clinikoHost(tab.url) !== null).map(([id]) => id);
  }

  /** Tracked tabs whose page names this note. */
  tabsShowing(key: string): number[] {
    return [...this.tabs.keys()].filter((id) => this.reported.has(id) && noteKey(this.view(id)) === key);
  }

  /** Go inert (no app, or a new connection pending): nothing is reported. */
  deactivate(): void {
    this.allowList = null;
    this.reported.clear();
  }

  /** A new allow-list from `state`: every known tab is judged again. */
  setAllowList(list: readonly string[]): void {
    const same =
      this.allowList !== null && this.allowList.length === list.length && list.every((h) => this.allowList?.includes(h));
    this.allowList = [...list];
    if (!same) this.evaluateAll();
  }

  /**
   * Replace the tab table from a fresh query, take the allow-list, forget
   * what was sent (a new connection's app knows nothing yet) and report
   * every allow-listed tab once.
   */
  resync(tabs: readonly TabSnapshot[], focusedWindow: number | null, allowList: readonly string[]): void {
    this.tabs.clear();
    this.reported.clear();
    for (const tab of tabs) this.tabs.set(tab.id, { windowId: tab.windowId, active: tab.active, url: tab.url });
    if (focusedWindow !== null) this.focusedWindow = focusedWindow;
    this.allowList = [...allowList];
    this.evaluateAll();
  }

  tabUpdated(tab: TabSnapshot): void {
    const unfocused = tab.active ? this.unfocusSiblings(tab.id, tab.windowId) : [];
    this.tabs.set(tab.id, { windowId: tab.windowId, active: tab.active, url: tab.url });
    for (const id of unfocused) this.evaluate(id);
    this.evaluate(tab.id);
  }

  /** `tabs.onActivated`. False when the tab is unknown (the caller fetches it). */
  tabActivated(tabId: number, windowId: number): boolean {
    const tab = this.tabs.get(tabId);
    if (!tab) return false;
    const unfocused = this.unfocusSiblings(tabId, windowId);
    tab.active = true;
    tab.windowId = windowId;
    for (const id of unfocused) this.evaluate(id);
    this.evaluate(tabId);
    return true;
  }

  tabRemoved(tabId: number): void {
    const tab = this.tabs.get(tabId);
    this.tabs.delete(tabId);
    if (!this.reported.has(tabId)) return;
    this.reported.delete(tabId);
    this.emit({ tab_id: tabId, window_id: tab?.windowId ?? 0, focused: false, page: "closed" });
  }

  /** `windows.onFocusChanged`; the caller drops `WINDOW_ID_NONE`. */
  windowFocused(windowId: number): void {
    if (windowId === this.focusedWindow) return;
    const before = this.focusedTab();
    this.focusedWindow = windowId;
    const after = this.focusedTab();
    if (before !== null) this.evaluate(before);
    if (after !== null && after !== before) this.evaluate(after);
  }

  private unfocusSiblings(tabId: number, windowId: number): number[] {
    const changed: number[] = [];
    for (const [id, tab] of this.tabs) {
      if (id !== tabId && tab.windowId === windowId && tab.active) {
        tab.active = false;
        changed.push(id);
      }
    }
    return changed;
  }

  private evaluateAll(): void {
    for (const id of [...this.tabs.keys()]) this.evaluate(id);
  }

  private evaluate(tabId: number): void {
    if (this.allowList === null) return;
    const tab = this.tabs.get(tabId);
    if (!tab) return;
    const view = classifyUrl(tab.url, this.allowList);
    const focused = tab.active && tab.windowId === this.focusedWindow;
    if (view.page === "not_cliniko") {
      if (!this.reported.has(tabId)) return; // never tracked: never reported
      this.reported.delete(tabId);
      this.emit({ tab_id: tabId, window_id: tab.windowId, focused, page: "not_cliniko" });
      return;
    }
    const report: Omit<ContextPayload, "seq"> = { tab_id: tabId, window_id: tab.windowId, focused, ...view };
    const key = JSON.stringify(report);
    if (this.reported.get(tabId) === key) return;
    if (this.emit(report)) this.reported.set(tabId, key);
  }

  private emit(report: Omit<ContextPayload, "seq">): boolean {
    if (this.seq >= MAX_SEQ) return false;
    this.seq += 1;
    return this.send({ seq: this.seq, ...report });
  }
}

// --- the per-tab slice of `state` (D1, D2, D13) --------------------------------

export type Frame = "recording" | "paused" | null;

export interface PageBlock {
  session_ref: string;
  state_rev: number;
  reason: string;
  /** The recording belongs to this tab's own clinic. */
  same_clinic: boolean;
  /** The recording's clinic, by label. */
  recording_clinic: string;
  /** The recording's patient — only when it is this tab's own clinic. */
  previous_patient?: string;
  /** The patient Cliniko verified on THIS tab's note, when known. */
  this_patient?: string;
}

export interface PageSlice {
  /** The tab's host is allow-listed: the page script is live. */
  active: boolean;
  frame: Frame;
  block?: PageBlock;
}

export const INERT_SLICE: PageSlice = { active: false, frame: null };

/**
 * One tab's slice. `state` is the app's latest snapshot, or null when the
 * link is down (then `wasLive` shows the frame the app's pause rule leaves:
 * paused). `allowList` is the last one known.
 */
export function sliceFor(
  state: StatePayload | null,
  tabId: number,
  host: string | null,
  allowList: readonly string[],
  wasLive: boolean,
): PageSlice {
  if (host === null || !allowList.includes(host)) return INERT_SLICE;
  if (state === null || !state.app_running) {
    return { active: state === null, frame: state === null && wasLive ? "paused" : null };
  }
  const phase = state.live?.phase;
  let frame: Frame = null;
  if (phase === "recording") frame = "recording";
  if (phase === "paused" || state.block !== undefined) frame = "paused";
  const slice: PageSlice = { active: true, frame };
  const block = state.block;
  if (block !== undefined) {
    const same = block.clinic_host === host;
    const scoped: PageBlock = {
      session_ref: block.session_ref,
      state_rev: state.state_rev,
      reason: block.reason,
      same_clinic: same,
      recording_clinic: block.clinic_label,
    };
    if (same && block.patient_name !== undefined) scoped.previous_patient = block.patient_name;
    const report = state.report;
    if (
      report !== undefined &&
      report.tab_id === tabId &&
      report.clinic_host === host &&
      report.verification === "verified" &&
      report.patient_name !== undefined
    ) {
      scoped.this_patient = report.patient_name;
    }
    slice.block = scoped;
  }
  return slice;
}
