"""The product's display name is "Clinic Scribe" (practitioner decision
2026-09-28, the H2a naming item); the internal ``ClinikoScribe`` identifiers
stay byte-identical, because changing them would orphan saved state — above
all the Credential Manager prefix that holds the practitioner's Cliniko keys.

A TEXT-MATCHING guard over the production source, not a proof. It cannot see
a name built at run time or split across adjacent literals, the built
extension in ``extension/dist``, or the docs; the pipe name, mutex name and
native-host name are pinned by their own modules' tests."""

from __future__ import annotations

import re
from pathlib import Path

from scribe_desktop import (
    audit,
    install_layout,
    past_sessions,
    practitioner_profile,
    secure_storage,
    session_store,
)
from scribe_desktop.pipe_server import PIPE_PREFIX
from scribe_desktop.protocol import HOST_NAME

REPO = Path(__file__).resolve().parents[2]
_OLD_DISPLAY_NAME = re.compile(r"cliniko\s+scribe", re.IGNORECASE)


def _production_files() -> list[Path]:
    files = sorted((REPO / "desktop" / "src").rglob("*.py"))
    files += sorted((REPO / "scripts").glob("*.py"))
    extension = REPO / "extension" / "src"
    files += sorted(
        path
        for path in extension.rglob("*")
        if path.suffix in {".ts", ".html"} and not path.name.endswith(".test.ts")
    )
    return files


def test_no_production_file_shows_the_old_display_name() -> None:
    files = _production_files()
    assert len(files) > 20, "the scan found too few files to mean anything"
    offenders = [
        f"{path.relative_to(REPO)}:{number}"
        for path in files
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if _OLD_DISPLAY_NAME.search(line)
    ]
    assert offenders == []


def test_the_internal_identifiers_are_unchanged() -> None:
    assert secure_storage._SERVICE_PREFIX == "ClinikoScribe"
    assert session_store.SESSION_KEY_DESCRIPTION == "ClinikoScribe session key"
    assert practitioner_profile.PROFILE_KEY_DESCRIPTION == "ClinikoScribe practitioner profile key"
    assert practitioner_profile.STYLE_KEY_DESCRIPTION == "ClinikoScribe practitioner style key"
    assert audit.AUDIT_KEY_DESCRIPTION == "ClinikoScribe audit key"
    assert past_sessions.PAST_SESSION_KEY_DESCRIPTION == "ClinikoScribe past-session key"
    assert PIPE_PREFIX == "\\\\.\\pipe\\ClinikoScribe-"
    assert HOST_NAME == "com.scribe.cliniko_host"
    # Installation plan Task 1.2: the registration script's install folder is
    # the data root (``install_layout``, the one place a ``ClinikoScribe``
    # path is built), whose production name is pinned here instead of the
    # script's former literal.
    assert install_layout.APP_FOLDER_NAME == "ClinikoScribe"
    register = (REPO / "scripts" / "register-native-host.py").read_text(encoding="utf-8")
    assert "INSTALL_DIR = install_layout.data_root()" in register
