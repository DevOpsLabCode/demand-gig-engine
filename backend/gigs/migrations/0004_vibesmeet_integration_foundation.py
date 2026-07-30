# Generated manually for the contract-first VibesMeet integration foundation.

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("gigs", "0003_scope_pledge_idempotency")]

    operations = [
        migrations.CreateModel(
            name="ExternalResourceLink",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("provider", models.CharField(default="vibesmeet", max_length=40)),
                ("local_resource_type", models.CharField(max_length=80)),
                ("local_resource_id", models.CharField(max_length=180)),
                ("remote_resource_type", models.CharField(max_length=80)),
                ("remote_resource_id", models.CharField(max_length=180)),
                ("remote_version", models.CharField(blank=True, max_length=100)),
                ("sync_status", models.CharField(choices=[("pending", "Pending"), ("synced", "Synced"), ("conflict", "Conflict"), ("failed", "Failed"), ("disconnected", "Disconnected")], default="pending", max_length=20)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("last_synced_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="IntegrationWebhookEvent",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("provider", models.CharField(default="vibesmeet", max_length=40)),
                ("event_id", models.CharField(max_length=180)),
                ("event_type", models.CharField(max_length=160)),
                ("resource_type", models.CharField(blank=True, max_length=80)),
                ("resource_id", models.CharField(blank=True, max_length=180)),
                ("resource_version", models.CharField(blank=True, max_length=100)),
                ("sequence", models.BigIntegerField(default=0)),
                ("payload", models.JSONField(default=dict)),
                ("status", models.CharField(choices=[("received", "Received"), ("processed", "Processed"), ("quarantined", "Quarantined"), ("failed", "Failed")], default="received", max_length=20)),
                ("error", models.TextField(blank=True)),
                ("received_at", models.DateTimeField(auto_now_add=True)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"ordering": ["received_at"]},
        ),
        migrations.AddConstraint(
            model_name="externalresourcelink",
            constraint=models.UniqueConstraint(fields=("provider", "local_resource_type", "local_resource_id", "remote_resource_type"), name="int_local_resource_uniq"),
        ),
        migrations.AddConstraint(
            model_name="externalresourcelink",
            constraint=models.UniqueConstraint(fields=("provider", "remote_resource_type", "remote_resource_id"), name="int_remote_resource_uniq"),
        ),
        migrations.AddIndex(
            model_name="externalresourcelink",
            index=models.Index(fields=["provider", "sync_status"], name="int_provider_status_idx"),
        ),
        migrations.AddConstraint(
            model_name="integrationwebhookevent",
            constraint=models.UniqueConstraint(fields=("provider", "event_id"), name="int_provider_event_uniq"),
        ),
        migrations.AddIndex(
            model_name="integrationwebhookevent",
            index=models.Index(fields=["provider", "status", "received_at"], name="int_webhook_queue_idx"),
        ),
        migrations.AddIndex(
            model_name="integrationwebhookevent",
            index=models.Index(fields=["provider", "resource_type", "resource_id"], name="int_webhook_resource_idx"),
        ),
    ]
