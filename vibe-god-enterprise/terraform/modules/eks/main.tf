# EKS Module for Vibe-God
# Creates a production-grade EKS cluster with managed node groups

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.10"
    }
  }
}

variable "cluster_name" {
  type        = string
  description = "EKS cluster name"
  default     = "vibe-god"
}

variable "cluster_version" {
  type        = string
  description = "Kubernetes version"
  default     = "1.28"
}

variable "vpc_id" {
  type        = string
  description = "VPC ID"
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "Private subnet IDs"
}

variable "security_group_ids" {
  type        = map(string)
  description = "Security group IDs"
}

variable "tags" {
  type        = map(string)
  description = "Common tags"
  default     = {}
}

variable "node_groups" {
  type = map(object({
    instance_types     = list(string)
    capacity_type      = string
    min_size           = number
    max_size           = number
    desired_size       = number
    disk_size          = number
    labels             = map(string)
    taints             = list(object({
      key    = string
      value  = string
      effect = string
    }))
  }))
  description = "Managed node group configurations"
  default = {
    general = {
      instance_types     = ["m6i.xlarge", "m6i.2xlarge"]
      capacity_type      = "ON_DEMAND"
      min_size           = 3
      max_size           = 20
      desired_size       = 3
      disk_size          = 100
      labels             = { workload = "general" }
      taints             = []
    }
    compute = {
      instance_types     = ["c6i.xlarge", "c6i.2xlarge"]
      capacity_type      = "SPOT"
      min_size           = 0
      max_size           = 10
      desired_size       = 0
      disk_size          = 100
      labels             = { workload = "compute" }
      taints             = [{ key = "workload", value = "compute", effect = "NO_SCHEDULE" }]
    }
    memory = {
      instance_types     = ["r6i.xlarge", "r6i.2xlarge"]
      capacity_type      = "ON_DEMAND"
      min_size           = 2
      max_size           = 10
      desired_size       = 2
      disk_size          = 200
      labels             = { workload = "memory" }
      taints             = [{ key = "workload", value = "memory", effect = "NO_SCHEDULE" }]
    }
    gpu = {
      instance_types     = ["g5.xlarge", "g5.2xlarge"]
      capacity_type      = "ON_DEMAND"
      min_size           = 0
      max_size           = 4
      desired_size       = 0
      disk_size          = 200
      labels             = { workload = "gpu", accelerator = "nvidia-gpu" }
      taints             = [{ key = "nvidia.com/gpu", value = "true", effect = "NO_SCHEDULE" }]
    }
  }
}

locals {
  common_tags = merge(var.tags, {
    Project     = "vibe-god"
    Environment = "production"
    ManagedBy   = "terraform"
  })
}

# IAM Role for EKS Cluster
resource "aws_iam_role" "cluster" {
  name = "${var.cluster_name}-cluster-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "eks.amazonaws.com"
      }
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "cluster_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.cluster.name
}

resource "aws_iam_role_policy_attachment" "cluster_service_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSServicePolicy"
  role       = aws_iam_role.cluster.name
}

# IAM Role for Node Groups
resource "aws_iam_role" "node_group" {
  name = "${var.cluster_name}-node-group-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "node_group_worker" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.node_group.name
}

resource "aws_iam_role_policy_attachment" "node_group_cni" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.node_group.name
}

resource "aws_iam_role_policy_attachment" "node_group_ecr" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.node_group.name
}

# Custom policy for additional permissions
resource "aws_iam_policy" "node_group_custom" {
  name = "${var.cluster_name}-node-group-custom"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret",
          "ssm:GetParameter",
          "ssm:GetParameters",
          "ssm:GetParametersByPath",
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:GenerateDataKey",
          "cloudwatch:PutMetricData",
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords"
        ]
        Effect   = "Allow"
        Resource = "*"
      },
      {
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "node_group_custom" {
  policy_arn = aws_iam_policy.node_group_custom.arn
  role       = aws_iam_role.node_group.name
}

# EKS Cluster
resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  role_arn = aws_iam_role.cluster.arn
  version  = var.cluster_version

  vpc_config {
    subnet_ids              = var.private_subnet_ids
    security_group_ids      = [var.security_group_ids.eks_nodes]
    endpoint_private_access = true
    endpoint_public_access  = true
    public_access_cidrs     = ["0.0.0.0/0"]
  }

  # Encryption
  encryption_config {
    provider {
      key_arn = aws_kms_key.eks.arn
    }
    resources = ["secrets"]
  }

  # Logging
  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  # Kubernetes network config
  kubernetes_network_config {
    service_ipv4_cidr = "172.20.0.0/16"
    ip_family         = "ipv4"
  }

  # Access config
  access_config {
    authentication_mode = "API_AND_CONFIG_MAP"
  }

  tags = merge(local.common_tags, {
    Name = var.cluster_name
  })

  depends_on = [
    aws_iam_role_policy_attachment.cluster_policy,
    aws_iam_role_policy_attachment.cluster_service_policy,
  ]
}

# KMS Key for EKS Secrets Encryption
resource "aws_kms_key" "eks" {
  description             = "KMS key for EKS secrets encryption"
  deletion_window_in_days = 10
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Allow EKS Service"
        Effect = "Allow"
        Principal = {
          Service = "eks.amazonaws.com"
        }
        Action = [
          "kms:Encrypt",
          "kms:Decrypt",
          "kms:ReEncrypt*",
          "kms:GenerateDataKey*",
          "kms:DescribeKey"
        ]
        Resource = "*"
      },
      {
        Sid    = "Allow Administration"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action = "kms:*"
        Resource = "*"
      }
    ]
  })

  tags = local.common_tags
}

data "aws_caller_identity" "current" {}

# Managed Node Groups
resource "aws_eks_node_group" "node_groups" {
  for_each = var.node_groups

  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${var.cluster_name}-${each.key}"
  node_role_arn   = aws_iam_role.node_group.arn
  subnet_ids      = var.private_subnet_ids

  instance_types = each.value.instance_types
  capacity_type  = each.value.capacity_type

  scaling_config {
    min_size     = each.value.min_size
    max_size     = each.value.max_size
    desired_size = each.value.desired_size
  }

  disk_size = each.value.disk_size

  labels = merge(each.value.labels, {
    "node-group" = each.key
  })

  taints = each.value.taints

  update_config {
    max_unavailable_percentage = 25
  }

  launch_template {
    name = aws_launch_template.node_group[each.key].name
    version = "$Latest"
  }

  tags = merge(local.common_tags, {
    Name = "${var.cluster_name}-${each.key}"
  })

  depends_on = [
    aws_iam_role_policy_attachment.node_group_worker,
    aws_iam_role_policy_attachment.node_group_cni,
    aws_iam_role_policy_attachment.node_group_ecr,
    aws_iam_role_policy_attachment.node_group_custom,
  ]
}

# Launch Template for Node Groups
resource "aws_launch_template" "node_group" {
  for_each = var.node_groups

  name_prefix = "${var.cluster_name}-${each.key}-"

  image_id = data.aws_ami.eks_optimized.id

  instance_type = each.value.instance_types[0]

  vpc_security_group_ids = [var.security_group_ids.eks_nodes]

  user_data = base64encode(templatefile("${path.module}/user_data.sh.tpl", {
    cluster_name = var.cluster_name
    labels       = merge(each.value.labels, { "node-group" = each.key })
    taints       = each.value.taints
  }))

  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_size           = each.value.disk_size
      volume_type           = "gp3"
      encrypted             = true
      delete_on_termination = true
      iops                  = 3000
      throughput            = 125
    }
  }

  tag_specifications {
    resource_type = "instance"
    tags = merge(local.common_tags, {
      Name = "${var.cluster_name}-${each.key}-node"
    })
  }

  lifecycle {
    create_before_destroy = true
  }
}

# EKS Optimized AMI
data "aws_ami" "eks_optimized" {
  most_recent = true
  owners      = ["602401143452"] # Amazon EKS

  filter {
    name   = "name"
    values = ["amazon-eks-node-${var.cluster_version}-v*"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}

# Kubernetes Provider
provider "kubernetes" {
  host                   = aws_eks_cluster.main.endpoint
  cluster_ca_certificate = base64decode(aws_eks_cluster.main.certificate_authority[0].data)
  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", var.cluster_name]
  }
}

provider "helm" {
  kubernetes {
    host                   = aws_eks_cluster.main.endpoint
    cluster_ca_certificate = base64decode(aws_eks_cluster.main.certificate_authority[0].data)
    exec {
      api_version = "client.authentication.k8s.io/v1beta1"
      command     = "aws"
      args        = ["eks", "get-token", "--cluster-name", var.cluster_name]
    }
  }
}

# Essential Add-ons
resource "aws_eks_addon" "vpc_cni" {
  cluster_name = aws_eks_cluster.main.name
  addon_name   = "vpc-cni"
  addon_version = "v1.14.0-eksbuild.1"

  resolve_conflicts = "OVERWRITE"

  configuration_values = jsonencode({
    env = {
      AWS_VPC_K8S_CNI_EXTERNALSNAT = "true"
      AWS_VPC_K8S_CNI_CUSTOM_NETWORK_CFG = "true"
    }
  })

  depends_on = [aws_eks_cluster.main]
}

resource "aws_eks_addon" "coredns" {
  cluster_name = aws_eks_cluster.main.name
  addon_name   = "coredns"
  addon_version = "v1.10.1-eksbuild.6"

  resolve_conflicts = "OVERWRITE"

  depends_on = [aws_eks_cluster.main]
}

resource "aws_eks_addon" "kube_proxy" {
  cluster_name = aws_eks_cluster.main.name
  addon_name   = "kube-proxy"
  addon_version = "v1.28.0-eksbuild.1"

  resolve_conflicts = "OVERWRITE"

  depends_on = [aws_eks_cluster.main]
}

resource "aws_eks_addon" "ebs_csi_driver" {
  cluster_name = aws_eks_cluster.main.name
  addon_name   = "aws-ebs-csi-driver"
  addon_version = "v1.24.0-eksbuild.1"

  resolve_conflicts = "OVERWRITE"

  service_account_role_arn = aws_iam_role.ebs_csi_driver.arn

  depends_on = [aws_eks_cluster.main]
}

# IAM Role for EBS CSI Driver
resource "aws_iam_role" "ebs_csi_driver" {
  name = "${var.cluster_name}-ebs-csi-driver"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRoleWithWebIdentity"
      Effect = "Allow"
      Principal = {
        Federated = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/${aws_eks_cluster.main.identity[0].oidc[0].issuer}"
      }
      Condition = {
        StringEquals = {
          "${aws_eks_cluster.main.identity[0].oidc[0].issuer}:sub" = "system:serviceaccount:kube-system:ebs-csi-controller-sa"
        }
      }
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_policy" "ebs_csi_driver" {
  name = "${var.cluster_name}-ebs-csi-driver-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = [
        "ec2:CreateSnapshot",
        "ec2:DeleteSnapshot",
        "ec2:CreateTags",
        "ec2:DescribeSnapshots",
        "ec2:DescribeVolumes",
        "ec2:DescribeVolumeAttribute",
        "ec2:DescribeVolumesModifications",
        "ec2:DescribeVolumeStatus",
        "ec2:AttachVolume",
        "ec2:DetachVolume",
        "ec2:ModifyVolume",
        "ec2:CreateVolume"
      ]
      Effect   = "Allow"
      Resource = "*"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ebs_csi_driver" {
  policy_arn = aws_iam_policy.ebs_csi_driver.arn
  role       = aws_iam_role.ebs_csi_driver.name
}

# Cluster Autoscaler IAM Role
resource "aws_iam_role" "cluster_autoscaler" {
  name = "${var.cluster_name}-cluster-autoscaler"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRoleWithWebIdentity"
      Effect = "Allow"
      Principal = {
        Federated = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/${aws_eks_cluster.main.identity[0].oidc[0].issuer}"
      }
      Condition = {
        StringEquals = {
          "${aws_eks_cluster.main.identity[0].oidc[0].issuer}:sub" = "system:serviceaccount:kube-system:cluster-autoscaler"
        }
      }
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_policy" "cluster_autoscaler" {
  name = "${var.cluster_name}-cluster-autoscaler-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = [
        "autoscaling:DescribeAutoScalingGroups",
        "autoscaling:DescribeAutoScalingInstances",
        "autoscaling:DescribeLaunchConfigurations",
        "autoscaling:DescribeTags",
        "autoscaling:SetDesiredCapacity",
        "autoscaling:TerminateInstanceInAutoScalingGroup",
        "ec2:DescribeLaunchTemplateVersions"
      ]
      Effect   = "Allow"
      Resource = "*"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "cluster_autoscaler" {
  policy_arn = aws_iam_policy.cluster_autoscaler.arn
  role       = aws_iam_role.cluster_autoscaler.name
}

# External DNS IAM Role
resource "aws_iam_role" "external_dns" {
  name = "${var.cluster_name}-external-dns"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRoleWithWebIdentity"
      Effect = "Allow"
      Principal = {
        Federated = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/${aws_eks_cluster.main.identity[0].oidc[0].issuer}"
      }
      Condition = {
        StringEquals = {
          "${aws_eks_cluster.main.identity[0].oidc[0].issuer}:sub" = "system:serviceaccount:kube-system:external-dns"
        }
      }
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_policy" "external_dns" {
  name = "${var.cluster_name}-external-dns-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = [
        "route53:ChangeResourceRecordSets",
        "route53:ListHostedZones",
        "route53:ListResourceRecordSets"
      ]
      Effect   = "Allow"
      Resource = "*"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "external_dns" {
  policy_arn = aws_iam_policy.external_dns.arn
  role       = aws_iam_role.external_dns.name
}

# Outputs
output "cluster_name" {
  value = aws_eks_cluster.main.name
}

output "cluster_endpoint" {
  value = aws_eks_cluster.main.endpoint
}

output "cluster_arn" {
  value = aws_eks_cluster.main.arn
}

output "cluster_certificate_authority" {
  value = aws_eks_cluster.main.certificate_authority[0].data
}

output "cluster_oidc_issuer" {
  value = aws_eks_cluster.main.identity[0].oidc[0].issuer
}

output "node_group_role_arn" {
  value = aws_iam_role.node_group.arn
}

output "security_group_id" {
  value = var.security_group_ids.eks_nodes
}