// Step 2: validate the TS mirror against the canonical fixtures.
// The pydantic mirror runs the same checks against the same files.
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, test } from "vitest";

import {
  HOST_NAME,
  MAX_FRAME_BYTES,
  MIN_SUPPORTED_VERSION,
  PROTOCOL_VERSION,
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
});

describe("valid fixtures parse", () => {
  for (const file of fixtureFiles("valid")) {
    test(file, () => {
      const envelope = parseEnvelope(readJson(join(FIXTURES, "valid", file)));
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
      expect(() => parseEnvelope(fixture.message)).toThrow();
    });
  }
});

test("builders produce valid envelopes", () => {
  expect(() => parseEnvelope(JSON.parse(JSON.stringify(makeHello("req-1"))))).not.toThrow();
  expect(() =>
    parseEnvelope(JSON.parse(JSON.stringify(makePing("req-2", "9f2c4a8e1b7d3f6a5c0e8b2d4f7a9c1e")))),
  ).not.toThrow();
});
