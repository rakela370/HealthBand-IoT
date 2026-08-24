import boto3

REGION = "eu-central-1"
dynamodb = boto3.client("dynamodb", region_name=REGION)

TABLES = [
    {
        "TableName": "HealthBandTelemetry",
        "AttributeDefinitions": [
            {"AttributeName": "deviceId", "AttributeType": "S"},
            {"AttributeName": "timestamp", "AttributeType": "S"},
        ],
        "KeySchema": [
            {"AttributeName": "deviceId", "KeyType": "HASH"},
            {"AttributeName": "timestamp", "KeyType": "RANGE"},
        ],
        "BillingMode": "PAY_PER_REQUEST",
        "Tags": [
            {"Key": "Project", "Value": "HealthBand"},
            {"Key": "Environment", "Value": "Development"},
            {"Key": "DataType", "Value": "Telemetry"},
        ],
    },
    {
        "TableName": "HealthBandAnalytics",
        "AttributeDefinitions": [
            {"AttributeName": "deviceId", "AttributeType": "S"},
            {"AttributeName": "windowEnd", "AttributeType": "S"},
        ],
        "KeySchema": [
            {"AttributeName": "deviceId", "KeyType": "HASH"},
            {"AttributeName": "windowEnd", "KeyType": "RANGE"},
        ],
        "BillingMode": "PAY_PER_REQUEST",
        "Tags": [
            {"Key": "Project", "Value": "HealthBand"},
            {"Key": "Environment", "Value": "Development"},
            {"Key": "DataType", "Value": "Analytics"},
        ],
    },
    {
        "TableName": "HealthBandEvents",
        "AttributeDefinitions": [
            {"AttributeName": "deviceId", "AttributeType": "S"},
            {"AttributeName": "timestampEventId", "AttributeType": "S"},
        ],
        "KeySchema": [
            {"AttributeName": "deviceId", "KeyType": "HASH"},
            {"AttributeName": "timestampEventId", "KeyType": "RANGE"},
        ],
        "BillingMode": "PAY_PER_REQUEST",
        "Tags": [
            {"Key": "Project", "Value": "HealthBand"},
            {"Key": "Environment", "Value": "Development"},
            {"Key": "DataType", "Value": "Events"},
        ],
    },
]

existing_tables = dynamodb.list_tables().get("TableNames", [])

for table_def in TABLES:
    table_name = table_def["TableName"]
    print(f"\nChecking DynamoDB table: {table_name}")
    if table_name in existing_tables:
        print(f"Table already exists: {table_name}")
        continue

    print(f"Creating table: {table_name}...")
    dynamodb.create_table(**table_def)
    print("Waiting for table to become ACTIVE...")
    waiter = dynamodb.get_waiter("table_exists")
    waiter.wait(TableName=table_name)
    print(f"Table is ACTIVE: {table_name}")

print("\nAll HealthBand DynamoDB tables are ready.")