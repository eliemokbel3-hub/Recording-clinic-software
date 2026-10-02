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

# Task 1.7: what a packaged build tells the user when an installed file is
# missing or damaged. The source-run commands are below, in the two remedies.
FROZEN_REMEDY: Final = "reinstall Clinic Scribe"


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


def data_root() -> Path:
    """``%LOCALAPPDATA%\\ClinikoScribe`` (production) or ``…\\ClinikoScribe-dev``
    (dev); the home folder stands in for an unset or empty ``LOCALAPPDATA``.
    Read on every call — never cached."""
    return _data_root_from(os.environ.get("LOCALAPPDATA"))


def app_data_root_via(layer: WindowsLayer) -> Path:
    """``data_root()`` with ``LOCALAPPDATA`` read through the ``WindowsLayer``
    seam (the start-up exclusion checks, C6)."""
    return _data_root_from(layer.environ("LOCALAPPDATA"))


def instance_guard_root() -> Path:
    """Task 1.5 (D3): the folder of the ONE single-instance lock file, the
    same for both channels — the PRODUCTION data folder, where every earlier
    build already keeps ``app.lock``. Chosen because (a) an older build, the
    installed app and a dev run then all contend for one file; (b) it lies in
    this user's own profile, which another standard account can neither open
    nor create in (the property the lock relies on); (c) D3/C8 name the guard
    as the one thing the dev channel shares. The dev channel only ever holds
    ``app.lock`` there, creating the folder if it is absent, and reads or
    writes nothing else in it."""
    return _data_root_from(os.environ.get("LOCALAPPDATA"), "production")


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
        raise InstallLayoutError("Clinic Scribe is not running from its install folder")
    return folder


def models_root() -> Path:
    """``<install folder>\\models`` when frozen; ``<data root>\\models`` for a
    source run, raising ``RuntimeError`` when ``LOCALAPPDATA`` is unset (no
    home fallback for models — the long-standing contract)."""
    root = install_root()
    if root is not None:
        return root / MODELS_DIRNAME
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise RuntimeError("LOCALAPPDATA is not set; model cache location unknown")
    return _data_root_from(local_app_data) / MODELS_DIRNAME


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


__all__ = [
    "APP_FOLDER_NAME",
    "DEV_FOLDER_NAME",
    "FROZEN_REMEDY",
    "INSTALL_ROOTS",
    "MODELS_DIRNAME",
    "Channel",
    "InstallLayoutError",
    "ModelEntry",
    "app_data_root_via",
    "channel",
    "channel_for",
    "data_root",
    "executable",
    "folder_name",
    "install_root",
    "instance_guard_root",
    "is_frozen",
    "model_remedy",
    "models_root",
    "registration_remedy",
]
