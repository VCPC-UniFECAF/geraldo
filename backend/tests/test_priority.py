from app.models import DeliveryStatus, Priority
from app.priority import policy_for


def test_rank_orders_critica_media_rotina():
    ranks = [policy_for(p).rank for p in (Priority.critica, Priority.media, Priority.rotina)]
    assert ranks == sorted(ranks) and len(set(ranks)) == 3


def test_only_critica_starts_pending_approval():
    assert policy_for(Priority.critica).initial_status == DeliveryStatus.PENDENTE_APROVACAO
    assert policy_for(Priority.media).initial_status == DeliveryStatus.NA_FILA
    assert policy_for(Priority.rotina).initial_status == DeliveryStatus.NA_FILA


def test_every_priority_has_its_own_policy():
    for priority in Priority:
        assert policy_for(priority).priority == priority
