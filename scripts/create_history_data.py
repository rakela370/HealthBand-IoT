"""Generate synthetic HealthBand aggregate history in DynamoDB."""

import argparse
import json
import os
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import boto3
from dotenv import load_dotenv

from device_simulator.analytics.analytics_manager import (
    AnalyticsManager,
)
from device_simulator.analytics.calorie_estimator import (
    CalorieEstimator,
)
from device_simulator.sensors.sensor_manager import (
    SensorManager,
)
from device_simulator.simulation.scenario import (
    SimulationScenario,
)
from device_simulator.simulation.scenario_engine import (
    ScenarioEngine,
)
from device_simulator.simulation.user_profile import (
    UserProfile,
)


DEFAULT_DEVICE_ID = "healthband-device-001"
DEFAULT_TABLE_NAME = "HealthBandAnalytics"
DEFAULT_REGION = "eu-central-1"

SAMPLES_PER_HOUR = 6


def scenario_for_datetime(
    timestamp: datetime,
) -> SimulationScenario:
    """Choose a realistic deterministic scenario for one historical hour."""

    hour = (
        timestamp.hour
    )

    weekday = (
        timestamp.weekday()
    )

    if (
        hour >= 23
        or hour < 6
    ):
        return (
            SimulationScenario.SLEEPING
        )

    if hour in {
        7,
        8,
        12,
        13,
    }:
        return (
            SimulationScenario.WALKING
        )

    if (
        weekday
        in {
            1,
            3,
        }
        and hour == 18
    ):
        return (
            SimulationScenario.RUNNING
        )

    if hour == 17:
        return (
            SimulationScenario.EXERCISING
        )

    if hour == 19:
        return (
            SimulationScenario.RECOVERY
        )

    return (
        SimulationScenario.RESTING
    )


def generate_history_items(
    days: int = 30,
    device_id: str = DEFAULT_DEVICE_ID,
    seed: int = 42,
    end_time: datetime | None = None,
) -> list[dict[str, Any]]:
    """
    Generate hourly aggregate records using the real simulator models.

    One aggregate record is generated for every hour.

    HealthBand 2.0.0 historical records include simulated SpO2 analytics
    and derived estimated-calorie analytics.
    """

    if days <= 0:
        raise ValueError(
            "days must be greater than zero."
        )

    if not device_id.strip():
        raise ValueError(
            "device_id cannot be empty."
        )

    if end_time is None:
        end_time = (
            datetime.now(
                timezone.utc
            )
        )

    if (
        end_time.tzinfo
        is None
    ):
        raise ValueError(
            "end_time must be timezone-aware."
        )

    normalized_end = (
        end_time
        .astimezone(
            timezone.utc
        )
        .replace(
            minute=0,
            second=0,
            microsecond=0,
        )
    )

    start_time = (
        normalized_end
        - timedelta(
            days=days
        )
    )

    user_profile = (
        UserProfile()
    )

    calorie_estimator = (
        CalorieEstimator(
            user_profile=(
                user_profile
            )
        )
    )

    results: list[
        dict[str, Any]
    ] = []

    total_windows = (
        days
        * 24
    )

    for window_index in range(
        total_windows
    ):
        window_start = (
            start_time
            + timedelta(
                hours=window_index
            )
        )

        window_end = (
            window_start
            + timedelta(
                hours=1
            )
        )

        scenario = (
            scenario_for_datetime(
                window_start
            )
        )

        scenario_engine = (
            ScenarioEngine(
                user_profile
            )
        )

        scenario_engine.set_scenario(
            scenario
        )

        sensor_manager = (
            SensorManager(
                user_profile=(
                    user_profile
                ),
                random_seed=(
                    seed
                    + window_index
                ),
                software_version="2.0.0",
            )
        )

        analytics_manager = (
            AnalyticsManager(
                device_id=(
                    device_id
                ),
                software_version="2.0.0",
                window_sec=float(
                    SAMPLES_PER_HOUR
                ),
                spo2_minimum_threshold=92.0,
                spo2_enabled=True,
            )
        )

        analytics_result = (
            None
        )

        for sample_index in range(
            SAMPLES_PER_HOUR
        ):
            context = (
                scenario_engine
                .get_context()
            )

            snapshot = (
                sensor_manager.read_all(
                    context=context,
                    elapsed_sec=1.0,
                )
            )

            historical_timestamp = (
                window_start
                + timedelta(
                    minutes=(
                        sample_index
                        * (
                            60
                            // SAMPLES_PER_HOUR
                        )
                    )
                )
            )

            calorie_values = (
                calorie_estimator
                .estimate_interval(
                    measurements=(
                        snapshot.measurements
                    ),
                    activity_level=(
                        snapshot.activity_level
                    ),
                    scenario=(
                        snapshot.scenario
                    ),
                    elapsed_sec=(
                        3600.0
                        / SAMPLES_PER_HOUR
                    ),
                    timestamp=(
                        historical_timestamp
                    ),
                )
            )

            historical_snapshot = (
                replace(
                    snapshot,
                    measurements={
                        **snapshot.measurements,
                        **calorie_values,
                    },
                    timestamp=(
                        historical_timestamp
                    ),
                )
            )

            completed = (
                analytics_manager
                .add_snapshot(
                    snapshot=(
                        historical_snapshot
                    ),
                    elapsed_sec=1.0,
                )
            )

            if completed is not None:
                analytics_result = (
                    completed
                )

        if analytics_result is None:
            raise RuntimeError(
                "Historical analytics window "
                "did not complete."
            )

        item = (
            analytics_result
            .to_dict()
        )

        # Override timestamps so each record represents one
        # exact historical hour.
        item[
            "windowStart"
        ] = (
            window_start.isoformat()
        )

        item[
            "windowEnd"
        ] = (
            window_end.isoformat()
        )

        item[
            "historyGenerated"
        ] = (
            True
        )

        item[
            "historySource"
        ] = (
            "scripts/create_history_data.py"
        )

        item[
            "historicalScenario"
        ] = (
            scenario.value
        )

        item[
            "simulated"
        ] = (
            True
        )

        results.append(
            item
        )

    return (
        results
    )


def to_dynamodb_compatible(
    value: Any,
) -> Any:
    """
    Convert Python floating-point numbers to Decimal.

    boto3 DynamoDB resources intentionally reject normal Python floats.
    """

    serialized = (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
        )
    )

    return (
        json.loads(
            serialized,
            parse_float=Decimal,
        )
    )


def create_boto3_session(
    region: str,
    profile: str | None,
) -> boto3.Session:
    """Create AWS SDK session without hard-coded credentials."""

    if profile:
        return (
            boto3.Session(
                profile_name=(
                    profile
                ),
                region_name=(
                    region
                ),
            )
        )

    return (
        boto3.Session(
            region_name=(
                region
            )
        )
    )


def write_history_to_dynamodb(
    items: list[dict[str, Any]],
    table_name: str,
    region: str,
    profile: str | None,
) -> None:
    """Batch-write generated aggregate history to DynamoDB."""

    if not items:
        return

    session = (
        create_boto3_session(
            region=region,
            profile=profile,
        )
    )

    dynamodb = (
        session.resource(
            "dynamodb"
        )
    )

    table = (
        dynamodb.Table(
            table_name
        )
    )

    with table.batch_writer(
        overwrite_by_pkeys=[
            "deviceId",
            "windowEnd",
        ]
    ) as batch:
        for item in items:
            batch.put_item(
                Item=(
                    to_dynamodb_compatible(
                        item
                    )
                )
            )


def build_argument_parser(
    default_profile: str | None,
    default_region: str,
) -> argparse.ArgumentParser:
    """Build command-line interface."""

    parser = (
        argparse.ArgumentParser(
            description=(
                "Generate synthetic HealthBand "
                "aggregate history."
            )
        )
    )

    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help=(
            "Number of historical days. "
            "Default: 30."
        ),
    )

    parser.add_argument(
        "--device-id",
        default=(
            DEFAULT_DEVICE_ID
        ),
        help=(
            "HealthBand device identifier."
        ),
    )

    parser.add_argument(
        "--table-name",
        default=(
            DEFAULT_TABLE_NAME
        ),
        help=(
            "DynamoDB analytics table name."
        ),
    )

    parser.add_argument(
        "--region",
        default=(
            default_region
        ),
        help=(
            "AWS region."
        ),
    )

    parser.add_argument(
        "--profile",
        default=(
            default_profile
        ),
        help=(
            "Optional AWS CLI/boto3 profile."
        ),
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help=(
            "Deterministic random seed."
        ),
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Generate data but do not write "
            "anything to AWS."
        ),
    )

    return (
        parser
    )


def main() -> None:
    """Generate and optionally upload historical HealthBand analytics."""

    load_dotenv(
        override=False
    )

    default_region = (
        os.getenv(
            "AWS_REGION",
            DEFAULT_REGION,
        ).strip()
        or DEFAULT_REGION
    )

    default_profile = (
        os.getenv(
            "AWS_PROFILE",
            "",
        ).strip()
        or None
    )

    parser = (
        build_argument_parser(
            default_profile=(
                default_profile
            ),
            default_region=(
                default_region
            ),
        )
    )

    args = (
        parser.parse_args()
    )

    print(
        "Generating HealthBand "
        f"history for {args.days} day(s)..."
    )

    items = (
        generate_history_items(
            days=(
                args.days
            ),
            device_id=(
                args.device_id
            ),
            seed=(
                args.seed
            ),
        )
    )

    print(
        f"Generated {len(items)} "
        "aggregate record(s)."
    )

    if items:
        print(
            "First window:",
            items[0][
                "windowStart"
            ],
            "->",
            items[0][
                "windowEnd"
            ],
        )

        print(
            "Last window:",
            items[-1][
                "windowStart"
            ],
            "->",
            items[-1][
                "windowEnd"
            ],
        )

    if args.dry_run:
        print(
            "Dry run enabled. "
            "Nothing was written to AWS."
        )

        return

    print(
        "Writing generated history "
        f"to DynamoDB table "
        f"'{args.table_name}'..."
    )

    write_history_to_dynamodb(
        items=(
            items
        ),
        table_name=(
            args.table_name
        ),
        region=(
            args.region
        ),
        profile=(
            args.profile
        ),
    )

    print(
        "Historical HealthBand data "
        "successfully written to DynamoDB."
    )


if __name__ == "__main__":
    main()