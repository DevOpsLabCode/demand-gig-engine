data "aws_availability_zones" "available" {
  state = "available"
}
locals {
  azs = slice(data.aws_availability_zones.available.names,0,var.az_count)
}
resource "aws_vpc" "this" {
  cidr_block = var.cidr
  enable_dns_support = true
  enable_dns_hostnames = true
  tags = merge(var.tags,{Name = "${var.name}-vpc"})
}
resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id
  tags = merge(var.tags,{Name = "${var.name}-igw"})
}
resource "aws_subnet" "public" {
  for_each = {for i,az in local.azs :az => i}
  vpc_id = aws_vpc.this.id
  availability_zone = each.key
  cidr_block = cidrsubnet(var.cidr,4,each.value)
  map_public_ip_on_launch = true
  tags = merge(var.tags,{Name = "${var.name}-public-${each.key}",Tier = "public"})
}
resource "aws_subnet" "app" {
  for_each = {for i,az in local.azs :az => i}
  vpc_id = aws_vpc.this.id
  availability_zone = each.key
  cidr_block = cidrsubnet(var.cidr,4,each.value + 4)
  tags = merge(var.tags,{Name = "${var.name}-app-${each.key}",Tier = "private-app"})
}
resource "aws_subnet" "db" {
  for_each = {for i,az in local.azs :az => i}
  vpc_id = aws_vpc.this.id
  availability_zone = each.key
  cidr_block = cidrsubnet(var.cidr,4,each.value + 8)
  tags = merge(var.tags,{Name = "${var.name}-db-${each.key}",Tier = "private-db"})
}
resource "aws_eip" "nat" {
  for_each = var.nat_gateway_per_az ? aws_subnet.public :{(keys(aws_subnet.public)[0]) = values(aws_subnet.public)[0]}
  domain = "vpc"
  tags = var.tags
}
resource "aws_nat_gateway" "this" {
  for_each = aws_eip.nat
  allocation_id = each.value.id
  subnet_id = aws_subnet.public[each.key].id
  depends_on = [aws_internet_gateway.this]
  tags = var.tags
}
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }
  tags = var.tags
}
resource "aws_route_table_association" "public" {
  for_each = aws_subnet.public
  subnet_id = each.value.id
  route_table_id = aws_route_table.public.id
}
resource "aws_route_table" "app" {
  for_each = aws_subnet.app
  vpc_id = aws_vpc.this.id
  route {
    cidr_block = "0.0.0.0/0"
    nat_gateway_id = var.nat_gateway_per_az ? aws_nat_gateway.this[each.key].id :values(aws_nat_gateway.this)[0].id
  }
  tags = var.tags
}
resource "aws_route_table_association" "app" {
  for_each = aws_subnet.app
  subnet_id = each.value.id
  route_table_id = aws_route_table.app[each.key].id
}
resource "aws_route_table" "db" {
  vpc_id = aws_vpc.this.id
  tags = var.tags
}
resource "aws_route_table_association" "db" {
  for_each = aws_subnet.db
  subnet_id = each.value.id
  route_table_id = aws_route_table.db.id
}
resource "aws_vpc_endpoint" "s3" {
  vpc_id = aws_vpc.this.id
  service_name = "com.amazonaws.${data.aws_region.current.name}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids = concat([for x in aws_route_table.app :x.id],[aws_route_table.db.id])
  tags = var.tags
}
data "aws_region" "current" {
}
