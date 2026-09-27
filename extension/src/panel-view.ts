// The side panel's layout, as data (Cliniko workflow safeguards plan Task 6.4;
// D1's five layouts plus the banner). Pure: `panelModel` turns the worker's
// `PanelView` into what to show, and `panel.ts` draws it with `textContent`
// only. Every decision stays the app's (Constraint 3): this only chooses a
// layout from the app's `state`, and every button becomes a command the app
// may refuse (the refusal comes back as `state.last_refusal`).
//
// Rules the model holds:
// - Ready is shown only for the note in FRONT of the practitioner: the app's
//   bound report must be the focused tab's. Start carries that report's
//   target and the `state_rev` it was drawn from (D2).
// - Session commands carry the `session_ref` of the state they were drawn
//   from (D2): the live session's, the block's, or the banner's.
// - A queued (finished, awaiting review) or reopened session shows NO
//   timer — its recorded time is not live — only a line that it is waiting.
// - "Another Chrome profile is connected" has no signal in the protocol (the
//   host reports `app_running: false` whenever it cannot reach the app), so
//   the not-running message names that possibility as a hint.

import type { PanelView } from "./hub";
import type { CommandTarget, StatePayload } from "./protocol";

export const NOT_RUNNING = "Clinic Scribe is not running — open it to record";
export const PROFILE_HINT = "If it is open, another Chrome profile may be connected to it.";
export const CONNECTING = "Connecting to Clinic Scribe…";
export const CLINIC_NOT_SET_UP = "This clinic is not set up — add its key in Clinic Scribe's Clinics tab";
export const OPEN_A_NOTE = "Open a patient's treatment note to record";
export const RESTORING = "Restoring the safeguards on this tab…";
export const CHECKING = "Checking with Cliniko…";
export const QUEUED_LINE = "The last recording is waiting for review in Clinic Scribe.";
export const VERIFIED_LINE = "Note verified with Cliniko. It is checked again before anything is written back.";
export const OFFLINE_LINE =
  "Cliniko could not be reached — you can record, but this note cannot be written back until Cliniko verifies it.";
// PLAN.md Flow 2 step 4, verbatim (the desktop's `RECORDING_CONSENT_TEXT`).
export const CONSENT_TEXT = "I confirm the patient has consented to AI-assisted recording and documentation";
export const DISCARD_CONFIRM = "Discard this recording? This cannot be undone. Press Confirm discard to delete it.";

// D4's named refusals (`encounter.NoteRefusal`), in the desktop's words.
const NOTE_REFUSALS: Readonly<Record<string, string>> = {
  clinic_not_set_up: "this clinic is not set up - add its key in Clinic Scribe's Clinics tab",
  clinic_mismatch: "the note is not in this clinic's Cliniko account",
  patient_mismatch: "the note belongs to a different patient than the page",
  note_final: "the note is already final in Cliniko",
  note_archived: "the note has been archived or deleted in Cliniko",
  wrong_practitioner: "the note belongs to another practitioner",
  note_not_found: "Cliniko has no such note for this key",
  key_rejected: "Cliniko rejected the clinic's API key - replace it in Clinic Scribe's Clinics tab",
  key_unavailable: "the clinic's API key could not be read - replace it in Clinic Scribe's Clinics tab",
  certificate_rejected: "Cliniko's certificate was not trusted",
  answer_unreadable: "Cliniko's answer could not be read",
};

// Why the block is up (`context_rules.PauseReason`).
const BLOCK_REASONS: Readonly<Record<string, string>> = {
  note_changed: "The recording's tab opened a different treatment note.",
  left_note: "The recording's tab left its treatment note.",
  tab_closed: "The recording's tab was closed.",
  other_note: "Another treatment note is open.",
  login: "Cliniko's login page is open.",
  pipe_lost: "Chrome disconnected from Clinic Scribe.",
  new_client: "Chrome reconnected to Clinic Scribe.",
  suspend: "The computer went to sleep.",
};

// `state.warnings` codes (Phase 7 adds them); an unknown code shows nothing.
const WARNINGS: Readonly<Record<string, string>> = {
  new_consultation: "This sounds like a new consultation — finish this recording before the next patient.",
};

export interface ReadyModel {
  kind: "ready";
  patient: string;
  appointment: string;
  clinic: string;
  verification: string;
  offline: boolean;
  target: CommandTarget;
  state_rev: number;
  /** The context the consent tick belongs to; any change clears the tick. */
  key: string;
}

export interface LiveModel {
  kind: "live";
  phase: "recording" | "paused" | "finishing";
  title: string;
  patient: string;
  clinic?: string;
  timer?: string;
  consent: string;
  session_ref: string;
  state_rev: number;
}

export interface BlockedModel {
  kind: "blocked";
  reason: string;
  previous: string;
  previous_clinic: string;
  current: string;
  session_ref: string;
  state_rev: number;
}

export type Layout =
  | { kind: "message"; text: string; hint?: string }
  | { kind: "checking"; clinic?: string }
  | ReadyModel
  | LiveModel
  | BlockedModel;

export interface PanelModel {
  layout: Layout;
  banner?: { text: string; session_ref: string; state_rev: number };
  queued?: string;
  refusal?: string;
  warnings: string[];
}

export interface Formatters {
  /** An appointment's start, local time with the zone named. */
  appointment(iso: string): string;
  /** A time of day, local, with the zone named. */
  clock(iso: string): string;
}

export const LOCAL_FORMAT: Formatters = {
  appointment: (iso) =>
    new Date(iso).toLocaleString(undefined, {
      weekday: "short",
      day: "numeric",
      month: "short",
      hour: "numeric",
      minute: "2-digit",
      timeZoneName: "short",
    }),
  clock: (iso) => new Date(iso).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit", timeZoneName: "short" }),
};

/** Seconds as m:ss, or h:mm:ss from an hour. */
export function timer(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const ss = String(s % 60).padStart(2, "0");
  return h > 0 ? `${String(h)}:${String(m).padStart(2, "0")}:${ss}` : `${String(m)}:${ss}`;
}

/** A code's own entry only: `constructor` and the like are unknown codes (round 38 PR-LOW-211). */
function lookUp(dictionary: Readonly<Record<string, string>>, code: string | undefined): string | undefined {
  return code !== undefined && Object.hasOwn(dictionary, code) ? dictionary[code] : undefined;
}

export function noteRefusalText(code: string | undefined): string {
  return lookUp(NOTE_REFUSALS, code) ?? "no reason given";
}

export function blockReasonText(code: string): string {
  return lookUp(BLOCK_REASONS, code) ?? "The recording was paused.";
}

function message(text: string, hint?: string): Layout {
  return hint === undefined ? { kind: "message", text } : { kind: "message", text, hint };
}

function bannerFor(state: StatePayload): PanelModel["banner"] {
  const banner = state.banner;
  if (banner === undefined) return undefined;
  let text: string;
  if (banner.count > 1) {
    text = `${String(banner.count)} unreviewed recordings for ${banner.patient_name ?? "this note"} — Open for review`;
  } else {
    text =
      banner.patient_name !== undefined
        ? `Unreviewed note for ${banner.patient_name} — Open for review`
        : "Unreviewed recording for this note — Open for review";
  }
  return { text, session_ref: banner.session_ref, state_rev: state.state_rev };
}

function contentLayout(view: PanelView, state: StatePayload, fmt: Formatters): Layout {
  const live = state.live;
  const block = state.block;
  if (block !== undefined) {
    const report = state.report;
    const current =
      report?.verification === "verified" && report.patient_name !== undefined
        ? report.patient_name
        : "The patient on screen";
    return {
      kind: "blocked",
      reason: blockReasonText(block.reason),
      previous: block.patient_name ?? "The patient being recorded",
      previous_clinic: block.clinic_label,
      current,
      session_ref: block.session_ref,
      state_rev: state.state_rev,
    };
  }
  if (live !== undefined && live.phase !== "queued") {
    const patient = live.linked
      ? (live.patient_name ?? "Patient not checked with Cliniko")
      : "Not linked to a Cliniko note";
    const model: LiveModel = {
      kind: "live",
      phase: live.phase,
      title: live.phase === "recording" ? "Recording" : live.phase === "paused" ? "Paused" : `Finishing ${live.patient_name ?? "the recording"}…`,
      patient,
      consent: `Consent confirmed ${fmt.clock(live.consent_confirmed_at)}`,
      session_ref: live.session_ref,
      state_rev: state.state_rev,
    };
    if (live.clinic_label !== undefined) model.clinic = live.clinic_label;
    if (live.phase !== "finishing") model.timer = timer(live.recorded_seconds);
    return model;
  }
  const focus = view.focus;
  if (focus.restoring && (focus.kind === "cliniko" || focus.kind === "clinic_not_set_up")) return message(RESTORING);
  if (state.notice === "review_open") {
    const who = live?.patient_name;
    return message(
      who !== undefined
        ? `Save or cancel ${who}'s note review to start`
        : "Save or cancel the open note review in Clinic Scribe to start",
    );
  }
  if (focus.kind === "clinic_not_set_up") return message(CLINIC_NOT_SET_UP);
  const report = state.report;
  if (report === undefined || focus.kind !== "cliniko" || report.tab_id !== focus.tab_id) return message(OPEN_A_NOTE);
  const clinic = report.clinic_label ?? report.clinic_host;
  if (report.verification === "checking") return { kind: "checking", clinic };
  if (report.verification === "refused") return message(`Cliniko did not verify this note: ${noteRefusalText(report.refusal)}.`);
  const verified = report.verification === "verified";
  const target: CommandTarget = {
    tab_id: report.tab_id,
    clinic_host: report.clinic_host,
    patient_id: report.patient_id,
    note_id: report.note_id,
  };
  return {
    kind: "ready",
    patient: verified ? (report.patient_name ?? "Unnamed patient") : "Patient not checked with Cliniko",
    appointment:
      report.appointment_starts_at !== undefined
        ? fmt.appointment(report.appointment_starts_at)
        : verified
          ? "No linked appointment"
          : "Appointment not checked",
    clinic,
    verification: verified ? VERIFIED_LINE : OFFLINE_LINE,
    offline: !verified,
    target,
    state_rev: state.state_rev,
    key: `${String(report.tab_id)}|${report.clinic_host}|${report.patient_id}|${report.note_id}|${report.verification}`,
  };
}

export function panelModel(view: PanelView, fmt: Formatters = LOCAL_FORMAT): PanelModel {
  const state = view.state;
  if (view.connection !== "connected" || state === null) {
    const connecting = view.connection === "connecting" || view.connection === "connected";
    return { layout: connecting ? message(CONNECTING) : message(NOT_RUNNING, PROFILE_HINT), warnings: [] };
  }
  if (!state.app_running) return { layout: message(NOT_RUNNING, PROFILE_HINT), warnings: [] };
  const layout = contentLayout(view, state, fmt);
  const model: PanelModel = {
    layout,
    warnings: state.warnings.flatMap((code) => {
      const text = lookUp(WARNINGS, code);
      return text !== undefined ? [text] : [];
    }),
  };
  const banner = bannerFor(state);
  // The banner names the note on the app's bound tab; it is shown only while a
  // Cliniko tab is in front, never over another site (round 36 LOW-029).
  if (banner !== undefined && view.focus.kind === "cliniko" && (layout.kind === "message" || layout.kind === "ready")) {
    model.banner = banner;
  }
  if (state.live?.phase === "queued" && layout.kind !== "blocked") model.queued = QUEUED_LINE;
  if (state.last_refusal !== undefined) model.refusal = state.last_refusal.message;
  return model;
}
