from datetime import datetime
from typing import Protocol

from app.config import settings


class Clock(Protocol):  # a hora entra pelo construtor/dependência; o teste passa uma hora fixa
    def now(self) -> datetime: ...


class SystemClock:  # STRATEGY: relógio de verdade (fuso da máquina; em contêiner defina TZ)
    def now(self) -> datetime:
        return datetime.now().astimezone()  # hora local do hospital


class FixedClock:  # STRATEGY: relógio fixo para os testes
    def __init__(self, moment: datetime) -> None:
        self._moment = moment

    def now(self) -> datetime:
        return self._moment


class OffPeakWindow:
    """Horário de baixo pico, em horas cheias [start, end). Atravessa a meia-noite quando start > end (20 a 6)."""

    def __init__(self, start_hour: int, end_hour: int) -> None:
        self._start_hour = start_hour
        self._end_hour = end_hour

    def contains(self, moment: datetime) -> bool:
        hour = moment.hour
        if self._start_hour <= self._end_hour:
            return self._start_hour <= hour < self._end_hour
        return hour >= self._start_hour or hour < self._end_hour


def get_clock() -> Clock:
    return SystemClock()


def get_off_peak() -> OffPeakWindow:
    return OffPeakWindow(settings.off_peak_start, settings.off_peak_end)
