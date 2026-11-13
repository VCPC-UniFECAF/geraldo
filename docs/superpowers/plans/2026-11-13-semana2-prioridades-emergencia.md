# Semana 2 (Samuel): prioridades e parada de emergência — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** O robô aplica um perfil de navegação por prioridade (crítica, média, rotina) e para por completo quando `/geraldo/estop` vale `true`, publicando `PARADA_EMERGENCIA` e retomando a mesma meta ao liberar.

**Architecture:** `profiles.py` guarda os perfis e a escolha por prioridade (tabela, sem `if/elif`). `emergency.py` guarda a bandeira de emergência (thread-safe). O `Dispatcher` consulta a bandeira em pontos de checagem (antes de cada meta, depois de uma meta cortada, a cada consulta do recebimento e antes de pedir tarefa) e usa uma porta `NavigationTuner` para aplicar o perfil. `node.py` liga os dois ao ROS.

**Tech Stack:** Python 3.12, pytest, ROS 2 Jazzy (Nav2 MPPI, `nav2_msgs/SpeedLimit`, `rcl_interfaces/SetParameters`).

**Spec:** `docs/superpowers/specs/2026-11-13-semana2-robo-design.md`, seção 5. Plano anterior: `docs/superpowers/plans/2026-11-13-semana2-dispatcher-sensores.md` (mesma branch `feat/robo-dispatcher-estados`).

## Global Constraints

- `/geraldo/estop` (`std_msgs/Bool`: `true` para, `false` libera) e os estados vêm de `docs/contracts/ros-interfaces.md`. Não criar tópico novo; `/speed_limit` é o tópico padrão do Nav2.
- Prioridades (`Priority` do OpenAPI): `critica`, `media`, `rotina`.
- Padrões de projeto (`docs/padroes-de-projeto.md`): dependências pelo construtor, tabela no lugar de `if/elif` por tipo, adapter para o Nav2.
- Todo código novo vem com teste (falha primeiro). Commit pequeno em português (`tipo: o que mudou`), terminando com `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- Simulação isolada: `export ROS_DOMAIN_ID=77 GZ_PARTITION=verif` em todo comando de ROS/Gazebo.
- Testes do dispatcher: `cd robot/ros2_ws/src/geraldo_dispatcher && python3 -m pytest test -q`.

## Decisões e limites (fora do robô)

- **"Rotina só em baixo pico"** não dá para impor no robô: o backend já marca a entrega `EM_ROTA` quando entrega a tarefa, e o contrato não tem endpoint para devolvê-la. Quem filtra é o `POST /robot/next-task` do Erik (pular `rotina` fora da janela de baixo pico). Registrado em `robot/AGENTS.md` como aviso ao Erik.
- **"Cede passagem a humanos"** não existe na simulação (não há pessoas). O perfil `rotina` só anda mais devagar.
- Parada de emergência por colisão automática, botão no painel e endpoint do backend ficam para a semana 3.

## Mapa de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `geraldo_dispatcher/states.py` | `StateMachine.stop()` e `resume()` (emergência guarda o estado anterior) |
| `geraldo_dispatcher/emergency.py` (novo) | `EmergencyStop`: bandeira thread-safe (`engage`, `release`, `active`) |
| `geraldo_dispatcher/profiles.py` (novo) | `NavProfile`, `PROFILES`, `profile_for(priority)` |
| `geraldo_dispatcher/ports.py` | porta `NavigationTuner.apply(profile)` |
| `geraldo_dispatcher/dispatcher.py` | `hold_if_stopped`, pontos de checagem e aplicação do perfil |
| `geraldo_dispatcher/node.py` | assina `/geraldo/estop`; `Nav2Tuner`; `Nav2Navigator` corta a meta na emergência |

---

### Task 1: Emergência na máquina de estados e a bandeira `EmergencyStop`

**Files:**
- Modify: `robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/states.py`
- Create: `robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/emergency.py`
- Test: `robot/ros2_ws/src/geraldo_dispatcher/test/test_states.py`, `robot/ros2_ws/src/geraldo_dispatcher/test/test_emergency.py`

**Interfaces:**
- Produces: `StateMachine.stop()` (de qualquer estado vai a `PARADA_EMERGENCIA`, guardando o anterior; sem efeito se já parada) e `StateMachine.resume()` (volta ao estado guardado; sem efeito se não está parada); ambos notificam os listeners. `go(State.PARADA_EMERGENCIA)` continua levantando `ValueError`. `EmergencyStop` com `.active: bool`, `.engage()`, `.release()`.

- [ ] **Step 1: Escrever os testes que falham**

Acrescentar ao fim de `test_states.py`:

```python
@pytest.mark.parametrize("before", [State.IDLE, State.A_CAMINHO, State.AGUARDANDO_RETIRADA, State.VOLTANDO])
def test_emergency_stop_remembers_where_the_robot_was_and_resume_goes_back(before):
    machine, heard = StateMachine(initial=before), []
    machine.subscribe(heard.append)
    machine.stop()
    assert machine.state is State.PARADA_EMERGENCIA
    machine.resume()
    assert machine.state is before and heard == [State.PARADA_EMERGENCIA, before]


def test_stop_twice_and_resume_when_not_stopped_do_nothing():
    machine, heard = StateMachine(), []
    machine.subscribe(heard.append)
    machine.resume()
    machine.stop()
    machine.stop()
    assert heard == [State.PARADA_EMERGENCIA]


def test_the_emergency_state_is_entered_only_through_stop():
    with pytest.raises(ValueError, match="PARADA_EMERGENCIA"):
        StateMachine().go(State.PARADA_EMERGENCIA)
    stopped = StateMachine()
    stopped.stop()
    with pytest.raises(ValueError):
        stopped.go(State.IDLE)
```

Criar `test_emergency.py`:

```python
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from geraldo_dispatcher.emergency import EmergencyStop  # noqa: E402


def test_it_starts_released_and_follows_engage_and_release():
    estop = EmergencyStop()
    assert estop.active is False
    estop.engage()
    assert estop.active is True
    estop.release()
    assert estop.active is False
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd robot/ros2_ws/src/geraldo_dispatcher && python3 -m pytest test/test_states.py test/test_emergency.py -q`
Expected: FAIL (`AttributeError: ... 'stop'` e `ModuleNotFoundError: ... emergency`)

- [ ] **Step 3: Implementar**

Em `states.py`, trocar o comentário do `PARADA_EMERGENCIA` por `# só entra por StateMachine.stop() e sai por resume()`, trocar `__init__` e acrescentar os métodos (o resto da classe fica igual):

```python
    def __init__(self, initial: State = State.IDLE) -> None:
        self._state = initial
        self._before_stop: State | None = None
        self._listeners: list[Callable[[State], None]] = []
```

```python
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
```

Criar `emergency.py`:

```python
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
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd robot/ros2_ws/src/geraldo_dispatcher && python3 -m pytest test -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add robot/ros2_ws/src/geraldo_dispatcher
git commit -m "feat(dispatcher): parada de emergencia na maquina de estados e bandeira EmergencyStop"
```

---

### Task 2: O dispatcher para, espera a liberação e retoma a mesma meta

**Files:**
- Modify: `robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/dispatcher.py`
- Test: `robot/ros2_ws/src/geraldo_dispatcher/test/test_dispatcher.py`

**Interfaces:**
- Consumes: `EmergencyStop` (Task 1), `StateMachine.stop/resume` (Task 1).
- Produces: `Dispatcher(..., estop: EmergencyStop | None = None, estop_poll: float = 0.5, ...)` com `.estop` e `hold_if_stopped() -> bool` (público: o nó chama quando está ocioso). Pontos de checagem: início de `run_once`, antes de cada `go_to`, depois de um `go_to` que falhou com a emergência acionada (refaz a mesma meta), e a cada consulta do recebimento.

- [ ] **Step 1: Escrever os testes que falham** — em `test_dispatcher.py`: (a) acrescentar `from geraldo_dispatcher.emergency import EmergencyStop  # noqa: E402` entre os imports; (b) trocar o helper `run` por

```python
def run(backend, navigator=None, poses=POSES, estop=None, sleep=None, **kwargs):
    machine, history, sleeps = StateMachine(), [], []
    machine.subscribe(history.append)
    dispatcher = Dispatcher(backend, poses, navigator or FakeNavigator(), machine=machine,
                            sleep=sleep(sleeps) if sleep else sleeps.append, estop=estop, log=lambda *_: None, **kwargs)
    return dispatcher.run_once(), history, sleeps


def releasing_after(estop, count):  # sleep de teste: libera a emergência na `count`-ésima espera
    def make(sleeps):
        def sleep(seconds):
            sleeps.append(seconds)
            if len(sleeps) >= count:
                estop.release()
        return sleep
    return make
```

(c) acrescentar no fim do arquivo:

```python
class CutOnceNavigator(FakeNavigator):  # a emergência corta a primeira meta
    def __init__(self, estop) -> None:
        super().__init__()
        self.estop, self.calls = estop, 0

    def go_to(self, pose):
        self.calls += 1
        if self.calls == 1:
            self.visited.append(pose)
            self.estop.engage()
            return False
        return super().go_to(pose)


def test_an_emergency_cuts_the_goal_holds_in_parada_emergencia_and_retries_the_same_goal():
    estop = EmergencyStop()
    navigator = CutOnceNavigator(estop)
    result, history, sleeps = run(ScriptedBackend([TASK]), navigator, estop=estop, sleep=releasing_after(estop, 2))
    assert result["result"] == "ENTREGUE"
    assert history[:3] == [State.A_CAMINHO, State.PARADA_EMERGENCIA, State.A_CAMINHO]
    assert navigator.visited[:2] == [POSES["farmacia_balcao"]] * 2
    assert sleeps == [0.5, 0.5]


def test_an_emergency_while_waiting_for_the_receipt_holds_before_the_next_poll():
    estop = EmergencyStop()

    class EngagesOnce(ScriptedBackend):
        engaged = False

        def delivery_status(self, delivery_id):
            if not self.engaged:
                self.engaged = True
                estop.engage()
                return WAITING
            return "ENTREGUE"

    result, history, sleeps = run(EngagesOnce([TASK]), estop=estop, sleep=releasing_after(estop, 2))
    assert result["result"] == "ENTREGUE"
    assert history[4:8] == [State.AGUARDANDO_RETIRADA, State.PARADA_EMERGENCIA, State.AGUARDANDO_RETIRADA, State.VOLTANDO]
    assert sleeps == [2.0, 0.5]


def test_an_emergency_while_idle_holds_before_asking_for_a_task():
    estop = EmergencyStop()
    estop.engage()
    result, history, sleeps = run(ScriptedBackend([]), estop=estop, sleep=releasing_after(estop, 1))
    assert result is None and history == [State.PARADA_EMERGENCIA, State.IDLE] and sleeps == [0.5]


def test_hold_if_stopped_does_nothing_when_the_emergency_is_off():
    dispatcher = Dispatcher(ScriptedBackend([]), POSES, FakeNavigator(), log=lambda *_: None)
    assert dispatcher.hold_if_stopped() is False and dispatcher.machine.state is State.IDLE
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd robot/ros2_ws/src/geraldo_dispatcher && python3 -m pytest test/test_dispatcher.py -q`
Expected: FAIL (`TypeError: Dispatcher.__init__() got an unexpected keyword argument 'estop'`)

- [ ] **Step 3: Implementar** — em `dispatcher.py`: (a) `from .emergency import EmergencyStop`; (b) assinatura e atributos do `__init__`:

```python
    def __init__(self, backend: BackendPort, poses: dict[str, Pose], navigator: Navigator,
                 machine: StateMachine | None = None, home: str = "base_robo", sleep=time.sleep,
                 poll_interval: float = 2.0, receipt_timeout: float = 300.0,
                 estop: EmergencyStop | None = None, estop_poll: float = 0.5, log=print) -> None:
        self.backend, self.poses, self.navigator = backend, poses, navigator
        self.machine = machine or StateMachine()
        self.home, self.sleep, self.log = home, sleep, log
        self.poll_interval, self.receipt_timeout = poll_interval, receipt_timeout
        self.estop, self.estop_poll = estop or EmergencyStop(), estop_poll
        self.delivery_id: int | None = None
```

(c) no começo de `run_once`, antes de `task = self.backend.next_task()`: `self.hold_if_stopped()`; (d) em `_wait_for_receipt`, primeira linha dentro do `while True:`: `self.hold_if_stopped()`; (e) substituir `_go` e acrescentar `hold_if_stopped`:

```python
    def hold_if_stopped(self) -> bool:
        """Com a emergência acionada, para em PARADA_EMERGENCIA até ela ser liberada e volta ao estado anterior."""
        if not self.estop.active:
            return False
        self.log("parada de emergência acionada: robô parado")
        self.machine.stop()
        while self.estop.active:
            self.sleep(self.estop_poll)
        self.machine.resume()
        self.log("parada de emergência liberada: retomando")
        return True

    def _go(self, waypoint: str) -> bool:
        self.log(f"entrega {self.delivery_id}: indo para {waypoint}")
        pose = self._pose(waypoint)
        while True:
            self.hold_if_stopped()
            reached = self.navigator.go_to(pose)
            if reached or not self.estop.active:  # chegou, ou falhou de verdade (não foi a emergência que cortou a meta)
                break
        if not reached:
            self.log(f"entrega {self.delivery_id}: não chegou a {waypoint}")
        return reached
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd robot/ros2_ws/src/geraldo_dispatcher && python3 -m pytest test -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add robot/ros2_ws/src/geraldo_dispatcher
git commit -m "feat(dispatcher): parada de emergencia segura a meta, espera a liberacao e retoma"
```

---

### Task 3: Perfis por prioridade e a porta `NavigationTuner`

**Files:**
- Create: `robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/profiles.py`
- Modify: `robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/ports.py`
- Modify: `robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/dispatcher.py`
- Test: `robot/ros2_ws/src/geraldo_dispatcher/test/test_profiles.py`, `robot/ros2_ws/src/geraldo_dispatcher/test/test_dispatcher.py`

**Interfaces:**
- Produces: `NavProfile(name: str, max_speed: float, inflation_radius: float)` (frozen); `PROFILES: dict[str, NavProfile]` com `critica` (1,0 m/s, 0,55 m), `media` (0,8 m/s, 0,70 m) e `rotina` (0,5 m/s, 0,70 m); `DEFAULT_PROFILE = PROFILES["media"]`; `profile_for(priority: str) -> NavProfile` (`ValueError("Prioridade desconhecida: ...")`). `NavigationTuner.apply(profile) -> None` (porta). `Dispatcher(..., tuner: NavigationTuner | None = None)`: com `tuner`, aplica o perfil da prioridade da tarefa ao começar e `DEFAULT_PROFILE` ao terminar.

- [ ] **Step 1: Escrever os testes que falham** — criar `test_profiles.py`:

```python
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from geraldo_dispatcher.profiles import DEFAULT_PROFILE, PROFILES, profile_for  # noqa: E402


def test_profiles_cover_exactly_the_contract_priorities():
    spec = yaml.safe_load((ROOT / "docs/contracts/openapi.yaml").read_text(encoding="utf-8"))
    assert list(PROFILES) == spec["components"]["schemas"]["Priority"]["enum"]


def test_critical_is_faster_and_squeezes_closer_than_routine():
    assert PROFILES["critica"].max_speed > PROFILES["media"].max_speed > PROFILES["rotina"].max_speed
    assert PROFILES["critica"].inflation_radius < PROFILES["media"].inflation_radius


def test_the_default_profile_matches_the_nav2_inflation_radius():
    params = yaml.safe_load((ROOT / "robot/ros2_ws/src/geraldo_nav/config/nav2_params.yaml").read_text())
    radius = params["local_costmap"]["local_costmap"]["ros__parameters"]["inflation_layer"]["inflation_radius"]
    assert DEFAULT_PROFILE is PROFILES["media"] and DEFAULT_PROFILE.inflation_radius == pytest.approx(radius)


def test_profile_for_picks_by_priority_and_rejects_unknown_ones():
    assert profile_for("critica") is PROFILES["critica"]
    with pytest.raises(ValueError, match="Prioridade desconhecida: urgente"):
        profile_for("urgente")
```

Em `test_dispatcher.py`: importar `from geraldo_dispatcher.ports import BackendPort, NavigationTuner, Navigator` e `from geraldo_dispatcher.profiles import DEFAULT_PROFILE, PROFILES`; trocar `TASK` por `{"id": 5, "origin_waypoint": "farmacia_balcao", "dest_waypoint": "cc_entrega", "priority": "media"}`; no helper `run` acrescentar o parâmetro `tuner=None` e passar `tuner=tuner` ao `Dispatcher`; acrescentar no fim:

```python
class RecordingTuner(NavigationTuner):
    def __init__(self) -> None:
        self.applied = []

    def apply(self, profile) -> None:
        self.applied.append(profile)


def test_each_delivery_applies_its_priority_profile_and_goes_back_to_the_default():
    tuner = RecordingTuner()
    result, _, _ = run(ScriptedBackend([{**TASK, "priority": "critica"}]), tuner=tuner)
    assert result["result"] == "ENTREGUE"
    assert tuner.applied == [PROFILES["critica"], DEFAULT_PROFILE]


def test_an_unknown_priority_is_an_error_before_the_robot_moves():
    navigator = FakeNavigator()
    with pytest.raises(ValueError, match="Prioridade desconhecida"):
        run(ScriptedBackend([{**TASK, "priority": "urgente"}]), navigator, tuner=RecordingTuner())
    assert navigator.visited == []
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd robot/ros2_ws/src/geraldo_dispatcher && python3 -m pytest test -q`
Expected: FAIL (`ModuleNotFoundError: ... profiles` e `ImportError: ... NavigationTuner`)

- [ ] **Step 3: Implementar** — criar `profiles.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class NavProfile:
    """Como o robô navega numa prioridade: velocidade máxima (m/s) e raio de inflação do costmap local (m)."""

    name: str
    max_speed: float
    inflation_radius: float  # menor = passa mais perto dos obstáculos (desvio mais agressivo)


# O contrato fixa as prioridades (OpenAPI Priority). A média usa o raio padrão do Nav2 (nav2_params.yaml).
PROFILES: dict[str, NavProfile] = {
    "critica": NavProfile("critica", max_speed=1.0, inflation_radius=0.55),
    "media": NavProfile("media", max_speed=0.8, inflation_radius=0.70),
    "rotina": NavProfile("rotina", max_speed=0.5, inflation_radius=0.70),
}
DEFAULT_PROFILE = PROFILES["media"]


def profile_for(priority: str) -> NavProfile:
    if priority not in PROFILES:
        raise ValueError(f"Prioridade desconhecida: {priority}. Use critica, media ou rotina.")
    return PROFILES[priority]
```

Em `ports.py`, importar `from .profiles import NavProfile` e acrescentar ao fim:

```python
class NavigationTuner(ABC):  # porta: ajusta a navegação para a prioridade da entrega
    @abstractmethod
    def apply(self, profile: NavProfile) -> None:
        """Aplica velocidade máxima e raio de inflação do perfil."""
```

Em `dispatcher.py`: importar `from .ports import BackendPort, NavigationTuner, Navigator` e `from .profiles import DEFAULT_PROFILE, profile_for`; acrescentar o parâmetro `tuner: NavigationTuner | None = None` ao `__init__` (antes de `log`) com `self.tuner = tuner`; em `run_once`, logo depois do laço que valida os waypoints, acrescentar

```python
        if self.tuner is not None:
            self.tuner.apply(profile_for(task["priority"]))
```

e, logo depois de `self.delivery_id = None` (depois da volta à base), acrescentar

```python
        if self.tuner is not None:
            self.tuner.apply(DEFAULT_PROFILE)
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd robot/ros2_ws/src/geraldo_dispatcher && python3 -m pytest test -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add robot/ros2_ws/src/geraldo_dispatcher
git commit -m "feat(dispatcher): perfil de navegacao por prioridade aplicado a cada entrega"
```

---

### Task 4: Nó ROS (`/geraldo/estop`, `Nav2Tuner`) e documentação

**Files:**
- Modify: `robot/ros2_ws/src/geraldo_dispatcher/geraldo_dispatcher/node.py`
- Modify: `robot/ros2_ws/src/geraldo_dispatcher/package.xml`
- Modify: `robot/AGENTS.md`

**Interfaces:**
- Consumes: `EmergencyStop`, `NavigationTuner`, `NavProfile`, `Dispatcher(estop=..., tuner=...)`.
- Produces: o robô reage a `/geraldo/estop`; `Nav2Navigator(nav, timeout, estop)` cancela a meta com a emergência acionada; `Nav2Tuner(node)` publica `/speed_limit` (`nav2_msgs/SpeedLimit`, `percentage=False`) e muda `inflation_layer.inflation_radius` de `/local_costmap/local_costmap`.

- [ ] **Step 1: Dependências** — em `package.xml`, depois de `<exec_depend>nav_msgs</exec_depend>`: `<exec_depend>nav2_msgs</exec_depend>` e `<exec_depend>rcl_interfaces</exec_depend>`.

- [ ] **Step 2: Alterar `node.py`**

Imports a acrescentar: `from nav2_msgs.msg import SpeedLimit`, `from rcl_interfaces.msg import Parameter as ParameterMsg, ParameterType, ParameterValue`, `from rcl_interfaces.srv import SetParameters`, `from std_msgs.msg import Bool, String` (junto do `String` existente), `from .emergency import EmergencyStop`, `from .ports import NavigationTuner, Navigator`, `from .profiles import NavProfile`.

`Nav2Navigator` recebe a bandeira e corta a meta:

```python
class Nav2Navigator(Navigator):  # ADAPTER: traduz Pose para o NavigateToPose do Nav2 (BasicNavigator)
    def __init__(self, nav: BasicNavigator, timeout: float = 300.0, estop: EmergencyStop | None = None) -> None:
        self._nav = nav
        self._timeout = timeout
        self._estop = estop or EmergencyStop()

    def go_to(self, pose: Pose) -> bool:
        nav = self._nav
        goal = PoseStamped()
        goal.header.frame_id = "map"
        goal.header.stamp = nav.get_clock().now().to_msg()
        goal.pose.position.x, goal.pose.position.y = pose.x, pose.y
        goal.pose.orientation.z, goal.pose.orientation.w = pose.quaternion()
        nav.goToPose(goal)
        start = time.monotonic()
        while not nav.isTaskComplete():
            if self._estop.active or time.monotonic() - start > self._timeout:
                nav.cancelTask()  # o controlador para o robô ao cancelar
                break
            time.sleep(0.5)
        return nav.getResult() == TaskResult.SUCCEEDED
```

`GeraldoStateNode` ganha a assinatura do `/geraldo/estop` (recebe a bandeira):

```python
    def __init__(self, estop: EmergencyStop) -> None:
        super().__init__("geraldo_state")
        self._estop = estop
        ...  # o resto do __init__ continua igual
        self.create_subscription(Bool, "/geraldo/estop", self._on_estop, 10)

    def _on_estop(self, msg: Bool) -> None:
        self._estop.engage() if msg.data else self._estop.release()
```

`Nav2Tuner` (novo, depois do `GeraldoStateNode`):

```python
class Nav2Tuner(NavigationTuner):  # ADAPTER: traduz o perfil para o /speed_limit e o costmap local do Nav2
    def __init__(self, node: Node) -> None:
        self._node = node
        self._speed = node.create_publisher(SpeedLimit, "/speed_limit", 10)
        self._costmap = node.create_client(SetParameters, "/local_costmap/local_costmap/set_parameters")

    def apply(self, profile: NavProfile) -> None:
        self._speed.publish(SpeedLimit(percentage=False, speed_limit=profile.max_speed))
        if not self._costmap.wait_for_service(timeout_sec=2.0):
            self._node.get_logger().warning("costmap local indisponível: raio de inflação não alterado")
            return
        value = ParameterValue(type=ParameterType.PARAMETER_DOUBLE, double_value=profile.inflation_radius)
        request = SetParameters.Request(parameters=[ParameterMsg(name="inflation_layer.inflation_radius", value=value)])
        self._costmap.call_async(request)
        self._node.get_logger().info(f"perfil {profile.name}: {profile.max_speed} m/s, inflação {profile.inflation_radius} m")
```

No `main()`: criar `estop = EmergencyStop()` antes do `Nav2Navigator`, passar `estop=estop` a ele, criar `state_node = GeraldoStateNode(estop)` e `tuner = Nav2Tuner(state_node)`, e montar `Dispatcher(client, load_poses(waypoints_file), Nav2Navigator(nav, timeout=300, estop=estop), machine=machine, estop=estop, tuner=tuner)`. Como o `Dispatcher` agora depende do nó, mover a criação de `state_node`, do executor e da thread do executor para antes da criação do `Dispatcher`. No laço principal, o ocioso passa a chamar a emergência através do `run_once` (que já checa no começo), então nada muda ali.

- [ ] **Step 3: Documentar em `robot/AGENTS.md`** — depois do bullet "Sensores de alcance", acrescentar:

```markdown
- Prioridades e emergência: cada entrega aplica o perfil da sua prioridade (`profiles.py`: crítica 1,0 m/s e inflação 0,55 m; média 0,8 m/s e 0,70 m; rotina 0,5 m/s e 0,70 m) pelo `/speed_limit` do Nav2 e pelo `inflation_layer.inflation_radius` do costmap local, e volta ao perfil médio no fim. `/geraldo/estop` (`std_msgs/Bool`) em `true` cancela a meta, para o robô e publica `PARADA_EMERGENCIA`; em `false` ele volta ao estado anterior e refaz a mesma meta. Teste na mão: `ros2 topic pub -r 5 -t 3 /geraldo/estop std_msgs/msg/Bool "{data: true}"`. **Aviso ao Erik:** "rotina só em baixo pico" não dá para impor no robô (a entrega já sai `EM_ROTA` do `next-task`); o `POST /robot/next-task` deve pular `rotina` fora da janela de baixo pico.
```

- [ ] **Step 4: Testes e build**

Run: `cd robot/ros2_ws/src/geraldo_dispatcher && python3 -m pytest test -q`
Expected: PASS
Run: `source /opt/ros/jazzy/setup.bash && cd robot/ros2_ws && colcon build --symlink-install 2>&1 | tail -2 && source install/setup.bash && python3 -c "import geraldo_dispatcher.node"`
Expected: `Summary: 3 packages finished` e nenhum erro de import.

- [ ] **Step 5: Commit**

```bash
git add robot/ros2_ws/src/geraldo_dispatcher robot/AGENTS.md
git commit -m "feat(dispatcher): no ROS reage a /geraldo/estop e aplica o perfil da prioridade no Nav2"
```

---

### Task 5: Verificar na simulação

**Files:** nenhum arquivo novo (só evidências).

- [ ] **Step 1: Subir tudo** (`ROS_DOMAIN_ID=77 GZ_PARTITION=verif`, `source /opt/ros/jazzy/setup.bash && source robot/ros2_ws/install/setup.bash`): sim headless, Nav2 com os 5 nós `active` (`grep -q '^active'`), `python3 robot/scripts/fake_backend.py --port 8000` e `GERALDO_ROBOT_PASSWORD=robo-local ros2 run geraldo_dispatcher dispatcher`.

- [ ] **Step 2: Perfil** — a entrega 1 é `media`: conferir `ros2 param get /local_costmap/local_costmap inflation_layer.inflation_radius` (0,7) e, com o robô andando, o pico de `linear.x` em `/odom` (≤ 0,8 m/s + folga). Esperar a entrega 2 (`critica`) e conferir raio 0,55 e pico de `/odom` acima de 0,85 m/s.
Expected: os picos seguem os perfis; ao fim das entregas o raio volta a 0,7.

- [ ] **Step 3: Emergência** — com o robô em `A_CAMINHO`, `ros2 topic pub -r 5 -t 3 /geraldo/estop std_msgs/msg/Bool "{data: true}"`; conferir `/geraldo/state` = `PARADA_EMERGENCIA` em até 2 s e `/odom` com `linear.x` ≈ 0; depois `... "{data: false}"`.
Expected: o estado volta a `A_CAMINHO`, o robô retoma a mesma meta e a entrega termina com `UNLOCKED` no log da API.

- [ ] **Step 4: Suítes** — `python3 -m pytest tools robot -q`, e os testes dos dois pacotes (`geraldo_dispatcher`, `geraldo_description`). Expected: PASS.

- [ ] **Step 5: Encerrar** os processos deste domínio, conferir `git status` limpo e resumir: o que passou, o que não foi verificado, os avisos ao Erik e ao Pedro.
