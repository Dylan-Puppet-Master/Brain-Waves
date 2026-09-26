"""The week's statistics: how much each day asks of staff outside the cabins.

A button in the corner of the board opens them, zooming out of the corner the way a card
zooms out of its slot. Across the top is one tile per measure, each with its week total and
the shape of its week in miniature, and choosing a tile puts that measure on the chart
below: one column per weekday, with a line where the columns would stand if the week were
perfectly level. The Village Leaders use it to move acts off a crowded day.
"""

import math

from PySide6.QtCore import (
    QEasingCurve,
    QPointF,
    QRectF,
    QSize,
    Qt,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QKeySequence,
    QPainter,
    QPainterPath,
    QPen,
    QShortcut,
)
from PySide6.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from brainwaves.app.theme import tone
from brainwaves.model import DAY_COLUMNS, WEEKDAYS, Week
from brainwaves.stats import MEASURES, Spread, spread, spreads

SWITCH_MS = 280
# Columns are thin marks with air between them, however wide the chart grows.
BAR_SHARE = 0.44
MAX_BAR = 88
BAR_RADIUS = 6
# The most cards a column's tooltip names before it says how many more there are.
TOOLTIP_ROWS = 8


class StatsButton(QAbstractButton):
    """The corner of the board: opens the statistics, and sketches the week while it waits.

    The sketch is the measure the statistics were last left on, HEROes to begin with, so
    whatever was being balanced stays in view once they are closed. The statistics open on
    that measure again.
    """

    def __init__(self) -> None:
        super().__init__()
        self.measure = MEASURES[0]
        self.week: Week | None = None
        self.loads = [0] * DAY_COLUMNS
        self.setObjectName("statsButton")
        self.setCursor(Qt.PointingHandCursor)
        self.setAccessibleName("Week statistics")
        self.setAttribute(Qt.WA_Hover, True)
        self._sketch()

    def show_week(self, week: Week) -> None:
        """Sketch this week."""
        self.week = week
        self._sketch()

    def set_measure(self, key: str) -> None:
        """Sketch another measure: the one the statistics have just been switched to."""
        self.measure = next((m for m in MEASURES if m.key == key), MEASURES[0])
        self._sketch()

    def _sketch(self) -> None:
        loads = spread(self.week, self.measure).totals if self.week else [0] * DAY_COLUMNS
        self.setToolTip(
            f"Week statistics. The columns are {self.measure.units} on each weekday, "
            f"{', '.join(str(load) for load in loads)}."
        )
        if loads != self.loads:
            self.loads = loads
            self.update()

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt's name
        """About the size of a day heading."""
        return QSize(140, 62)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt's name
        """A tile like the day headings, titled, with five little columns along its foot."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        hovered = self.underMouse() or self.isDown()
        frame = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        painter.setPen(QPen(QColor(tone("ACCENT" if hovered else "LINE")), 1))
        painter.setBrush(QColor(tone("ACCENT_SOFT" if self.isDown() else "SURFACE")))
        painter.drawRoundedRect(frame, 8, 8)

        painter.setPen(QColor(tone("ACCENT" if hovered else "INK")))
        painter.setFont(_font(14, QFont.Bold))
        painter.drawText(QRectF(12, 7, self.width() - 24, 20), Qt.AlignLeft, "Week stats")

        area = QRectF(12, 30, self.width() - 24, self.height() - 38)
        _mini_columns(painter, area, self.loads, QColor(tone("ACCENT")))


class MeasureTab(QAbstractButton):
    """One measure's tile: its name, its week total, where it peaks, and its week in small."""

    def __init__(self, title: str) -> None:
        super().__init__()
        self.title = title
        self.spread: Spread | None = None
        self.setCheckable(True)
        self.setFocusPolicy(Qt.NoFocus)  # the panel takes the arrow keys for all of them
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setAccessibleName(title)

    def show_spread(self, spread: Spread) -> None:
        """Show this measure as it now stands."""
        self.spread = spread
        self.setAccessibleDescription(_summary(spread))
        self.update()

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt's name
        """Wide enough for the total and the sketch side by side."""
        return QSize(180, 88)

    def minimumSizeHint(self) -> QSize:  # noqa: N802 - Qt's name
        """Narrower than that still reads."""
        return QSize(120, 88)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt's name
        """The tile, lit in the accent while it is the one on the chart."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        chosen, hovered = self.isChecked(), self.underMouse()
        frame = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        line = "ACCENT" if chosen or hovered else "LINE"
        painter.setPen(QPen(QColor(tone(line)), 1.5 if chosen else 1))
        painter.setBrush(QColor(tone("ACCENT_SOFT" if chosen else "SURFACE")))
        painter.drawRoundedRect(frame, 10, 10)

        left, width = 14.0, self.width() - 28.0
        painter.setPen(QColor(tone("ACCENT_DARK" if chosen else "MUTED")))
        painter.setFont(_font(11, QFont.Bold, spacing=1))
        painter.drawText(QRectF(left, 10, width, 16), Qt.AlignLeft, self.title.upper())
        if self.spread is None:
            return
        total = str(self.spread.total)
        painter.setPen(QColor(tone("INK")))
        painter.setFont(_font(28, QFont.DemiBold))
        painter.drawText(QRectF(left, 26, width, 36), Qt.AlignLeft | Qt.AlignVCenter, total)
        number_width = QFontMetrics(painter.font()).horizontalAdvance(total)

        peak = _peak(self.spread)
        painter.setPen(QColor(tone("MUTED")))
        painter.setFont(_font(12))
        painter.drawText(QRectF(left, 62, width, 18), Qt.AlignLeft, peak)

        sketch_left = left + number_width + 16
        sketch_width = min(64.0, self.width() - 14 - sketch_left)
        if sketch_width >= 30:
            area = QRectF(self.width() - 14 - sketch_width, 32, sketch_width, 26)
            color = QColor(tone("ACCENT" if chosen else "FAINT"))
            _mini_columns(painter, area, self.spread.totals, color)


class BarChart(QWidget):
    """One measure, one column per weekday, and the level a perfectly even week would have.

    Changing the measure moves the columns and the scale from one to the other rather than
    redrawing them, so the eye can follow which days rose and which fell. Hovering a column
    lists the acts that make it up.
    """

    def __init__(self) -> None:
        super().__init__()
        self.spread: Spread | None = None
        self.days: list[str] = [""] * DAY_COLUMNS  # the subtitles under the day names
        # The columns as drawn this frame, and where a change of measure moves them from and to.
        self.shown = [0.0] * DAY_COLUMNS
        self.start = [0.0] * DAY_COLUMNS
        self.target = [0.0] * DAY_COLUMNS
        self.top, self.start_top, self.target_top = 4.0, 4.0, 4.0
        self.step = 1
        self.hover: int | None = None
        self.animation = QVariantAnimation(self)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setDuration(SWITCH_MS)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.animation.valueChanged.connect(self._step)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(240)

    def show_spread(self, spread: Spread, subtitles, animate: bool = True) -> None:
        """Put a measure on the chart, gliding from whatever was there, or not."""
        changed = self.spread is None or spread.totals != self.spread.totals
        self.spread = spread
        self.days = list(subtitles)
        self.setAccessibleDescription(_summary(spread))
        target_top, self.step = _scale(max(spread.totals, default=0))
        self.animation.stop()
        self.start, self.start_top = list(self.shown), self.top
        self.target, self.target_top = [float(v) for v in spread.totals], float(target_top)
        if animate and changed and self.isVisible():
            self.animation.start()
        else:
            self._step(1.0)

    def _step(self, value) -> None:
        amount = float(value)
        self.shown = [_mix(a, b, amount) for a, b in zip(self.start, self.target, strict=True)]
        self.top = _mix(self.start_top, self.target_top, amount)
        self.update()

    def _plot(self) -> QRectF:
        """Where the columns stand, inside the room the labels around them need.

        The scale goes on the left, the even line's name on the right, the values above the
        column tops and the days below.
        """
        return QRectF(52, 34, max(1.0, self.width() - 52 - 96), max(1.0, self.height() - 34 - 58))

    def _band(self, plot: QRectF) -> float:
        return plot.width() / DAY_COLUMNS

    def _y(self, plot: QRectF, value: float) -> float:
        return plot.bottom() - value / max(self.top, 1e-6) * plot.height()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt's name
        """The scale, the columns, the even line, the days, and the tooltip if one is up."""
        if self.spread is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        plot = self._plot()
        self._paint_scale(painter, plot)
        self._paint_columns(painter, plot)
        self._paint_even(painter, plot)
        self._paint_days(painter, plot)
        if not self.spread.total:
            painter.setPen(QColor(tone("MUTED")))
            painter.setFont(_font(15))
            painter.drawText(
                plot.adjusted(0, 0, 0, -plot.height() * 0.3),
                Qt.AlignCenter,
                f"No {self.spread.measure.units} on any day this week",
            )
        if self.hover is not None:
            self._paint_tooltip(painter, plot, self.hover)

    def _paint_scale(self, painter: QPainter, plot: QRectF) -> None:
        """Hairline gridlines at round numbers, labelled on the left."""
        painter.setFont(_font(12))
        grid = QColor(tone("LINE"))
        for tick in range(0, math.ceil(self.top) + 1, self.step):
            y = self._y(plot, tick)
            if y < plot.top() - 0.5:
                break
            painter.setPen(QPen(grid, 1))
            painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            painter.setPen(QColor(tone("MUTED")))
            painter.drawText(
                QRectF(0, y - 9, plot.left() - 12, 18), Qt.AlignRight | Qt.AlignVCenter, str(tick)
            )
        base = QColor(tone("FAINT"))
        painter.setPen(QPen(base, 1))
        painter.drawLine(QPointF(plot.left(), plot.bottom()), QPointF(plot.right(), plot.bottom()))

    def _paint_columns(self, painter: QPainter, plot: QRectF) -> None:
        """Each day's column, rounded at its top and square on the baseline, value on its cap."""
        band = self._band(plot)
        width = min(band * BAR_SHARE, MAX_BAR)
        for index, value in enumerate(self.shown):
            left = plot.left() + band * index + (band - width) / 2
            top = self._y(plot, value)
            height = plot.bottom() - top
            if height > 0.5:
                radius = min(BAR_RADIUS, width / 2, height)
                path = QPainterPath()
                path.addRoundedRect(QRectF(left, top, width, height + radius), radius, radius)
                painter.save()
                painter.setClipRect(
                    QRectF(left - 1, plot.top() - 40, width + 2, plot.bottom() - plot.top() + 40)
                )
                lit = "ACCENT_DARK" if index == self.hover else "ACCENT"
                painter.fillPath(path, QColor(tone(lit)))
                painter.restore()
            painter.setPen(QColor(tone("INK" if round(value) else "FAINT")))
            painter.setFont(_font(15, QFont.DemiBold))
            painter.drawText(
                QRectF(left - 20, top - 26, width + 40, 22),
                Qt.AlignHCenter | Qt.AlignBottom,
                str(round(value)),
            )

    def _paint_even(self, painter: QPainter, plot: QRectF) -> None:
        """The level every day would stand at if the week's total were shared out evenly."""
        if not self.spread.total:
            return
        share = self.spread.even_share
        y = self._y(plot, share)
        ink = QColor(tone("INK"))
        ink.setAlphaF(0.7)
        pen = QPen(ink, 1.5)
        pen.setDashPattern([4, 3])
        painter.setPen(pen)
        painter.drawLine(QPointF(plot.left(), y), QPointF(plot.right() + 6, y))
        painter.setPen(QColor(tone("MUTED")))
        painter.setFont(_font(10, QFont.Bold, spacing=1))
        label = QRectF(plot.right() + 12, y - 17, 84, 15)
        painter.drawText(label, Qt.AlignLeft | Qt.AlignBottom, "EVEN SPLIT")
        painter.setPen(QColor(tone("INK")))
        painter.setFont(_font(13, QFont.DemiBold))
        painter.drawText(label.translated(0, 16), Qt.AlignLeft | Qt.AlignTop, f"{share:.1f} a day")

    def _paint_days(self, painter: QPainter, plot: QRectF) -> None:
        """Each weekday's name under its column, and what else is on that day under that."""
        band = self._band(plot)
        for index, name in enumerate(WEEKDAYS):
            cell = QRectF(plot.left() + band * index + 4, plot.bottom() + 10, band - 8, 20)
            painter.setPen(QColor(tone("ACCENT" if index == self.hover else "INK")))
            painter.setFont(_font(14, QFont.DemiBold))
            painter.drawText(cell, Qt.AlignHCenter | Qt.AlignVCenter, name)
            subtitle = self.days[index] if index < len(self.days) else ""
            if subtitle:
                painter.setPen(QColor(tone("MUTED")))
                painter.setFont(_font(12))
                text = QFontMetrics(painter.font()).elidedText(
                    subtitle, Qt.ElideRight, int(cell.width())
                )
                painter.drawText(cell.translated(0, 20), Qt.AlignHCenter | Qt.AlignVCenter, text)

    def _paint_tooltip(self, painter: QPainter, plot: QRectF, index: int) -> None:
        """What makes up one day's column: which cabins, which acts, and what they asked for."""
        day = self.spread.days[index]
        measure = self.spread.measure
        parts = sorted(day.parts, key=lambda part: -part.count)
        shown = parts[:TOOLTIP_ROWS]
        rows = sum(2 if part.names else 1 for part in shown)
        width = 300.0
        height = 16 + 22 + 8 + max(1, rows) * 19 + (19 if len(parts) > len(shown) else 0) + 12

        band = self._band(plot)
        column_right = plot.left() + band * index + band / 2 + min(band * BAR_SHARE, MAX_BAR) / 2
        column_left = column_right - min(band * BAR_SHARE, MAX_BAR)
        left = column_right + 12
        if left + width > self.width() - 8:
            left = column_left - 12 - width
        left = max(8.0, left)
        top = self._y(plot, self.shown[index]) - 12
        top = min(max(8.0, top), self.height() - height - 8)
        box = QRectF(left, top, width, height)

        shadow = QColor(0, 0, 0, 40)
        painter.setPen(Qt.NoPen)
        painter.setBrush(shadow)
        painter.drawRoundedRect(box.translated(0, 3), 10, 10)
        painter.setPen(QPen(QColor(tone("LINE")), 1))
        painter.setBrush(QColor(tone("SURFACE")))
        painter.drawRoundedRect(box, 10, 10)

        inner = box.adjusted(14, 12, -14, -12)
        painter.setPen(QColor(tone("INK")))
        painter.setFont(_font(14, QFont.Bold))
        painter.drawText(
            QRectF(inner.left(), inner.top(), inner.width(), 22), Qt.AlignLeft, WEEKDAYS[index]
        )
        painter.setPen(QColor(tone("ACCENT")))
        painter.setFont(_font(13, QFont.DemiBold))
        painter.drawText(
            QRectF(inner.left(), inner.top(), inner.width(), 22),
            Qt.AlignRight,
            measure.say(day.total),
        )
        y = inner.top() + 30
        if not parts:
            painter.setPen(QColor(tone("MUTED")))
            painter.setFont(_font(13))
            painter.drawText(
                QRectF(inner.left(), y, inner.width(), 19), Qt.AlignLeft, "Nothing asked for"
            )
            return
        for part in shown:
            painter.setPen(QColor(tone("MUTED")))
            painter.setFont(_font(12, QFont.Bold))
            painter.drawText(
                QRectF(inner.left(), y, 44, 19), Qt.AlignLeft | Qt.AlignVCenter, part.cabin
            )
            painter.setPen(QColor(tone("INK")))
            painter.setFont(_font(13))
            count = str(part.count) if part.names else ""
            room = inner.width() - 44 - (24 if count else 0)
            title = QFontMetrics(painter.font()).elidedText(part.title, Qt.ElideRight, int(room))
            painter.drawText(
                QRectF(inner.left() + 44, y, room, 19), Qt.AlignLeft | Qt.AlignVCenter, title
            )
            if count:
                painter.setFont(_font(13, QFont.DemiBold))
                painter.drawText(
                    QRectF(inner.left(), y, inner.width(), 19),
                    Qt.AlignRight | Qt.AlignVCenter,
                    count,
                )
            y += 19
            if part.names:
                painter.setPen(QColor(tone("MUTED")))
                painter.setFont(_font(12))
                names = QFontMetrics(painter.font()).elidedText(
                    ", ".join(part.names), Qt.ElideRight, int(inner.width() - 44)
                )
                painter.drawText(
                    QRectF(inner.left() + 44, y, inner.width() - 44, 19),
                    Qt.AlignLeft | Qt.AlignVCenter,
                    names,
                )
                y += 19
        if len(parts) > len(shown):
            painter.setPen(QColor(tone("MUTED")))
            painter.setFont(_font(12))
            painter.drawText(
                QRectF(inner.left() + 44, y, inner.width() - 44, 19),
                Qt.AlignLeft | Qt.AlignVCenter,
                f"and {len(parts) - len(shown)} more",
            )

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 - Qt's name
        """A whole day's band is the column's hover target, not only the painted column."""
        plot = self._plot()
        point = event.position()
        index = None
        if (
            plot.left() <= point.x() < plot.right()
            and plot.top() - 30 <= point.y() <= self.height()
        ):
            index = int((point.x() - plot.left()) // self._band(plot))
        if index != self.hover:
            self.hover = index
            self.update()

    def leaveEvent(self, event) -> None:  # noqa: N802 - Qt's name
        """Nothing is pointed at."""
        super().leaveEvent(event)
        if self.hover is not None:
            self.hover = None
            self.update()


class StatsPanel(QFrame):
    """The statistics as a sheet the board zooms into. Esc, or Close, zooms back out."""

    rejected = Signal()
    measure_changed = Signal(str)

    def __init__(self, measure: str = MEASURES[0].key, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("statsPanel")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setFocusPolicy(Qt.StrongFocus)
        self.spreads: list[Spread] = []
        self.subtitles: list[str] = []
        keys = [m.key for m in MEASURES]
        self.current = keys.index(measure) if measure in keys else 0

        self.where = QLabel("")
        self.where.setObjectName("sectionTitle")
        title = QLabel("How the week's load falls")
        title.setObjectName("statsTitle")
        close = QPushButton("Close")
        close.setObjectName("quiet")
        close.setToolTip("Esc")
        close.setFocusPolicy(Qt.NoFocus)
        close.clicked.connect(self.rejected)
        heading = QVBoxLayout()
        heading.setSpacing(2)
        heading.addWidget(self.where)
        heading.addWidget(title)
        top = QHBoxLayout()
        top.addLayout(heading, 1)
        top.addWidget(close, 0, Qt.AlignTop)

        self.tabs = [MeasureTab(measure.title) for measure in MEASURES]
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        tabs = QHBoxLayout()
        tabs.setSpacing(10)
        for index, tab in enumerate(self.tabs):
            self.group.addButton(tab, index)
            tabs.addWidget(tab)
        self.tabs[self.current].setChecked(True)
        self.group.idClicked.connect(self.choose)

        self.chart = BarChart()
        self.insight = QLabel("")
        self.insight.setObjectName("statsInsight")
        self.insight.setWordWrap(True)
        self.insight.setTextFormat(Qt.RichText)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(16)
        layout.addLayout(top)
        layout.addLayout(tabs)
        layout.addWidget(self.chart, 1)
        layout.addWidget(self.insight)

        shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)
        shortcut.setContext(Qt.WidgetWithChildrenShortcut)
        shortcut.activated.connect(self.rejected)

    @property
    def measure(self) -> str:
        """The key of the measure on the chart."""
        return MEASURES[self.current].key

    def show_week(self, week: Week) -> None:
        """Count the week again and show it, the chart gliding to any change."""
        self.where.setText(f"{week.id} · STATISTICS")
        self.spreads = spreads(week)
        self.subtitles = [day.subtitle for day in week.days[:DAY_COLUMNS]]
        for tab, counted in zip(self.tabs, self.spreads, strict=True):
            tab.show_spread(counted)
        self._show(animate=True)

    def choose(self, index: int) -> None:
        """Put another measure on the chart."""
        index %= len(MEASURES)
        if index == self.current and self.tabs[index].isChecked():
            return
        self.current = index
        self.tabs[index].setChecked(True)
        self._show(animate=True)
        self.measure_changed.emit(self.measure)

    def _show(self, animate: bool) -> None:
        if not self.spreads:
            return
        spread = self.spreads[self.current]
        self.chart.show_spread(spread, self.subtitles, animate)
        self.insight.setText(_insight(spread))

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt's name
        """Left and right step through the measures; 1 to 5 jump straight to one."""
        key = event.key()
        if key in (Qt.Key_Right, Qt.Key_Tab):
            self.choose(self.current + 1)
        elif key in (Qt.Key_Left, Qt.Key_Backtab):
            self.choose(self.current - 1)
        elif Qt.Key_1 <= key < Qt.Key_1 + len(MEASURES):
            self.choose(key - Qt.Key_1)
        else:
            super().keyPressEvent(event)

    def focusNextPrevChild(self, forward: bool) -> bool:  # noqa: N802 - Qt's name
        """Tab steps through the measures rather than out of the panel."""
        return False


def _insight(spread: Spread) -> str:
    """What the chart says, in a sentence or two a Village Leader can act on."""
    measure = spread.measure
    if not spread.total:
        text = f"Nothing on the weekdays asks for {measure.units} yet."
    elif spread.gap <= 1:
        text = (
            f"<b>Nicely level.</b> No day is more than one {measure.unit} off another, "
            f"around {spread.even_share:.1f} a day."
        )
    else:
        busiest, quietest = spread.busiest, spread.quietest
        high, low = spread.totals[busiest[0]], spread.totals[quietest[0]]
        each = "" if len(busiest) == 1 else " each"
        most = f"<b>{_days(busiest)}</b> {_verb(busiest, 'carries', 'carry')} the most, "
        most += measure.say(high) + each
        if low:
            each = "" if len(quietest) == 1 else " each"
            least = f"<b>{_days(quietest)}</b> the least, {measure.say(low)}{each}"
        else:
            least = f"<b>{_days(quietest)}</b> {_verb(quietest, 'has', 'have')} none"
        text = f"{most}; {least}. An even week would be {spread.even_share:.1f} a day."
    if spread.unplaced:
        text += (
            f" {measure.say(spread.unplaced).capitalize()} more wait in Extra, not yet on a day."
        )
    return text


def _peak(spread: Spread) -> str:
    """Where a measure peaks, short enough for a tile."""
    busiest = spread.busiest
    if not busiest:
        return "None this week"
    high = spread.totals[busiest[0]]
    if len(busiest) == len(spread.days):
        return f"Level · {high} a day"
    return f"Peaks {', '.join(WEEKDAYS[i][:3] for i in busiest)} · {high}"


def _days(indices) -> str:
    """Weekdays by name, as a sentence lists them."""
    names = [WEEKDAYS[index] for index in indices]
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"


def _verb(indices, one: str, more: str) -> str:
    return one if len(indices) == 1 else more


def _summary(spread: Spread) -> str:
    """The chart as words, for a screen reader."""
    days = ", ".join(f"{name} {value}" for name, value in zip(WEEKDAYS, spread.totals, strict=True))
    return f"{spread.measure.title}: {spread.total} this week. {days}."


def _scale(peak: int) -> tuple[int, int]:
    """The top of the scale and the step between gridlines: round numbers, five or fewer."""
    if peak <= 4:
        return 4, 1
    for step in (1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000):
        if math.ceil(peak / step) <= 5:
            return math.ceil(peak / step) * step, step
    step = 10 ** math.ceil(math.log10(peak / 5))
    return math.ceil(peak / step) * step, step


def _mini_columns(painter: QPainter, area: QRectF, values, color: QColor) -> None:
    """A week in miniature: five columns scaled to the tallest, a sliver where one is empty."""
    count = len(values)
    gap = 3.0
    width = (area.width() - gap * (count - 1)) / count
    peak = max(max(values, default=0), 1)
    painter.save()
    painter.setPen(Qt.NoPen)
    for index, value in enumerate(values):
        height = max(2.0, area.height() * value / peak)
        shade = QColor(color)
        if not value:
            shade.setAlphaF(0.35)
        painter.setBrush(shade)
        left = area.left() + index * (width + gap)
        painter.drawRoundedRect(QRectF(left, area.bottom() - height, width, height), 1.5, 1.5)
    painter.restore()


def _font(pixels: int, weight=QFont.Normal, spacing: float = 0) -> QFont:
    font = QFont()
    font.setPixelSize(pixels)
    font.setWeight(weight)
    if spacing:
        font.setLetterSpacing(QFont.AbsoluteSpacing, spacing)
    return font


def _mix(start: float, end: float, amount: float) -> float:
    return start + (end - start) * amount
