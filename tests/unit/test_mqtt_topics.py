"""Unit tests for HealthBand MQTT topic construction."""

import pytest

from device_simulator.communication.mqtt_topics import (
    MqttTopics,
)


def test_healthband_topics_match_specification() -> None:
    topics = MqttTopics(
        "healthband-device-001"
    )

    assert topics.telemetry == (
        "healthband/healthband-device-001/telemetry"
    )

    assert topics.analytics == (
        "healthband/healthband-device-001/analytics"
    )

    assert topics.alerts == (
        "healthband/healthband-device-001/alerts"
    )

    assert topics.health == (
        "healthband/healthband-device-001/health"
    )

    assert topics.events == (
        "healthband/healthband-device-001/events"
    )

    assert topics.commands_request == (
        "healthband/healthband-device-001/"
        "commands/request"
    )

    assert topics.commands_response == (
        "healthband/healthband-device-001/"
        "commands/response"
    )

    assert topics.presence == (
        "healthband/healthband-device-001/presence"
    )


def test_empty_device_id_is_rejected() -> None:
    with pytest.raises(
        ValueError
    ):
        MqttTopics(
            "   "
        )