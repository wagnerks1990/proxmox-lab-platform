from app.telemetry.subscribers import register_subscribers
from app.architecture.events import bus, DomainEvent
from app.telemetry.lifecycle_metrics import as_dict


def test_telemetry_subscriber_increment():
    register_subscribers()
    bus.publish(DomainEvent(name='RECONNECT_ATTEMPT', payload={}))
    assert as_dict()['reconnect_attempts'] >= 1
