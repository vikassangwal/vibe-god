# Amazon MSK Module for Vibe-God
# Creates a production-grade Kafka cluster

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

variable "cluster_name" {
  type        = string
  description = "MSK cluster name"
  default     = "vibe-god"
}

variable "kafka_version" {
  type        = string
  description = "Kafka version"
  default     = "3.6"
}

variable "instance_type" {
  type        = string
  description = "Broker instance type"
  default     = "kafka.m7g.large"
}

variable "broker_count" {
  type        = number
  description = "Number of brokers"
  default     = 3
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

variable "storage_per_broker" {
  type        = number
  description = "Storage per broker in GB"
  default     = 100
}

variable "monitoring_level" {
  type        = string
  description = "Monitoring level (DEFAULT, PER_BROKER, PER_TOPIC_PER_BROKER, PER_TOPIC_PER_PARTITION)"
  default     = "PER_BROKER"
}

variable "encryption_in_transit" {
  type        = bool
  description = "Enable encryption in transit"
  default     = true
}

variable "encryption_at_rest" {
  type        = bool
  description = "Enable encryption at rest"
  default     = true
}

variable "client_authentication" {
  type        = string
  description = "Client authentication type (SASL_SCRAM, SASL_IAM, TLS)"
  default     = "SASL_SCRAM"
}

locals {
  common_tags = merge(var.tags, {
    Project     = "vibe-god"
    Environment = "production"
    ManagedBy   = "terraform"
  })
}

# KMS Key for Encryption at Rest
resource "aws_kms_key" "msk" {
  description             = "KMS key for MSK encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Allow MSK Service"
        Effect = "Allow"
        Principal = {
          Service = "kafka.amazonaws.com"
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

# MSK Cluster
resource "aws_msk_cluster" "main" {
  cluster_name           = var.cluster_name
  kafka_version          = var.kafka_version
  number_of_broker_nodes = var.broker_count

  broker_node_group_info {
    instance_type   = var.instance_type
    client_subnets  = var.private_subnet_ids
    security_groups = var.security_group_ids

    storage_info {
      ebs_storage_info {
        volume_size = var.storage_per_broker
      }
    }

    az_distribution = "DEFAULT"
  }

  encryption_info {
    encryption_at_rest {
      kms_key_id = var.encryption_at_rest ? aws_kms_key.msk.arn : null
    }
    encryption_in_transit {
      client_broker = var.encryption_in_transit ? var.client_authentication : "PLAINTEXT"
      in_cluster    = var.encryption_in_transit
    }
  }

  client_authentication {
    sasl {
      scram = var.client_authentication == "SASL_SCRAM"
      iam   = var.client_authentication == "SASL_IAM"
    }
    tls = var.client_authentication == "TLS"
  }

  logging_info {
    broker_logs {
      cloudwatch_logs {
        enabled   = true
        log_group = aws_cloudwatch_log_group.msk.name
      }
    }
  }

  monitoring_level = var.monitoring_level

  tags = merge(local.common_tags, {
    Name = var.cluster_name
  })
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "msk" {
  name              = "/aws/msk/${var.cluster_name}"
  retention_in_days = 30

  tags = local.common_tags
}

# IAM Role for MSK
resource "aws_iam_role" "msk" {
  name = "${var.cluster_name}-msk-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "kafka.amazonaws.com"
      }
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy" "msk" {
  name = "${var.cluster_name}-msk-policy"
  role = aws_iam_role.msk.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = [
        "ec2:CreateNetworkInterface",
        "ec2:DescribeNetworkInterfaces",
        "ec2:DeleteNetworkInterface",
        "ec2:DescribeSubnets",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeVpcs",
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogGroups"
      ]
      Effect   = "Allow"
      Resource = "*"
    }]
  })
}

# Outputs
output "cluster_arn" {
  value = aws_msk_cluster.main.arn
}

output "cluster_name" {
  value = aws_msk_cluster.main.cluster_name
}

output "bootstrap_brokers" {
  value = aws_msk_cluster.main.bootstrap_brokers
}

output "bootstrap_brokers_tls" {
  value = aws_msk_cluster.main.bootstrap_brokers_tls
}

output "bootstrap_brokers_sasl_scram" {
  value = aws_msk_cluster.main.bootstrap_brokers_sasl_scram
}

output "bootstrap_brokers_sasl_iam" {
  value = aws_msk_cluster.main.bootstrap_brokers_sasl_iam
}

output "zookeeper_connect_string" {
  value = aws_msk_cluster.main.zookeeper_connect_string
}

output "zookeeper_connect_string_tls" {
  value = aws_msk_cluster.main.zookeeper_connect_string_tls
}