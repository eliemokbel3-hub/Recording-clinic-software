"""Installation plan round 35 MED-001: the transcription stack's import
warm-up (``ml_warmup``). No test imports the real stack: the conftest pins
the default importer to a recorder, and the tests here pass their own."""

from __future__ import annotations

import logging
import threading
from types import ModuleType
from typing import Any

import pytest

from scribe_desktop import ml_warmup
from scribe_desktop.benchmark import OfflineEnvError
from scribe_desktop.ml_warmup import WARMED_MODULES, ImportWarmup, warm_transcription_imports


class _Records(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


@pytest.fixture
def records() -> Any:
    logger = logging.getLogger("test-ml-warmup")
    handler = _Records()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    yield logger, handler
    logger.removeHandler(handler)


class _FakeModule(ModuleType):
    def __init__(self, name: str, calls: list[str]) -> None:
        super().__init__(name)
        self._calls = calls

    def disable_telemetry_events(self) -> None:
        self._calls.append(f"{self.__name__}.disable_telemetry_events")


class TestWarmTranscriptionImports:
    def test_asserts_offline_then_imports_the_stack_in_order(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[str] = []
        monkeypatch.setattr(ml_warmup, "assert_offline_env", lambda: calls.append("offline"))

        def importer(name: str) -> ModuleType:
            calls.append(name)
            return _FakeModule(name, calls)

        warm_transcription_imports(importer)
        assert calls == [
            "offline",
            "numpy",
            "onnxruntime",
            "onnxruntime.disable_telemetry_events",
            "faster_whisper",
        ]
        assert WARMED_MODULES == ("numpy", "onnxruntime", "faster_whisper")

    def test_an_offline_refusal_imports_nothing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def refuse() -> None:
            raise OfflineEnvError("offline kill-switches not active: X")

        monkeypatch.setattr(ml_warmup, "assert_offline_env", refuse)
        imported: list[str] = []
        with pytest.raises(OfflineEnvError):
            warm_transcription_imports(lambda name: imported.append(name) or ModuleType(name))
        assert imported == []


class TestImportWarmup:
    def test_not_ready_until_the_warm_up_returns(self, records: Any) -> None:
        logger, handler = records
        gate = threading.Event()
        entered = threading.Event()

        def warm() -> None:
            entered.set()
            gate.wait()

        warmup = ImportWarmup(warm, logger=logger)
        assert not warmup.is_finished()  # before start: not ready
        warmup.start()
        assert entered.wait(5.0)
        assert not warmup.is_finished()
        gate.set()
        assert warmup.wait(5.0) and warmup.is_finished()
        (line,) = handler.messages
        assert line.startswith("ml_warmup duration_ms=") and line.endswith(" state=done")

    def test_a_failed_warm_up_is_finished_and_logs_the_type_name_only(
        self, records: Any
    ) -> None:
        logger, handler = records

        def warm() -> None:
            raise ImportError("DLL load failed: SECRET-PATH")

        warmup = ImportWarmup(warm, logger=logger)
        warmup.start()
        assert warmup.wait(5.0) and warmup.is_finished()
        (line,) = handler.messages
        assert line.startswith("ml_warmup duration_ms=")
        assert line.endswith(" error_code=ImportError state=failed")
        assert "SECRET" not in line and "DLL" not in line

    def test_start_twice_is_refused(self) -> None:
        warmup = ImportWarmup(lambda: None)
        warmup.start()
        with pytest.raises(RuntimeError, match="already started"):
            warmup.start()
        assert warmup.wait(5.0)

    def test_the_default_warm_up_uses_the_importer_bound_at_construction(
        self, monkeypatch: pytest.MonkeyPatch, _no_real_ml_warmup_imports: list[str]
    ) -> None:
        """The conftest's recorder is the module importer here; a default
        ``ImportWarmup`` binds it when built, so even a warm-up thread that
        outlives its test never reaches the real import."""
        monkeypatch.setattr(ml_warmup, "assert_offline_env", lambda: None)
        warmup = ImportWarmup()
        monkeypatch.setattr(
            ml_warmup,
            "_import_module",
            lambda name: pytest.fail("the importer was resolved after construction"),
        )
        warmup.start()
        assert warmup.wait(5.0)
        assert _no_real_ml_warmup_imports == list(WARMED_MODULES)


class TestHoldsStart:
    """Round 36 MED-001 (the practitioner's option (b)): Start waits on the
    warm-up, bounded — a fake clock, never a real import or a sleep."""

    def test_nothing_holds_before_start(self) -> None:
        assert not ImportWarmup(lambda: None, clock=lambda: 0.0).holds_start()

    def test_holds_while_running_inside_the_bound_then_lets_go(self) -> None:
        gate = threading.Event()
        now = [10.0]

        def hang() -> None:
            gate.wait()

        warmup = ImportWarmup(hang, clock=lambda: now[0], hold_seconds=60.0)
        warmup.start()
        try:
            assert warmup.holds_start()
            now[0] = 69.999
            assert warmup.holds_start()
            now[0] = 70.0  # the bound, measured from start: a hung warm-up lets go
            assert not warmup.holds_start() and not warmup.is_finished()
        finally:
            gate.set()
            assert warmup.wait(5.0)
        now[0] = 10.0
        assert not warmup.holds_start()  # finished: never holds again

    def test_a_finished_or_failed_warm_up_holds_nothing(self) -> None:
        def broken() -> None:
            raise ImportError("no ML stack")

        for warm in (lambda: None, broken):
            warmup = ImportWarmup(warm, clock=lambda: 0.0)
            warmup.start()
            assert warmup.wait(5.0)
            assert not warmup.holds_start()

    def test_the_default_bound_is_a_minute(self) -> None:
        from scribe_desktop.ml_warmup import START_HOLD_SECONDS

        assert START_HOLD_SECONDS == 60.0
