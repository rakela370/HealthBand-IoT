import os
import json
import time
import boto3

REGION = "eu-central-1"

sts = boto3.client("sts", region_name=REGION)
iam = boto3.client("iam", region_name=REGION)
iot = boto3.client("iot", region_name=REGION)

# 1. Resolving Account ID
account_id = sts.get_caller_identity()["Account"]
role_name = "HealthBandIoTRulesDynamoDBRole"
role_arn = f"arn:aws:iam::{account_id}:role/{role_name}"

print(f"AWS account resolved: {account_id}")
print(f"IoT Rule role ARN: {role_arn}\n")

# 2. IAM Role Setup
trust_policy_path = "infrastructure/iot_rules/healthband-iot-dynamodb-trust-policy.json"
with open(trust_policy_path, "r", encoding="utf-8") as f:
    trust_policy_doc = f.read()

try:
    iam.get_role(RoleName=role_name)
    print(f"IAM role already exists: {role_name}")
except Exception:
    print(f"Creating IAM role: {role_name}")
    iam.create_role(
        RoleName=role_name,
        AssumeRolePolicyDocument=trust_policy_doc
    )

# 3. Policy Setup
perm_template_path = "infrastructure/iot_rules/healthband-iot-dynamodb-permissions.template.json"
perm_local_path = "infrastructure/iot_rules/healthband-iot-dynamodb-permissions.local.json"

with open(perm_template_path, "r", encoding="utf-8") as f:
    perm_content = f.read().replace("YOUR_AWS_ACCOUNT_ID", account_id)

with open(perm_local_path, "w", encoding="utf-8") as f:
    f.write(perm_content)

print("Attaching inline DynamoDB policy...")
iam.put_role_policy(
    RoleName=role_name,
    PolicyName="HealthBandIoTRulesDynamoDBWritePolicy",
    PolicyDocument=perm_content
)

print("\nWaiting 10 seconds for IAM propagation...")
time.sleep(10)

# 4. Deploy IoT Rules
rules = [
    {"name": "StoreTelemetryRule", "template": "infrastructure/iot_rules/store_telemetry_rule.template.json", "local": "infrastructure/iot_rules/store_telemetry_rule.local.json"},
    {"name": "StoreAnalyticsRule", "template": "infrastructure/iot_rules/store_analytics_rule.template.json", "local": "infrastructure/iot_rules/store_analytics_rule.local.json"},
    {"name": "StoreAlertsRule", "template": "infrastructure/iot_rules/store_alerts_rule.template.json", "local": "infrastructure/iot_rules/store_alerts_rule.local.json"},
    {"name": "StoreEventsRule", "template": "infrastructure/iot_rules/store_events_rule.template.json", "local": "infrastructure/iot_rules/store_events_rule.local.json"},
    {"name": "StoreCommandResponsesRule", "template": "infrastructure/iot_rules/store_command_responses_rule.template.json", "local": "infrastructure/iot_rules/store_command_responses_rule.local.json"},
]

for r in rules:
    print(f"\nPreparing IoT Rule: {r['name']}")
    with open(r["template"], "r", encoding="utf-8") as f:
        payload_str = f.read().replace("YOUR_IOT_RULE_ROLE_ARN", role_arn)

    with open(r["local"], "w", encoding="utf-8") as f:
        f.write(payload_str)

    payload_json = json.loads(payload_str)

    try:
        iot.get_topic_rule(ruleName=r["name"])
        iot.replace_topic_rule(ruleName=r["name"], topicRulePayload=payload_json)
        print(f"Replaced existing rule: {r['name']}")
    except Exception:
        iot.create_topic_rule(ruleName=r["name"], topicRulePayload=payload_json)
        print(f"Created rule: {r['name']}")

print("\nAll HealthBand IoT Rules are ready.")