from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key


class DynamoStore:
    """Stores readings in DynamoDB.

    Table design:
      partition key = device_id  (groups all readings of one device)
      sort key      = timestamp  (keeps them in time order)
    """

    def __init__(self, table_name: str, region: str | None = None):
        self.table = boto3.resource("dynamodb", region_name=region).Table(table_name)

    def add(self, reading: dict):
        # DynamoDB does not accept Python floats, so we convert to Decimal.
        item = dict(reading)
        item["temperature"] = Decimal(str(reading["temperature"]))
        item["humidity"] = Decimal(str(reading["humidity"]))
        self.table.put_item(Item=item)

    def get(self, device_id: str) -> list[dict]:
        kwargs = {"KeyConditionExpression": Key("device_id").eq(device_id)}
        items = []
        while True:  # DynamoDB returns results in pages of up to 1 MB
            resp = self.table.query(**kwargs)
            items.extend(resp["Items"])
            if "LastEvaluatedKey" not in resp:
                break
            kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
        return [self._to_python(i) for i in items]

    def devices(self) -> list[str]:
        # A scan reads the whole table. Fine for a small project; at scale
        # you would keep a separate small "devices" table instead.
        ids, kwargs = set(), {"ProjectionExpression": "device_id"}
        while True:
            resp = self.table.scan(**kwargs)
            ids.update(i["device_id"] for i in resp["Items"])
            if "LastEvaluatedKey" not in resp:
                break
            kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
        return sorted(ids)

    @staticmethod
    def _to_python(item: dict) -> dict:
        item["temperature"] = float(item["temperature"])
        item["humidity"] = float(item["humidity"])
        return item
