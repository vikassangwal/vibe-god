# Production Environment for Vibe-God
# Deploys all infrastructure using modules

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
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }

  backend "s3" {
    bucket         = "vibe-god-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project     = "vibe-god"
      Environment = "production"
      ManagedBy   = "terraform"
      Owner       = "platform-team"
    }
  }
}

provider "kubernetes" {
  host                   = module.eks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority)
  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name]
  }
}

provider "helm" {
  kubernetes {
    host                   = module.eks.cluster_endpoint
    cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority)
    exec {
      api_version = "client.authentication.k8s.io/v1beta1"
      command     = "aws"
      args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name]
    }
  }
}

# Variables
variable "region" {
  type        = string
  description = "AWS region"
  default     = "us-east-1"
}

variable "environment" {
  type        = string
  description = "Environment name"
  default     = "production"
}

variable "domain_name" {
  type        = string
  description = "Domain name for ingress"
  default     = "vibe-god.example.com"
}

variable "acm_certificate_arn" {
  type        = string
  description = "ACM certificate ARN for TLS"
  default     = ""
}

# VPC Module
module "vpc" {
  source = "../../modules/vpc"

  region              = var.region
  vpc_cidr            = "10.0.0.0/16"
  availability_zones  = ["us-east-1a", "us-east-1b", "us-east-1c"]
  public_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  private_subnet_cidrs = ["10.0.11.0/24", "10.0.12.0/24", "10.0.13.0/24"]
  database_subnet_cidrs = ["10.0.21.0/24", "10.0.22.0/24", "10.0.23.0/24"]

  tags = {
    Environment = var.environment
  }
}

# EKS Module
module "eks" {
  source = "../../modules/eks"

  cluster_name        = "vibe-god-prod"
  cluster_version     = "1.28"
  vpc_id              = module.vpc.vpc_id
  private_subnet_ids  = module.vpc.private_subnet_ids
  security_group_ids  = module.vpc.security_group_ids

  node_groups = {
    general = {
      instance_types     = ["m6i.xlarge", "m6i.2xlarge"]
      capacity_type      = "ON_DEMAND"
      min_size           = 5
      max_size           = 30
      desired_size       = 5
      disk_size          = 100
      labels             = { workload = "general" }
      taints             = []
    }
    compute = {
      instance_types     = ["c6i.xlarge", "c6i.2xlarge"]
      capacity_type      = "SPOT"
      min_size           = 0
      max_size           = 20
      desired_size       = 0
      disk_size          = 100
      labels             = { workload = "compute" }
      taints             = [{ key = "workload", value = "compute", effect = "NO_SCHEDULE" }]
    }
    memory = {
      instance_types     = ["r6i.xlarge", "r6i.2xlarge"]
      capacity_type      = "ON_DEMAND"
      min_size           = 3
      max_size           = 15
      desired_size       = 3
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

  tags = {
    Environment = var.environment
  }
}

# RDS Module
module "rds" {
  source = "../../modules/rds"

  identifier             = "vibe-god-prod"
  engine_version         = "16.3"
  instance_class         = "db.r6g.xlarge"
  allocated_storage      = 200
  max_allocated_storage  = 1000
  db_name                = "vibe_god"
  username               = "postgres"
  password               = var.db_password
  vpc_id                 = module.vpc.vpc_id
  database_subnet_ids    = module.vpc.database_subnet_ids
  security_group_ids     = [module.vpc.security_group_ids.rds]
  backup_retention_period = 30
  replica_count          = 3
  replica_instance_class = "db.r6g.large"

  tags = {
    Environment = var.environment
  }
}

# ElastiCache Module
module "elasticache" {
  source = "../../modules/elasticache"

  cluster_id              = "vibe-god-prod"
  engine_version          = "7.1"
  node_type               = "cache.r6g.xlarge"
  num_cache_nodes         = 4
  automatic_failover_enabled = true
  multi_az_enabled        = true
  vpc_id                  = module.vpc.vpc_id
  private_subnet_ids      = module.vpc.private_subnet_ids
  security_group_ids      = [module.vpc.security_group_ids.elasticache]
  auth_token              = var.redis_password
  backup_retention_limit  = 7

  tags = {
    Environment = var.environment
  }
}

# MQ Module
module "mq" {
  source = "../../modules/mq"

  broker_name        = "vibe-god-prod"
  engine_version     = "3.12"
  instance_type      = "mq.m5.xlarge"
  deployment_mode    = "CLUSTER_MULTI_AZ"
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
  security_group_ids = [module.vpc.security_group_ids.mq]
  username           = "admin"
  password           = var.mq_password
  publicly_accessible = false

  tags = {
    Environment = var.environment
  }
}

# MSK Module
module "msk" {
  source = "../../modules/msk"

  cluster_name         = "vibe-god-prod"
  kafka_version        = "3.6"
  instance_type        = "kafka.m7g.large"
  broker_count         = 6
  vpc_id               = module.vpc.vpc_id
  private_subnet_ids   = module.vpc.private_subnet_ids
  security_group_ids   = [module.vpc.security_group_ids.msk]
  storage_per_broker   = 500
  monitoring_level     = "PER_BROKER"
  client_authentication = "SASL_IAM"

  tags = {
    Environment = var.environment
  }
}

# ALB for Ingress
module "alb" {
  source = "terraform-aws-modules/alb/aws"
  version = "~> 9.0"

  name = "vibe-god-prod"

  load_balancer_type = "application"
  vpc_id             = module.vpc.vpc_id
  subnets            = module.vpc.public_subnet_ids
  security_groups    = [module.vpc.security_group_ids.alb]

  enable_deletion_protection = true
  enable_http2               = true
  idle_timeout               = 300
  ip_address_type            = "ipv4"

  access_logs = {
    bucket = aws_s3_bucket.alb_logs.bucket
    prefix = "alb-logs"
    enabled = true
  }

  target_groups = {
    api = {
      name             = "vibe-god-api"
      backend_protocol = "HTTP"
      backend_port     = 8000
      target_type      = "ip"
      vpc_id           = module.vpc.vpc_id
      health_check = {
        path                = "/health/ready"
        healthy_threshold   = 2
        unhealthy_threshold = 3
        timeout             = 10
        interval            = 30
      }
    }
  }

  https_listeners = var.acm_certificate_arn != "" ? [{
    port            = 443
    protocol        = "HTTPS"
    certificate_arn = var.acm_certificate_arn
    action = {
      type = "forward"
      target_group_key = "api"
    }
  }] : []

  http_listeners = [{
    port     = 80
    protocol = "HTTP"
    action = {
      type = "redirect"
      redirect = {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }
  }]

  tags = {
    Environment = var.environment
  }
}

# S3 Bucket for ALB Logs
resource "aws_s3_bucket" "alb_logs" {
  bucket = "vibe-god-alb-logs-${data.aws_caller_identity.current.account_id}"

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }

  lifecycle_rule {
    enabled = true
    expiration {
      days = 90
    }
  }

  tags = {
    Environment = var.environment
  }
}

resource "aws_s3_bucket_policy" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "delivery.logs.amazonaws.com"
      }
      Action = "s3:PutObject"
      Resource = "${aws_s3_bucket.alb_logs.arn}/*"
      Condition = {
        StringEquals = {
          "s3:x-amz-acl" = "bucket-owner-full-control"
        }
      }
    }]
  })
}

data "aws_caller_identity" "current" {}

# Secrets Manager for Application Secrets
resource "aws_secretsmanager_secret" "app_secrets" {
  name        = "vibe-god/prod/app-secrets"
  description = "Application secrets for vibe-god production"
  kms_key_id  = aws_kms_key.secrets.arn

  tags = {
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret_version" "app_secrets" {
  secret_id = aws_secretsmanager_secret.app_secrets.id

  secret_string = jsonencode({
    DATABASE_URL       = "postgresql+asyncpg://postgres:${var.db_password}@${module.rds.primary_endpoint}/vibe_god"
    REDIS_URL          = "redis://:${var.redis_password}@${module.elasticache.primary_endpoint}:6379/0"
    RABBITMQ_URL       = "amqp://admin:${var.mq_password}@${module.mq.broker_amqp_endpoints[0]}:5672/"
    KAFKA_BOOTSTRAP_SERVERS = module.msk.bootstrap_brokers_sasl_iam
    JWT_SECRET         = random_password.jwt_secret.result
    ENCRYPTION_KEY     = random_password.encryption_key.result
    SENTRY_DSN         = var.sentry_dsn
  })
}

resource "aws_kms_key" "secrets" {
  description             = "KMS key for application secrets"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Allow SecretsManager Service"
        Effect = "Allow"
        Principal = {
          Service = "secretsmanager.amazonaws.com"
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

  tags = {
    Environment = var.environment
  }
}

# Random passwords for secrets
resource "random_password" "db_password" {
  length  = 32
  special = false
  keepers = {
    # Regenerate on environment change
    environment = var.environment
  }
}

resource "random_password" "redis_password" {
  length  = 32
  special = false
}

resource "random_password" "mq_password" {
  length  = 32
  special = false
}

resource "random_password" "jwt_secret" {
  length  = 64
  special = false
}

resource "random_password" "encryption_key" {
  length  = 32
  special = false
}

# Variables for sensitive values (override in terraform.tfvars)
variable "db_password" {
  type        = string
  description = "Database password"
  sensitive   = true
  default     = ""
}

variable "redis_password" {
  type        = string
  description = "Redis password"
  sensitive   = true
  default     = ""
}

variable "mq_password" {
  type        = string
  description = "MQ password"
  sensitive   = true
  default     = ""
}

variable "sentry_dsn" {
  type        = string
  description = "Sentry DSN"
  sensitive   = true
  default     = ""
}

# Outputs
output "vpc_id" {
  value = module.vpc.vpc_id
}

output "eks_cluster_name" {
  value = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "rds_endpoint" {
  value = module.rds.primary_endpoint
}

output "redis_endpoint" {
  value = module.elasticache.primary_endpoint
}

output "mq_endpoints" {
  value = module.mq.broker_amqp_endpoints
}

output "msk_bootstrap_brokers" {
  value = module.msk.bootstrap_brokers_sasl_iam
}

output "alb_dns_name" {
  value = module.alb.alb_dns_name
}

output "app_secrets_arn" {
  value = aws_secretsmanager_secret.app_secrets.arn
}