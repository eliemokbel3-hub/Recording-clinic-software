// Step 2: validate the TS mirror against the canonical fixtures.
// The pydantic mirror runs the same checks against the same files.
// Protocol v2 (Cliniko workflow safeguards plan Task 4.1): meta.json's
// `limits` are pinned to LIMITS, and valid fixtures are named
// `<type>[__<variant>].json`.
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, test } from "vitest";

import {
  HOST_NAME,
  LIMITS,
  MAX_FRAME_BYTES,
  MIN_SUPPORTED_VERSION,
  PROTOCOL_VERSION,
  ProtocolError,
  makeHello,
  makePing,
  parseEnvelope,
} from "./protocol";

const FIXTURES = join(fileURLToPath(new URL(".", import.meta.url)), "..", "..", "protocol", "fixtures");

function readJson(path: string): unknown {
  return JSON.parse(readFileSync(path, "utf-8"));
}

function fixtureFiles(dir: string): string[] {
  return readdirSync(join(FIXTURES, dir))
    .filter((f: string) => f.endsWith(".json"))
    .sort();
}

interface Message {
  payload: Record<string, unknown>;
  [key: string]: unknown;
}

function validFixture(name: string): Message {
  return readJson(join(FIXTURES, "valid", name)) as Message;
}

function reportOf(message: Message): Record<string, unknown> {
  return message.payload["report"] as Record<string, unknown>;
}

test("fixture dirs are populated", () => {
  expect(fixtureFiles("valid").length).toBeGreaterThanOrEqual(5);
  expect(fixtureFiles("invalid").length).toBeGreaterThanOrEqual(5);
});

test("meta matches constants", () => {
  const meta = readJson(join(FIXTURES, "meta.json")) as Record<string, unknown>;
  expect(meta.protocol_version).toBe(PROTOCOL_VERSION);
  expect(meta.min_supported_version).toBe(MIN_SUPPORTED_VERSION);
  expect(meta.host_name).toBe(HOST_NAME);
  expect(meta.max_frame_bytes).toBe(MAX_FRAME_BYTES);
  expect(meta.limits).toEqual(LIMITS);
  expect(PROTOCOL_VERSION).toBe(2);
});

describe("valid fixtures parse", () => {
  for (const file of fixtureFiles("valid")) {
    test(file, () => {
      const envelope = parseEnvelope(readJson(join(FIXTURES, "valid", file)));
      expect(envelope.type).toBe(file.replace(/\.json$/, "").split("__")[0]);
      // round-trip: serialising and re-parsing yields an equal envelope
      expect(parseEnvelope(JSON.parse(JSON.stringify(envelope)))).toEqual(envelope);
    });
  }
});

describe("invalid fixtures are rejected", () => {
  for (const file of fixtureFiles("invalid")) {
    test(file, () => {
      const fixture = readJson(join(FIXTURES, "invalid", file)) as {
        reason: string;
        message: unknown;
      };
      expect(fixture.reason).toBeTruthy();
      expect(() => parseEnvelope(fixture.message)).toThrow(ProtocolError);
    });
  }
});

test("every v2 type has valid and invalid fixtures", () => {
  for (const type of ["context", "command", "state"]) {
    expect(fixtureFiles("valid").some((f) => f.startsWith(`${type}__`))).toBe(true);
    expect(fixtureFiles("invalid").some((f) => f.startsWith(`${type}__`))).toBe(true);
  }
});

test("a missing nonce on a v2 type is bad_nonce, as on the Python mirror", () => {
  const fixture = readJson(join(FIXTURES, "invalid", "context__missing_nonce.json")) as { message: unknown };
  expect(() => parseEnvelope(fixture.message)).toThrow(expect.objectContaining({ code: "bad_nonce" }));
});

test("a refusal travels in state.last_refusal, never as error", () => {
  const envelope = parseEnvelope(validFixture("state__refusal.json"));
  expect(envelope.type).toBe("state");
  expect(envelope.payload["last_refusal"]).toMatchObject({ action: "start", reason: "not_verified" });
});

test("a display string of exactly the limit is accepted, one more refused", () => {
  const message = validFixture("state__live.json");
  reportOf(message)["patient_name"] = "A".repeat(LIMITS.max_display_chars);
  expect(() => parseEnvelope(message)).not.toThrow();
  reportOf(message)["patient_name"] = "A".repeat(LIMITS.max_display_chars + 1);
  expect(() => parseEnvelope(message)).toThrow(ProtocolError);
});

test("lengths count code points, as Python's len() does", () => {
  const message = validFixture("state__live.json");
  // 120 astral characters are 240 UTF-16 units: still 120 characters.
  reportOf(message)["patient_name"] = "\u{1F600}".repeat(LIMITS.max_display_chars);
  expect(() => parseEnvelope(message)).not.toThrow();
});

test.each([
  ["seq", true],
  ["seq", "7"],
  ["tab_id", LIMITS.max_tab_id + 1],
  ["focused", 1],
])("context %s = %j is refused", (field, value) => {
  const message = validFixture("context__note.json");
  message.payload[field] = value;
  expect(() => parseEnvelope(message)).toThrow(ProtocolError);
});

test.each(["resume", "finish", "resume_previous", "open_review"])("%s needs its session_ref", (action) => {
  const message = validFixture("command__resume.json");
  message.payload["action"] = action;
  expect(() => parseEnvelope(message)).not.toThrow();
  delete message.payload["session_ref"];
  expect(() => parseEnvelope(message)).toThrow(ProtocolError);
});

test("confirmed is refused outside discard", () => {
  const message = validFixture("command__finish.json");
  message.payload["confirmed"] = true;
  expect(() => parseEnvelope(message)).toThrow(ProtocolError);
});

test("builders produce valid envelopes", () => {
  expect(() => parseEnvelope(JSON.parse(JSON.stringify(makeHello("req-1"))))).not.toThrow();
  expect(() =>
    parseEnvelope(JSON.parse(JSON.stringify(makePing("req-2", "9f2c4a8e1b7d3f6a5c0e8b2d4f7a9c1e")))),
  ).not.toThrow();
});
