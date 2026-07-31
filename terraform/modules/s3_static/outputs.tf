# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Publishes reusable values produced by the s3 static Terraform module.
# Reading guide: Each comment explains why the following Terraform block exists.

# Output `bucket_id`: Identifier of the bucket resource consumed by this module.
output "bucket_id" {
  value = aws_s3_bucket.this.id
}
# Output `bucket_arn`: ARN of the S3 bucket protected or consumed by the module.
output "bucket_arn" {
  value = aws_s3_bucket.this.arn
}
# Output `regional_domain_name`: Regional S3 hostname used by CloudFront origin configuration.
output "regional_domain_name" {
  value = aws_s3_bucket.this.bucket_regional_domain_name
}
