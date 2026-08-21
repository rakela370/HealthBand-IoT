"""Unit tests for signal generation."""

from device_simulator.simulation.signal_generator import (
    SignalGenerator,
)


def test_same_seed_produces_same_values() -> None:
    generator_a = SignalGenerator(
        seed=123
    )

    generator_b = SignalGenerator(
        seed=123
    )

    values_a = [
        generator_a.move_towards(
            current=70,
            target=100,
            max_delta=5,
            noise=1,
        )
        for _ in range(5)
    ]

    values_b = [
        generator_b.move_towards(
            current=70,
            target=100,
            max_delta=5,
            noise=1,
        )
        for _ in range(5)
    ]

    assert values_a == values_b


def test_move_towards_respects_maximum_change_without_noise(
) -> None:
    generator = SignalGenerator(
        seed=1
    )

    value = generator.move_towards(
        current=70,
        target=100,
        max_delta=5,
        noise=0,
    )

    assert value == 75