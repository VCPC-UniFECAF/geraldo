import os
import signal
import subprocess
from collections.abc import Callable

GUI_COMMAND = ["gz", "sim", "-g"]


class GuiError(Exception):
    pass


class GazeboGui:
    """Abre a janela 3D do Gazebo (`gz sim -g`) na mesma partição do servidor da simulação. Só uma janela por vez."""

    def __init__(
        self,
        spawn: Callable = subprocess.Popen,
        kill_group: Callable[[int, int], None] | None = None,
        partition: str | None = None,
    ) -> None:
        self._spawn = spawn
        # os.killpg não existe no Windows (onde o Erik desenvolve): resolver aqui, não na assinatura, para o módulo importar lá
        self._kill_group = kill_group or getattr(os, "killpg", None)
        self._partition = partition or os.environ.get("GZ_PARTITION", "verif")
        self._proc = None

    def _running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def open(self) -> tuple[int, bool]:
        """Devolve (pid, já_estava_aberto)."""
        if self._running():
            return self._proc.pid, True
        # no Wayland com GPU híbrida a janela do Gazebo (Ogre2) quebra; roda via X11 (igual ao sim.launch.py)
        env = {**os.environ, "GZ_PARTITION": self._partition, "QT_QPA_PLATFORM": "xcb", "EGL_PLATFORM": ""}
        try:
            self._proc = self._spawn(
                GUI_COMMAND, env=env, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except OSError as err:
            raise GuiError(
                "Não consegui abrir o Gazebo (`gz`). Confira se o Gazebo Harmonic está instalado: bash robot/scripts/check_ros_env.sh."
            ) from err
        return self._proc.pid, False

    def close(self) -> None:
        """Derruba a janela pelo PID do grupo de processos (kill -9); nunca por nome."""
        if self._running():
            self._kill_group(self._proc.pid, getattr(signal, "SIGKILL", 9))
