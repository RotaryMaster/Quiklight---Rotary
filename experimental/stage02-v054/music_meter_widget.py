"""Medidor musical Stage 02: 5 canais distinguíveis, limites editáveis na barra.

Componente isolado para inclusão posterior na GUI Stage 02 exata. Importar
somente a partir de um ambiente com PySide6; não escreve no TOML e não aciona
serviço. O host recebe valueChanged(key, value) e controla persistência.
"""
from __future__ import annotations

from pathlib import Path
import time

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

try:
    from .music_telemetry import (COLORS, LABELS_PT, MIN_MAX_FIELDS,
                                  ON_FIELDS, clamp_range, read_audio, request_audio)
except ImportError:  # módulo extraído na mesma pasta
    from music_telemetry import (COLORS, LABELS_PT, MIN_MAX_FIELDS,
                                 ON_FIELDS, clamp_range, read_audio, request_audio)


class LiveMusicMeter(QWidget):
    """Cinco linhas: bass, treble, volume, RPM estimado, reação após DSP.

    Cliques no interruptor ativam/desativam canal. Arrastar marcas de entrada
    mínima/saída máxima modifica exclusivamente os campos daquela linha.
    Duplo clique na barra restaura [0, 1]. A quinta barra é somente leitura.
    """
    valueChanged = Signal(str, object)
    dataAvailable = Signal(bool)

    LABEL_W = 158.0
    SWITCH_W = 25.0
    ROWS = 5
    MIN_GAP = 0.05

    def __init__(self, parent=None, runtime_dir: Path | None = None):
        super().__init__(parent)
        self._cfg: dict = {}
        self._levels: tuple[float, ...] = (0.0,) * 5
        self._available = False
        self._signature = None
        self._runtime_dir = Path(runtime_dir) if runtime_dir is not None else None
        self._last_request = 0.0
        self._drag: tuple[int, int] | None = None
        self.setMinimumHeight(238)
        self.setMouseTracking(True)
        self.setToolTip("Níveis reais: graves, agudos, volume, RPM sonoro e reação da luz")
        self._timer = QTimer(self)
        self._timer.setInterval(90)
        self._timer.timeout.connect(self._poll)

    def set_runtime_dir(self, runtime_dir: Path | None) -> None:
        self._runtime_dir = Path(runtime_dir) if runtime_dir is not None else None
        self._signature = None
        self._last_request = 0.0

    def set_config(self, config: dict) -> None:
        # Cópia: uma alteração local não modifica a configuração ativa.
        self._cfg = dict(config)
        self.update()

    def set_levels(self, values: tuple[float, ...] | None) -> None:
        # A GUI pode fornecer amostras por sinal; sem valores -> indisponível.
        from math import isfinite
        valid = (values is not None and len(values) == 5
                 and all(isfinite(x) for x in values))
        next_available = bool(valid)
        clamped = (tuple(max(0.0, min(1.0, x)) for x in values)
                   if valid else (0.0,) * 5)
        if next_available != self._available:
            self._available = next_available
            self.dataAvailable.emit(self._available)
        if clamped != self._levels or not next_available:
            self._levels = clamped
            self.update()

    def _poll(self) -> None:
        runtime = self._runtime_dir
        if runtime is None or not runtime.is_dir():
            self._signature = None
            if self._available:
                self.set_levels(None)
            return
        _, self._last_request = request_audio(runtime, last_request=self._last_request)
        frame = read_audio(runtime)
        if frame is None:
            self._signature = None
            if self._available:
                self.set_levels(None)
            return
        if frame.sequence == self._signature:
            return
        self._signature = frame.sequence
        self.set_levels(frame.levels)

    def showEvent(self, event):
        super().showEvent(event)
        self._timer.start()
        self._poll()

    def hideEvent(self, event):
        self._timer.stop()
        super().hideEvent(event)

    def _metrics(self):
        # Reserva legenda inferior de 20px.
        width = max(1.0, self.width() - self.LABEL_W - 12.0)
        row_h = max(24.0, (self.height() - 27.0) / 5.0)
        return width, row_h

    def _bar(self, index: int) -> QRectF:
        width, height = self._metrics()
        return QRectF(self.LABEL_W, 4.0 + index * height,
                      width, height - 9.0)

    def _pos_to_fraction(self, x: float) -> float:
        width, _ = self._metrics()
        return max(0.0, min(1.0, (x - self.LABEL_W) / width))

    def _row_at(self, y: float) -> int | None:
        _, row_h = self._metrics()
        i = int((y - 4.0) // row_h)
        return i if 0 <= i < 5 else None

    def _thresholds(self, i: int) -> tuple[float, float]:
        low_key, high_key = MIN_MAX_FIELDS[i]
        low = self._cfg.get(low_key, 0.0)
        high = self._cfg.get(high_key, 1.0)
        try:
            return clamp_range(float(low), float(high), gap=self.MIN_GAP)
        except (TypeError, ValueError):
            return 0.0, 1.0

    def paintEvent(self, _):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setFont(QFont(self.font().family(), 10))
        fg = self.palette().text().color()
        muted = QColor(fg)
        muted.setAlpha(150)

        for i, label in enumerate(LABELS_PT):
            bar = self._bar(i)
            on = True if i == 4 else bool(self._cfg.get(ON_FIELDS[i], True))
            level = self._levels[i] if self._available else 0.0
            if i < 4:
                sw = QRectF(1.5, bar.center().y() - 8, self.SWITCH_W, 16)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor("#33B974") if on else QColor("#737987"))
                painter.drawRoundedRect(sw, 8, 8)
                painter.setBrush(QColor("#FFFFFF"))
                painter.drawEllipse(QPointF(sw.left() + (17.5 if on else 7.0),
                                           sw.center().y()), 5.3, 5.3)

            painter.setPen(fg if on else muted)
            painter.drawText(QRectF(32, bar.top() - 1,
                                    self.LABEL_W - 36, bar.height() + 2),
                             Qt.AlignmentFlag.AlignVCenter |
                             Qt.AlignmentFlag.AlignLeft, label)

            bg = QColor(fg)
            bg.setAlpha(28)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(bg)
            painter.drawRoundedRect(bar, 5, 5)

            color = QColor(COLORS[i])
            if not on:
                color.setAlpha(90)
            painter.setBrush(color)
            if level > 0.001:
                painter.drawRoundedRect(
                    QRectF(bar.left(), bar.top(), max(2.0, bar.width()*level),
                           bar.height()), 4, 4)

            if i < 4:
                lo, hi = self._thresholds(i)
                dim = QColor("#000000")
                dim.setAlpha(105)
                painter.setBrush(dim)
                if lo > 0:
                    painter.drawRect(QRectF(bar.left(),bar.top(),
                                            bar.width()*lo,bar.height()))
                if hi < 1:
                    painter.drawRect(QRectF(bar.left()+bar.width()*hi,bar.top(),
                                            bar.width()*(1-hi),bar.height()))
                for val in (lo,hi):
                    xx=bar.left()+val*bar.width()
                    painter.setPen(QPen(QColor("#FFD45C"),2.2))
                    painter.drawLine(QPointF(xx,bar.top()-2),
                                     QPointF(xx,bar.bottom()+2))
                    painter.setPen(Qt.PenStyle.NoPen)
            painter.setPen(QColor("#F5F5F5") if level > 0.22 else fg)
            painter.drawText(bar.adjusted(4,0,-5,0),
                             Qt.AlignmentFlag.AlignRight |
                             Qt.AlignmentFlag.AlignVCenter,
                             f"{round(level*100)}%")

        painter.setPen(muted)
        message = ("Sem dados de áudio recentes"
                   if not self._available else
                   "Marcas amarelas: entrada mínima / saída máxima · duplo clique: restaurar")
        painter.drawText(QRectF(4,self.height()-21,self.width()-8,20),
                         Qt.AlignmentFlag.AlignCenter,message)
        painter.end()

    def _change(self,key:str,value) -> None:
        if self._cfg.get(key)==value:
            return
        self._cfg[key]=value
        self.valueChanged.emit(key,value)
        self.update()

    def _drag_to(self,x:float) -> None:
        if self._drag is None:
            return
        row,mark=self._drag
        low_key,high_key=MIN_MAX_FIELDS[row]
        low,high=self._thresholds(row)
        fraction=round(self._pos_to_fraction(x),3)
        if mark==0:
            self._change(low_key,min(fraction,high-self.MIN_GAP))
        else:
            self._change(high_key,max(fraction,low+self.MIN_GAP))

    def mousePressEvent(self,e):
        if e.button()!=Qt.MouseButton.LeftButton:
            return super().mousePressEvent(e)
        row=self._row_at(e.position().y())
        if row is None or row==4:
            return
        x=e.position().x()
        if x<self.SWITCH_W+4:
            k=ON_FIELDS[row]
            self._change(k,not bool(self._cfg.get(k,True)))
            return
        if x<self.LABEL_W:
            return
        lo,hi=self._thresholds(row)
        val=self._pos_to_fraction(x)
        self._drag=(row,0 if abs(val-lo)<=abs(val-hi) else 1)
        self._drag_to(x)
        e.accept()

    def mouseMoveEvent(self,e):
        if self._drag is not None:
            self._drag_to(e.position().x())
            e.accept()
            return
        row=self._row_at(e.position().y())
        active=(row is not None and row<4
                and (e.position().x()<self.SWITCH_W+4 or
                     e.position().x()>=self.LABEL_W))
        self.setCursor(Qt.CursorShape.SizeHorCursor
                       if row is not None and row<4 and
                       e.position().x()>=self.LABEL_W else
                       Qt.CursorShape.PointingHandCursor if active else
                       Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self,e):
        self._drag=None
        e.accept()

    def mouseDoubleClickEvent(self,e):
        row=self._row_at(e.position().y())
        if row is None or row==4 or e.position().x()<self.LABEL_W:
            return
        low_key,high_key=MIN_MAX_FIELDS[row]
        self._change(low_key,0.0)
        self._change(high_key,1.0)
        e.accept()
