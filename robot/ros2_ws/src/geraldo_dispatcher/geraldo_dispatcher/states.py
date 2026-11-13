from collections.abc import Callable
from enum import Enum


class State(str, Enum):
    IDLE = "IDLE"
    CARREGANDO = "CARREGANDO"  # na origem, até a carga ser trancada (evento LOADED)
    A_CAMINHO = "A_CAMINHO"
    CHEGOU = "CHEGOU"
    AGUARDANDO_RETIRADA = "AGUARDANDO_RETIRADA"  # no destino, até o solicitante confirmar o recebimento
    VOLTANDO = "VOLTANDO"
    PARADA_EMERGENCIA = "PARADA_EMERGENCIA"  # só entra por StateMachine.stop() e sai por resume()


TRANSITIONS: dict[State, set[State]] = {
    State.IDLE: {State.A_CAMINHO},
    State.A_CAMINHO: {State.CARREGANDO, State.CHEGOU, State.VOLTANDO},
    State.CARREGANDO: {State.A_CAMINHO},
    State.CHEGOU: {State.AGUARDANDO_RETIRADA},
    State.AGUARDANDO_RETIRADA: {State.VOLTANDO},
    State.VOLTANDO: {State.IDLE},
    State.PARADA_EMERGENCIA: set(),
}


class StateMachine:
    """Guarda o estado do robô e avisa os interessados (OBSERVER) a cada transição válida."""

    def __init__(self, initial: State = State.IDLE) -> None:
        self._state = initial
        self._before_stop: State | None = None
        self._listeners: list[Callable[[State], None]] = []

    @property
    def state(self) -> State:
        return self._state

    def subscribe(self, listener: Callable[[State], None]) -> None:
        self._listeners.append(listener)

    def stop(self) -> None:
        """Emergência: de qualquer estado vai a PARADA_EMERGENCIA, guardando o anterior."""
        if self._state is State.PARADA_EMERGENCIA:
            return
        self._before_stop = self._state
        self._set(State.PARADA_EMERGENCIA)

    def resume(self) -> None:
        """Libera a emergência: volta ao estado em que estava."""
        if self._state is not State.PARADA_EMERGENCIA:
            return
        self._set(self._before_stop)

    def go(self, new: State) -> None:
        if new not in TRANSITIONS[self._state]:
            raise ValueError(f"Transição inválida: {self._state.value} → {new.value}.")
        self._set(new)

    def _set(self, new: State) -> None:
        self._state = new
        for listener in self._listeners:
            listener(new)
