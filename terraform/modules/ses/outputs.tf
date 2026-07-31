output "identity_arn" {
  value = try(aws_ses_domain_identity.this[0].arn,null)
}
