"""Note-learning plan Phase 1, Tasks 1.2 + 1.3: the live worker inside the
session controller and the processing-thread drain in ``build_transcriber``.

Controller tests run the real DPAPI custody path (Windows-only, like
``test_session_machine.py``) with ``MockCaptureBackend`` feeding 1 s blocks
(each block is one store chunk) and a real ``LiveTranscriber`` over the mock
speech provider and the amplitude VAD — no ML stack. The batch fallback's
models are stubbed at the composition layer (``ui.models``), so a fallback
proves its routing without loading anything.

Covered: the tee feeds the worker the store's bytes and the drained document
equals the batch document; Finish seals only and stays under 100 ms with a
blocked tail, the last flushed chunk lands in the drained tail; Discard in
RECORDING / PAUSED / pre-claim PROCESSING / FAILED stops and joins the
worker and confirms its buffers cleared BEFORE ``discard_session`` destroys
the key, with late live posts dropped; a join timeout is reported (logged)
and never counted as cleared while the key still goes; capture failure,
footer failure and retirement on ``start()`` stop an attached worker; pause
and resume gate feeding; ``claim_live_transcriber`` is legal only inside a
run; a transcriber failure after the claim leaves nothing attached; a tee
exception never reaches the capture worker's failure path; the three C8
fallback lines; today's behaviour without a factory. Installation plan
round 35 MED-001: a blocked model load never fails capture, a factory that
returns None records without a worker, and a capture failure logs its type
name and detail word only.
"""

from __future__ import annotations

import logging
import math
import struct
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from conftest import start_unlinked
from scribe_desktop import session as session_mod
from scribe_desktop.audio_capture import (
    CHUNK_BYTES,
    CaptureOverflowError,
    DeviceLostError,
    MockCaptureBackend,
)
from scribe_desktop.benchmark import apply_offline_env
from scribe_desktop.secure_storage import SessionCrypto
from scribe_desktop.session import SessionActivityError, SessionController, SessionState
from scribe_desktop.session_store import (
    KEY_FILENAME,
    SessionChunkStore,
    StoreWriteError,
    iter_chunks,
    unwrap_key_from_file,
)
from scribe_desktop.speech import BYTES_PER_SAMPLE, SAMPLE_RATE, MockSpeechProvider, TranscribedWord
from scribe_desktop.transcription import (
    LiveFailure,
    LiveFailureKind,
    LiveTranscriber,
    LiveTranscriptionError,
    LiveTranscriptionFailed,
    TranscriptDocument,
    TranscriptSegment,
    read_transcript,
    transcribe_session,
)
from scribe_desktop.ui import models

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="DPAPI custody is Windows-only")


@pytest.fixture(autouse=True)
def _offline_env() -> None:
    apply_offline_env()


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------


def tone_pcm(seconds: float, frequency: float = 440.0, amplitude: float = 0.5) -> bytes:
    count = int(seconds * SAMPLE_RATE)
    scale = amplitude * 32767
    return struct.pack(
        f"<{count}h",
        *(int(scale * math.sin(2 * math.pi * frequency * i / SAMPLE_RATE)) for i in range(count)),
    )


def silence_pcm(seconds: float) -> bytes:
    return b"\0" * (int(seconds * SAMPLE_RATE) * BYTES_PER_SAMPLE)


def amplitude_vad(frame: bytes) -> float:
    samples = struct.unpack(f"<{len(frame) // 2}h", frame)
    peak = max(abs(s) for s in samples)
    return 0.95 if peak > 1000 else 0.02


def _feed(backend: MockCaptureBackend, pcm: bytes) -> None:
    """One backend block per store chunk (``CHUNK_BYTES`` = 1 s)."""
    for i in range(0, len(pcm), CHUNK_BYTES):
        backend.feed(pcm[i : i + CHUNK_BYTES])


def _wait(predicate: Callable[[], bool], timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() > deadline:
            raise AssertionError("condition not reached in time")
        time.sleep(0.005)


def _wait_for_state(controller: SessionController, state: SessionState) -> None:
    _wait(lambda: controller.state is state)


def _strip_created(document: TranscriptDocument) -> dict[str, Any]:
    data = document.model_dump()
    data.pop("created_at")
    return data


class _BlockingProvider:
    def __init__(self, gate: threading.Event) -> None:
        self._gate = gate
        self._inner = MockSpeechProvider()
        self.entered = threading.Event()

    def transcribe_segment(self, pcm: bytes, sample_rate: int) -> list[TranscribedWord]:
        self.entered.set()
        self._gate.wait()
        return self._inner.transcribe_segment(pcm, sample_rate)


class _StubVad:
    """The batch fallback's VAD at the composition layer (no ONNX)."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    def frame_probability(self, frame: bytes) -> float:
        return amplitude_vad(frame)


class _StubWhisper:
    """The batch fallback's provider at the composition layer (no model)."""

    constructed: list[str] = []

    def __init__(self, *args: Any, model_name: str = "", **kwargs: Any) -> None:
        self._inner = MockSpeechProvider()
        self._model_name = model_name
        type(self).constructed.append(model_name)

    @property
    def model_name(self) -> str:
        return self._model_name

    def transcribe_segment(self, pcm: bytes, sample_rate: int) -> list[TranscribedWord]:
        return self._inner.transcribe_segment(pcm, sample_rate)


class _NoBatchModels:
    """A batch model constructed on a path that must not build one."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise AssertionError("the batch fallback must not construct a model here")


@pytest.fixture
def batch_stubs(monkeypatch: pytest.MonkeyPatch) -> type[_StubWhisper]:
    _StubWhisper.constructed = []
    monkeypatch.setattr(models, "SileroVad", _StubVad)
    monkeypatch.setattr(models, "WhisperSpeechProvider", _StubWhisper)
    monkeypatch.setattr(models, "resolve_whisper_model", lambda *a, **k: "mock-batch")
    return _StubWhisper


@pytest.fixture
def no_batch_models(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(models, "SileroVad", _NoBatchModels)
    monkeypatch.setattr(models, "WhisperSpeechProvider", _NoBatchModels)


class _Workers:
    """The controller's live-worker factory, keeping every worker it built."""

    def __init__(
        self,
        *,
        provider: Any = None,
        provider_factory: Callable[[], Any] | None = None,
        on_window: Callable[[tuple[TranscriptSegment, ...]], None] | None = None,
        stop_timeout: float = 10.0,
    ) -> None:
        self.built: list[LiveTranscriber] = []
        self._provider = provider
        self._provider_factory = provider_factory
        self._on_window = on_window
        self._stop_timeout = stop_timeout

    def __call__(self) -> LiveTranscriber:
        def provider() -> Any:
            if self._provider_factory is not None:
                return self._provider_factory()
            return self._provider if self._provider is not None else MockSpeechProvider()

        worker = LiveTranscriber(
            provider_factory=provider,
            vad_factory=lambda: amplitude_vad,
            on_window=self._on_window,
            stop_timeout=self._stop_timeout,
        )
        self.built.append(worker)
        return worker

    @property
    def last(self) -> LiveTranscriber:
        return self.built[-1]


class _Records(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


def _controller(
    tmp_path: Path, workers: _Workers | None, logger: logging.Logger | None = None
) -> tuple[SessionController, MockCaptureBackend]:
    backend = MockCaptureBackend()
    controller = SessionController(
        backend, sessions_root=tmp_path, logger=logger, live_transcriber_factory=workers
    )
    return controller, backend


def _transcribe(
    controller: SessionController, statuses: list[str]
) -> tuple[TranscriptDocument, Path, SessionCrypto]:
    """Run the Task 1.3 callable through the controller; capture custody."""
    raw = models.build_transcriber(
        attribution=lambda: (None, None),
        live_source=controller.claim_live_transcriber,
        on_status=statuses.append,
    )
    seen: list[tuple[TranscriptDocument, Path, SessionCrypto]] = []

    def wrapped(directory: Path, crypto: SessionCrypto) -> TranscriptDocument:
        document = raw(directory, crypto)
        seen.append((document, directory, crypto))
        return document

    controller.transcribe(wrapped)
    return seen[0]


# ---------------------------------------------------------------------------
# Task 1.2 — the controller
# ---------------------------------------------------------------------------


@windows_only
class TestLiveSessionController:
    def test_the_tee_feeds_the_worker_and_the_drained_document_is_the_batch_document(
        self, tmp_path: Path, no_batch_models: None
    ) -> None:
        pytest.importorskip("numpy")
        posts: list[tuple[TranscriptSegment, ...]] = []
        workers = _Workers(on_window=posts.append)
        controller, backend = _controller(tmp_path, workers)
        start_unlinked(controller)
        worker = workers.last
        assert worker.running and not worker.sealed
        pcm = silence_pcm(1.0) + tone_pcm(2.0) + silence_pcm(1.0)
        _feed(backend, pcm)
        finished = controller.finish()
        assert finished.state is SessionState.PROCESSING
        assert worker.sealed
        statuses: list[str] = []
        document, directory, crypto = _transcribe(controller, statuses)
        assert controller.state is SessionState.QUEUED
        assert statuses == [models.LIVE_ASSEMBLED_STATUS]
        assert read_transcript(directory, crypto) == document
        assert len(document.transcript_segments) == 1
        assert posts and all(s.transcript_words for w in posts for s in w)
        # the batch path over the SAME store yields the same document
        batch = transcribe_session(directory, crypto, MockSpeechProvider(), amplitude_vad)
        assert _strip_created(batch) == _strip_created(document)
        assert worker.buffers_cleared and not worker.models_loaded
        controller.discard()

    def test_finish_seals_only_and_the_last_flushed_chunk_is_in_the_tail(
        self, tmp_path: Path, no_batch_models: None
    ) -> None:
        pytest.importorskip("numpy")
        gate = threading.Event()
        provider = _BlockingProvider(gate)
        workers = _Workers(provider=provider)
        controller, backend = _controller(tmp_path, workers)
        start_unlinked(controller)
        worker = workers.last
        _feed(backend, tone_pcm(1.0) + silence_pcm(5.0))
        assert provider.entered.wait(5.0)  # blocked in the first window
        backend.feed(tone_pcm(0.5))  # a partial chunk, flushed by Finish
        started = time.perf_counter()
        finished = controller.finish()
        elapsed = time.perf_counter() - started
        assert finished.state is SessionState.PROCESSING
        # Finish does real disk I/O (the flush and the store footer): 0.32 s
        # once on a shared CI runner (2026-10-03). Waiting on the gated worker
        # instead would take the 10 s stop timeout, or never return.
        assert elapsed < 2.0
        assert worker.sealed and worker.running  # sealed, NOT drained
        gate.set()
        statuses: list[str] = []
        document, _directory, _crypto = _transcribe(controller, statuses)
        assert statuses == [models.LIVE_ASSEMBLED_STATUS]
        last = document.transcript_segments[-1]
        assert last.end_seconds == pytest.approx(6.5, abs=0.15)
        assert last.transcript_words
        controller.discard()

    @pytest.mark.parametrize("prepare", ["recording", "paused", "processing", "failed"])
    def test_discard_clears_the_attached_worker_before_the_key_is_deleted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, prepare: str
    ) -> None:
        pytest.importorskip("numpy")
        posts: list[tuple[TranscriptSegment, ...]] = []
        workers = _Workers(on_window=posts.append)
        controller, backend = _controller(tmp_path, workers)
        session = start_unlinked(controller)
        worker = workers.last
        session_dir = tmp_path / session.session_id
        _feed(backend, silence_pcm(0.5) + tone_pcm(2.0))
        if prepare == "paused":
            controller.pause()
        elif prepare == "processing":
            assert controller.finish().state is SessionState.PROCESSING
        elif prepare == "failed":
            backend.fail(DeviceLostError("usb yanked"))
            _wait_for_state(controller, SessionState.FAILED)
        observed: list[tuple[bool, bool, bool]] = []
        real_discard = session_mod.discard_session

        def observing(directory: Path, crypto: SessionCrypto | None) -> None:
            observed.append(
                (worker.running, worker.buffers_cleared, (session_dir / KEY_FILENAME).exists())
            )
            real_discard(directory, crypto)

        monkeypatch.setattr(session_mod, "discard_session", observing)
        posted_before = len(posts)
        discarded = controller.discard()
        assert discarded.state is SessionState.DISCARDED
        # at the moment the key was destroyed: worker joined, buffers gone, key present
        assert observed == [(False, True, True)]
        assert not (session_dir / KEY_FILENAME).exists()
        assert worker.stopped
        time.sleep(0.05)
        assert len(posts) == posted_before  # no late live-view update

    @pytest.mark.parametrize("prepare", ["recording", "paused", "processing"])
    def test_a_stop_timeout_refuses_discard_keeps_the_key_then_succeeds(
        self, tmp_path: Path, prepare: str
    ) -> None:
        """Peer round 9 PR-MED-017 (C7, fail closed): a Discard whose live
        worker cannot be confirmed cleared is REFUSED before the key goes —
        the session is routed to FAILED (recoverable, key + chunks kept), the
        timeout is logged, and the same Discard succeeds once the worker has
        cleared itself."""
        pytest.importorskip("numpy")
        gate = threading.Event()
        provider = _BlockingProvider(gate)
        workers = _Workers(provider=provider, stop_timeout=0.2)
        logger = logging.getLogger("test-live-session-timeout")
        records = _Records()
        logger.addHandler(records)
        logger.setLevel(logging.INFO)
        try:
            controller, backend = _controller(tmp_path, workers, logger)
            session = start_unlinked(controller)
            worker = workers.last
            _feed(backend, tone_pcm(1.0) + silence_pcm(5.0))
            assert provider.entered.wait(5.0)
            if prepare == "paused":
                controller.pause()
            elif prepare == "processing":
                assert controller.finish().state is SessionState.PROCESSING
            key_path = tmp_path / session.session_id / KEY_FILENAME
            with pytest.raises(SessionActivityError, match="has not stopped yet"):
                controller.discard()
            assert key_path.is_file()  # the key stayed
            assert controller.state is SessionState.FAILED  # recoverable, Discard legal
            assert worker.running and worker.stopped  # stopping, NOT counted as cleared
            timeouts = [m for m in records.messages if "live_transcriber_stop_timeout" in m]
            assert len(timeouts) == 1
            assert f"session_id={session.session_id}" in timeouts[0]
            assert controller.reserved_session_ids() == frozenset()  # reservation released
            gate.set()
            _wait(lambda: not worker.running)
            assert worker.buffers_cleared  # the daemon worker cleared itself
            discarded = controller.discard()  # the retry succeeds
            assert discarded.state is SessionState.DISCARDED
            assert not key_path.exists()
        finally:
            logger.removeHandler(records)

    def test_a_stop_timeout_refuses_complete_and_keeps_the_session_queued(
        self, tmp_path: Path
    ) -> None:
        """PR-MED-017, the Complete shape: an unclaimed worker still
        transcribing its tail cannot be confirmed cleared, so every Complete
        path refuses and the session stays QUEUED with its key; once the
        worker exits the same Complete succeeds."""
        pytest.importorskip("numpy")
        gate = threading.Event()
        provider = _BlockingProvider(gate)
        workers = _Workers(provider=provider, stop_timeout=0.2)
        controller, backend = _controller(tmp_path, workers)
        session = start_unlinked(controller)
        worker = workers.last
        _feed(backend, silence_pcm(0.5) + tone_pcm(1.0))
        controller.finish()  # seals: the tail window blocks in the provider
        controller.transcribe(
            lambda directory, crypto: transcribe_session(
                directory, crypto, MockSpeechProvider(), amplitude_vad
            )
        )
        assert controller.state is SessionState.QUEUED
        assert provider.entered.wait(5.0) and worker.running
        key_path = tmp_path / session.session_id / KEY_FILENAME
        with pytest.raises(SessionActivityError, match="has not stopped yet"):
            controller.complete()
        assert controller.state is SessionState.QUEUED and key_path.is_file()
        lease = controller.begin_generation()
        with pytest.raises(SessionActivityError, match="has not stopped yet"):
            controller.complete_without_note(lease)
        assert controller.generating  # the lease is kept on failure
        controller.end_generation(lease)
        with pytest.raises(SessionActivityError, match="has not stopped yet"):
            controller.complete_deleting_saved_note()
        assert controller.state is SessionState.QUEUED and key_path.is_file()
        gate.set()
        _wait(lambda: not worker.running)
        completed = controller.complete()
        assert completed.state is SessionState.WRITTEN
        assert not key_path.exists()

    def test_capture_failure_stops_the_attached_worker(self, tmp_path: Path) -> None:
        pytest.importorskip("numpy")
        workers = _Workers()
        controller, backend = _controller(tmp_path, workers)
        start_unlinked(controller)
        worker = workers.last
        _feed(backend, tone_pcm(1.0))
        backend.fail(DeviceLostError("usb yanked"))
        _wait_for_state(controller, SessionState.FAILED)
        _wait(lambda: not worker.running)
        assert worker.stopped and worker.buffers_cleared
        controller.discard()

    def test_footer_failure_enters_failed_and_stops_the_worker(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pytest.importorskip("numpy")
        workers = _Workers()
        controller, backend = _controller(tmp_path, workers)
        session = start_unlinked(controller)
        worker = workers.last
        _feed(backend, tone_pcm(1.0))
        monkeypatch.setattr(
            SessionChunkStore,
            "finish",
            lambda self: (_ for _ in ()).throw(StoreWriteError("disk full at footer")),
        )
        assert controller.finish().state is SessionState.FAILED
        assert worker.stopped and not worker.sealed
        _wait(lambda: not worker.running)
        assert worker.buffers_cleared
        controller.discard()
        assert not (tmp_path / session.session_id / KEY_FILENAME).exists()

    def test_retire_on_start_refuses_while_a_timed_out_failure_left_a_worker_uncleared(
        self, tmp_path: Path
    ) -> None:
        """PR-MED-017, the retirement shape: a FAILED session whose worker
        could not be confirmed cleared refuses the Start that would retire it
        (handle and in-memory crypto kept); once the worker exits the same
        Start retires it and attaches a NEW worker to the new session."""
        pytest.importorskip("numpy")
        gate = threading.Event()
        provider = _BlockingProvider(gate)
        workers = _Workers(provider=provider, stop_timeout=0.2)
        logger = logging.getLogger("test-live-session-retire")
        records = _Records()
        logger.addHandler(records)
        logger.setLevel(logging.INFO)
        try:
            controller, backend = _controller(tmp_path, workers, logger)
            failed = start_unlinked(controller)
            first = workers.last
            _feed(backend, tone_pcm(1.0) + silence_pcm(5.0))
            assert provider.entered.wait(5.0)
            backend.fail(DeviceLostError("usb yanked"))
            _wait_for_state(controller, SessionState.FAILED)
            assert first.running  # the in-lock stop timed out: still attached
            assert len([m for m in records.messages if "stop_timeout" in m]) == 1
            with pytest.raises(SessionActivityError, match="has not stopped yet"):
                start_unlinked(controller)  # retirement refused: the worker is uncleared
            assert len(workers.built) == 1  # no new worker was built
            assert controller.state is SessionState.FAILED  # the session is still tracked
            assert (tmp_path / failed.session_id / KEY_FILENAME).is_file()
            assert len([m for m in records.messages if "stop_timeout" in m]) == 2
            gate.set()
            _wait(lambda: not first.running)
            assert first.buffers_cleared
            start_unlinked(controller)  # FAILED -> retired; a NEW worker for the new session
            second = workers.last
            assert second is not first and second.running
            controller.discard()
            assert not second.running and second.buffers_cleared
        finally:
            logger.removeHandler(records)

    def test_pause_and_resume_gate_the_worker(self, tmp_path: Path, no_batch_models: None) -> None:
        pytest.importorskip("numpy")
        workers = _Workers()
        controller, backend = _controller(tmp_path, workers)
        start_unlinked(controller)
        worker = workers.last
        _feed(backend, silence_pcm(1.0))
        controller.pause()
        assert worker.paused
        _feed(backend, tone_pcm(1.0))  # dropped by the capture worker's gate
        controller.resume()
        assert not worker.paused
        assert worker.failed_reason is None
        _feed(backend, tone_pcm(2.0) + silence_pcm(1.0))
        assert controller.finish().state is SessionState.PROCESSING
        statuses: list[str] = []
        document, _directory, _crypto = _transcribe(controller, statuses)
        assert statuses == [models.LIVE_ASSEMBLED_STATUS]
        assert len(document.transcript_segments) == 1
        assert document.transcript_segments[0].start_seconds == pytest.approx(1.0, abs=0.15)
        controller.discard()

    def test_claim_is_legal_only_inside_a_transcription_run(self, tmp_path: Path) -> None:
        pytest.importorskip("numpy")
        workers = _Workers()
        controller, backend = _controller(tmp_path, workers)
        start_unlinked(controller)
        worker = workers.last
        with pytest.raises(SessionActivityError):
            controller.claim_live_transcriber()  # RECORDING
        _feed(backend, tone_pcm(1.0))
        controller.finish()
        with pytest.raises(SessionActivityError):
            controller.claim_live_transcriber()  # PROCESSING but no run
        claims: list[Any] = []

        def callable_(directory: Path, crypto: SessionCrypto) -> None:
            claims.append(controller.claim_live_transcriber())
            claims.append(controller.claim_live_transcriber())
            assert worker.stop()

        controller.transcribe(callable_)
        assert claims == [worker, None]
        controller.discard()

    def test_a_transcriber_failure_after_the_claim_leaves_nothing_attached(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, no_batch_models: None
    ) -> None:
        pytest.importorskip("numpy")
        workers = _Workers()
        controller, backend = _controller(tmp_path, workers)
        session = start_unlinked(controller)
        worker = workers.last
        _feed(backend, silence_pcm(0.5) + tone_pcm(1.0))
        controller.finish()
        monkeypatch.setattr(
            models,
            "write_transcript",
            lambda *a, **k: (_ for _ in ()).throw(StoreWriteError("disk full")),
        )
        statuses: list[str] = []
        with pytest.raises(StoreWriteError):
            _transcribe(controller, statuses)
        assert controller.state is SessionState.FAILED
        assert worker.stopped and worker.buffers_cleared
        # nothing attached: Discard has no worker to wait for and the key goes
        controller.discard()
        assert not (tmp_path / session.session_id / KEY_FILENAME).exists()

    def test_a_tee_exception_never_reaches_the_capture_failure_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, batch_stubs: type[_StubWhisper]
    ) -> None:
        pytest.importorskip("numpy")
        workers = _Workers()
        controller, backend = _controller(tmp_path, workers)
        start_unlinked(controller)
        worker = workers.last
        assert controller.live_transcription_attached and controller.live_failure is None

        def broken_feed(data: bytes) -> None:
            raise RuntimeError("tee broke")

        monkeypatch.setattr(worker, "feed", broken_feed)
        _feed(backend, silence_pcm(0.5) + tone_pcm(1.0))
        _wait(lambda: worker.failed_reason is not None)
        time.sleep(0.05)
        assert controller.state is SessionState.RECORDING  # capture unaffected
        failure = worker.failed_reason
        assert failure is not None and failure.kind == LiveFailureKind.WORKER_ERROR
        assert "RuntimeError: tee broke" in failure.detail
        # Task 4.5: the controller surfaces it (the panel's "spoken pause
        # unavailable" line) while the worker stays attached until Finish.
        assert controller.live_failure == failure
        assert controller.live_transcription_attached
        assert controller.finish().state is SessionState.PROCESSING
        statuses: list[str] = []
        document, directory, crypto = _transcribe(controller, statuses)
        assert statuses[0].startswith(models.LIVE_FALLBACK_STATUS[LiveFailureKind.WORKER_ERROR])
        assert "tee broke" in statuses[0]
        assert batch_stubs.constructed == ["mock-batch"]  # the batch closure ran
        assert document.model_name == "mock-batch"
        assert len(document.transcript_segments) == 1  # the store held every chunk
        assert read_transcript(directory, crypto) == document
        controller.discard()

    @pytest.mark.parametrize("with_worker", [True, False])
    def test_a_store_exception_still_fails_the_session_through_the_tee(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, with_worker: bool
    ) -> None:
        """The tee's OTHER exception path: disk full in ``append_chunk`` must
        reach ``CaptureWorker._fail`` exactly as before the tee — with a live
        worker attached and without one (the store method resolved per call,
        so this class-level patch after Start is honoured)."""
        pytest.importorskip("numpy")
        workers = _Workers() if with_worker else None
        controller, backend = _controller(tmp_path, workers)
        session = start_unlinked(controller)
        monkeypatch.setattr(
            SessionChunkStore,
            "append_chunk",
            lambda self, data: (_ for _ in ()).throw(StoreWriteError("disk full")),
        )
        _feed(backend, tone_pcm(1.0))
        _wait_for_state(controller, SessionState.FAILED)
        assert (tmp_path / session.session_id / KEY_FILENAME).is_file()  # recoverable
        if workers is not None:
            worker = workers.last
            _wait(lambda: not worker.running)
            assert worker.stopped and worker.buffers_cleared
        controller.discard()

    def test_a_model_load_failure_falls_back_with_its_reason(
        self, tmp_path: Path, batch_stubs: type[_StubWhisper]
    ) -> None:
        pytest.importorskip("numpy")

        def broken() -> Any:
            raise RuntimeError("no snapshot")

        workers = _Workers(provider_factory=broken)
        controller, backend = _controller(tmp_path, workers)
        start_unlinked(controller)
        worker = workers.last
        _feed(backend, silence_pcm(0.5) + tone_pcm(1.0))
        _wait(lambda: worker.failed_reason is not None)
        assert controller.state is SessionState.RECORDING  # the consultation continues
        assert controller.finish().state is SessionState.PROCESSING
        statuses: list[str] = []
        document, _directory, _crypto = _transcribe(controller, statuses)
        assert statuses[0].startswith(models.LIVE_FALLBACK_STATUS[LiveFailureKind.MODEL_LOAD])
        assert "no snapshot" in statuses[0]
        assert not worker.models_loaded and worker.buffers_cleared
        assert batch_stubs.constructed == ["mock-batch"]
        assert len(document.transcript_segments) == 1
        controller.discard()

    def test_without_a_factory_the_batch_path_runs_as_today(
        self, tmp_path: Path, batch_stubs: type[_StubWhisper]
    ) -> None:
        pytest.importorskip("numpy")
        controller, backend = _controller(tmp_path, None)
        start_unlinked(controller)
        _feed(backend, silence_pcm(0.5) + tone_pcm(1.0))
        controller.finish()
        statuses: list[str] = []
        document, _directory, _crypto = _transcribe(controller, statuses)
        assert statuses == []
        assert batch_stubs.constructed == ["mock-batch"]
        assert len(document.transcript_segments) == 1
        controller.discard()

    @pytest.mark.parametrize(
        "complete", ["complete", "complete_without_note", "complete_deleting_saved_note"]
    )
    def test_complete_stops_an_unclaimed_worker_before_the_key_is_deleted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, complete: str
    ) -> None:
        """Round 7 MED-001: a transcriber callable that never claims the
        worker (not the shipped one) leaves it attached at QUEUED holding its
        plaintext products; every Complete path stops it BEFORE
        ``complete_session`` destroys the key."""
        pytest.importorskip("numpy")
        workers = _Workers()
        controller, backend = _controller(tmp_path, workers)
        session = start_unlinked(controller)
        worker = workers.last
        _feed(backend, silence_pcm(0.5) + tone_pcm(1.0))
        controller.finish()
        # a non-claiming callable: writes a document itself, leaves the worker
        controller.transcribe(
            lambda directory, crypto: transcribe_session(
                directory, crypto, MockSpeechProvider(), amplitude_vad
            )
        )
        assert controller.state is SessionState.QUEUED
        _wait(lambda: not worker.running)  # sealed tail finished; result retained
        assert not worker.buffers_cleared  # the undrained result is plaintext
        observed: list[bool] = []
        real_complete = session_mod.complete_session

        def observing(directory: Path, crypto: SessionCrypto, **kwargs: Any) -> Any:
            observed.append(worker.buffers_cleared)
            return real_complete(directory, crypto, **kwargs)

        monkeypatch.setattr(session_mod, "complete_session", observing)
        if complete == "complete":
            controller.complete()
        elif complete == "complete_without_note":
            lease = controller.begin_generation()
            controller.complete_without_note(lease)
        else:
            controller.complete_deleting_saved_note()
        assert controller.state is SessionState.IDLE
        assert observed == [True]  # cleared BEFORE the key was destroyed
        assert not (tmp_path / session.session_id / KEY_FILENAME).exists()

    def test_a_start_failure_stops_a_loading_worker_with_the_short_bound(
        self, tmp_path: Path
    ) -> None:
        """Round 7 LOW-002: Start fails after the live worker started (the
        device cannot be opened) — the cleanup under the lock waits the short
        in-lock bound, not the 10 s Discard bound, and the worker (holding no
        audio yet) clears itself when its load returns."""
        gate = threading.Event()

        def blocked_provider() -> Any:
            gate.wait()
            return MockSpeechProvider()

        workers = _Workers(provider_factory=blocked_provider)
        controller, _backend = _controller(tmp_path, workers)
        started = time.perf_counter()
        with pytest.raises(DeviceLostError):
            start_unlinked(controller, 99)  # no such device: the capture stream fails to open
        elapsed = time.perf_counter() - started
        assert elapsed < 5.0  # the 1 s in-lock bound, not LIVE_STOP_TIMEOUT_SECONDS
        assert controller.state is SessionState.IDLE
        assert list(tmp_path.iterdir()) == []
        worker = workers.last
        assert worker.stopped
        gate.set()
        _wait(lambda: not worker.running)
        assert worker.buffers_cleared

    def test_a_slow_model_load_never_fails_capture(
        self, tmp_path: Path, no_batch_models: None
    ) -> None:
        """Installation plan round 35 MED-001: the live worker loads its
        models on its own thread, so capture never waits on it — five seconds
        of audio fed while the load is blocked are all in the encrypted store
        before the load is released (round 38 PR-LOW-B01), the session
        stays RECORDING, and the worker catches up from its queue once the
        load returns. (The mock backend has no PortAudio callback, so this
        pins the controller's half: nothing on the capture path waits for
        the load; the interpreter-lock half is ``ml_warmup``'s.)"""
        pytest.importorskip("numpy")
        gate = threading.Event()
        loading = threading.Event()

        def slow_provider() -> Any:
            loading.set()
            gate.wait()
            return MockSpeechProvider()

        workers = _Workers(provider_factory=slow_provider)
        controller, backend = _controller(tmp_path, workers)
        session = start_unlinked(controller)
        worker = workers.last
        pcm = silence_pcm(1.0) + tone_pcm(2.0) + silence_pcm(2.0)
        expected = [pcm[i : i + CHUNK_BYTES] for i in range(0, len(pcm), CHUNK_BYTES)]
        session_dir = tmp_path / session.session_id
        crypto = unwrap_key_from_file(session_dir)

        def stored() -> list[bytes]:
            return list(iter_chunks(session_dir / "audio.enc", crypto))

        try:
            assert loading.wait(5.0)
            _feed(backend, pcm)
            # Round 38 PR-LOW-B01: every chunk reaches ENCRYPTED STORAGE while
            # the load is still blocked (bounded wait, the gate still closed).
            _wait(lambda: len(stored()) == len(expected))
            assert not gate.is_set()
            assert stored() == expected
            assert controller.state is SessionState.RECORDING
            assert worker.running and not worker.models_loaded
            assert worker.failed_reason is None
        finally:
            gate.set()
        finished = controller.finish()
        assert finished.state is SessionState.PROCESSING
        statuses: list[str] = []
        document, _directory, _crypto = _transcribe(controller, statuses)
        assert statuses == [models.LIVE_ASSEMBLED_STATUS]  # no fallback was needed
        assert len(document.transcript_segments) == 1
        controller.discard()

    def test_a_factory_returning_none_records_without_a_worker(
        self, tmp_path: Path, batch_stubs: type[_StubWhisper]
    ) -> None:
        """Round 35 MED-001: the window's factory returns None while the
        import warm-up runs (since round 36, a Start admitted only after the
        60 s hold) — that Start records without a live worker (one
        metadata line), and Finish runs the batch path with no fallback line."""
        pytest.importorskip("numpy")
        logger = logging.getLogger("test-live-session-not-attached")
        records = _Records()
        logger.addHandler(records)
        logger.setLevel(logging.INFO)
        try:
            controller, backend = _controller(tmp_path, None, logger)
            controller.set_live_transcriber_factory(lambda: None)
            session = start_unlinked(controller)
            assert controller.state is SessionState.RECORDING
            assert not controller.live_transcription_attached
            assert (
                f"live_transcriber session_id={session.session_id} state=not_attached"
                in records.messages
            )
            _feed(backend, silence_pcm(0.5) + tone_pcm(1.0))
            controller.finish()
            statuses: list[str] = []
            document, _directory, _crypto = _transcribe(controller, statuses)
            assert statuses == []
            assert batch_stubs.constructed == ["mock-batch"]
            assert len(document.transcript_segments) == 1
            controller.discard()
        finally:
            logger.removeHandler(records)

    @pytest.mark.parametrize(
        ("failure", "error_code", "detail_code"),
        [
            (
                CaptureOverflowError(
                    "device reported dropped frames (status: SECRET-TEXT)",
                    detail_code="status_input_overflow",
                ),
                "CaptureOverflowError",
                "status_input_overflow",
            ),
            (
                DeviceLostError("SECRET-TEXT", detail_code="stream_ended"),
                "DeviceLostError",
                "stream_ended",
            ),
            (StoreWriteError("SECRET-TEXT disk full"), "StoreWriteError", "none"),
        ],
        ids=["overflow", "device-lost", "store"],
    )
    def test_a_capture_failure_logs_its_type_name_and_detail_code_only(
        self, tmp_path: Path, failure: Exception, error_code: str, detail_code: str
    ) -> None:
        """Round 35 MED-001: the line that was missing from the installed
        app's log — the failure's type name and fixed detail word, before
        the session's transition to failed; never the message."""
        logger = logging.getLogger("test-live-session-capture-failure")
        records = _Records()
        logger.addHandler(records)
        logger.setLevel(logging.INFO)
        try:
            controller, backend = _controller(tmp_path, None, logger)
            session = start_unlinked(controller)
            backend.fail(failure)
            _wait_for_state(controller, SessionState.FAILED)
            line = (
                f"capture_failure detail_code={detail_code} error_code={error_code} "
                f"session_id={session.session_id} session_state=recording"
            )
            assert line in records.messages
            failed = (
                f"session_transition session_id={session.session_id} session_state=failed"
            )
            assert records.messages.index(line) < records.messages.index(failed)
            assert not any("SECRET" in m or "dropped" in m for m in records.messages)
            controller.discard()
        finally:
            logger.removeHandler(records)

    def test_the_factory_can_be_registered_after_construction(self, tmp_path: Path) -> None:
        pytest.importorskip("numpy")
        controller, backend = _controller(tmp_path, None)
        workers = _Workers()
        controller.set_live_transcriber_factory(workers)
        start_unlinked(controller)
        assert len(workers.built) == 1 and workers.last.running
        controller.discard()
        assert not workers.last.running


# ---------------------------------------------------------------------------
# Task 1.3 — build_transcriber / build_live_transcriber (no DPAPI)
# ---------------------------------------------------------------------------


def _make_store(session_dir: Path, pcm: bytes) -> SessionCrypto:
    session_dir.mkdir(parents=True, exist_ok=True)
    (session_dir / KEY_FILENAME).write_bytes(b"\0" * 64)
    crypto = SessionCrypto()
    store = SessionChunkStore.create(session_dir / "audio.enc", crypto, session_dir.name)
    for i in range(0, len(pcm), CHUNK_BYTES):
        store.append_chunk(pcm[i : i + CHUNK_BYTES])
    store.finish()
    return crypto


class TestBuildTranscriberLive:
    def test_a_drained_worker_writes_the_document_and_builds_no_batch_model(
        self, tmp_path: Path, no_batch_models: None
    ) -> None:
        pytest.importorskip("numpy")
        pcm = silence_pcm(0.5) + tone_pcm(1.0)
        session_dir = tmp_path / ("a" * 32)
        crypto = _make_store(session_dir, pcm)
        worker = LiveTranscriber(
            provider_factory=MockSpeechProvider, vad_factory=lambda: amplitude_vad
        )
        worker.start()
        for i in range(0, len(pcm), CHUNK_BYTES):
            worker.feed(pcm[i : i + CHUNK_BYTES])
        worker.seal()
        statuses: list[str] = []
        transcriber = models.build_transcriber(
            attribution=lambda: (None, None),
            live_source=lambda: worker,
            on_status=statuses.append,
        )
        document = transcriber(session_dir, crypto)
        assert statuses == [models.LIVE_ASSEMBLED_STATUS]
        assert document.session_id == session_dir.name
        assert read_transcript(session_dir, crypto) == document
        assert worker.buffers_cleared and not worker.models_loaded

    def test_a_failed_worker_reports_its_reason_and_runs_the_batch_closure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, batch_stubs: type[_StubWhisper]
    ) -> None:
        def broken() -> Any:
            raise RuntimeError("no snapshot")

        worker = LiveTranscriber(provider_factory=broken, vad_factory=lambda: amplitude_vad)
        worker.start()
        worker.seal()
        recorded: list[dict[str, Any]] = []

        def record(*args: Any, **kwargs: Any) -> Any:
            recorded.append(kwargs)
            return object()

        monkeypatch.setattr(models, "transcribe_session", record)
        statuses: list[str] = []
        transcriber = models.build_transcriber(
            attribution=lambda: (None, None),
            live_source=lambda: worker,
            on_status=statuses.append,
        )
        transcriber(tmp_path, SessionCrypto())
        assert len(statuses) == 1
        assert statuses[0].startswith(models.LIVE_FALLBACK_STATUS[LiveFailureKind.MODEL_LOAD])
        assert len(recorded) == 1 and recorded[0]["model_name"] == "mock-batch"
        assert batch_stubs.constructed == ["mock-batch"]
        assert worker.buffers_cleared

    def test_a_live_source_returning_none_is_todays_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, batch_stubs: type[_StubWhisper]
    ) -> None:
        recorded: list[dict[str, Any]] = []
        monkeypatch.setattr(
            models, "transcribe_session", lambda *a, **k: recorded.append(k) or object()
        )
        statuses: list[str] = []
        transcriber = models.build_transcriber(
            attribution=lambda: (None, None), live_source=lambda: None, on_status=statuses.append
        )
        transcriber(tmp_path, SessionCrypto())
        assert statuses == [] and len(recorded) == 1

    def test_an_unconfirmed_stop_refuses_the_batch_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Phase H round 24 LOW-002: `stop()`'s verdict is consulted — a
        worker that did not confirm its buffers cleared raises out of the
        transcriber instead of admitting the batch path beside a possibly
        alive worker (fail closed; unreachable by construction, pinned)."""

        class _Uncleared:
            def drain(self) -> Any:
                raise LiveTranscriptionFailed(LiveFailure(LiveFailureKind.MODEL_LOAD, "x"))

            def stop(self) -> bool:
                return False

        recorded: list[dict[str, Any]] = []
        monkeypatch.setattr(
            models, "transcribe_session", lambda *a, **k: recorded.append(k) or object()
        )
        statuses: list[str] = []
        transcriber = models.build_transcriber(
            attribution=lambda: (None, None),
            live_source=lambda: _Uncleared(),
            on_status=statuses.append,
        )
        with pytest.raises(LiveTranscriptionError, match="did not confirm"):
            transcriber(tmp_path, SessionCrypto())
        assert len(statuses) == 1 and recorded == []

    def test_build_live_transcriber_builds_its_models_on_the_worker_thread(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        pytest.importorskip("numpy")
        threads: list[str] = []

        class _ThreadRecordingWhisper(_StubWhisper):
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                threads.append(threading.current_thread().name)
                super().__init__(*args, **kwargs)

        _StubWhisper.constructed = []
        monkeypatch.setattr(models, "SileroVad", _StubVad)
        monkeypatch.setattr(models, "WhisperSpeechProvider", _ThreadRecordingWhisper)
        monkeypatch.setattr(models, "resolve_whisper_model", lambda *a, **k: "small")
        worker = models.build_live_transcriber(on_window=None, attribution=lambda: (None, None))
        assert threads == []  # nothing built at construction
        worker.start()
        _wait(lambda: worker.models_loaded)
        assert threads == ["scribe-live-transcriber"]
        assert _StubWhisper.constructed == ["small"]
        assert worker.stop()
        assert not worker.models_loaded

    def test_the_fallback_lines_name_every_reason(self) -> None:
        assert set(models.LIVE_FALLBACK_STATUS) == set(LiveFailureKind)
        for line in models.LIVE_FALLBACK_STATUS.values():
            assert line.endswith("transcribing after the recording instead.")
