# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Runs the long-polling SQS worker that dispatches campaign-expiry jobs, acknowledges successful messages, and leaves failures for retry or DLQ handling.
# Documentation: Inline comments explain intent; executable behavior is unchanged.

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
    """
    Run the long-polling SQS worker with bounded waits, graceful shutdown, acknowledgement, and retry-preserving failure behavior.
    """
    help = "Continuously process background jobs from SQS."

    def add_arguments(self, parser) -> None:
        """
        Register command-line switches that control worker polling and one-shot execution.
        
        Args:
            parser: Argument parser receiving management-command options.
        """
        parser.add_argument("--once", action="store_true", help="Poll once and exit.")
        parser.add_argument("--wait-seconds", type=int, default=20)

    def handle(self, *args: Any, **options: Any) -> None:
        """
        Poll SQS for campaign-expiry jobs, process them safely, and acknowledge only completed work.
        
        Args:
            *args: Additional positional arguments forwarded to the underlying implementation.
            **options: Additional keyword arguments forwarded to the underlying implementation.
        
        Raises:
            CommandError: When the documented validation or integration precondition fails.
        """
        queue_url = os.getenv("SQS_QUEUE_URL", "").strip()
        # Fail fast when the SQS queue URL is missing; polling without a target would silently do no work.
        if not queue_url:
            raise CommandError("SQS_QUEUE_URL is required")

        region = os.getenv("AWS_REGION", "us-east-1")
        client = boto3.client("sqs", region_name=region)
        running = True

        def stop(*_args: Any) -> None:
            """
            Signal the long-running queue worker to leave its polling loop cleanly.
            
            Args:
                *_args: Additional positional arguments forwarded to the underlying implementation.
            """
            nonlocal running
            running = False

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)

        # Repeat this block while `running` remains true.
        while running:
            response = client.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=max(0, min(options["wait_seconds"], 20)),
                VisibilityTimeout=300,
            )
            messages = response.get("Messages", [])
            # Process each `message` from `messages` in a deterministic order.
            for message in messages:
                self._process_message(client, queue_url, message)
            # Exit after one receive cycle in one-shot mode, which makes health checks and tests deterministic.
            if options["once"]:
                break

    def _process_message(self, client: Any, queue_url: str, message: dict[str, Any]) -> None:
        """
        Validate one SQS job, dispatch supported work, and acknowledge only successfully handled messages.
        
        Args:
            client: Injected HTTP, AWS, or payment client used by the operation.
            queue_url: SQS queue URL from which the worker receives campaign jobs.
            message: Queue, webhook, or validation message being processed.
        """
        # Leave a failed SQS message unacknowledged so its visibility timeout and retry/DLQ policy can work as designed.
        try:
            payload = json.loads(message.get("Body", "{}"))
            job_type = payload.get("type") or payload.get("detail-type")
            # Dispatch only the documented campaign-expiry job types; unknown jobs are acknowledged separately.
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
