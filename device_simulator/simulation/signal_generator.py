"""Deterministic-capable signal generation helpers."""

import random


class SignalGenerator:
    """Generates smooth simulated signal changes with optional noise."""

    def __init__(
        self,
        seed: int | None = None,
    ) -> None:
        self._random = random.Random(seed)

    def move_towards(
        self,
        current: float,
        target: float,
        max_delta: float,
        noise: float = 0.0,
        minimum: float | None = None,
        maximum: float | None = None,
    ) -> float:
        """
        Move a value gradually toward its target.

        A small random variation can be added after the deterministic
        movement.
        """

        if max_delta <= 0:
            raise ValueError(
                "max_delta must be greater than zero."
            )

        difference = target - current

        change = max(
            -max_delta,
            min(max_delta, difference),
        )

        value = current + change

        if noise > 0:
            value += self._random.uniform(
                -noise,
                noise,
            )

        if minimum is not None:
            value = max(minimum, value)

        if maximum is not None:
            value = min(maximum, value)

        return value

    def variation_factor(
        self,
        maximum_fraction: float = 0.10,
    ) -> float:
        """Return a small multiplicative variation around 1.0."""

        if maximum_fraction < 0:
            raise ValueError(
                "maximum_fraction cannot be negative."
            )

        return 1.0 + self._random.uniform(
            -maximum_fraction,
            maximum_fraction,
        )