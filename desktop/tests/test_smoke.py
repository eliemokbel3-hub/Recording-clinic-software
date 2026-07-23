"""Step 1 trivial smoke test: the package imports and exposes its entry points."""

from scribe_desktop import __version__, app, native_host


def test_package_imports() -> None:
    assert __version__
    assert callable(app.main)
    assert callable(native_host.main)
