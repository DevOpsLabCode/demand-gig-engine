# Author: Stan Zvenigorodskiy | DevOps Lab Inc. | https://DevOpsLabInc.com
# Purpose: Verifies an SES domain and publishes DKIM, custom MAIL FROM, SPF, and DMARC records.

data "aws_region" "current" {}

resource "aws_ses_domain_identity" "this" {
  count  = var.create_dns ? 1 : 0
  domain = var.domain_name
}

resource "aws_route53_record" "verification" {
  count   = var.create_dns ? 1 : 0
  zone_id = var.hosted_zone_id
  name    = "_amazonses.${var.domain_name}"
  type    = "TXT"
  ttl     = 300
  records = [aws_ses_domain_identity.this[0].verification_token]
}

resource "aws_ses_domain_dkim" "this" {
  count  = var.create_dns ? 1 : 0
  domain = aws_ses_domain_identity.this[0].domain
}

resource "aws_route53_record" "dkim" {
  count   = var.create_dns ? 3 : 0
  zone_id = var.hosted_zone_id
  name    = "${aws_ses_domain_dkim.this[0].dkim_tokens[count.index]}._domainkey.${var.domain_name}"
  type    = "CNAME"
  ttl     = 300
  records = ["${aws_ses_domain_dkim.this[0].dkim_tokens[count.index]}.dkim.amazonses.com"]
}

# Use a custom MAIL FROM subdomain so envelope-domain alignment can pass DMARC.
resource "aws_ses_domain_mail_from" "this" {
  count                  = var.create_dns ? 1 : 0
  domain                 = aws_ses_domain_identity.this[0].domain
  mail_from_domain       = "${var.mail_from_subdomain}.${var.domain_name}"
  behavior_on_mx_failure = "RejectMessage"
}

resource "aws_route53_record" "mail_from_mx" {
  count   = var.create_dns ? 1 : 0
  zone_id = var.hosted_zone_id
  name    = aws_ses_domain_mail_from.this[0].mail_from_domain
  type    = "MX"
  ttl     = 300
  records = ["10 feedback-smtp.${data.aws_region.current.name}.amazonses.com"]
}

resource "aws_route53_record" "mail_from_spf" {
  count   = var.create_dns ? 1 : 0
  zone_id = var.hosted_zone_id
  name    = aws_ses_domain_mail_from.this[0].mail_from_domain
  type    = "TXT"
  ttl     = 300
  records = ["v=spf1 include:amazonses.com -all"]
}

# Publish an explicit DMARC policy. Start with none in development and use quarantine/reject for production.
resource "aws_route53_record" "dmarc" {
  count   = var.create_dns ? 1 : 0
  zone_id = var.hosted_zone_id
  name    = "_dmarc.${var.domain_name}"
  type    = "TXT"
  ttl     = 300
  records = [join("; ", compact([
    "v=DMARC1",
    "p=${var.dmarc_policy}",
    "pct=${var.dmarc_percentage}",
    var.dmarc_rua == "" ? "" : "rua=mailto:${var.dmarc_rua}",
    "adkim=s",
    "aspf=s",
  ]))]
}
