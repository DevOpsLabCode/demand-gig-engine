"""Process asynchronous Demand Gig Engine jobs from Amazon SQS."""

from __future__ import annotations

import json
import logging
import os
import signal
from typing import Any

import boto3
from django.core.management.base import BaseCommand, CommandError

from gigs.services import expire_due_campaigns

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Continuously process background jobs from SQS."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--once", action="store_true", help="Poll once and exit.")
        parser.add_argument("--wait-seconds", type=int, default=20)

    def handle(self, *args: Any, **options: Any) -> None:
        queue_url = os.getenv("SQS_QUEUE_URL", "").strip()
        if not queue_url:
            raise CommandError("SQS_QUEUE_URL is required")

        region = os.getenv("AWS_REGION", "us-east-1")
        client = boto3.client("sqs", region_name=region)
        running = True

        def stop(*_args: Any) -> None:
            nonlocal running
            running = False

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)

        while running:
            response = client.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=max(0, min(options["wait_seconds"], 20)),
                VisibilityTimeout=300,
            )
            messages = response.get("Messages", [])
            for message in messages:
                self._process_message(client, queue_url, message)
            if options["once"]:
                break

    def _process_message(self, client: Any, queue_url: str, message: dict[str, Any]) -> None:
        try:
            payload = json.loads(message.get("Body", "{}"))
            job_type = payload.get("type") or payload.get("detail-type")
            if job_type in {"campaign.expiry.scan", "Scheduled Event"}:
                updated = expire_due_campaigns()
                logger.info("Expired %s due campaigns", updated)
            else:
                logger.warning("Ignoring unknown background job type: %s", job_type)
            client.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=message["ReceiptHandle"],
            )
        except Exception:
            logger.exception("Background job failed; SQS will retry it")
