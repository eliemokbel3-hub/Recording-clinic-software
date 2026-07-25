"""Structured, clinical-data-free logging (plan Step 4).

Enforcement is STRUCTURAL (plan Key Design Decision):
1. Code logs ONLY through :func:`log_event`, which accepts a whitelisted
   metadata schema — message type, protocol version, byte sizes, timings,
   state names, error codes, filesystem paths. It never accepts a message
   object or free-form interpolated content.
2. A last-line tripwire filter (:class:`PayloadTripwireFilter`) scans every
   formatted record for protocol-payload signatures and DROPS the record,
   counting the violation, so even misuse of the stdlib logger cannot leak
   payload content.
3. Ruff G004 bans f-strings in logging calls; TID251 bans network imports.

Critical Constraint: the native host's stdout carries only framed protocol
bytes — logging goes to a rotating file and stderr, NEVER stdout.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Final

# Whitelisted metadata keys accepted by log_event (plan: whitelisted schema).
ALLOWED_KEYS: Final[frozenset[str]] = frozenset(
    {
        "message_type",
        "protocol_version",
        "byte_size",
        "duration_ms",
        "state",
        "error_code",
        "path",
        "detail_code",
        "count",
        "pid",
    }
)

# Signatures that indicate a protocol envelope/payload leaked into a log line.
# Both quoted (JSON/dict repr) and unquoted (pydantic model repr, e.g.
# "session_nonce='...' payload={}") forms are covered (HIGH-003). These
# strings MUST stay disjoint from log_event's ALLOWED_KEYS renderings —
# payload/session_nonce/request_id are deliberately not whitelisted keys.
_PAYLOAD_SIGNATURES: Final[tuple[str, ...]] = (
    '"payload"',
    "'payload'",
    "payload=",
    '"session_nonce"',
    "'session_nonce'",
    "session_nonce=",
    "request_id=",
    '"protocol_version":',
    "'protocol_version':",
)

_dropped_records = 0


def dropped_record_count() -> int:
    """Number of log records dropped by the tripwire (exposed for tests/audit)."""
    return _dropped_records


class PayloadTripwireFilter(logging.Filter):
    """Last-line defence: drop any record whose formatted text looks like it
    contains a protocol envelope or payload, and count the violation."""

    def filter(self, record: logging.LogRecord) -> bool:
        global _dropped_records
        try:
            text = record.getMessage()
        except Exception:  # noqa: BLE001 - malformed record: drop it
            _dropped_records += 1
            return False
        if any(sig in text for sig in _PAYLOAD_SIGNATURES):
            _dropped_records += 1
            return False
        return True


def default_log_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / "ClinikoScribe" / "logs"


def setup_logging(
    name: str,
    *,
    log_dir: Path | None = None,
    stderr: bool = True,
    max_bytes: int = 1_000_000,
) -> logging.Logger:
    """Configure the process logger: rotating file + optional stderr, tripwired.

    NEVER attaches a stdout handler (Critical Constraint: stdout purity).
    Replaced handlers are CLOSED, not just detached (MED-002: an orphaned
    open handle on the log file breaks rotation renames on Windows).
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    for handler in logger.handlers:
        handler.close()
    logger.handlers.clear()
    tripwire = PayloadTripwireFilter()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")

    directory = log_dir if log_dir is not None else default_log_dir()
    try:
        directory.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            directory / f"{name}.log", maxBytes=max_bytes, backupCount=3, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(tripwire)
        logger.addHandler(file_handler)
    except OSError:
        # LOW-012: an unwritable log dir must not kill the process before the
        # origin check — fall back to stderr-only logging.
        pass

    # sys.stderr is None under a pythonw-backed launcher with no redirection.
    if stderr and sys.stderr is not None:
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setFormatter(formatter)
        stderr_handler.addFilter(tripwire)
        logger.addHandler(stderr_handler)

    logger.propagate = False
    return logger


def log_event(logger: logging.Logger, event: str, **fields: str | int | float) -> None:
    """The ONLY sanctioned logging call sites use: event name + whitelisted fields.

    Raises ValueError on a non-whitelisted key so misuse fails tests, not
    silently leaks. Values are scalars only — never message objects.
    """
    bad = set(fields) - ALLOWED_KEYS
    if bad:
        raise ValueError(f"log_event fields not in whitelist: {sorted(bad)}")
    parts = [event] + [f"{key}={fields[key]}" for key in sorted(fields)]
    logger.info("%s", " ".join(parts))
