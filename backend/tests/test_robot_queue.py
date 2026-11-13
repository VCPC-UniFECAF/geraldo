def make(client, auth, user, priority, **over):
    body = {"origin_id": "farmacia", "items": [{"item_id": "dipirona-500mg", "quantity": 1}], "priority": priority}
    body.update(over)
    r = client.post("/deliveries", json=body, headers=auth(user))
    assert r.status_code == 201, r.text
    return r.json()["id"]


def next_task(client, auth):
    return client.post("/robot/next-task", headers=auth("robo"))


def test_media_goes_before_rotina_and_fifo_within_the_same_priority(client, auth):
    rotina = make(client, auth, "medico1", "rotina")
    media_a = make(client, auth, "medico1", "media")
    media_b = make(client, auth, "medico2", "media")
    order = [next_task(client, auth).json()["id"] for _ in range(3)]
    assert order == [media_a, media_b, rotina]
    assert next_task(client, auth).status_code == 204


def test_dispatched_delivery_becomes_em_rota(client, auth):
    delivery_id = make(client, auth, "medico1", "media")
    task = next_task(client, auth)
    assert task.status_code == 200
    assert task.json()["status"] == "EM_ROTA"
    assert client.get(f"/deliveries/{delivery_id}", headers=auth("medico1")).json()["status"] == "EM_ROTA"


def test_task_carries_the_waypoints_of_origin_and_destination(client, auth):
    make(client, auth, "medico1", "media")
    body = next_task(client, auth).json()
    assert body["origin_waypoint"] == "farmacia_balcao"
    assert body["dest_waypoint"] == "cons1_entrega"
    assert body["items"] == [{"item_id": "dipirona-500mg", "quantity": 1}]


def test_critical_is_not_dispatched_until_approved(client, auth):
    make(client, auth, "medico1", "critica", origin_id="banco_sangue", items=[{"item_id": "bolsa-sangue-o-neg", "quantity": 1}])
    assert next_task(client, auth).status_code == 204


def test_only_the_robot_can_ask_for_tasks(client, auth):
    assert client.post("/robot/next-task").status_code == 401
    assert client.post("/robot/next-task", headers=auth("medico1")).status_code == 403
    assert client.post("/robot/next-task", headers=auth("admin")).status_code == 403
