"""The shell's icons, drawn in code (ui-refresh plan D12).

Five painter primitives — ``record`` (a ring round a dot), ``review`` (a page
with lines), ``past_sessions`` (a clock), ``recovery`` (a circular arrow) and
``settings`` (a gear) — and the app's own mark. Each is drawn with
``QPainterPath`` on a transparent ``QPixmap`` at 1x and 2x, in the colour the
caller takes from the theme's tokens, so the navigation rail re-tints them
when the Windows scheme changes. There is no file asset and no ``QtSvg``:
nothing to bundle, nothing for the installer to carry.

Every icon sits beside its text; no button is an icon alone. The painter is
always made as ``QPainter(pixmap)`` and closed with ``end()`` — never a
``.begin(`` call (``test_shadow_exits.py`` reserves that name).
``docs/design-system.md``'s "Surfaces & layout" section documents the rail that
shows them (ui-refresh plan Task 5.1).
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Final

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPainterPath, QPen, QPixmap

from scribe_desktop.ui import theme

ICON_NAMES: Final = ("record", "review", "past_sessions", "recovery", "settings")
# The device-pixel ratios each icon is drawn at (100 % and 200 % displays;
# Qt scales between them).
SCALES: Final = (1, 2)
# The window icon's logical sizes (title bar, taskbar, Alt+Tab, Explorer).
_APP_ICON_SIZES: Final = (16, 24, 32, 48, 64, 256)

_Draw = Callable[[QPainter, float, str], None]


def _stroke_width(size: float) -> float:
    return max(1.5, size / 12)


def _pen(colour: str, width: float) -> QPen:
    pen = QPen(theme.colour(colour))
    pen.setWidthF(width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


def _stroke(painter: QPainter, path: QPainterPath, colour: str, width: float) -> None:
    painter.setPen(_pen(colour, width))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(path)


def _fill(painter: QPainter, path: QPainterPath, colour: str) -> None:
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(theme.colour(colour))
    painter.drawPath(path)


def _circle(path: QPainterPath, centre: QPointF, radius: float) -> None:
    path.addEllipse(centre, radius, radius)


def _draw_record(painter: QPainter, size: float, colour: str) -> None:
    width = _stroke_width(size)
    centre = QPointF(size / 2, size / 2)
    ring = QPainterPath()
    _circle(ring, centre, size * 0.40 - width / 2)
    _stroke(painter, ring, colour, width)
    dot = QPainterPath()
    _circle(dot, centre, size * 0.18)
    _fill(painter, dot, colour)


def _draw_review(painter: QPainter, size: float, colour: str) -> None:
    width = _stroke_width(size)
    page = QPainterPath()
    page.addRoundedRect(
        QRectF(size * 0.22, size * 0.12, size * 0.56, size * 0.76), size * 0.08, size * 0.08
    )
    _stroke(painter, page, colour, width)
    lines = QPainterPath()
    for top, right in ((0.36, 0.66), (0.50, 0.66), (0.64, 0.56)):
        lines.moveTo(size * 0.34, size * top)
        lines.lineTo(size * right, size * top)
    _stroke(painter, lines, colour, width)


def _draw_past_sessions(painter: QPainter, size: float, colour: str) -> None:
    width = _stroke_width(size)
    centre = QPointF(size / 2, size / 2)
    face = QPainterPath()
    _circle(face, centre, size * 0.40 - width / 2)
    _stroke(painter, face, colour, width)
    hands = QPainterPath()
    hands.moveTo(centre.x(), centre.y() - size * 0.22)
    hands.lineTo(centre)
    hands.lineTo(centre.x() + size * 0.16, centre.y())
    _stroke(painter, hands, colour, width)


def _draw_recovery(painter: QPainter, size: float, colour: str) -> None:
    width = _stroke_width(size)
    radius = size * 0.30
    centre = QPointF(size / 2, size / 2)
    box = QRectF(centre.x() - radius, centre.y() - radius, radius * 2, radius * 2)
    # Three quarters of a turn, counter-clockwise from the top round to the
    # right-hand side, then an arrowhead pointing on round the turn (upwards).
    arc = QPainterPath()
    arc.arcMoveTo(box, 90)
    arc.arcTo(box, 90, 270)
    _stroke(painter, arc, colour, width)
    end_x = centre.x() + radius
    head = QPainterPath()
    head.moveTo(end_x, centre.y() - size * 0.16)
    head.lineTo(end_x - size * 0.13, centre.y() + size * 0.03)
    head.lineTo(end_x + size * 0.13, centre.y() + size * 0.03)
    head.closeSubpath()
    _fill(painter, head, colour)


def _draw_settings(painter: QPainter, size: float, colour: str) -> None:
    centre = QPointF(size / 2, size / 2)
    teeth = QPainterPath()
    for step in range(8):
        angle = math.radians(step * 45)
        cos, sin = math.cos(angle), math.sin(angle)
        teeth.moveTo(centre.x() + cos * size * 0.28, centre.y() - sin * size * 0.28)
        teeth.lineTo(centre.x() + cos * size * 0.40, centre.y() - sin * size * 0.40)
    _stroke(painter, teeth, colour, size * 0.14)
    body = QPainterPath()
    _circle(body, centre, size * 0.30)
    # The hole: under the odd-even rule the inner circle is left unfilled.
    body.setFillRule(Qt.FillRule.OddEvenFill)
    _circle(body, centre, size * 0.11)
    _fill(painter, body, colour)


def _draw_app_mark(painter: QPainter, size: float, colour: str) -> None:
    """The app's own mark: the record shape, light on an accent tile."""
    tile = QPainterPath()
    tile.addRoundedRect(QRectF(0, 0, size, size), size * 0.22, size * 0.22)
    _fill(painter, tile, theme.LIGHT.accent)
    width = _stroke_width(size)
    centre = QPointF(size / 2, size / 2)
    ring = QPainterPath()
    _circle(ring, centre, size * 0.30 - width / 2)
    _stroke(painter, ring, colour, width)
    dot = QPainterPath()
    _circle(dot, centre, size * 0.13)
    _fill(painter, dot, colour)


_DRAWINGS: Final[dict[str, _Draw]] = {
    "record": _draw_record,
    "review": _draw_review,
    "past_sessions": _draw_past_sessions,
    "recovery": _draw_recovery,
    "settings": _draw_settings,
}


def _paint(draw: _Draw, colour: str, size: int, scale: int) -> QPixmap:
    canvas = QPixmap(size * scale, size * scale)
    canvas.setDevicePixelRatio(scale)
    canvas.fill(Qt.GlobalColor.transparent)
    painter = QPainter(canvas)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        draw(painter, float(size), colour)
    finally:
        painter.end()
    return canvas


def pixmap(name: str, colour: str, size: int, scale: int = 1) -> QPixmap:
    """One of ``ICON_NAMES`` at ``size`` logical pixels and device-pixel ratio
    ``scale``, drawn in ``colour`` (a token's ``#rrggbb`` value)."""
    draw = _DRAWINGS.get(name)
    if draw is None:
        raise ValueError(f"unknown icon: {name}")
    return _paint(draw, colour, size, scale)


def icon(name: str, colour: str, size: int, *, checked: str | None = None) -> QIcon:
    """``name`` as an icon at every scale in ``SCALES``; with ``checked``, a
    second colour for a checked button (the rail's lit entry)."""
    result = QIcon()
    for scale in SCALES:
        result.addPixmap(pixmap(name, colour, size, scale), QIcon.Mode.Normal, QIcon.State.Off)
        if checked is not None:
            result.addPixmap(
                pixmap(name, checked, size, scale), QIcon.Mode.Normal, QIcon.State.On
            )
    return result


def app_icon() -> QIcon:
    """The window's icon: the app mark at the sizes Windows asks for. Fixed
    colours (the taskbar does not follow the app's scheme)."""
    result = QIcon()
    for size in _APP_ICON_SIZES:
        result.addPixmap(_paint(_draw_app_mark, theme.LIGHT.on_accent, size, 1))
    return result


__all__ = ["ICON_NAMES", "SCALES", "app_icon", "icon", "pixmap"]
