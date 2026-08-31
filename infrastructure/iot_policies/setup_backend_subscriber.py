"""Provision the dedicated HealthBand backend MQTT identity and policy."""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv


POLICY_NAME = "HealthBandBackendSubscriberPolicy"
DEFAULT_REGION = "eu-central-1"
DEFAULT_THING_NAME = "healthband-device-001"
DEFAULT_CLIENT_ID = "healthband-control-backend"


def normalized_pem(value: str) -> str:
    """Normalize PEM text for certificate comparison."""

    return "".join(value.split())


def decode_policy_document(
    value: Any,
) -> dict[str, Any] | None:
    """Decode an AWS IoT policy document returned by get_policy."""

    if isinstance(value, dict):
        return value

    if not isinstance(value, str):
        return None

    for candidate in (
        value,
        unquote(value),
    ):
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue

        if isinstance(parsed, dict):
            return parsed

    return None


def upsert_policy(
    iot: Any,
    policy_document: dict[str, Any],
) -> None:
    """Create or update the backend subscriber policy."""

    document = json.dumps(
        policy_document,
        separators=(",", ":"),
    )

    try:
        existing = iot.get_policy(
            policyName=POLICY_NAME
        )

    except iot.exceptions.ResourceNotFoundException:
        iot.create_policy(
            policyName=POLICY_NAME,
            policyDocument=document,
        )

        print(
            f"Created IoT policy: {POLICY_NAME}"
        )

        return

    current = decode_policy_document(
        existing.get(
            "policyDocument"
        )
    )

    if current == policy_document:
        print(
            f"IoT policy already up to date: {POLICY_NAME}"
        )

        return

    versions = iot.list_policy_versions(
        policyName=POLICY_NAME
    )[
        "policyVersions"
    ]

    if len(versions) >= 5:
        candidates = sorted(
            (
                item
                for item in versions
                if not item.get(
                    "isDefaultVersion",
                    False,
                )
            ),
            key=lambda item: int(
                item[
                    "versionId"
                ]
            ),
        )

        if not candidates:
            raise RuntimeError(
                "No non-default IoT policy version can be "
                "deleted before creating a new version."
            )

        iot.delete_policy_version(
            policyName=POLICY_NAME,
            policyVersionId=(
                candidates[
                    0
                ][
                    "versionId"
                ]
            ),
        )

    response = iot.create_policy_version(
        policyName=POLICY_NAME,
        policyDocument=document,
        setAsDefault=True,
    )

    print(
        f"Updated IoT policy: {POLICY_NAME} -> "
        f"version {response['policyVersionId']}"
    )


def find_certificate_arn_by_pem(
    iot: Any,
    certificate_path: Path,
) -> str:
    """Return the AWS certificate ARN matching the local PEM."""

    target = normalized_pem(
        certificate_path.read_text(
            encoding="utf-8"
        )
    )

    paginator = iot.get_paginator(
        "list_certificates"
    )

    for page in paginator.paginate(
        pageSize=100
    ):
        for certificate in page.get(
            "certificates",
            [],
        ):
            description = iot.describe_certificate(
                certificateId=(
                    certificate[
                        "certificateId"
                    ]
                )
            )[
                "certificateDescription"
            ]

            pem = description.get(
                "certificatePem"
            )

            if (
                isinstance(
                    pem,
                    str,
                )
                and normalized_pem(
                    pem
                )
                == target
            ):
                return str(
                    description[
                        "certificateArn"
                    ]
                )

    raise RuntimeError(
        "Local backend certificate exists, but no matching "
        "AWS IoT certificate was found."
    )


def render_policy(
    template_path: Path,
    *,
    region: str,
    account_id: str,
    thing_name: str,
    client_id: str,
) -> dict[str, Any]:
    """Render and validate the backend subscriber policy template."""

    text = template_path.read_text(
        encoding="utf-8"
    )

    replacements = {
        "YOUR_AWS_REGION":
            region,

        "YOUR_AWS_ACCOUNT_ID":
            account_id,

        "YOUR_THING_NAME":
            thing_name,

        "YOUR_BACKEND_CLIENT_ID":
            client_id,
    }

    for (
        source,
        target,
    ) in replacements.items():
        text = text.replace(
            source,
            target,
        )

    data = json.loads(
        text
    )

    if not isinstance(
        data,
        dict,
    ):
        raise RuntimeError(
            "Backend IoT policy template must render "
            "to a JSON object."
        )

    return data


def main() -> None:
    """Create/align the backend MQTT certificate and subscriber policy."""

    script_dir = (
        Path(__file__)
        .resolve()
        .parent
    )

    repo_root = (
        script_dir
        .parent
        .parent
    )

    load_dotenv(
        repo_root
        / ".env",
        override=False,
    )

    region = (
        os.getenv(
            "AWS_REGION",
            DEFAULT_REGION,
        ).strip()
        or DEFAULT_REGION
    )

    profile = (
        os.getenv(
            "AWS_PROFILE",
            "",
        ).strip()
        or None
    )

    thing_name = (
        os.getenv(
            "HEALTHBAND_DEVICE_ID",
            DEFAULT_THING_NAME,
        ).strip()
        or DEFAULT_THING_NAME
    )

    client_id = (
        os.getenv(
            "BACKEND_MQTT_CLIENT_ID",
            DEFAULT_CLIENT_ID,
        ).strip()
        or DEFAULT_CLIENT_ID
    )

    session_kwargs: dict[
        str,
        str,
    ] = {
        "region_name":
            region,
    }

    if profile:
        session_kwargs[
            "profile_name"
        ] = (
            profile
        )

    try:
        session = boto3.Session(
            **session_kwargs
        )

        sts_client = (
            session.client(
                "sts"
            )
        )

        iot_client = (
            session.client(
                "iot"
            )
        )

        account_id = str(
            sts_client
            .get_caller_identity()[
                "Account"
            ]
        )

    except Exception as exc:
        print(
            "Greška pri inicijalizaciji AWS klijenta: "
            f"{exc}"
        )

        sys.exit(
            1
        )

    template_path = (
        script_dir
        / (
            "healthband-backend-"
            "subscriber-policy.template.json"
        )
    )

    local_policy_path = (
        script_dir
        / (
            "healthband-backend-"
            "subscriber-policy.local.json"
        )
    )

    if not (
        template_path
        .is_file()
    ):
        print(
            "Greška: Template fajl ne postoji: "
            f"{template_path}"
        )

        sys.exit(
            1
        )

    policy_document = render_policy(
        template_path,
        region=(
            region
        ),
        account_id=(
            account_id
        ),
        thing_name=(
            thing_name
        ),
        client_id=(
            client_id
        ),
    )

    local_policy_path.write_text(
        json.dumps(
            policy_document,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    try:
        upsert_policy(
            iot_client,
            policy_document,
        )

    except ClientError as exc:
        print(
            "Greška pri kreiranju/ažuriranju "
            "IoT policy-ja: "
            f"{exc}"
        )

        sys.exit(
            1
        )

    cert_dir = (
        repo_root
        / "certificates"
        / "healthband-control-backend"
    )

    cert_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    cert_path = (
        cert_dir
        / "backend.pem.crt"
    )

    private_key_path = (
        cert_dir
        / "backend.private.key"
    )

    public_key_path = (
        cert_dir
        / "backend.public.key"
    )

    cert_arn_path = (
        cert_dir
        / "certificate_arn.txt"
    )

    if (
        not cert_path.is_file()
        or not private_key_path.is_file()
    ):
        print(
            "Creating separate backend X.509 certificate..."
        )

        response = (
            iot_client
            .create_keys_and_certificate(
                setAsActive=True
            )
        )

        certificate_arn = str(
            response[
                "certificateArn"
            ]
        )

        cert_path.write_text(
            response[
                "certificatePem"
            ],
            encoding="utf-8",
        )

        private_key_path.write_text(
            response[
                "keyPair"
            ][
                "PrivateKey"
            ],
            encoding="utf-8",
        )

        public_key_path.write_text(
            response[
                "keyPair"
            ][
                "PublicKey"
            ],
            encoding="utf-8",
        )

        cert_arn_path.write_text(
            certificate_arn,
            encoding="utf-8",
        )

    else:
        print(
            "Backend certificate already exists."
        )

        try:
            certificate_arn = (
                find_certificate_arn_by_pem(
                    iot_client,
                    cert_path,
                )
            )

        except RuntimeError as exc:
            print(
                f"Greška: {exc}"
            )

            sys.exit(
                1
            )

        cert_arn_path.write_text(
            certificate_arn,
            encoding="utf-8",
        )

    device_ca_path = (
        repo_root
        / "certificates"
        / thing_name
        / "AmazonRootCA1.pem"
    )

    backend_ca_path = (
        cert_dir
        / "AmazonRootCA1.pem"
    )

    if not (
        backend_ca_path
        .is_file()
    ):
        if not (
            device_ca_path
            .is_file()
        ):
            print(
                "Greška: AmazonRootCA1.pem nije pronađen "
                "u certifikatima uređaja."
            )

            sys.exit(
                1
            )

        shutil.copy(
            device_ca_path,
            backend_ca_path,
        )

    try:
        iot_client.attach_policy(
            policyName=(
                POLICY_NAME
            ),
            target=(
                certificate_arn
            ),
        )

    except ClientError as exc:
        print(
            "Greška pri spajanju policy-ja i certifikata: "
            f"{exc}"
        )

        sys.exit(
            1
        )

    print()

    print(
        "Backend MQTT identity is ready."
    )

    print(
        f"Client ID: {client_id}"
    )

    print(
        f"Thing: {thing_name}"
    )

    print(
        f"Policy: {POLICY_NAME}"
    )

    print(
        f"Certificate ARN: {certificate_arn}"
    )

    print(
        f"Rendered policy: {local_policy_path}"
    )


if __name__ == "__main__":
    main()