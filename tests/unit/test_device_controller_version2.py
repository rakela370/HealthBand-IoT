"""Integration-style unit test for HealthBand 2.0.0 DeviceController wiring."""

from pathlib import Path

import pytest

from device_simulator.configuration.configuration_manager import (
    ConfigurationManager,
)
from device_simulator.core.device_controller import (
    DeviceController,
)
from device_simulator.storage.local_database import (
    LocalDatabase,
)
from device_simulator.storage.offline_queue import (
    OfflineQueue,
)


@pytest.mark.asyncio
async def test_version2_controller_exposes_new_runtime_features(
    tmp_path: Path,
) -> None:
    configuration_manager = ConfigurationManager(
        runtime_config_path=(
            tmp_path
            / "device_config.json"
        ),
        software_version="2.0.0",
    )

    offline_queue = OfflineQueue(
        database=LocalDatabase(
            tmp_path
            / "healthband.db"
        ),
        maximum_items=(
            configuration_manager
            .current
            .offline_queue_maximum_items
        ),
    )

    controller = DeviceController(
        device_id="test-device-v2",
        software_version="2.0.0",
        random_seed=1,
        configuration_manager=(
            configuration_manager
        ),
        offline_queue=(
            offline_queue
        ),
    )

    try:
        await controller.start()

        snapshot = (
            await controller
            .read_sensors_now()
        )

        assert (
            "oxygenSaturationPercentage"
            in snapshot.measurements
        )

        assert (
            "caloriesBurnedInInterval"
            in snapshot.measurements
        )

        assert (
            "caloriesBurnedToday"
            in snapshot.measurements
        )

        telemetry = (
            controller
            ._build_telemetry_payload(
                snapshot
            )
        )

        assert telemetry[
            "schemaVersion"
        ] == 2

        report = (
            await controller
            .create_health_report_now()
        )

        assert (
            "SPO2_MONITORING"
            in report.capabilities
        )

        assert (
            "CALORIE_ESTIMATION"
            in report.capabilities
        )

    finally:
        await controller.shutdown()