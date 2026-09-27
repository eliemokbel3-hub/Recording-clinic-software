// Cliniko workflow safeguards plan Constraint 8 and D1 (round 36 LOW-032):
// "rendered as text only, never stored, never logged". Every production
// source file under src/ (tests and the test fakes excluded) is scanned,
// comment lines skipped, for an HTML-parsing sink, any browser storage API,
// dynamic code, and console output — the one allowed console call (the native
// host's disconnect diagnostic, which carries no payload) is pinned by count.
//
// This is a LEXICAL guard (rounds 38 PR-LOW-210, 39 PR-LOW-220 and 40
// PR-LOW-230). Two kinds of rule, with different reach:
// - BARE NAMES: any literal occurrence of a listed name as a token in a
//   non-comment line fails, whatever the spelling around it — dotted, a
//   bracketed string key, destructured or aliased (the name is still spelled
//   once, and a comment cannot split a token). The bare names are the HTML
//   sinks below plus `write`/`writeln`, the storage names, `eval` and
//   `Function`.
// - PREFIX-DEPENDENT: `constructor` (the other literal route to the Function
//   constructor) is matched only as `.constructor`, `?.constructor` or
//   `["constructor"]` with nothing but whitespace or newlines between the
//   accessor and the name; a class declares `constructor(` with no accessor
//   and is not matched. A string timer is matched only as a direct
//   `setTimeout(` / `setInterval(` call whose first argument is a string
//   literal, again with only whitespace between.
// The fixtures below prove each stated spelling is caught. For dynamic code
// the syntax-aware check is lint: `extension/eslint.config.js` spreads
// `tseslint.configs.recommendedTypeChecked`, which enables
// `@typescript-eslint/no-implied-eval` (`new Function`, `Function(...)` and
// string timers, judged on the syntax tree, so comments do not fool it).
// Residue, where code review stays the control:
// - a name assembled at run time (`el["inner" + "HTML"]`, `obj[key]`,
//   `Reflect.get(o, key)`);
// - a capability reached through a name NOT on the list (an HTML sink such as
//   `srcdoc`, a `javascript:` URL, a created <script>);
// - any other route to a prefix-dependent name: a comment inside the access or
//   the call (`f./* x */constructor`), destructuring (`const { constructor: C }
//   = f`), `Reflect.get(o, "constructor")`, an aliased timer;
// - only lines starting with `//` are skipped: a trailing or block comment is
//   scanned — a false positive for the bare names, and a missed match inside a
//   prefix-dependent spelling (named above).
import { readFileSync, readdirSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test } from "vitest";

const SRC = fileURLToPath(new URL(".", import.meta.url));

function sources(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return entry.name === "test" ? [] : sources(path);
    if (/\.test\.[cm]?[jt]sx?$/.test(entry.name)) return [];
    return /\.([cm]?js|tsx?|html)$/.test(entry.name) ? [path] : [];
  });
}

function code(text: string): string {
  return text
    .split("\n")
    .filter((line) => !line.trim().startsWith("//"))
    .join("\n");
}

const FORBIDDEN: [string, RegExp][] = [
  [
    "an HTML-parsing sink",
    /\b(innerHTML|outerHTML|insertAdjacentHTML|createContextualFragment|DOMParser|parseFromString|setHTMLUnsafe|write|writeln)\b/,
  ],
  ["browser storage", /\b(storage|localStorage|sessionStorage|indexedDB|cookie)\b/],
  ["dynamic code", /\b(eval|Function)\b|(\.|\[\s*["'`])\s*constructor\b|\bset(Timeout|Interval)\s*\(\s*["'`]/],
];

function flagged(text: string): string[] {
  const body = code(text);
  return FORBIDDEN.filter(([, pattern]) => pattern.test(body)).map(([name]) => name);
}

test("the scan sees every production file", () => {
  const names = sources(SRC).map((p) => relative(SRC, p).replace(/\\/g, "/"));
  for (const expected of ["background.ts", "context.ts", "hub.ts", "page.ts", "panel.ts", "panel-view.ts", "panel.html"]) {
    expect(names).toContain(expected);
  }
  expect(names.some((n) => n.startsWith("test/") || /\.test\./.test(n))).toBe(false);
});

test.each([
  ["a dotted HTML sink", "el.innerHTML = x;", "an HTML-parsing sink"],
  ["a bracketed HTML sink", 'el["outerHTML"] = x;', "an HTML-parsing sink"],
  ["a dotted document.write", "document.write(x);", "an HTML-parsing sink"],
  ["a bracketed document.write", 'document["write"](x);', "an HTML-parsing sink"],
  ["an aliased document.write", "const d = document; d.writeln(x);", "an HTML-parsing sink"],
  ["a parser method", 'new window["DOMParser"]().parseFromString(x, "text/html");', "an HTML-parsing sink"],
  ["dotted chrome storage", "chrome.storage.local.set(x);", "browser storage"],
  ["bracketed chrome storage", 'chrome["storage"].local.set(x);', "browser storage"],
  ["destructured chrome storage", "const { storage } = chrome;", "browser storage"],
  ["bracketed web storage", 'window["localStorage"].setItem(k, v);', "browser storage"],
  ["a cookie write", "document.cookie = x;", "browser storage"],
  ["an eval call", "eval(x);", "dynamic code"],
  ["an aliased eval", "const run = eval; run(x);", "dynamic code"],
  ["a Function constructor", "new Function(x)();", "dynamic code"],
  ["a bare Function call", "Function(x)();", "dynamic code"],
  ["a string timer", 'setTimeout("run()", 1);', "dynamic code"],
  ["a destructured document.write", "const { write } = document; write.call(document, x);", "an HTML-parsing sink"],
  ["a renamed destructured writeln", "const { writeln: w } = document; w(x);", "an HTML-parsing sink"],
  ["an aliased Function", "const Build = Function; Build(x)();", "dynamic code"],
  ["a dotted constructor", '(() => 0).constructor("x")();', "dynamic code"],
  ["a bracketed constructor", 'f["constructor"]("x");', "dynamic code"],
  ["a constructor after a line break", 'f\n  .constructor("x")();', "dynamic code"],
  ["an optional-chained constructor", 'f?.constructor("x");', "dynamic code"],
])("the scan detects %s", (_spelling, text, kind) => {
  expect(flagged(text)).toContain(kind);
});

test("the scan passes text-only rendering and skips comment lines", () => {
  const clean = [
    "el.textContent = name;",
    "const writer = 1; port.postMessage(x);",
    "class A { constructor() {} }",
    "class B extends A {\n  constructor(readonly api: Api) {\n    super();\n  }\n}",
    "setTimeout(() => this.tick(), 500);",
    "// chrome.storage is never used; eval(x) neither",
  ].join("\n");
  expect(flagged(clean)).toEqual([]);
});

test.each(FORBIDDEN)("no production file uses %s", (_name, pattern) => {
  const hits = sources(SRC).filter((path) => pattern.test(code(readFileSync(path, "utf-8"))));
  expect(hits.map((p) => relative(SRC, p))).toEqual([]);
});

test("the only console call is the host-disconnect diagnostic", () => {
  const calls = sources(SRC).flatMap((path) =>
    [...code(readFileSync(path, "utf-8")).matchAll(/console\.\w+\(([^)]*)\)/g)].map(
      (m) => `${relative(SRC, path).replace(/\\/g, "/")}: ${m[0]}`,
    ),
  );
  expect(calls).toEqual(['background.ts: console.warn("native host disconnect:", err.message)']);
});
