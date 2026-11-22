"""QuikLight Stage 02: leitura segura de telemetria musical (Linux/Windows).

Compatível com o protocolo legado quiklight-audio.txt: cinco floats em [0, 1]
na ordem Graves, Agudos, Volume, RPM estimado e Reação da luz. Não gera amostras
fictícias e não usa dados RGB de QLV3 como se fossem áudio.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from pathlib import Path
import time
from typing import Optional

CHANNELS = ("bass", "treble", "volume", "rpm", "reaction")
LABELS_PT = ("Graves", "Agudos", "Volume", "Motor (RPM)", "Reação da luz")
COLORS = ("#4699F5", "#B27CEF", "#2FC49E", "#EF7763", "#E6BD49")

# Os quatro primeiros canais são entradas editáveis; reação é resultado DSP.
MIN_MAX_FIELDS = (
    ("music_in_bass", "music_out_bass"),
    ("music_in_treble", "music_out_treble"),
    ("music_in_vol", "music_out_vol"),
    ("music_in_rpm", "music_out_rpm"),
)
ON_FIELDS = ("music_on_bass", "music_on_treble", "music_on_vol", "music_on_rpm")


@dataclass(frozen=True)
class AudioFrame:
    levels: tuple[float, float, float, float, float]
    sequence: int  # assinatura mtime_ns, não sequência do DSP
    observed_at: float


def normalize(raw: str) -> Optional[tuple[float, float, float, float, float]]:
    """Lê exatamente as cinco primeiras amplitudes, recusando NaN/Inf e lixo."""
    values = raw.strip().split()
    if len(values) < 5:
        return None
    try:
        nums = tuple(float(x) for x in values[:5])
    except (TypeError, ValueError):
        return None
    if len(nums) != 5 or any(not isfinite(x) for x in nums):
        return None
    return tuple(max(0.0, min(1.0, x)) for x in nums)  # type: ignore[return-value]


def read_audio(runtime: Path, *, max_age: float = 2.0, now: float | None = None
              ) -> AudioFrame | None:
    """Somente leitura; não interpreta amostras antigas como nível atual."""
    source = Path(runtime) / "quiklight-audio.txt"
    try:
        st = source.stat()
        moment = time.time() if now is None else now
        age = moment - st.st_mtime
        if age < -1.0 or age > max_age or st.st_size > 512:
            return None
        raw = source.read_text(encoding="utf-8")
        vals = normalize(raw)
        if vals is None:
            return None
        return AudioFrame(vals, st.st_mtime_ns, moment)
    except (OSError, UnicodeError):
        return None


def request_audio(runtime: Path, *, now: float | None = None,
                  last_request: float = 0.0, minimum_interval: float = 1.5
                 ) -> tuple[bool, float]:
    """Solicita telemetria (want) sem tocar na configuração nem no serviço.

    O chamador decide se deve pedir dados. Requisita no máximo uma vez por
    intervalo; não cria diretório de runtime se ele não existir.
    """
    moment = time.monotonic() if now is None else now
    if last_request > 0 and moment - last_request < minimum_interval:
        return False, last_request
    path = Path(runtime)
    if not path.is_dir():
        return False, last_request
    try:
        (path / "quiklight-audio.want").touch()
    except OSError:
        return False, last_request
    return True, moment


def clamp_range(low: float, high: float, *, gap: float = 0.05
               ) -> tuple[float, float]:
    """Intervalo válido para as alças mínimo/máximo do medidor."""
    if not (isfinite(low) and isfinite(high)):
        raise ValueError("Os limites precisam ser números finitos")
    gap = max(0.01, min(gap, 0.5))
    lo = max(0.0, min(1.0-gap, low))
    hi = max(lo + gap, min(1.0, high))
    return round(lo, 3), round(hi, 3)
