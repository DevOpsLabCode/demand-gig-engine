# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Verifies SQS worker argument handling, supported and unknown job dispatch, acknowledgements, one-shot mode, and retry-preserving failures.
# Documentation: Inline comments explain intent; executable behavior is unchanged.

"""
Verifies SQS worker argument handling, supported and unknown job dispatch, acknowledgements, one-shot mode, and retry-preserving failures.

Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
"""

from unittest.mock import Mock, patch

from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from gigs.management.commands.process_tasks import Command


class ProcessTasksCommandTests(SimpleTestCase):
    """
    Exercise ProcessTasksCommand behavior, edge cases, and failure handling with isolated tests.
    """
    def setUp(self):
        """
        Create reusable fixtures and mocks required by each test in this class.
        """
        self.command = Command()
        self.client = Mock()
        self.queue_url = "https://sqs.us-east-1.amazonaws.com/123456789012/tasks"

    @patch.dict("os.environ", {}, clear=True)
    def test_requires_queue_url(self):
        """
        Verify that requires queue URL.
        """
        # Enter the context manager to scope resources, transactions, or cleanup to this block.
        with self.assertRaisesMessage(CommandError, "SQS_QUEUE_URL is required"):
            self.command.handle(once=True, wait_seconds=0)

    @patch("gigs.management.commands.process_tasks.expire_due_campaigns", return_value=3)
    def test_expiry_job_runs_service_and_deletes_message(self, expire_due_campaigns):
        """
        Verify that expiry job runs service and deletes message.
        
        Args:
            expire_due_campaigns: Injected expiry function, allowing the queue command to be tested without database side effects.
        """
        message = {
            "Body": '{"type":"campaign.expiry.scan"}',
            "ReceiptHandle": "receipt",
        }

        self.command._process_message(self.client, self.queue_url, message)

        expire_due_campaigns.assert_called_once_with()
        self.client.delete_message.assert_called_once_with(
            QueueUrl=self.queue_url,
            ReceiptHandle="receipt",
        )

    def test_unknown_job_is_acknowledged(self):
        """
        Verify that unknown job is acknowledged.
        """
        message = {
            "Body": '{"type":"unknown.job"}',
            "ReceiptHandle": "receipt",
        }

        # Enter the context manager to scope resources, transactions, or cleanup to this block.
        with self.assertLogs("gigs.management.commands.process_tasks", level="WARNING"):
            self.command._process_message(self.client, self.queue_url, message)

        self.client.delete_message.assert_called_once()

    @patch("gigs.management.commands.process_tasks.expire_due_campaigns")
    def test_failure_is_not_deleted_so_sqs_can_retry(self, expire_due_campaigns):
        """
        Verify that failure is not deleted so SQS can retry.
        
        Args:
            expire_due_campaigns: Injected expiry function, allowing the queue command to be tested without database side effects.
        """
        expire_due_campaigns.side_effect = RuntimeError("database unavailable")
        message = {
            "Body": '{"type":"campaign.expiry.scan"}',
            "ReceiptHandle": "receipt",
        }

        # Enter the context manager to scope resources, transactions, or cleanup to this block.
        with self.assertLogs("gigs.management.commands.process_tasks", level="ERROR"):
            self.command._process_message(self.client, self.queue_url, message)

        self.client.delete_message.assert_not_called()

    @patch.dict(
        "os.environ",
        {
            "SQS_QUEUE_URL": "https://sqs.us-east-1.amazonaws.com/123456789012/tasks",
            "AWS_REGION": "us-east-1",
        },
        clear=True,
    )
    @patch("gigs.management.commands.process_tasks.signal.signal")
    @patch("gigs.management.commands.process_tasks.boto3.client")
    def test_once_mode_polls_exactly_once(self, boto_client, _signal):
        """
        Verify that once mode polls exactly once.
        
        Args:
            boto_client: Injected AWS SDK client or test double used by the helper.
            _signal: Injected signal object supplied by the test framework.
        """
        sqs = boto_client.return_value
        sqs.receive_message.return_value = {"Messages": []}

        self.command.handle(once=True, wait_seconds=99)

        boto_client.assert_called_once_with("sqs", region_name="us-east-1")
        sqs.receive_message.assert_called_once_with(
            QueueUrl=self.queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=20,
            VisibilityTimeout=300,
        )
