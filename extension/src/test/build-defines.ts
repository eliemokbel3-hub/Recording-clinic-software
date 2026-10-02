// Installation plan Task 1.3 (D2): a vitest setup file for EVERY test
// project. The build replaces `__SCRIBE_HOST_NAME__` statically (vite's
// `define`), but a jsdom test project transforms modules for the client,
// where vite leaves `define` to its dev client script, which jsdom never
// loads, so the identifier is unbound there. Assigning the same values on
// `globalThis` binds it in every environment, from the one source the build
// uses (`buildDefines`, release channel: the tests pin what ships).
import { buildDefines } from "../channel";

const scope = globalThis as unknown as Record<string, unknown>;
for (const [name, value] of Object.entries(buildDefines("release"))) {
  scope[name] = JSON.parse(value) as unknown;
}
