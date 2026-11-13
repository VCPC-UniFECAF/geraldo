# Padrões de projeto do G.E.R.A.L.D.O.

Este é o padrão de código de **todo mundo** (Samuel, Erik, Vieira, Pedro e as IAs que o grupo usar). Ele vem da disciplina Programming Paradigms (SOLID, Factory Method, Strategy, Builder, Observer, Adapter, injeção de dependência, programação funcional e POO). O código da web já segue o estilo; o backend e o robô passam a seguir também.

> **Regra de ouro: padrão só entra onde há variação real.** Se existe um só caminho e nada indica que vá mudar, escreva a função simples. Padrão decorativo custa tempo, e o prazo é curto.

## As 8 regras

1. **Uma responsabilidade por classe e por módulo (SRP).** Router valida e traduz erro; comando decide; consulta lê; seed popula. Se a descrição da classe pede um "e", divida.
2. **Aberto para extensão, fechado para modificação (OCP).** Nova prioridade, novo tipo de movimentação ou novo status = **classe nova**, sem mexer em `if/elif` espalhados.
3. **Sem `if/elif` por tipo.** Quando o comportamento depende de um tipo (prioridade, status, movimentação), use Strategy ou Factory Method em vez de comparar valores em vários lugares.
4. **Subtipos substituíveis (LSP).** Quem implementa uma interface cumpre o contrato inteiro: o `FakeNavigator` troca o Nav2 e o `fake_backend` troca a API de verdade, sem o chamador perceber.
5. **Interfaces pequenas (ISP).** Uma interface com 1 a 3 métodos que o cliente realmente usa (`Navigator.go_to`, `BackendPort.next_task`), nunca uma interface gorda.
6. **Dependa de abstração e injete pelo construtor (DIP).** Nenhuma classe cria sua própria dependência (`Session`, cliente HTTP, relógio, navegador). Ela recebe pelo `__init__`; o valor padrão pode ser o real, o teste passa o falso.
7. **Funções puras para transformar dados.** Filtrar, mapear, ordenar e somar usam `filter`/`map`/`sorted`/compreensões, sem mudar a lista original nem ler estado global.
8. **Encapsule o estado (POO).** Atributos privados (`_x` em Python, `#x` em TypeScript) e acesso por método ou `@property`. Estoque, por exemplo, só muda por `Movimentacao`.

## Qual padrão usar

| Situação | Padrão | No Geraldo |
|---|---|---|
| Uma ação do domínio com validação e efeitos | **Command** | `CreateDelivery` (backend), uma classe por ação em `app/commands/` |
| Comportamento que muda conforme um tipo | **Strategy** | `PriorityPolicy` (backend), `PrioridadeStrategy`, `StatusStrategy` e `NivelEstoqueStrategy` (web: nível do estoque, sem `if/elif` por nível na tela), `EstadoRoboStrategy` (web: texto, cor e ícone de cada estado do robô em `apresentacao/estadoRobo.ts`; a emergência é uma classe própria, sem `if` no card), política de navegação por prioridade (robô, semana 2) |
| Criar o objeto certo para o tipo recebido | **Factory Method** | `policy_for(priority)`, `MovementCreator` por tipo de movimentação, `Pose.from_dict` |
| Montar um objeto aos poucos e validar no fim | **Builder** | `SolicitacaoBuilder` (web); em testes, para montar payloads |
| Avisar vários interessados quando algo acontece | **Observer** | `Sessao` e `TokenObserver` (web); eventos de entrega e telemetria (backend e robô, semana 2) |
| Falar com uma biblioteca ou serviço de interface diferente | **Adapter** | `EntregaAdapter` (web), `Nav2Navigator` em volta do `BasicNavigator` (robô), `BackendClient` |
| Trocar implementação sem mudar quem usa | **DIP / injeção** | `Dispatcher(client, poses, navigator)`; `MockRobot` e `fake_backend` nos testes |

Cada classe de padrão leva um comentário curto com o nome (`# STRATEGY`, `# FACTORY`, `# ADAPTER`), como o código da web já faz.

## Exemplos curtos (Python)

Todo bloco abaixo roda como está; o código real do projeto segue o mesmo formato (nomes em inglês, textos de erro em português).

### Strategy e Factory

```python
from abc import ABC, abstractmethod


class PriorityPolicy(ABC):  # STRATEGY
    @property
    @abstractmethod
    def rank(self) -> int: ...

    @property
    @abstractmethod
    def needs_approval(self) -> bool: ...


class Critical(PriorityPolicy):
    rank = 0
    needs_approval = True


class Standard(PriorityPolicy):
    rank = 1
    needs_approval = False


class Routine(PriorityPolicy):
    rank = 2
    needs_approval = False


_POLICIES = {"critica": Critical(), "media": Standard(), "rotina": Routine()}


def policy_for(priority: str) -> PriorityPolicy:  # FACTORY
    if priority not in _POLICIES:
        raise ValueError(f"Prioridade desconhecida: {priority}. Use critica, media ou rotina.")
    return _POLICIES[priority]


queue = sorted(["rotina", "critica", "media"], key=lambda p: policy_for(p).rank)
assert queue == ["critica", "media", "rotina"]
```

Prioridade nova? Crie uma classe e registre no dicionário. Nenhum `if` espalhado muda.

### Factory Method com método-modelo (como o `Creator` da disciplina)

```python
from abc import ABC, abstractmethod


class MovementCreator(ABC):  # FACTORY METHOD + TEMPLATE METHOD
    type: str

    @abstractmethod
    def apply(self, stock: dict, quantity: int) -> None:
        """Efeito deste tipo de movimentação no estoque."""

    def register(self, stock: dict, quantity: int) -> dict:
        if quantity <= 0:
            raise ValueError("A quantidade da movimentação deve ser positiva.")
        self.apply(stock, quantity)
        return {"type": self.type, "quantity": quantity}


class ReservaCreator(MovementCreator):
    type = "RESERVA"

    def apply(self, stock, quantity):
        stock["reserved"] += quantity


stock = {"quantity": 10, "reserved": 0}
movement = ReservaCreator().register(stock, 3)
assert movement == {"type": "RESERVA", "quantity": 3} and stock["reserved"] == 3
```

É o jeito de garantir a regra "o estoque só muda por `Movimentacao`": cada tipo tem uma classe, e só ela mexe no saldo.

### Adapter, DIP e LSP

```python
from abc import ABC, abstractmethod


class Navigator(ABC):  # porta (ISP: um método só)
    @abstractmethod
    def go_to(self, x: float, y: float) -> bool: ...


class Nav2Navigator(Navigator):  # ADAPTER: traduz para a biblioteca real
    def __init__(self, basic_navigator) -> None:
        self._basic = basic_navigator

    def go_to(self, x, y):
        return self._basic.goToPose((x, y))


class FakeNavigator(Navigator):  # substituto de teste (LSP)
    def __init__(self) -> None:
        self.visited = []

    def go_to(self, x, y):
        self.visited.append((x, y))
        return True


class Dispatcher:  # DIP: recebe a dependência pelo construtor
    def __init__(self, navigator: Navigator) -> None:
        self._navigator = navigator

    def run(self, stops):
        return all(self._navigator.go_to(x, y) for x, y in stops)


fake = FakeNavigator()
assert Dispatcher(fake).run([(1, 2), (3, 4)]) and fake.visited == [(1, 2), (3, 4)]
```

### Observer

```python
class Subject:  # OBSERVER (mesmos nomes da disciplina)
    def __init__(self) -> None:
        self._observers = []

    def add_observer(self, observer) -> None:
        self._observers.append(observer)

    def remove_observer(self, observer) -> None:
        self._observers.remove(observer)

    def notify(self, event) -> None:
        for observer in list(self._observers):
            observer.update(event)


class LowStockAlert:
    def __init__(self) -> None:
        self.alerts = []

    def update(self, event) -> None:
        if event["quantity"] < event["minimum"]:
            self.alerts.append(event["item_id"])


deliveries = Subject()
alert = LowStockAlert()
deliveries.add_observer(alert)
deliveries.notify({"item_id": "bolsa-sangue-o-neg", "quantity": 6, "minimum": 10})
assert alert.alerts == ["bolsa-sangue-o-neg"]
```

### Programação funcional

```python
def available(entry: dict) -> int:  # função pura
    return entry["quantity"] - entry["reserved"]


def with_stock(entries: list[dict]) -> list[dict]:
    return [e for e in entries if available(e) > 0]  # não altera a lista original


entries = [{"quantity": 5, "reserved": 5}, {"quantity": 5, "reserved": 1}]
assert with_stock(entries) == [entries[1]] and len(entries) == 2
```

## O que evitar

- Criar `Session`, cliente HTTP ou `datetime.now()` dentro da regra de negócio (impede o teste e viola o DIP).
- Herança só para reaproveitar código; prefira composição.
- Uma "interface" com um único implementador e nenhum motivo para trocar.
- Classes "Manager" ou "Helper" que fazem de tudo (violam o SRP).
- Variável global mutável; o estado vive em objetos que alguém injeta.
- Repository genérico em cima do SQLModel: a `Session` já é a abstração; só crie uma porta nova quando houver um segundo destino real.

## Checklist para o Pull Request

- [ ] Cada classe nova tem uma responsabilidade que cabe em uma frase sem "e".
- [ ] Dependências entram pelo construtor (nada de `Session()`, `requests` ou `now()` dentro da regra).
- [ ] Não há `if/elif` por tipo onde um Strategy ou Factory resolveria.
- [ ] Transformações de dados são funções puras com teste.
- [ ] Tem teste usando um substituto (fake) no lugar da dependência real.

## Quem faz o quê

| Frente | Foco |
|---|---|
| Samuel, robô | `Navigator` com `Nav2Navigator` e `FakeNavigator`; `BackendPort` com `BackendClient`; `Pose.from_dict`; módulos separados `api`, `waypoints`, `dispatcher`, `node` |
| Samuel, fundação | `gen_hospital.py` em funções puras (parse, raster, inflação, escrita) |
| Erik, backend | `CreateDelivery` com dependências injetadas; `PriorityPolicy`/`policy_for`; `MovementCreator`; Observer de eventos na semana 2 |
| Vieira, web | Já aplicado em `src/domain/` e `src/apresentacao/`; manter o vocabulário e documentar |
| Pedro, qualidade | `MockRobot` e `fake_backend` obedecem ao mesmo contrato do backend real (LSP); cliente HTTP e `sleep` entram pelo construtor (DIP) |
