import os
import sys
import shutil
from pathlib import Path
import boto3
from botocore.exceptions import ClientError

def main():
    region = os.getenv("AWS_REGION", "eu-central-1")
    policy_name = "HealthBandBackendSubscriberPolicy"
    client_id = "healthband-control-backend"

    # Korijenski direktorij projekta
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent.parent
    os.chdir(repo_root)

    # Boto3 sesija i klijenti
    try:
        session = boto3.Session(region_name=region)
        sts_client = session.client("sts")
        iot_client = session.client("iot")
        account_id = sts_client.get_caller_identity()["Account"]
    except Exception as e:
        print(f"Greška pri inicijalizaciji AWS klijenta: {e}")
        sys.exit(1)

    template_path = repo_root / "infrastructure" / "iot_policies" / "healthband-backend-subscriber-policy.template.json"
    local_policy_path = repo_root / "infrastructure" / "iot_policies" / "healthband-backend-subscriber-policy.local.json"

    if not template_path.exists():
        print(f"Greška: Template fajl ne postoji: {template_path}")
        sys.exit(1)

    with open(template_path, "r", encoding="utf-8") as f:
        template_content = f.read()

    policy_document = template_content.replace("YOUR_AWS_ACCOUNT_ID", account_id)

    with open(local_policy_path, "w", encoding="utf-8") as f:
        f.write(policy_document)

    # 1. Projera i kreiranje IoT Policy-ja
    try:
        iot_client.get_policy(policyName=policy_name)
        print(f"IoT policy already exists: {policy_name}")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            print(f"Creating IoT policy: {policy_name}")
            iot_client.create_policy(
                policyName=policy_name,
                policyDocument=policy_document
            )
        else:
            print(f"Greška pri provjeri IoT policy-ja: {e}")
            sys.exit(1)

    # 2. Kreiranje certifikata za backend
    cert_dir = repo_root / "certificates" / "healthband-control-backend"
    cert_dir.mkdir(parents=True, exist_ok=True)

    cert_path = cert_dir / "backend.pem.crt"
    private_key_path = cert_dir / "backend.private.key"
    public_key_path = cert_dir / "backend.public.key"
    cert_arn_path = cert_dir / "certificate_arn.txt"

    if not cert_path.exists() or not private_key_path.exists():
        print("Creating separate backend X.509 certificate...")
        res = iot_client.create_keys_and_certificate(setAsActive=True)

        cert_arn = res["certificateArn"]
        cert_pem = res["certificatePem"]
        key_pair = res["keyPair"]

        with open(cert_path, "w", encoding="utf-8") as f:
            f.write(cert_pem)
        with open(private_key_path, "w", encoding="utf-8") as f:
            f.write(key_pair["PrivateKey"])
        with open(public_key_path, "w", encoding="utf-8") as f:
            f.write(key_pair["PublicKey"])
        with open(cert_arn_path, "w", encoding="utf-8") as f:
            f.write(cert_arn)
    else:
        print("Backend certificate already exists.")

    # 3. Kopiranje Root CA certifikata
    device_ca_path = repo_root / "certificates" / "healthband-device-001" / "AmazonRootCA1.pem"
    backend_ca_path = cert_dir / "AmazonRootCA1.pem"

    if not backend_ca_path.exists():
        if not device_ca_path.exists():
            print("Greška: AmazonRootCA1.pem nije pronađen u certifikatima uređaja.")
            sys.exit(1)
        shutil.copy(device_ca_path, backend_ca_path)

    # 4. Povezivanje policy-ja i certifikata
    if not cert_arn_path.exists():
        print("Greška: certificate_arn.txt nedostaje.")
        sys.exit(1)

    with open(cert_arn_path, "r", encoding="utf-8") as f:
        certificate_arn = f.read().strip()

    print("Attaching backend IoT policy...")
    try:
        iot_client.attach_policy(
            policyName=policy_name,
            target=certificate_arn
        )
    except ClientError as e:
        print(f"Greška pri spajanju policy-ja: {e}")
        sys.exit(1)

    print("\nBackend MQTT identity is ready.")
    print(f"Client ID: {client_id}")
    print(f"Policy: {policy_name}")

if __name__ == "__main__":
    main()