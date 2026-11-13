import threading


class EmergencyStop:
    """Bandeira da parada de emergência. O ROS liga e desliga (outra thread); o dispatcher só consulta."""

    def __init__(self) -> None:
        self._engaged = threading.Event()

    @property
    def active(self) -> bool:
        return self._engaged.is_set()

    def engage(self) -> None:
        self._engaged.set()

    def release(self) -> None:
        self._engaged.clear()
