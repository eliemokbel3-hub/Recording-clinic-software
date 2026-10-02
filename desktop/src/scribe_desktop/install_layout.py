"""Where Clinic Scribe lives on this computer — the channel and every root
(installation plan Phase 1, D2/D3/D5).

THE single place a ``ClinikoScribe`` folder path is built. A source-scan
test (``test_install_layout.py``) refuses a spelling of the name, or a
reference to the folder-name constants here, anywhere else — a scan, not a
proof (a name assembled at run time is unseen).

- **The channel** comes from ``sys.frozen`` through ``is_frozen()`` (D2): a
  packaged build is ``"production"``, a source checkout is ``"dev"``. There is
  no environment-variable switch. Tests pin the production channel (the
  conftest autouse fixture), so existing tests test what ships; dedicated
  tests inject the dev channel.
- **The data root** is ``%LOCALAPPDATA%\\ClinikoScribe`` in production and
  ``%LOCALAPPDATA%\\ClinikoScribe-dev`` in dev (C8: the dev channel never
  touches the production data folder), re-reading the environment on EVERY
  call (tests redirect ``LOCALAPPDATA`` per test) and keeping the home-folder
  fallback when it is unset.
- **The models root** is ``<install folder>\\models`` when frozen (read-only to
  users, D5) and ``<data root>\\models`` otherwise; with no ``LOCALAPPDATA``
  the source-run root RAISES, exactly as ``benchmark.default_models_root``
  always has (no home fallback for models).
- **The one shared place** is the single-instance guard (D3): both channels
  hold the same lock file, so the installed and the dev app never run at once
  (``instance_guard_root``).
- **The remedies** a missing model or registration names (Task 1.7): the
  setup scripts from a source checkout, "reinstall Clinic Scribe" in a
  packaged build, where the scripts do not exist.

Frozen-only behaviour (the install folder, the models root, the remedies)
follows ``is_frozen()``; channel behaviour (the data folder, the identities in
``identity.py``, the dev write guard) follows ``channel()``. In a real run the
two always agree; only a test that pins one and not the other separates them.
"""

from __future__ import annotations

import ntpath
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Final, Literal

if TYPE_CHECKING:
    from scribe_desktop.exclusions import WindowsLayer

Channel = Literal["production", "dev"]
ModelEntry = Literal["speaker-embedding", "language-model"]

# C2: the production folder name never changes (existing data, keys and the
# Chrome link must keep working in the installed app).
APP_FOLDER_NAME: Final = "ClinikoScribe"
DEV_FOLDER_NAME: Final = "ClinikoScribe-dev"
MODELS_DIRNAME: Final = "models"

# D-I1 (decided by the practitioner after Task 0.2, 2026-10-02): the one
# folder a packaged build may run from — the per-machine install under
# Program Files, admin-only to change. A tuple, so a test can inject its own
# root through the same seam; its pin is in test_install_layout.py.
INSTALL_ROOTS: Final[tuple[str, ...]] = (r"C:\Program Files\ClinikoScribe",)

# D6 / Task 3.4 (the forms Task 0.3 fixed): the installer's backup and
# snapshot exclusion value, named after the production folder, holding the
# two ``$UserProfile$``-relative patterns ``backup_exclusion_patterns``
# returns. Only the production folder is ever covered (the dev folder is a
# developer's own, C8).
BACKUP_VALUE_NAME: Final = APP_FOLDER_NAME

# D5 / Task 3.5: the release model pack is a folder beside setup.exe named
# after the production folder and the models manifest's digest
# (``model_pack_name``); the installer looks for exactly that name.
MODEL_PACK_INFIX: Final = "-models-"
MODEL_PACK_DIGEST_CHARS: Final = 8

# Task 1.7: what a packaged build tells the user when an installed file is
# missing or damaged. The source-run commands are below, in the two remedies.
FROZEN_REMEDY: Final = "reinstall Clinic Scribe"

_NOT_INSTALLED: Final = "Clinic Scribe is not running from its install folder"
# Task 2.7: what a packaged build copied outside its install folder says
# instead of starting (``scribe-app``'s message box).
NOT_INSTALLED_LINE: Final = f"{_NOT_INSTALLED} — {FROZEN_REMEDY}."


class InstallLayoutError(RuntimeError):
    """A packaged build is not running from an accepted install folder. A
    ``RuntimeError``, so every model probe that already treats an unknown
    models root as "unavailable" (``LOCALAPPDATA`` unset) treats this the
    same way."""


# --- the channel ------------------------------------------------------------------


def is_frozen() -> bool:
    """Whether this is a packaged (PyInstaller) build — the D2 input. The
    seam tests replace; nothing else reads ``sys.frozen``."""
    return bool(getattr(sys, "frozen", False))


def channel_for(frozen: bool) -> Channel:
    return "production" if frozen else "dev"


def channel() -> Channel:
    """``"production"`` for a packaged build, ``"dev"`` for a source run."""
    return channel_for(is_frozen())


def folder_name(of: Channel | None = None) -> str:
    """The data folder's name under ``%LOCALAPPDATA%`` for ``of`` (default:
    this process's channel)."""
    which = of if of is not None else channel()
    return APP_FOLDER_NAME if which == "production" else DEV_FOLDER_NAME


# --- the roots --------------------------------------------------------------------


def _data_root_from(local_app_data: str | None, of: Channel | None = None) -> Path:
    return Path(local_app_data or str(Path.home())) / folder_name(of)


def data_root(of: Channel | None = None) -> Path:
    """``%LOCALAPPDATA%\\ClinikoScribe`` (production) or ``…\\ClinikoScribe-dev``
    (dev) — of channel ``of``, default this process's; the home folder stands
    in for an unset or empty ``LOCALAPPDATA``. Read on every call — never
    cached. ``of="dev"`` is what the dev-only registration script installs
    into whatever the channel pin (Task 3.7)."""
    return _data_root_from(os.environ.get("LOCALAPPDATA"), of)


def app_data_root_via(layer: WindowsLayer) -> Path:
    """``data_root()`` with ``LOCALAPPDATA`` read through the ``WindowsLayer``
    seam (the start-up exclusion checks, C6)."""
    return _data_root_from(layer.environ("LOCALAPPDATA"))


def backup_exclusion_patterns() -> tuple[str, ...]:
    """D6: the live-session and log patterns of the installer's
    ``FilesNotToBackup`` / ``FilesNotToSnapshot`` value
    (``BACKUP_VALUE_NAME``), written literally (Task 3.4)."""
    base = "$UserProfile$\\AppData\\Local\\" + APP_FOLDER_NAME
    return (f"{base}\\sessions\\* /s", f"{base}\\logs\\* /s")


def model_pack_name(manifest_sha256: str) -> str:
    """D5 / Task 3.5: the release model pack's folder name —
    ``ClinikoScribe-models-<the manifest's SHA-256, first 8 hex>`` — so a pack
    is tied to the one manifest its installer compiled in."""
    digest = manifest_sha256.lower()
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("a model pack is named by a SHA-256 hex digest")
    return f"{APP_FOLDER_NAME}{MODEL_PACK_INFIX}{digest[:MODEL_PACK_DIGEST_CHARS]}"


def instance_guard_root() -> Path:
    """Task 1.5 (D3): the folder of the ONE single-instance lock file, the
    same for both channels — the PRODUCTION data folder, where every earlier
    build already keeps ``app.lock``. Chosen because (a) an older build, the
    installed app and a dev run then all contend for one file; (b) it lies in
    this user's own profile, which another standard account can neither open
    nor create in (the property the lock relies on); (c) D3/C8 name the guard
    as the one thing the RUNNING dev app shares. The dev app only ever holds
    ``app.lock`` there, creating the folder if it is absent, and reads or
    writes nothing else in it; C8's other named exception is not the app but
    the one-time ``register-native-host.py --unregister`` migration, which
    deletes the old per-user registration's two files there (round 28
    PR-LOW-032)."""
    return data_root("production")


def executable() -> str:
    """``sys.executable`` — the seam ``install_root`` reads through."""
    return sys.executable


def _normalised(path: str) -> str:
    return ntpath.normcase(ntpath.normpath(path))


def install_root(accepted: Sequence[str] | None = None) -> Path | None:
    """The folder of the packaged ``scribe-app.exe``; ``None`` for a source
    run. A packaged build anywhere but an accepted root (``INSTALL_ROOTS``,
    or ``accepted``) raises ``InstallLayoutError``: links and junctions are
    resolved first, so a link at the install path that points elsewhere is
    refused too."""
    if not is_frozen():
        return None
    folder = Path(os.path.realpath(executable())).parent
    roots = INSTALL_ROOTS if accepted is None else accepted
    if _normalised(str(folder)) not in {_normalised(root) for root in roots}:
        raise InstallLayoutError(_NOT_INSTALLED)
    return folder


def outside_install_folder() -> InstallLayoutError | None:
    """Task 2.7: the refusal ``app.main`` and ``native_host.main`` check
    before logging, the single-instance guard, any data root and any window
    (only ``app.main``'s build-audit self-check, Task 3.5, which touches none
    of them, answers earlier). The ``InstallLayoutError`` when a packaged build is not
    running from an accepted install folder (``install_root``); ``None``
    for a source run or a packaged build where it belongs. Touches no data
    root."""
    try:
        install_root()
    except InstallLayoutError as exc:
        return exc
    return None


def models_root(of: Channel | None = None) -> Path:
    """``<install folder>\\models`` when frozen; ``<data root>\\models`` for a
    source run — of channel ``of``, default this process's — raising
    ``RuntimeError`` when ``LOCALAPPDATA`` is unset (no home fallback for
    models — the long-standing contract). ``of="dev"`` is the source run's
    own root whatever the channel pin (the real-ML test legs, Task 2.6)."""
    root = install_root()
    if root is not None:
        return root / MODELS_DIRNAME
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise RuntimeError("LOCALAPPDATA is not set; model cache location unknown")
    return _data_root_from(local_app_data, of) / MODELS_DIRNAME


# --- the remedies (Task 1.7) --------------------------------------------------------


def model_remedy(only: ModelEntry | None = None) -> str:
    """The clause that tells the user how to restore a missing or damaged
    model file (or the prose runtime): the setup script from a source
    checkout, ``FROZEN_REMEDY`` in a packaged build."""
    if is_frozen():
        return FROZEN_REMEDY
    command = "scripts/setup-models.py" + (f" --only {only}" if only is not None else "")
    return f"run {command} from a normal terminal"


def registration_remedy() -> str:
    """The clause that tells the user how to restore the Chrome link or the
    crash-report exclusions: the registration script from a source checkout,
    ``FROZEN_REMEDY`` in a packaged build (the installer writes both)."""
    if is_frozen():
        return FROZEN_REMEDY
    return "run scripts/register-native-host.py again from a normal terminal"


# The Win32 extended-length and device prefixes and the NT object-namespace
# prefix, after ``/`` → ``\`` (round 28 PR-LOW-028).
_DEVICE_PREFIXES: Final = ("\\\\?\\", "\\\\.\\", "\\??\\")


def is_unc_path(path: str | os.PathLike[str]) -> bool:
    """A network (UNC) path, or a device-namespace path that is not a plain
    drive: ``\\\\server\\share…``, ``//server/share…`` and the mixed
    ``\\/server/…`` / ``/\\server\\…`` forms, which Windows reads as UNC too —
    so the separators are normalised the way ``pathlib`` does before the test
    (round 27 PR-MED-020: a RAW string, such as a registry value, would
    otherwise pass). The one definition (H.4 SEC-003).

    Round 28 PR-LOW-028: the extended and device prefixes (``\\\\?\\``,
    ``\\\\.\\`` and the NT ``\\??\\``) are judged by an ALLOW-list — local only
    when a drive follows (``\\\\?\\C:\\…``); ``\\\\?\\UNC\\…`` and every other
    form after them (``GLOBALROOT\\Device\\Mup\\…`` reaches the network too,
    ``Volume{…}``, pipes) count as network, failing closed. Mapped network
    drive letters stay the documented residue.

    Its callers refuse such a path BEFORE any filesystem touch: the model
    loaders and probes, the benchmark, and the Chrome-link registry readers.
    The custody stores (sessions, audit, Past sessions, profile, config,
    clinics) deliberately do NOT refuse — a folder-redirected
    ``LOCALAPPDATA`` puts them on SMB, the accepted residue
    (``session_store.default_sessions_root``)."""
    text = str(path).replace("/", "\\")
    for prefix in _DEVICE_PREFIXES:
        if text.startswith(prefix):
            rest = text[len(prefix) :]
            return not (
                len(rest) >= 2
                and rest[0].isascii()
                and rest[0].isalpha()
                and rest[1] == ":"
                and (len(rest) == 2 or rest[2] == "\\")
            )
    return text.startswith("\\\\")


__all__ = [
    "APP_FOLDER_NAME",
    "BACKUP_VALUE_NAME",
    "DEV_FOLDER_NAME",
    "FROZEN_REMEDY",
    "INSTALL_ROOTS",
    "MODELS_DIRNAME",
    "MODEL_PACK_DIGEST_CHARS",
    "MODEL_PACK_INFIX",
    "NOT_INSTALLED_LINE",
    "Channel",
    "InstallLayoutError",
    "ModelEntry",
    "app_data_root_via",
    "backup_exclusion_patterns",
    "channel",
    "channel_for",
    "data_root",
    "executable",
    "folder_name",
    "install_root",
    "instance_guard_root",
    "is_frozen",
    "is_unc_path",
    "model_pack_name",
    "model_remedy",
    "models_root",
    "outside_install_folder",
    "registration_remedy",
]
