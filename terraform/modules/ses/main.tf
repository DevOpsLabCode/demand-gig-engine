resource "aws_ses_domain_identity" "this" {
  count = var.create_dns ? 1 :0
  domain = var.domain_name
}
resource "aws_route53_record" "verification" {
  count = var.create_dns ? 1 :0
  zone_id = var.hosted_zone_id
  name = "_amazonses.${var.domain_name}"
  type = "TXT"
  ttl = 300
  records = [aws_ses_domain_identity.this[0].verification_token]
}
resource "aws_ses_domain_dkim" "this" {
  count = var.create_dns ? 1 :0
  domain = aws_ses_domain_identity.this[0].domain
}
resource "aws_route53_record" "dkim" {
  count = var.create_dns ? 3 :0
  zone_id = var.hosted_zone_id
  name = "${aws_ses_domain_dkim.this[0].dkim_tokens[count.index]}._domainkey.${var.domain_name}"
  type = "CNAME"
  ttl = 300
  records = ["${aws_ses_domain_dkim.this[0].dkim_tokens[count.index]}.dkim.amazonses.com"]
}
