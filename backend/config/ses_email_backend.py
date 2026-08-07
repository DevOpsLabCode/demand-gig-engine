# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Sends Django email through Amazon SES using the ECS task IAM role instead of SMTP credentials.

from __future__ import annotations

import logging

import boto3
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)


class EmailBackend(BaseEmailBackend):
    """Django email backend backed by the SES v1 API and ambient AWS credentials."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.region_name = getattr(settings, "AWS_REGION", None) or "us-east-1"

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        client = boto3.client("ses", region_name=self.region_name)
        sent = 0
        for message in email_messages:
            if not message.recipients():
                continue
            try:
                raw_message = message.message().as_bytes(linesep="\r\n")
                client.send_raw_email(
                    Source=message.from_email or settings.DEFAULT_FROM_EMAIL,
                    Destinations=message.recipients(),
                    RawMessage={"Data": raw_message},
                )
                sent += 1
            except Exception:
                logger.exception(
                    "SES email delivery failed recipients=%s subject=%s",
                    message.recipients(),
                    message.subject,
                )
                if not self.fail_silently:
                    raise
        return sent
