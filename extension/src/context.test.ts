// Cliniko workflow safeguards plan Tasks 6.2 / 6.5: the URL parser, the one
// `context` reporter and the per-tab slice of `state`.
import { describe, expect, test } from "vitest";

import type { PageSlice } from "./context";
import { ContextReporter, classifyUrl, clinikoHost, noteUrl, sliceFor } from "./context";
import type { ContextPayload, StatePayload } from "./protocol";
import { PROTOCOL_VERSION, parseEnvelope } from "./protocol";

const HOST = "example-clinic.au1.cliniko.com";
const OTHER = "other-clinic.au2.cliniko.com";
const UNLISTED = "unlisted-clinic.au3.cliniko.com";
const ALLOW = [HOST, OTHER];
const NOTE = `https://${HOST}/patients/1001/treatment_notes/2002/edit?page=1`;
const NOTE_B = `https://${HOST}/patients/1003/treatment_notes/2004/edit`;
const REF = "AbCdEfGhIjKlMnOpQrStUv_-";

describe("the URL parser", () => {
  test.each([
    [NOTE, { page: "note", host: HOST, patient_id: "1001", note_id: "2002" }],
    [`https://${HOST}/patients/1001/treatment_notes/2002/edit/`, { page: "note", host: HOST, patient_id: "1001", note_id: "2002" }],
    [`https://${HOST}/users/sign_in`, { page: "login", host: HOST }],
    [`https://${HOST}/appointments?calendar_start_date=2026-09-28`, { page: "other_cliniko", host: HOST }],
    [`https://${HOST}/patients/1001/treatment_notes/2002`, { page: "other_cliniko", host: HOST }],
    [`https://${HOST}/patients/0101/treatment_notes/2002/edit`, { page: "other_cliniko", host: HOST }],
    [`https://${HOST}/patients/abc/treatment_notes/2002/edit`, { page: "other_cliniko", host: HOST }],
    [`https://${HOST}/patients/12345678901234567890/treatment_notes/2002/edit`, { page: "other_cliniko", host: HOST }],
  ])("%s", (url, expected) => {
    expect(classifyUrl(url, ALLOW)).toEqual(expected);
  });

  test.each([
    undefined,
    "not a url",
    `http://${HOST}/patients/1001/treatment_notes/2002/edit`,
    `https://${HOST}:8443/patients/1001/treatment_notes/2002/edit`,
    `https://user:pw@${HOST}/patients/1001/treatment_notes/2002/edit`,
    `https://${UNLISTED}/patients/1001/treatment_notes/2002/edit`,
    "https://cliniko.com/patients/1001/treatment_notes/2002/edit",
    `https://${HOST}.evil.example/patients/1001/treatment_notes/2002/edit`,
    "https://mail.example.com/",
  ])("%s is not an allow-listed Cliniko page", (url) => {
    expect(classifyUrl(url, ALLOW)).toEqual({ page: "not_cliniko" });
  });

  test("a Cliniko host is recognised whether or not it is allow-listed", () => {
    expect(clinikoHost(`https://${UNLISTED}/`)).toBe(UNLISTED);
    expect(clinikoHost("https://www.cliniko.com/")).toBeNull();
    expect(clinikoHost(undefined)).toBeNull();
  });

  test("the note URL is built only from an allow-listed host and id-shaped ids", () => {
    expect(noteUrl(HOST, "1001", "2002", ALLOW)).toBe(`https://${HOST}/patients/1001/treatment_notes/2002/edit`);
    expect(noteUrl(UNLISTED, "1001", "2002", ALLOW)).toBeNull();
    expect(noteUrl(HOST, "1001/../x", "2002", ALLOW)).toBeNull();
    expect(noteUrl(HOST, "1001", undefined, ALLOW)).toBeNull();
  });
});

function reporter(): { sent: ContextPayload[]; r: ContextReporter } {
  const sent: ContextPayload[] = [];
  const r = new ContextReporter((p) => {
    sent.push(p);
    return true;
  });
  return { sent, r };
}

describe("the context reporter", () => {
  test("is inert until the first allow-list arrives", () => {
    const { sent, r } = reporter();
    r.tabUpdated({ id: 5, windowId: 1, active: true, url: NOTE });
    r.windowFocused(1);
    expect(sent).toEqual([]);
    r.setAllowList(ALLOW);
    expect(sent).toEqual([
      { seq: 1, tab_id: 5, window_id: 1, focused: true, page: "note", host: HOST, patient_id: "1001", note_id: "2002" },
    ]);
  });

  test("every report is a valid v2 context and carries no URL", () => {
    const { sent, r } = reporter();
    r.resync(
      [
        { id: 5, windowId: 1, active: true, url: NOTE },
        { id: 6, windowId: 1, active: false, url: `https://${HOST}/users/sign_in` },
        { id: 7, windowId: 1, active: false, url: `https://${OTHER}/appointments` },
      ],
      1,
      ALLOW,
    );
    r.tabUpdated({ id: 5, windowId: 1, active: true, url: undefined }); // left Cliniko
    r.tabRemoved(6);
    expect(sent.map((p) => p.page)).toEqual(["note", "login", "other_cliniko", "not_cliniko", "closed"]);
    for (const payload of sent) {
      parseEnvelope({ protocol_version: PROTOCOL_VERSION, type: "context", session_nonce: "n".repeat(32), payload });
      expect(JSON.stringify(payload)).not.toContain("https://");
    }
  });

  test("a never-tracked tab is never reported, however it changes", () => {
    const { sent, r } = reporter();
    r.setAllowList(ALLOW);
    r.tabUpdated({ id: 9, windowId: 1, active: true, url: "https://mail.example.com/" });
    r.tabUpdated({ id: 9, windowId: 1, active: true, url: undefined });
    r.tabUpdated({ id: 10, windowId: 1, active: false, url: `https://${UNLISTED}/patients/1/treatment_notes/2/edit` });
    r.tabRemoved(9);
    r.tabRemoved(10);
    expect(sent).toEqual([]);
  });

  test("a tracked tab that leaves the allow-list is reported not_cliniko once, then untracked", () => {
    const { sent, r } = reporter();
    r.windowFocused(1);
    r.setAllowList(ALLOW);
    r.tabUpdated({ id: 5, windowId: 1, active: true, url: NOTE });
    r.tabUpdated({ id: 5, windowId: 1, active: true, url: undefined });
    r.tabUpdated({ id: 5, windowId: 1, active: false, url: undefined });
    r.tabRemoved(5);
    expect(sent.map((p) => [p.page, p.host])).toEqual([
      ["note", HOST],
      ["not_cliniko", undefined],
    ]);
  });

  test("a host that leaves the allow-list sends not_cliniko for its tracked tabs", () => {
    const { sent, r } = reporter();
    r.setAllowList(ALLOW);
    r.tabUpdated({ id: 7, windowId: 1, active: false, url: `https://${OTHER}/appointments` });
    r.setAllowList([HOST]);
    expect(sent.map((p) => p.page)).toEqual(["other_cliniko", "not_cliniko"]);
  });

  test("an unchanged tab is not re-reported; seq only rises", () => {
    const { sent, r } = reporter();
    r.setAllowList(ALLOW);
    r.tabUpdated({ id: 5, windowId: 1, active: false, url: NOTE });
    r.tabUpdated({ id: 5, windowId: 1, active: false, url: NOTE });
    r.tabUpdated({ id: 5, windowId: 1, active: false, url: NOTE_B });
    expect(sent.map((p) => p.seq)).toEqual([1, 2]);
  });

  test("activating a tab reports the one losing focus, then the one gaining it", () => {
    const { sent, r } = reporter();
    r.resync(
      [
        { id: 5, windowId: 1, active: true, url: NOTE },
        { id: 6, windowId: 1, active: false, url: NOTE_B },
      ],
      1,
      ALLOW,
    );
    sent.length = 0;
    expect(r.tabActivated(6, 1)).toBe(true);
    expect(sent.map((p) => [p.tab_id, p.focused])).toEqual([
      [5, false],
      [6, true],
    ]);
    expect(r.focusedTab()).toBe(6);
  });

  test("focusing another window moves `focused`; an untracked focused tab sends only the loss", () => {
    const { sent, r } = reporter();
    r.resync(
      [
        { id: 5, windowId: 1, active: true, url: NOTE },
        { id: 8, windowId: 2, active: true, url: "https://mail.example.com/" },
      ],
      1,
      ALLOW,
    );
    sent.length = 0;
    r.windowFocused(2);
    expect(sent.map((p) => [p.tab_id, p.focused])).toEqual([[5, false]]);
  });

  test("a new connection re-reports every allow-listed tab", () => {
    const { sent, r } = reporter();
    const tabs = [{ id: 5, windowId: 1, active: true, url: NOTE }];
    r.resync(tabs, 1, ALLOW);
    r.deactivate();
    r.tabUpdated({ id: 5, windowId: 1, active: true, url: NOTE }); // inert meanwhile
    r.resync(tabs, 1, ALLOW);
    expect(sent.map((p) => [p.seq, p.page])).toEqual([
      [1, "note"],
      [2, "note"],
    ]);
  });

  test("an unknown activated tab is left for the caller to fetch", () => {
    const { r } = reporter();
    r.setAllowList(ALLOW);
    expect(r.tabActivated(42, 1)).toBe(false);
  });
});

function state(extra: Partial<StatePayload> = {}): StatePayload {
  return {
    state_rev: 7,
    app_running: true,
    allow_list: ALLOW,
    hotkey: { available: false },
    spoken_pause: false,
    warnings: [],
    ...extra,
  };
}

const BLOCK_A = {
  reason: "note_changed",
  session_ref: REF,
  clinic_host: HOST,
  clinic_label: "Example Clinic",
  patient_name: "<b>Alex</b> Example",
};

describe("the per-tab slice", () => {
  test("a host off the allow-list is inert", () => {
    expect(sliceFor(state(), 5, UNLISTED, ALLOW, false)).toEqual({ active: false, frame: null });
    expect(sliceFor(state(), 5, null, ALLOW, false)).toEqual({ active: false, frame: null });
  });

  test("an app that is not running tears every page down", () => {
    const off: StatePayload = { ...state(), app_running: false, allow_list: [] };
    expect(sliceFor(off, 5, HOST, ALLOW, true)).toEqual({ active: false, frame: null });
  });

  test("the frame is red while recording and amber while paused or blocked", () => {
    const live = {
      session_ref: REF,
      linked: false,
      recorded_seconds: 3,
      consent_confirmed_at: "2026-09-27T01:31:02Z",
    };
    expect(sliceFor(state({ live: { ...live, phase: "recording" } }), 5, HOST, ALLOW, false).frame).toBe("recording");
    expect(sliceFor(state({ live: { ...live, phase: "paused" } }), 5, HOST, ALLOW, false).frame).toBe("paused");
    expect(sliceFor(state({ live: { ...live, phase: "finishing" } }), 5, HOST, ALLOW, false).frame).toBeNull();
    expect(sliceFor(state({ block: BLOCK_A }), 5, HOST, ALLOW, false).frame).toBe("paused");
  });

  test("with the link down, a live session's tabs show the paused frame (the app pauses on pipe loss)", () => {
    expect(sliceFor(null, 5, HOST, ALLOW, true)).toEqual({ active: true, frame: "paused" });
    expect(sliceFor(null, 5, HOST, ALLOW, false)).toEqual({ active: true, frame: null });
  });

  test("a same-clinic block names both patients, this tab's only from its own verified report", () => {
    const s = state({
      block: BLOCK_A,
      report: {
        tab_id: 5,
        clinic_host: HOST,
        patient_id: "1003",
        note_id: "2004",
        verification: "verified",
        patient_name: "Sam Example",
      },
    });
    const own = sliceFor(s, 5, HOST, ALLOW, false);
    expect(own.block).toEqual({
      session_ref: REF,
      state_rev: 7,
      reason: "note_changed",
      same_clinic: true,
      recording_clinic: "Example Clinic",
      previous_patient: "<b>Alex</b> Example",
      this_patient: "Sam Example",
    });
    const sibling = sliceFor(s, 6, HOST, ALLOW, false);
    expect(sibling.block?.this_patient).toBeUndefined();
    expect(sibling.block?.previous_patient).toBe("<b>Alex</b> Example");
  });

  test("a cross-clinic block carries neither the previous patient's name nor any id", () => {
    const s = state({
      block: BLOCK_A,
      report: {
        tab_id: 9,
        clinic_host: OTHER,
        patient_id: "3001",
        note_id: "4002",
        verification: "verified",
        patient_name: "Jo Other",
      },
      live: {
        session_ref: REF,
        phase: "paused",
        linked: true,
        recorded_seconds: 40,
        consent_confirmed_at: "2026-09-27T01:31:02Z",
        clinic_host: HOST,
        patient_id: "1001",
        note_id: "2002",
        verification: "verified",
        clinic_label: "Example Clinic",
        patient_name: "<b>Alex</b> Example",
      },
    });
    const slice: PageSlice = sliceFor(s, 9, OTHER, ALLOW, false);
    expect(slice.block).toEqual({
      session_ref: REF,
      state_rev: 7,
      reason: "note_changed",
      same_clinic: false,
      recording_clinic: "Example Clinic",
      this_patient: "Jo Other",
    });
    const text = JSON.stringify(slice);
    for (const leak of ["Alex", "1001", "2002", HOST]) expect(text).not.toContain(leak);
  });

  test("an unverified report never names this tab's patient", () => {
    const s = state({
      block: BLOCK_A,
      report: { tab_id: 5, clinic_host: HOST, patient_id: "1003", note_id: "2004", verification: "checking" },
    });
    expect(sliceFor(s, 5, HOST, ALLOW, false).block?.this_patient).toBeUndefined();
  });
});
