module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = var.cluster_name
  cluster_version = "1.29"

  # Fix: CKV_AWS_37 - Enable all control plane logs
  cluster_enabled_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  # Fix: CKV_AWS_338 - Retain logs for at least 365 days (1 year)
  cloudwatch_log_group_retention_in_days = 365

  # Fix: CKV_AWS_58 - Enable KMS encryption for Kubernetes secrets
  create_kms_key = true
  cluster_encryption_config = {
    resources = ["secrets"]
  }

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.public_subnets

  cluster_endpoint_public_access = true

  # EKS Managed Node Group
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