"""Chrome Native Messaging host entry point (`scribe-host`).

Phase 1 scope: binary-mode stdio framing, origin verification, and the
hello handshake (built in plan Steps 4-5). This stub exists so the entry
point installs and the package imports cleanly from Step 1.

Critical Constraint reminder: stdout carries ONLY framed protocol bytes;
never print here once the real host lands.
"""

from __future__ import annotations

import sys


def main() -> int:
    # Real host (Steps 4-5) refuses to run without a Chrome origin argv.
    sys.stderr.write("scribe-host: native host arrives in plan Steps 4-5\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
