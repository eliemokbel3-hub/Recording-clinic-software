// Cliniko workflow safeguards plan Tasks 6.4 / 6.5: D1's five layouts plus the
// banner, chosen from the worker's view of the app's `state`.
import { describe, expect, test } from "vitest";

import type { PanelView } from "./hub";
import type { Formatters } from "./panel-view";
import {
  CHECKING,
  CLINIC_NOT_SET_UP,
  CONNECTING,
  HOTKEY_UNAVAILABLE,
  NOT_RUNNING,
  OFFLINE_LINE,
  OPEN_A_NOTE,
  PROFILE_HINT,
  QUEUED_LINE,
  RESTORING,
  SPOKEN_PAUSE_ON,
  SPOKEN_PAUSE_UNAVAILABLE,
  VERIFIED_LINE,
  blockReasonText,
  hotkeyLine,
  noteRefusalText,
  panelModel,
  timer,
} from "./panel-view";
import type { LiveState, ReportState, StatePayload } from "./protocol";

const HOST = "example-clinic.au1.cliniko.com";
const REF = "AbCdEfGhIjKlMnOpQrStUv_-";
const OLD_REF = "ZyXwVuTsRqPoNmLkJiHgFe01";
const FMT: Formatters = { appointment: (iso) => `appt ${iso}`, clock: (iso) => `clock ${iso}` };

const REPORT: ReportState = {
  tab_id: 5,
  clinic_host: HOST,
  patient_id: "1001",
  note_id: "2002",
  verification: "verified",
  clinic_label: "Example Clinic",
  patient_name: "Alex Example",
  appointment_starts_at: "2026-09-27T01:30:00Z",
};

const LIVE: LiveState = {
  session_ref: REF,
  phase: "recording",
  linked: true,
  recorded_seconds: 95,
  consent_confirmed_at: "2026-09-27T01:31:02Z",
  clinic_host: HOST,
  patient_id: "1001",
  note_id: "2002",
  verification: "verified",
  clinic_label: "Example Clinic",
  patient_name: "Alex Example",
};

function state(extra: Partial<StatePayload> = {}): StatePayload {
  return {
    state_rev: 21,
    app_running: true,
    allow_list: [HOST],
    hotkey: { available: false },
    spoken_pause: false,
    warnings: [],
    ...extra,
  };
}

function view(s: StatePayload | null, focus: PanelView["focus"] = { kind: "cliniko", restoring: false, tab_id: 5 }): PanelView {
  return { connection: "connected", state: s, focus };
}

describe("Message", () => {
  test("the app not running names the other-profile possibility", () => {
    for (const v of [
      { connection: "disconnected" as const, state: null, focus: { kind: "none" as const, restoring: false } },
      { connection: "error" as const, state: null, focus: { kind: "none" as const, restoring: false } },
      view({ ...state(), app_running: false, allow_list: [] }),
    ]) {
      expect(panelModel(v, FMT).layout).toEqual({ kind: "message", text: NOT_RUNNING, hint: PROFILE_HINT });
    }
  });

  test("connecting, before the app's first state", () => {
    expect(panelModel({ ...view(null), connection: "connecting" }, FMT).layout).toEqual({ kind: "message", text: CONNECTING });
    expect(panelModel(view(null), FMT).layout).toEqual({ kind: "message", text: CONNECTING });
  });

  test.each([
    ["no report", state(), { kind: "cliniko", restoring: false, tab_id: 5 }, OPEN_A_NOTE],
    ["the report is another tab's", state({ report: { ...REPORT, tab_id: 6 } }), { kind: "cliniko", restoring: false, tab_id: 5 }, OPEN_A_NOTE],
    ["a page that is not Cliniko in front", state({ report: REPORT }), { kind: "not_cliniko", restoring: false }, OPEN_A_NOTE],
    ["a clinic that is not set up", state({ report: REPORT }), { kind: "clinic_not_set_up", restoring: false, tab_id: 7 }, CLINIC_NOT_SET_UP],
    ["a page script being restored", state({ report: REPORT }), { kind: "cliniko", restoring: true, tab_id: 5 }, RESTORING],
  ] as const)("%s", (_name, s, focus, text) => {
    expect(panelModel(view(s, focus), FMT).layout).toEqual({ kind: "message", text });
  });

  test("a note review holding the lease names the patient when the app still has them", () => {
    const queued = { ...LIVE, phase: "queued" as const };
    expect(panelModel(view(state({ notice: "review_open", live: queued, report: REPORT })), FMT).layout).toEqual({
      kind: "message",
      text: "Save or cancel Alex Example's note review to start",
    });
    expect(panelModel(view(state({ notice: "review_open" })), FMT).layout).toEqual({
      kind: "message",
      text: "Save or cancel the open note review in Clinic Scribe to start",
    });
  });

  test("a refused note says why, in plain words", () => {
    const refused: ReportState = { tab_id: 5, clinic_host: HOST, patient_id: "1001", note_id: "2002", verification: "refused", refusal: "note_final" };
    expect(panelModel(view(state({ report: refused })), FMT).layout).toEqual({
      kind: "message",
      text: "Cliniko did not verify this note: the note is already final in Cliniko.",
    });
    expect(panelModel(view(state({ report: { ...refused, refusal: "something_new" } })), FMT).layout).toEqual({
      kind: "message",
      text: "Cliniko did not verify this note: no reason given.",
    });
  });
});

describe("Checking and Ready", () => {
  test("Checking", () => {
    const checking: ReportState = { tab_id: 5, clinic_host: HOST, patient_id: "1001", note_id: "2002", verification: "checking", clinic_label: "Example Clinic" };
    expect(CHECKING).toBe("Checking with Cliniko…");
    expect(panelModel(view(state({ report: checking })), FMT).layout).toEqual({ kind: "checking", clinic: "Example Clinic" });
  });

  test("Ready for a verified note carries its target and the rendered rev", () => {
    expect(panelModel(view(state({ report: REPORT })), FMT).layout).toEqual({
      kind: "ready",
      patient: "Alex Example",
      appointment: "appt 2026-09-27T01:30:00Z",
      clinic: "Example Clinic",
      verification: VERIFIED_LINE,
      offline: false,
      target: { tab_id: 5, clinic_host: HOST, patient_id: "1001", note_id: "2002" },
      state_rev: 21,
      key: `5|${HOST}|1001|2002|verified`,
    });
  });

  test("Ready with no appointment, and Ready while Cliniko is unreachable", () => {
    const noBooking: ReportState = { ...REPORT };
    delete noBooking.appointment_starts_at;
    expect(panelModel(view(state({ report: noBooking })), FMT).layout).toMatchObject({ appointment: "No linked appointment" });
    const offline: ReportState = { tab_id: 5, clinic_host: HOST, patient_id: "1001", note_id: "2002", verification: "unverified_offline" };
    expect(panelModel(view(state({ report: offline })), FMT).layout).toMatchObject({
      kind: "ready",
      patient: "Patient not checked with Cliniko",
      appointment: "Appointment not checked",
      clinic: HOST,
      verification: OFFLINE_LINE,
      offline: true,
    });
  });
});

describe("Live", () => {
  test("recording shows the timer, the patient and the consent time", () => {
    expect(panelModel(view(state({ live: LIVE })), FMT).layout).toEqual({
      kind: "live",
      phase: "recording",
      title: "Recording",
      patient: "Alex Example",
      clinic: "Example Clinic",
      timer: "1:35",
      consent: "Consent confirmed clock 2026-09-27T01:31:02Z",
      hands_free: [HOTKEY_UNAVAILABLE, SPOKEN_PAUSE_UNAVAILABLE],
      session_ref: REF,
      state_rev: 21,
    });
  });

  test("paused keeps the timer; finishing names the patient and shows none", () => {
    expect(panelModel(view(state({ live: { ...LIVE, phase: "paused" } })), FMT).layout).toMatchObject({ title: "Paused", timer: "1:35" });
    const finishing = panelModel(view(state({ live: { ...LIVE, phase: "finishing" } })), FMT).layout;
    expect(finishing).toMatchObject({ title: "Finishing Alex Example…" });
    expect(finishing).not.toHaveProperty("timer");
    expect(finishing).not.toHaveProperty("hands_free");
  });

  test.each(["recording", "paused"] as const)("%s shows the app's hotkey chord and the spoken pause (Phase 7)", (phase) => {
    const s = state({ live: { ...LIVE, phase }, hotkey: { available: true, chord: "Ctrl+Shift+F9" }, spoken_pause: true });
    expect(panelModel(view(s), FMT).layout).toMatchObject({
      hands_free: ["Ctrl+Shift+F9 pauses and resumes.", SPOKEN_PAUSE_ON],
    });
    expect(hotkeyLine("Ctrl+Shift+F9")).toBe("Ctrl+Shift+F9 pauses and resumes.");
    const off = state({ live: { ...LIVE, phase } });
    expect(panelModel(view(off), FMT).layout).toMatchObject({ hands_free: [HOTKEY_UNAVAILABLE, SPOKEN_PAUSE_UNAVAILABLE] });
  });

  test("an unlinked recording says so", () => {
    const unlinked: LiveState = { session_ref: REF, phase: "recording", linked: false, recorded_seconds: 5, consent_confirmed_at: LIVE.consent_confirmed_at };
    expect(panelModel(view(state({ live: unlinked })), FMT).layout).toMatchObject({ patient: "Not linked to a Cliniko note" });
  });

  test("a queued (or reopened) session shows no timer — only that it is waiting", () => {
    const model = panelModel(view(state({ live: { ...LIVE, phase: "queued", recorded_seconds: 0 }, report: REPORT })), FMT);
    expect(model.layout.kind).toBe("ready");
    expect(model.layout).not.toHaveProperty("timer");
    expect(model.queued).toBe(QUEUED_LINE);
    // With no note in front, still no timer: a Message and the waiting line.
    const bare = panelModel(view(state({ live: { ...LIVE, phase: "queued", recorded_seconds: 0 } })), FMT);
    expect(bare.layout).toEqual({ kind: "message", text: OPEN_A_NOTE });
    expect(bare.queued).toBe(QUEUED_LINE);
  });
});

describe("Blocked", () => {
  test("names both patients and carries the block's own ref", () => {
    const s = state({
      live: { ...LIVE, phase: "paused" },
      block: { reason: "note_changed", session_ref: REF, clinic_host: HOST, clinic_label: "Example Clinic", patient_name: "Alex Example" },
      report: { ...REPORT, patient_id: "1003", note_id: "2004", patient_name: "Sam Example" },
      banner: { session_ref: OLD_REF, clinic_host: HOST, note_id: "2004", count: 1 },
    });
    const model = panelModel(view(s), FMT);
    expect(model.layout).toEqual({
      kind: "blocked",
      reason: "The recording's tab opened a different treatment note.",
      previous: "Alex Example",
      previous_clinic: "Example Clinic",
      current: "Sam Example",
      session_ref: REF,
      state_rev: 21,
    });
    expect(model.banner).toBeUndefined(); // the banner shows over Message or Ready only
  });

  test("an unverified screen patient and an unknown reason stay generic", () => {
    const s = state({
      block: { reason: "patient_changed", session_ref: REF, clinic_host: HOST, clinic_label: "Example Clinic" },
      report: { tab_id: 5, clinic_host: HOST, patient_id: "1003", note_id: "2004", verification: "checking" },
    });
    expect(panelModel(view(s), FMT).layout).toMatchObject({
      reason: "The recording was paused.",
      previous: "The patient being recorded",
      current: "The patient on screen",
    });
  });
});

describe("the banner, refusals and warnings", () => {
  test.each([
    [{ count: 1 }, "Unreviewed recording for this note — Open for review"],
    [{ count: 1, patient_name: "Alex Example" }, "Unreviewed note for Alex Example — Open for review"],
    [{ count: 3 }, "3 unreviewed recordings for this note — Open for review"],
  ])("%j", (extra, text) => {
    const banner = { session_ref: OLD_REF, clinic_host: HOST, note_id: "2002", ...extra };
    const model = panelModel(view(state({ banner, report: REPORT })), FMT);
    expect(model.banner).toEqual({ text, session_ref: OLD_REF, state_rev: 21 });
    expect(panelModel(view(state({ banner })), FMT).banner?.text).toBe(text); // over Message too
  });

  test("no banner over Live", () => {
    const banner = { session_ref: OLD_REF, clinic_host: HOST, note_id: "2002", count: 1 };
    expect(panelModel(view(state({ banner, live: LIVE })), FMT).banner).toBeUndefined();
  });

  test("no banner while a page that is not Cliniko is in front (round 36 LOW-029)", () => {
    const banner = { session_ref: OLD_REF, clinic_host: HOST, note_id: "2002", count: 1 };
    for (const focus of [
      { kind: "not_cliniko" as const, restoring: false },
      { kind: "none" as const, restoring: false },
    ]) {
      expect(panelModel(view(state({ banner, report: REPORT }), focus), FMT).banner).toBeUndefined();
    }
  });

  test("the refusal line is the app's message; unknown warning codes show nothing", () => {
    const model = panelModel(
      view(
        state({
          warnings: ["new_consultation", "future_code"],
          last_refusal: { action: "start", reason: "stale_state", message: "The side panel was out of date." },
        }),
      ),
      FMT,
    );
    expect(model.refusal).toBe("The side panel was out of date.");
    expect(model.warnings).toEqual(["This sounds like a new consultation — finish this recording before the next patient."]);
  });

  test("the machine's own pause reasons have their text (D5 as amended 2026-09-28)", () => {
    expect(blockReasonText("suspend")).toBe("The computer went to sleep.");
    expect(blockReasonText("locked")).toBe("The computer was locked.");
  });

  test.each(["constructor", "toString", "__proto__"])("an inherited name %s is an unknown code everywhere (round 38 PR-LOW-211)", (code) => {
    expect(noteRefusalText(code)).toBe("no reason given");
    expect(blockReasonText(code)).toBe("The recording was paused.");
    expect(panelModel(view(state({ warnings: [code] })), FMT).warnings).toEqual([]);
  });
});

test.each([
  [0, "0:00"],
  [95, "1:35"],
  [3725, "1:02:05"],
])("timer(%i) is %s", (seconds, text) => {
  expect(timer(seconds)).toBe(text);
});
