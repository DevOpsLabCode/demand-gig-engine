output "fqdn" {
  value = try(aws_route53_record.ipv4[0].fqdn,null)
}
