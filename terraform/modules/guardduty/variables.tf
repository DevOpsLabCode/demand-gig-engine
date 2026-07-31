# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Declares whether the environment requires the shared GuardDuty account control.

variable "enabled" {
  type        = bool
  description = "Require an enabled regional GuardDuty detector owned by terraform/global/account."
  default     = true
}
