"""Small manual client for testing HealthBand WebSocket stream."""

import asyncio
import json

import websockets


DEVICE_ID = (
    "healthband-device-001"
)

URL = (
    "ws://127.0.0.1:8000/"
    f"ws/devices/{DEVICE_ID}"
)


async def main() -> None:
    """Print five messages received from FastAPI WebSocket."""

    print(
        f"Connecting to {URL}"
    )

    async with websockets.connect(
        URL
    ) as websocket:

        for index in range(
            5
        ):
            raw = (
                await websocket.recv()
            )

            payload = (
                json.loads(
                    raw
                )
            )

            print()
            print(
                f"Message {index + 1}:"
            )

            print(
                json.dumps(
                    payload,
                    indent=2,
                    ensure_ascii=False,
                )
            )


if __name__ == "__main__":
    asyncio.run(
        main()
    )