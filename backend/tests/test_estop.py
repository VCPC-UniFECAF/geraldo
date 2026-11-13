import pytest

from app.estop import EstopStore, get_estop
from app.events import EstopChanged
from app.main import app


@pytest.fixture(autouse=True)
def fresh_store(client):
    store = EstopStore()
    app.dependency_overrides[get_estop] = lambda: store
    yield store
    app.dependency_overrides.pop(get_estop, None)


def test_starts_off_and_the_robot_reads_the_state(client, auth):
    r = client.get("/robot/estop", headers=auth("robo"))
    assert r.status_code == 200 and r.json() == {"active": False}


@pytest.mark.parametrize("user", ["admin", "farmaceutico1"])
def test_panel_turns_the_emergency_on_and_off(client, auth, user):
    assert client.post("/robot/estop", json={"active": True}, headers=auth(user)).status_code == 204
    assert client.get("/robot/estop", headers=auth("robo")).json() == {"active": True}
    assert client.post("/robot/estop", json={"active": False}, headers=auth(user)).status_code == 204
    assert client.get("/robot/estop", headers=auth("robo")).json() == {"active": False}


def test_the_change_is_announced_to_the_observers(client, auth, spy):
    client.post("/robot/estop", json={"active": True}, headers=auth("farmaceutico1"))
    assert spy.events == [EstopChanged(True, "farmaceutico1")]


def test_roles_and_authentication(client, auth):
    assert client.post("/robot/estop", json={"active": True}).status_code == 401
    assert client.get("/robot/estop").status_code == 401
    for user in ("medico1", "enfermeiro1", "robo"):
        assert client.post("/robot/estop", json={"active": True}, headers=auth(user)).status_code == 403, user
    for user in ("medico1", "admin", "farmaceutico1"):
        assert client.get("/robot/estop", headers=auth(user)).status_code == 403, user


@pytest.mark.parametrize("body", [{}, {"active": "talvez"}, {"active": "true"}, {"active": 1}, {"ativo": True}])
def test_invalid_body_is_422(client, auth, body):
    assert client.post("/robot/estop", json=body, headers=auth("admin")).status_code == 422
