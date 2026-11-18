# ElastiCache Module for Vibe-God
# Creates a production-grade Redis cluster with replication

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

variable "cluster_id" {
  type        = string
  description = "ElastiCache cluster ID"
  default     = "vibe-god"
}

variable "engine_version" {
  type        = string
  description = "Redis version"
  default     = "7.1"
}

variable "node_type" {
  type        = string
  description = "Node type"
  default     = "cache.r6g.xlarge"
}

variable "num_cache_nodes" {
  type        = number
  description = "Number of cache nodes"
  default     = 2
}

variable "automatic_failover_enabled" {
  type        = bool
  description = "Enable automatic failover"
  default     = true
}

variable "multi_az_enabled" {
  type        = bool
  description = "Enable Multi-AZ"
  default     = true
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
  type        = list(string)
  description = "Security group IDs"
}

variable "tags" {
  type        = map(string)
  description = "Common tags"
  default     = {}
}

variable "parameter_group_name" {
  type        = string
  description = "Parameter group name"
  default     = "vibe-god-redis-params"
}

variable "backup_retention_limit" {
  type        = number
  description = "Backup retention in days"
  default     = 7
}

variable "snapshot_window" {
  type        = string
  description = "Snapshot window"
  default     = "03:00-05:00"
}

variable "maintenance_window" {
  type        = string
  description = "Maintenance window"
  default     = "sun:05:00-sun:07:00"
}

variable "auth_token" {
  type        = string
  description = "Auth token"
  sensitive   = true
  default     = ""
}

locals {
  common_tags = merge(var.tags, {
    Project     = "vibe-god"
    Environment = "production"
    ManagedBy   = "terraform"
  })
}

# Random auth token if not provided
resource "random_password" "auth_token" {
  length  = 32
  special = false
}

# Subnet Group
resource "aws_elasticache_subnet_group" "main" {
  name       = "${var.cluster_id}-subnet-group"
  subnet_ids = var.private_subnet_ids

  tags = local.common_tags
}

# Parameter Group
resource "aws_elasticache_parameter_group" "main" {
  name        = var.parameter_group_name
  family      = "redis7"
  description = "Parameter group for ${var.cluster_id}"

  parameter {
    name  = "maxmemory-policy"
    value = "allkeys-lru"
  }

  parameter {
    name  = "timeout"
    value = "300"
  }

  parameter {
    name  = "tcp-keepalive"
    value = "60"
  }

  parameter {
    name  = "lua-time-limit"
    value = "5000"
  }

  parameter {
    name  = "slowlog-log-slower-than"
    value = "10000"
  }

  parameter {
    name  = "slowlog-max-len"
    value = "128"
  }

  parameter {
    name  = "notify-keyspace-events"
    value = "Ex"
  }

  tags = local.common_tags
}

# KMS Key for Encryption
resource "aws_kms_key" "elasticache" {
  description             = "KMS key for ElastiCache encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Allow ElastiCache Service"
        Effect = "Allow"
        Principal = {
          Service = "elasticache.amazonaws.com"
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

# Replication Group (Cluster Mode Disabled)
resource "aws_elasticache_replication_group" "main" {
  replication_group_id       = var.cluster_id
  engine                     = "redis"
  engine_version             = var.engine_version
  node_type                  = var.node_type
  number_cache_clusters      = var.num_cache_nodes
  automatic_failover_enabled = var.automatic_failover_enabled
  multi_az_enabled           = var.multi_az_enabled

  subnet_group_name  = aws_elasticache_subnet_group.main.name
  parameter_group_name = aws_elasticache_parameter_group.main.name
  security_group_ids = var.security_group_ids

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = var.auth_token != "" ? var.auth_token : random_password.auth_token.result

  kms_key_id = aws_kms_key.elasticache.arn

  snapshot_retention_limit = var.backup_retention_limit
  snapshot_window          = var.snapshot_window
  maintenance_window       = var.maintenance_window

  log_delivery_configuration {
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "slow-log"
    destination_details {
      cloudwatch_logs {
        log_group = aws_cloudwatch_log_group.slow_log.name
      }
    }
  }

  log_delivery_configuration {
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "engine-log"
    destination_details {
      cloudwatch_logs {
        log_group = aws_cloudwatch_log_group.engine_log.name
      }
    }
  }

  tags = merge(local.common_tags, {
    Name = var.cluster_id
  })
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "slow_log" {
  name              = "/aws/elasticache/${var.cluster_id}/slow-log"
  retention_in_days = 30

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "engine_log" {
  name              = "/aws/elasticache/${var.cluster_id}/engine-log"
  retention_in_days = 30

  tags = local.common_tags
}

# Outputs
output "primary_endpoint" {
  value = aws_elasticache_replication_group.main.primary_endpoint_address
}

output "primary_port" {
  value = aws_elasticache_replication_group.main.primary_endpoint_port
}

output "reader_endpoint" {
  value = aws_elasticache_replication_group.main.reader_endpoint_address
}

output "reader_port" {
  value = aws_elasticache_replication_group.main.reader_endpoint_port
}

output "configuration_endpoint" {
  value = aws_elasticache_replication_group.main.configuration_endpoint_address
}

output "configuration_port" {
  value = aws_elasticache_replication_group.main.configuration_endpoint_port
}

output "auth_token" {
  value     = var.auth_token != "" ? var.auth_token : random_password.auth_token.result
  sensitive = true
}

output "arn" {
  value = aws_elasticache_replication_group.main.arn
}