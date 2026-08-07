# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Keeps outbound verification email functional when an environment uses a CloudFront hostname and an externally verified SES sender identity.

variable "ses_sender_identity" {
  type        = string
  description = "Verified SES domain identity used for outbound application mail when create_dns is false and ses_identity_arn is not supplied."
  default     = "devopslabinc.com"

  validation {
    condition = (
      trimspace(var.ses_sender_identity) == "" ||
      can(regex("^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$", trimspace(var.ses_sender_identity)))
    )
    error_message = "ses_sender_identity must be empty or a valid DNS domain name."
  }
}

locals {
  external_ses_identity_arn = (
    !var.create_dns &&
    var.ses_identity_arn == null &&
    trimspace(var.ses_sender_identity) != ""
  ) ? "arn:${data.aws_partition.current.partition}:ses:${var.aws_region}:${data.aws_caller_identity.current.account_id}:identity/${trimspace(var.ses_sender_identity)}" : null
}

check "verification_email_delivery" {
  assert {
    condition = (
      var.create_dns ||
      var.ses_identity_arn != null ||
      local.external_ses_identity_arn != null
    )
    error_message = "Outbound verification email requires Terraform-managed SES DNS, ses_identity_arn, or ses_sender_identity."
  }
}

# The ecs_service module already grants SES when module.ses.identity_arn is non-null.
# CloudFront-only development intentionally has no application DNS zone, so add the
# same least-privilege permission against the externally verified sender identity.
resource "aws_iam_role_policy" "backend_external_ses" {
  count = local.external_ses_identity_arn == null ? 0 : 1

  name = "${local.name}-api-external-ses"
  role = element(reverse(split("/", module.backend.task_role_arn)), 0)

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "SendOpenConcertVerificationEmail"
        Effect   = "Allow"
        Action   = ["ses:SendEmail", "ses:SendRawEmail"]
        Resource = local.external_ses_identity_arn
      }
    ]
  })
}

resource "aws_iam_role_policy" "worker_external_ses" {
  count = local.external_ses_identity_arn == null ? 0 : 1

  name = "${local.name}-worker-external-ses"
  role = element(reverse(split("/", module.worker.task_role_arn)), 0)

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "SendOpenConcertApplicationEmail"
        Effect   = "Allow"
        Action   = ["ses:SendEmail", "ses:SendRawEmail"]
        Resource = local.external_ses_identity_arn
      }
    ]
  })
}
