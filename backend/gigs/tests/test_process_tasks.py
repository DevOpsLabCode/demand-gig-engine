from unittest.mock import Mock, patch

from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from gigs.management.commands.process_tasks import Command


class ProcessTasksCommandTests(SimpleTestCase):
    def setUp(self):
        self.command = Command()
        self.client = Mock()
        self.queue_url = "https://sqs.us-east-1.amazonaws.com/123456789012/tasks"

    @patch.dict("os.environ", {}, clear=True)
    def test_requires_queue_url(self):
        with self.assertRaisesMessage(CommandError, "SQS_QUEUE_URL is required"):
            self.command.handle(once=True, wait_seconds=0)

    @patch("gigs.management.commands.process_tasks.expire_due_campaigns", return_value=3)
    def test_expiry_job_runs_service_and_deletes_message(self, expire_due_campaigns):
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
        message = {
            "Body": '{"type":"unknown.job"}',
            "ReceiptHandle": "receipt",
        }

        with self.assertLogs("gigs.management.commands.process_tasks", level="WARNING"):
            self.command._process_message(self.client, self.queue_url, message)

        self.client.delete_message.assert_called_once()

    @patch("gigs.management.commands.process_tasks.expire_due_campaigns")
    def test_failure_is_not_deleted_so_sqs_can_retry(self, expire_due_campaigns):
        expire_due_campaigns.side_effect = RuntimeError("database unavailable")
        message = {
            "Body": '{"type":"campaign.expiry.scan"}',
            "ReceiptHandle": "receipt",
        }

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
