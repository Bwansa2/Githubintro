#!/usr/bin/env python3

import boto3
import sys
import locale
import logging
import json
import base64
from collections import defaultdict

locale.setlocale(locale.LC_ALL, 'en_US')

# Log to the screen
sh = logging.StreamHandler()
sh.setLevel(logging.DEBUG)
sh.setFormatter(logging.Formatter('%(asctime)s: "%(name)s" (line: %(lineno)d) - %(levelname)s %(message)s'))

logger = logging.getLogger()
logger.addHandler(sh)
logger.setLevel(logging.WARNING)


class LambdaHandler(object):
    def __init__(self, event, context):
        self.event = event
        self.context = context
        self.query_params = dict()
        self.request_data = None

        self.return_code = None
        self.response = None

        self.munge_request(event, context)
        self.handle_request()

    def result(self):
        return {'statusCode': self.return_code, 'body': json.dumps(self.response)}

    def munge_request(self, event, context):
        self.query_params = event.get("queryStringParameters", dict)
        self.is_base64_encoded = event.get("isBase64Encoded", False)
        self.context = context

        request_body = event.get("body")

        logger.critical(request_body)

        if self.is_base64_encoded:
            request_data = base64.b64decode(request_body)
        else:
            request_data = request_body

        try:
            request_body = json.loads(request_data)
        except (json.decoder.JSONDecodeError, TypeError) as e:
            self.request_data = request_data
        else:
            self.request_data = request_body

    def handle_request(self):
        try:
            data_source = self.request_data.get("meta").get("data_src")
            pings = self.request_data.get("pings")

            ping_report = self.check_pings(pings=pings, data_source=data_source.lower())
        except Exception as e:
            self.return_code = 500
            self.response = {"error": str(e), "received_data": self.request_data}
            raise
        else:
            self.return_code = 200
            self.response = {"ping_report": ping_report}

    def check_pings(self, pings, data_source):
        ping_report = list()
        dynamo_table = "employee_location_map_{data_source}".format(data_source=data_source)

        table = boto3.resource('dynamodb').Table(dynamo_table)

        for curr_ping in pings:
            email = curr_ping["email"]
            log_entry= ""

            ping_record = {"email": email,
                            "ip": "",
                            "long": "",
                            "lat": "",
                            "zip": "",
                            "mac": "",
                            "region": "",
                            "city": "",
                            "imei": "",
                            "state": "",
                            "country": "",
                            "is_valid": False
            }

            try:
                prev_ping = table.get_item(Key={'email': email})
            except Exception:
                prev_ping = dict()
            else:
                prev_ping = prev_ping.get("Item")

            if prev_ping:
                is_valid = self.check_activity(curr_ping=curr_ping, prev_ping=prev_ping)

                curr_ping["is_valid"] = is_valid
                prev_ping.update(curr_ping)
            else:
                is_valid = False
                prev_ping = ping_record

            try:
                table.put_item(Item=prev_ping)
            except Exception as e:
                log_entry = str(e)
                logger.exception("Put update failure")
            else:
                log_entry = "upserted"

            ping_report.append({"email": email, "is_valid": is_valid, "log_entry": log_entry})

        return ping_report

    def check_activity(self, curr_ping, prev_ping):
        email = curr_ping.get("email")

        # Rather than binary, Tom thinks having a weighted score
        # would be more useful (v2?)
        if curr_ping.get("region") == prev_ping.get("region"):
            is_valid = True
        else:
            is_valid = False

        return is_valid


# Default name Lambda uses
def lambda_handler(event, context):
    return LambdaHandler(event, context).result()


if __name__ == "__main__":
    event = dict()
    context = dict()

    try:
        file = sys.argv[1]
    except IndexError:
        file = "data.json"

    with open(file, "r") as fh:
        event["body"] = fh.read()

    print(lambda_handler(event, context))

