from sqlalchemy import inspect, text

from app.db import create_db, make_engine

MEDIA = {"origin_id": "farmacia", "items": [{"item_id": "dipirona-500mg", "quantity": 1}], "priority": "media"}


def test_a_new_delivery_has_no_cancel_reason(client, auth):
    r = client.post("/deliveries", json=MEDIA, headers=auth("medico1"))
    assert r.status_code == 201 and r.json()["cancel_reason"] is None


def test_create_db_adds_the_cancel_reason_column_to_an_old_database(tmp_path):
    engine = make_engine(f"sqlite:///{tmp_path}/velho.db")
    with engine.begin() as conn:  # banco de antes desta mudança: tabela delivery sem cancel_reason
        conn.execute(text("CREATE TABLE delivery (id INTEGER PRIMARY KEY, origin_id TEXT, dest_id TEXT, priority TEXT, status TEXT, requested_by INTEGER, created_at TEXT)"))
    create_db(engine)
    assert "cancel_reason" in {c["name"] for c in inspect(engine).get_columns("delivery")}
    create_db(engine)  # de novo: não pode falhar
