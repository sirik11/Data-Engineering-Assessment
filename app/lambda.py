import io
import logging
import os

import boto3
import pandas as pd

import orders_analytics

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")
OUTPUT_BUCKET = os.environ["OUTPUT_BUCKET"]


def get_s3_path_from_event(event: dict) -> tuple[str, str]:
    """Extract bucket name and object key from an S3 trigger event."""
    record = event["Records"][0]["s3"]
    return record["bucket"]["name"], record["object"]["key"]


def write_csv_to_s3(df: pd.DataFrame, key: str) -> None:
    """Write a DataFrame as a CSV file to the output S3 bucket."""
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    s3.put_object(Bucket=OUTPUT_BUCKET, Key=key, Body=buffer.getvalue())
    logger.info("Wrote %s rows to s3://%s/%s", len(df), OUTPUT_BUCKET, key)


def lambda_handler(event, context):
    """Process a newly uploaded CSV from S3 and write analytics reports."""
    bucket, key = get_s3_path_from_event(event)
    logger.info("Processing s3://%s/%s", bucket, key)

    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        df = pd.read_csv(response["Body"])
        logger.info("Loaded %d rows", len(df))

        df = orders_analytics.calculate_profit_by_order(df)

        write_csv_to_s3(
            orders_analytics.calculate_most_profitable_region(df),
            "analytics/most_profitable_region.csv",
        )
        write_csv_to_s3(
            orders_analytics.find_most_common_ship_method(df),
            "analytics/most_common_ship_method.csv",
        )
        write_csv_to_s3(
            orders_analytics.find_number_of_order_per_category(df),
            "analytics/orders_by_category.csv",
        )

        logger.info("Done processing %s", key)
        return {"statusCode": 200, "body": f"Processed {key}"}

    except KeyError as e:
        logger.error("Missing expected column or event field: %s", e)
        raise
    except Exception as e:
        logger.error("Failed processing %s: %s", key, e)
        raise
