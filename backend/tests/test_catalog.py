def test_locations_require_login(client):
    assert client.get("/locations").status_code == 401


def test_locations_list_includes_waypoints(client, auth):
    r = client.get("/locations", headers=auth("medico1"))
    assert r.status_code == 200
    by_id = {l["id"]: l for l in r.json()}
    assert by_id["farmacia"]["waypoint"] == "farmacia_balcao"
    assert by_id["recepcao"]["waypoint"] is None
    assert by_id["recepcao"]["has_stock"] is False


def test_stock_can_be_filtered_by_location(client, auth):
    r = client.get("/stock", params={"location_id": "farmacia"}, headers=auth("medico1"))
    assert r.status_code == 200
    assert r.json() == [
        {"location_id": "farmacia", "item_id": "dipirona-500mg", "item_name": "Dipirona 500 mg", "quantity": 420, "reserved": 0, "minimum": 100}
    ]
    assert len(client.get("/stock", headers=auth("medico1")).json()) == 3
