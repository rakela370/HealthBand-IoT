"""Provision AWS resources required by HealthBand OTA delivery."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv


DEFAULT_REGION = "eu-central-1"
DEFAULT_THING_NAME = "healthband-device-001"
DEFAULT_BACKEND_CLIENT_ID = "healthband-control-backend"
DEFAULT_ROLE_NAME = "HealthBandIoTJobsS3Role"
DEFAULT_ROLE_POLICY_NAME = "HealthBandOtaS3Read"
DEFAULT_DEVICE_POLICY_NAME = "HealthBandDeviceJobsPolicy"
DEFAULT_BACKEND_POLICY_NAME = "HealthBandBackendSubscriberPolicy"
DEFAULT_S3_PREFIX = "releases"
DEFAULT_PRESIGNED_EXPIRY_SEC = 900
DEFAULT_RESOURCE_STATE_PATH = "runtime/ota_aws_resources.json"


BACKEND_SUBSCRIBE_SUFFIXES = (
    "telemetry",
    "analytics",
    "alerts",
    "health",
    "events",
    "commands/response",
    "presence",
    "ota/status",
)


def normalized_pem(value: str) -> str:
    """Normalize PEM text for certificate comparison."""

    return "".join(value.split())


def normalized_prefix(value: str) -> str:
    """Return an S3 prefix without leading/trailing slashes."""

    return value.strip().strip("/") or DEFAULT_S3_PREFIX


def make_session(
    region: str,
    profile: str | None,
) -> boto3.Session:
    """Create a boto3 session using the configured region/profile."""

    kwargs: dict[str, str] = {
        "region_name": region,
    }

    if profile:
        kwargs["profile_name"] = profile

    return boto3.Session(**kwargs)


def ensure_bucket(
    s3: Any,
    bucket: str,
    region: str,
) -> None:
    """Create/harden the private OTA bucket when required."""

    try:
        s3.head_bucket(Bucket=bucket)
        print(
            "S3 bucket already exists and is accessible: "
            f"{bucket}"
        )

    except ClientError as exc:
        code = str(
            exc.response.get("Error", {}).get("Code", "")
        )

        if code not in {
            "404",
            "NoSuchBucket",
            "NotFound",
        }:
            raise

        create_args: dict[str, Any] = {
            "Bucket": bucket,
        }

        if region != "us-east-1":
            create_args["CreateBucketConfiguration"] = {
                "LocationConstraint": region,
            }

        s3.create_bucket(**create_args)
        print(f"Created S3 bucket: {bucket}")

    s3.put_public_access_block(
        Bucket=bucket,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
    )

    s3.put_bucket_encryption(
        Bucket=bucket,
        ServerSideEncryptionConfiguration={
            "Rules": [
                {
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "AES256",
                    }
                }
            ]
        },
    )

    s3.put_bucket_versioning(
        Bucket=bucket,
        VersioningConfiguration={
            "Status": "Enabled",
        },
    )


def ensure_jobs_role(
    iam: Any,
    account_id: str,
    region: str,
    bucket: str,
    s3_prefix: str,
) -> str:
    """Create/update the IAM role used by AWS IoT Jobs for S3 downloads."""

    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "iot.amazonaws.com",
                },
                "Action": "sts:AssumeRole",
                "Condition": {
                    "StringEquals": {
                        "aws:SourceAccount": account_id,
                    },
                    "ArnLike": {
                        "aws:SourceArn": (
                            "arn:aws:iot:"
                            f"{region}:"
                            f"{account_id}:job/*"
                        ),
                    },
                },
            }
        ],
    }

    try:
        response = iam.get_role(
            RoleName=DEFAULT_ROLE_NAME
        )
        role_arn = response["Role"]["Arn"]

        iam.update_assume_role_policy(
            RoleName=DEFAULT_ROLE_NAME,
            PolicyDocument=json.dumps(trust_policy),
        )

        print(
            "IAM role already exists: "
            f"{DEFAULT_ROLE_NAME}"
        )

    except iam.exceptions.NoSuchEntityException:
        response = iam.create_role(
            RoleName=DEFAULT_ROLE_NAME,
            Description=(
                "Allows AWS IoT Jobs to generate presigned "
                "download URLs for HealthBand OTA artifacts."
            ),
            AssumeRolePolicyDocument=json.dumps(
                trust_policy
            ),
        )
        role_arn = response["Role"]["Arn"]

        print(
            "Created IAM role: "
            f"{DEFAULT_ROLE_NAME}"
        )

    object_arn = (
        f"arn:aws:s3:::{bucket}/"
        f"{s3_prefix}/*"
    )

    read_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "ReadHealthBandOtaObjects",
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                ],
                "Resource": object_arn,
            },
            {
                "Sid": "ReadHealthBandOtaBucketLocation",
                "Effect": "Allow",
                "Action": [
                    "s3:GetBucketLocation",
                ],
                "Resource": (
                    f"arn:aws:s3:::{bucket}"
                ),
            },
        ],
    }

    iam.put_role_policy(
        RoleName=DEFAULT_ROLE_NAME,
        PolicyName=DEFAULT_ROLE_POLICY_NAME,
        PolicyDocument=json.dumps(read_policy),
    )

    return str(role_arn)


def _decode_policy_document(
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


def upsert_iot_policy(
    iot: Any,
    policy_name: str,
    policy_document: dict[str, Any],
) -> None:
    """Create or safely update an AWS IoT policy."""

    document = json.dumps(
        policy_document,
        separators=(",", ":"),
    )

    try:
        existing = iot.get_policy(
            policyName=policy_name
        )

    except iot.exceptions.ResourceNotFoundException:
        iot.create_policy(
            policyName=policy_name,
            policyDocument=document,
        )
        print(
            "Created IoT policy: "
            f"{policy_name}"
        )
        return

    existing_document = _decode_policy_document(
        existing.get("policyDocument")
    )

    if existing_document == policy_document:
        print(
            "IoT policy already up to date: "
            f"{policy_name}"
        )
        return

    versions = iot.list_policy_versions(
        policyName=policy_name
    )["policyVersions"]

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
                item["versionId"]
            ),
        )

        if not candidates:
            raise RuntimeError(
                "Cannot create another version of IoT policy "
                f"'{policy_name}' because no non-default "
                "version can be deleted."
            )

        iot.delete_policy_version(
            policyName=policy_name,
            policyVersionId=(
                candidates[0]["versionId"]
            ),
        )

    response = iot.create_policy_version(
        policyName=policy_name,
        policyDocument=document,
        setAsDefault=True,
    )

    print(
        "Updated IoT policy: "
        f"{policy_name} -> version "
        f"{response['policyVersionId']}"
    )


def find_certificate_arn_by_pem(
    iot: Any,
    certificate_path: Path,
) -> str:
    """Find the AWS IoT certificate matching a local PEM file."""

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
            certificate_id = certificate[
                "certificateId"
            ]

            description = iot.describe_certificate(
                certificateId=certificate_id
            )["certificateDescription"]

            candidate_pem = description.get(
                "certificatePem"
            )

            if (
                isinstance(candidate_pem, str)
                and normalized_pem(candidate_pem)
                == target
            ):
                return str(
                    description["certificateArn"]
                )

    raise RuntimeError(
        "Unable to find the AWS IoT certificate matching "
        f"{certificate_path}."
    )


def build_device_jobs_policy(
    *,
    region: str,
    account_id: str,
    thing_name: str,
) -> dict[str, Any]:
    """Build the least-privilege policy used by the OTA supervisor."""

    prefix = (
        "arn:aws:iot:"
        f"{region}:"
        f"{account_id}"
    )

    jobs_root = (
        f"$aws/things/{thing_name}/jobs"
    )

    healthband_root = (
        f"healthband/{thing_name}"
    )

    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "OtaSupervisorConnect",
                "Effect": "Allow",
                "Action": [
                    "iot:Connect",
                ],
                "Resource": [
                    (
                        f"{prefix}:client/"
                        f"{thing_name}-ota"
                    )
                ],
            },
            {
                "Sid": "OtaJobsPublishReceive",
                "Effect": "Allow",
                "Action": [
                    "iot:Publish",
                    "iot:Receive",
                ],
                "Resource": [
                    (
                        f"{prefix}:topic/"
                        f"{jobs_root}/*"
                    )
                ],
            },
            {
                "Sid": "OtaJobsSubscribe",
                "Effect": "Allow",
                "Action": [
                    "iot:Subscribe",
                ],
                "Resource": [
                    (
                        f"{prefix}:topicfilter/"
                        f"{jobs_root}/*"
                    )
                ],
            },
            {
                "Sid": "OtaPresenceSubscribe",
                "Effect": "Allow",
                "Action": [
                    "iot:Subscribe",
                ],
                "Resource": [
                    (
                        f"{prefix}:topicfilter/"
                        f"{healthband_root}/presence"
                    )
                ],
            },
            {
                "Sid": "OtaPresenceReceive",
                "Effect": "Allow",
                "Action": [
                    "iot:Receive",
                ],
                "Resource": [
                    (
                        f"{prefix}:topic/"
                        f"{healthband_root}/presence"
                    )
                ],
            },
            {
                "Sid": "OtaPublishStatusAndEvents",
                "Effect": "Allow",
                "Action": [
                    "iot:Publish",
                ],
                "Resource": [
                    (
                        f"{prefix}:topic/"
                        f"{healthband_root}/ota/status"
                    ),
                    (
                        f"{prefix}:topic/"
                        f"{healthband_root}/events"
                    ),
                ],
            },
        ],
    }


def build_backend_subscriber_policy(
    *,
    region: str,
    account_id: str,
    thing_name: str,
    backend_client_id: str,
) -> dict[str, Any]:
    """Build the complete backend MQTT subscriber policy."""

    prefix = (
        "arn:aws:iot:"
        f"{region}:"
        f"{account_id}"
    )

    topic_root = (
        f"healthband/{thing_name}"
    )

    topic_filters = [
        (
            f"{prefix}:topicfilter/"
            f"{topic_root}/{suffix}"
        )
        for suffix in BACKEND_SUBSCRIBE_SUFFIXES
    ]

    receive_topics = [
        (
            f"{prefix}:topic/"
            f"{topic_root}/{suffix}"
        )
        for suffix in BACKEND_SUBSCRIBE_SUFFIXES
    ]

    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "BackendConnect",
                "Effect": "Allow",
                "Action": "iot:Connect",
                "Resource": (
                    f"{prefix}:client/"
                    f"{backend_client_id}"
                ),
            },
            {
                "Sid": "BackendSubscribe",
                "Effect": "Allow",
                "Action": "iot:Subscribe",
                "Resource": topic_filters,
            },
            {
                "Sid": "BackendReceive",
                "Effect": "Allow",
                "Action": "iot:Receive",
                "Resource": receive_topics,
            },
        ],
    }


def main() -> None:
    """Provision/align Module 12 AWS resources."""

    project_root = Path.cwd()

    load_dotenv(
        project_root / ".env",
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

    backend_client_id = (
        os.getenv(
            "BACKEND_MQTT_CLIENT_ID",
            DEFAULT_BACKEND_CLIENT_ID,
        ).strip()
        or DEFAULT_BACKEND_CLIENT_ID
    )

    s3_prefix = normalized_prefix(
        os.getenv(
            "OTA_S3_PREFIX",
            DEFAULT_S3_PREFIX,
        )
    )

    try:
        presigned_expiry = int(
            os.getenv(
                "OTA_PRESIGNED_URL_EXPIRES_SEC",
                os.getenv(
                    "OTA_PRESIGNED_URL_EXPIRY_SEC",
                    str(DEFAULT_PRESIGNED_EXPIRY_SEC),
                ),
            )
        )
    except ValueError as exc:
        raise RuntimeError(
            "OTA presigned URL expiry must be an integer."
        ) from exc

    if not 60 <= presigned_expiry <= 3600:
        raise RuntimeError(
            "OTA presigned URL expiry must be between "
            "60 and 3600 seconds."
        )

    session = make_session(
        region,
        profile,
    )

    sts = session.client("sts")
    s3 = session.client("s3")
    iam = session.client("iam")
    iot = session.client("iot")

    account_id = str(
        sts.get_caller_identity()["Account"]
    )

    bucket = (
        os.getenv(
            "OTA_S3_BUCKET",
            "",
        ).strip()
        or (
            "healthband-ota-"
            f"{account_id}-"
            f"{region}"
        )
    ).lower()

    ensure_bucket(
        s3,
        bucket,
        region,
    )

    role_arn = ensure_jobs_role(
        iam,
        account_id,
        region,
        bucket,
        s3_prefix,
    )

    device_policy = build_device_jobs_policy(
        region=region,
        account_id=account_id,
        thing_name=thing_name,
    )

    upsert_iot_policy(
        iot,
        DEFAULT_DEVICE_POLICY_NAME,
        device_policy,
    )

    principals = iot.list_thing_principals(
        thingName=thing_name
    ).get(
        "principals",
        [],
    )

    if not principals:
        raise RuntimeError(
            f"Thing '{thing_name}' has no attached "
            "certificate principal."
        )

    for principal in principals:
        iot.attach_policy(
            policyName=DEFAULT_DEVICE_POLICY_NAME,
            target=principal,
        )

    backend_cert_value = os.getenv(
        "BACKEND_IOT_CERT_PATH",
        (
            "certificates/"
            "healthband-control-backend/"
            "backend.pem.crt"
        ),
    ).strip()

    backend_cert_path = Path(
        backend_cert_value
    ).expanduser()

    if not backend_cert_path.is_absolute():
        backend_cert_path = (
            project_root / backend_cert_path
        )

    backend_cert_path = backend_cert_path.resolve()

    if not backend_cert_path.is_file():
        raise FileNotFoundError(
            "Backend certificate does not exist: "
            f"{backend_cert_path}. "
            "Run infrastructure/iot_policies/"
            "setup_backend_subscriber.py first if needed."
        )

    backend_certificate_arn = (
        find_certificate_arn_by_pem(
            iot,
            backend_cert_path,
        )
    )

    backend_policy = build_backend_subscriber_policy(
        region=region,
        account_id=account_id,
        thing_name=thing_name,
        backend_client_id=backend_client_id,
    )

    upsert_iot_policy(
        iot,
        DEFAULT_BACKEND_POLICY_NAME,
        backend_policy,
    )

    iot.attach_policy(
        policyName=DEFAULT_BACKEND_POLICY_NAME,
        target=backend_certificate_arn,
    )

    resource_state_value = os.getenv(
        "OTA_RESOURCE_STATE_PATH",
        DEFAULT_RESOURCE_STATE_PATH,
    ).strip() or DEFAULT_RESOURCE_STATE_PATH

    runtime_file = Path(
        resource_state_value
    ).expanduser()

    if not runtime_file.is_absolute():
        runtime_file = (
            project_root / runtime_file
        )

    runtime_file = runtime_file.resolve()
    runtime_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    resource_state = {
        "region": region,
        "accountId": account_id,
        "thingName": thing_name,
        "bucket": bucket,
        "s3Prefix": s3_prefix,
        "jobsRoleArn": role_arn,
        "presignedUrlExpirySec": presigned_expiry,
        "deviceJobsPolicy": DEFAULT_DEVICE_POLICY_NAME,
        "backendSubscriberPolicy": DEFAULT_BACKEND_POLICY_NAME,
    }

    runtime_file.write_text(
        json.dumps(
            resource_state,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print("HealthBand OTA AWS provisioning complete.")
    print(f"Region: {region}")
    print(f"Thing: {thing_name}")
    print(f"Private OTA bucket: {bucket}")
    print(f"S3 prefix: {s3_prefix}")
    print(f"IoT Jobs S3 role: {role_arn}")
    print(
        "Device Jobs policy: "
        f"{DEFAULT_DEVICE_POLICY_NAME}"
    )
    print(
        "Backend subscriber policy: "
        f"{DEFAULT_BACKEND_POLICY_NAME}"
    )
    print(
        "Saved local resource metadata: "
        f"{runtime_file}"
    )
    print()
    print(
        "No secret credentials were written to the project."
    )


if __name__ == "__main__":
    main()