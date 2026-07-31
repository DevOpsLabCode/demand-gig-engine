resource "aws_route53_record" "ipv4" {
  count = var.enabled ? 1 :0
  zone_id = var.zone_id
  name = var.record_name
  type = "A"
  alias {
    name = var.target_name
    zone_id = var.target_zone_id
    evaluate_target_health = false
  }
}
resource "aws_route53_record" "ipv6" {
  count = var.enabled && var.create_ipv6 ? 1 :0
  zone_id = var.zone_id
  name = var.record_name
  type = "AAAA"
  alias {
    name = var.target_name
    zone_id = var.target_zone_id
    evaluate_target_health = false
  }
}
