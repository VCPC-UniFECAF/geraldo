class EstopStore:
    """Estado da parada de emergência pedida pelo painel (só em memória: ao reiniciar o backend, desligada).

    O robô consulta GET /robot/estop a cada 1 s e junta este estado com o tópico ROS /geraldo/estop.
    """

    def __init__(self) -> None:
        self._active = False

    @property
    def active(self) -> bool:
        return self._active

    @active.setter
    def active(self, value: bool) -> None:
        self._active = value


estop = EstopStore()


def get_estop() -> EstopStore:
    return estop
