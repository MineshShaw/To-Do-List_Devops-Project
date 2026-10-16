module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = var.cluster_name
  cluster_version = "1.29"

  cluster_enabled_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]
  cloudwatch_log_group_retention_in_days = 365

  # Disable dedicated KMS creation to clear kms:TagResource restriction
  create_kms_key            = false
  cluster_encryption_config = {}

  # Reference the default VPC data sources instead of the module
  vpc_id     = data.aws_vpc.default.id
  subnet_ids = data.aws_subnets.default.ids

  cluster_endpoint_public_access = true
  
  eks_managed_node_groups = {
    one = {
      name           = "${var.cluster_name}-ng"
      instance_types = ["t3.small"]
      capacity_type  = "ON_DEMAND"
      min_size       = 1
      max_size       = 3
      desired_size   = 2
    }
  }

  tags = {
    Environment = "dev"
    Terraform   = "true"
  }
}