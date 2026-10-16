# Read the existing default VPC in ap-southeast-2
data "aws_vpc" "default" {
  default = true
}

# Read all default subnets associated with this default VPC
data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}