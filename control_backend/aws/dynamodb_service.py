"""DynamoDB queries used by the HealthBand backend."""

from decimal import Decimal
from typing import Any

from boto3.dynamodb.conditions import (
    Attr,
    Key,
)


def normalize_dynamodb_value(
    value: Any,
) -> Any:
    """Convert DynamoDB Decimal values into JSON-safe numbers."""

    if isinstance(
        value,
        Decimal,
    ):
        if (
            value
            == value.to_integral_value()
        ):
            return int(
                value
            )

        return float(
            value
        )

    if isinstance(
        value,
        dict,
    ):
        return {
            key: normalize_dynamodb_value(
                item
            )
            for (
                key,
                item,
            )
            in value.items()
        }

    if isinstance(
        value,
        list,
    ):
        return [
            normalize_dynamodb_value(
                item
            )
            for item in value
        ]

    return value


class DynamoDbService:
    """Read HealthBand cloud history from DynamoDB."""

    def __init__(
        self,
        dynamodb_resource: Any,
        telemetry_table: str,
        analytics_table: str,
        events_table: str,
    ) -> None:
        self.telemetry = (
            dynamodb_resource.Table(
                telemetry_table
            )
        )

        self.analytics = (
            dynamodb_resource.Table(
                analytics_table
            )
        )

        self.events = (
            dynamodb_resource.Table(
                events_table
            )
        )

    def get_telemetry(
        self,
        device_id: str,
        start_iso: str,
        end_iso: str,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """Return raw telemetry in chronological order."""

        return self._query_range(
            table=self.telemetry,
            partition_key="deviceId",
            partition_value=device_id,
            sort_key="timestamp",
            start_value=start_iso,
            end_value=end_iso,
            limit=limit,
        )

    def get_telemetry_recent(
        self,
        device_id: str,
        start_iso: str,
        end_iso: str,
        limit: int = 100000,
    ) -> list[dict[str, Any]]:
        """Return the newest raw telemetry rows in chronological order.

        Long history views still need the most recent live telemetry even when
        local analytics has been disabled in Device Shadow. Querying newest
        first prevents a bounded request from returning only old rows.
        """

        items = self._query_range(
            table=self.telemetry,
            partition_key="deviceId",
            partition_value=device_id,
            sort_key="timestamp",
            start_value=start_iso,
            end_value=end_iso,
            limit=limit,
            scan_index_forward=False,
        )

        return list(reversed(items))

    def get_analytics(
        self,
        device_id: str,
        start_iso: str,
        end_iso: str,
        limit: int = 2000,
    ) -> list[dict[str, Any]]:
        """Return aggregate history."""

        return self._query_range(
            table=self.analytics,
            partition_key="deviceId",
            partition_value=device_id,
            sort_key="windowEnd",
            start_value=start_iso,
            end_value=end_iso,
            limit=limit,
        )

    def get_alerts(
        self,
        device_id: str,
        start_iso: str,
        end_iso: str,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """Return alert events."""

        return self._query_events(
            device_id=device_id,
            start_iso=start_iso,
            end_iso=end_iso,
            record_type="ALERT",
            limit=limit,
        )

    def get_events(
        self,
        device_id: str,
        start_iso: str,
        end_iso: str,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """Return normal device events."""

        return self._query_events(
            device_id=device_id,
            start_iso=start_iso,
            end_iso=end_iso,
            record_type="EVENT",
            limit=limit,
        )

    def get_command_responses(
        self,
        device_id: str,
        start_iso: str,
        end_iso: str,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """Return persisted command lifecycle responses."""

        return self._query_events(
            device_id=device_id,
            start_iso=start_iso,
            end_iso=end_iso,
            record_type="COMMAND_RESPONSE",
            limit=limit,
        )

    def get_command_status(
        self,
        device_id: str,
        command_id: str,
    ) -> dict[str, Any] | None:
        """Find latest persisted status for one command."""

        exclusive_start_key: (
            dict[str, Any] | None
        ) = None

        while True:
            kwargs: dict[
                str,
                Any,
            ] = {
                "KeyConditionExpression": (
                    Key(
                        "deviceId"
                    ).eq(
                        device_id
                    )
                ),
                "FilterExpression": (
                    Attr(
                        "recordType"
                    ).eq(
                        "COMMAND_RESPONSE"
                    )
                    & Attr(
                        "commandId"
                    ).eq(
                        command_id
                    )
                ),
                "ScanIndexForward": False,
                "Limit": 100,
            }

            if (
                exclusive_start_key
                is not None
            ):
                kwargs[
                    "ExclusiveStartKey"
                ] = (
                    exclusive_start_key
                )

            response = (
                self.events.query(
                    **kwargs
                )
            )

            items = (
                response.get(
                    "Items",
                    [],
                )
            )

            if items:
                return normalize_dynamodb_value(
                    items[0]
                )

            exclusive_start_key = (
                response.get(
                    "LastEvaluatedKey"
                )
            )

            if not exclusive_start_key:
                return None

    def get_latest_telemetry(
        self,
        device_id: str,
    ) -> dict[str, Any] | None:
        """Return most recent persisted telemetry item."""

        response = (
            self.telemetry.query(
                KeyConditionExpression=(
                    Key(
                        "deviceId"
                    ).eq(
                        device_id
                    )
                ),
                ScanIndexForward=False,
                Limit=1,
            )
        )

        items = (
            response.get(
                "Items",
                [],
            )
        )

        if not items:
            return None

        return normalize_dynamodb_value(
            items[0]
        )

    def _query_events(
        self,
        device_id: str,
        start_iso: str,
        end_iso: str,
        record_type: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Query shared HealthBandEvents table."""

        return self._query_range(
            table=self.events,
            partition_key="deviceId",
            partition_value=device_id,
            sort_key="timestampEventId",
            start_value=start_iso,
            end_value=(
                end_iso
                + "\uffff"
            ),
            filter_expression=(
                Attr(
                    "recordType"
                ).eq(
                    record_type
                )
            ),
            limit=limit,
        )

    def _query_range(
        self,
        table: Any,
        partition_key: str,
        partition_value: str,
        sort_key: str,
        start_value: str,
        end_value: str,
        limit: int,
        filter_expression: Any | None = None,
        scan_index_forward: bool = True,
    ) -> list[dict[str, Any]]:
        """Perform paginated DynamoDB range query."""

        items: list[
            dict[str, Any]
        ] = []

        exclusive_start_key: (
            dict[str, Any] | None
        ) = None

        while (
            len(
                items
            )
            < limit
        ):
            kwargs: dict[
                str,
                Any,
            ] = {
                "KeyConditionExpression": (
                    Key(
                        partition_key
                    ).eq(
                        partition_value
                    )
                    & Key(
                        sort_key
                    ).between(
                        start_value,
                        end_value,
                    )
                ),
                "ScanIndexForward": scan_index_forward,
                "Limit": min(
                    500,
                    limit,
                ),
            }

            if (
                filter_expression
                is not None
            ):
                kwargs[
                    "FilterExpression"
                ] = (
                    filter_expression
                )

            if (
                exclusive_start_key
                is not None
            ):
                kwargs[
                    "ExclusiveStartKey"
                ] = (
                    exclusive_start_key
                )

            response = (
                table.query(
                    **kwargs
                )
            )

            items.extend(
                response.get(
                    "Items",
                    [],
                )
            )

            exclusive_start_key = (
                response.get(
                    "LastEvaluatedKey"
                )
            )

            if not exclusive_start_key:
                break

        return [
            normalize_dynamodb_value(
                item
            )
            for item in items[
                :limit
            ]
        ]