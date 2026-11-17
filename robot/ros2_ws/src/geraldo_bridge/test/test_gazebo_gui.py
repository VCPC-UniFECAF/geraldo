import os
import signal
import sys

import pytest

from geraldo_bridge.gazebo_gui import GazeboGui, GuiError

LINUX_ONLY = pytest.mark.skipif(sys.platform == "win32", reason="kill de grupo por PID só existe no Linux (alvo do app)")


class FakeProc:
    def __init__(self, pid=777):
        self.pid, self.code = pid, None

    def poll(self):
        return self.code


class Spawner:
    def __init__(self):
        self.calls, self.proc = [], FakeProc()

    def __call__(self, cmd, **kwargs):
        self.calls.append((cmd, kwargs))
        return self.proc


def test_opens_gz_sim_gui_in_the_verif_partition_in_its_own_session():
    spawn = Spawner()
    gui = GazeboGui(spawn=spawn, kill_group=lambda *a: None, partition="verif")
    assert gui.open() == (777, False)
    cmd, kwargs = spawn.calls[0]
    assert cmd == ["gz", "sim", "-g"]
    assert kwargs["env"]["GZ_PARTITION"] == "verif"
    assert kwargs["start_new_session"] is True


def test_partition_defaults_to_the_environment_then_to_verif(monkeypatch):
    monkeypatch.setenv("GZ_PARTITION", "outra")
    spawn = Spawner()
    GazeboGui(spawn=spawn, kill_group=lambda *a: None).open()
    assert spawn.calls[0][1]["env"]["GZ_PARTITION"] == "outra"
    monkeypatch.delenv("GZ_PARTITION")
    spawn2 = Spawner()
    GazeboGui(spawn=spawn2, kill_group=lambda *a: None).open()
    assert spawn2.calls[0][1]["env"]["GZ_PARTITION"] == "verif"


def test_second_open_while_running_does_not_spawn_again():
    spawn = Spawner()
    gui = GazeboGui(spawn=spawn, kill_group=lambda *a: None)
    gui.open()
    assert gui.open() == (777, True)
    assert len(spawn.calls) == 1


def test_opens_again_after_the_window_was_closed():
    spawn = Spawner()
    gui = GazeboGui(spawn=spawn, kill_group=lambda *a: None)
    gui.open()
    spawn.proc.code = 0
    assert gui.open() == (777, False)
    assert len(spawn.calls) == 2


def test_missing_gz_is_an_error_that_says_what_to_do():
    def broken(cmd, **kwargs):
        raise FileNotFoundError("gz")

    with pytest.raises(GuiError, match="Gazebo Harmonic"):
        GazeboGui(spawn=broken, kill_group=lambda *a: None).open()


@LINUX_ONLY
def test_close_kills_the_process_group_by_pid_with_sigkill():
    killed = []
    gui = GazeboGui(spawn=Spawner(), kill_group=lambda pid, sig: killed.append((pid, sig)))
    gui.close()
    assert killed == []  # nada aberto, nada a matar
    gui.open()
    gui.close()
    assert killed == [(777, signal.SIGKILL)]


@LINUX_ONLY
def test_default_kill_is_killpg():
    assert GazeboGui()._kill_group is os.killpg
