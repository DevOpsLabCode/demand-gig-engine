output "certificate_arn" {
  value = try(aws_acm_certificate_validation.this[0].certificate_arn,null)
}
