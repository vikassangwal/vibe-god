# Amazon MQ Module for Vibe-God
# Creates a production-grade RabbitMQ broker

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

variable "broker_name" {
  type        = string
  description = "Broker name"
  default     = "vibe-god"
}

variable "engine_version" {
  type        = string
  description = "RabbitMQ version"
  default     = "3.12"
}

variable "instance_type" {
  type        = string
  description = "Instance type"
  default     = "mq.m5.large"
}

variable "deployment_mode" {
  type        = string
  description = "Deployment mode (SINGLE_INSTANCE, CLUSTER_MULTI_AZ, ACTIVE_STANDBY_MULTI_AZ)"
  default     = "CLUSTER_MULTI_AZ"
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

variable "username" {
  type        = string
  description = "Admin username"
  default     = "admin"
}

variable "password" {
  type        = string
  description = "Admin password"
  sensitive   = true
  default     = ""
}

variable "publicly_accessible" {
  type        = bool
  description = "Publicly accessible"
  default     = false
}

variable "maintenance_window" {
  type        = string
  description = "Maintenance window"
  default     = "sun:03:00-sun:05:00"
}

locals {
  common_tags = merge(var.tags, {
    Project     = "vibe-god"
    Environment = "production"
    ManagedBy   = "terraform"
  })
}

# Random password if not provided
resource "random_password" "admin_password" {
  length  = 32
  special = false
}

# KMS Key for Encryption
resource "aws_kms_key" "mq" {
  description             = "KMS key for MQ encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Allow MQ Service"
        Effect = "Allow"
        Principal = {
          Service = "mq.amazonaws.com"
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

# MQ Broker
resource "aws_mq_broker" "main" {
  broker_name        = var.broker_name
  engine_type        = "RABBITMQ"
  engine_version     = var.engine_version
  host_instance_type = var.instance_type
  deployment_mode    = var.deployment_mode

  vpc_config {
    subnet_ids        = var.private_subnet_ids
    security_groups   = var.security_group_ids
    assign_public_ip  = var.publicly_accessible
  }

  encryption_options {
    kms_key_id = aws_kms_key.mq.arn
    use_aws_owned_key = var.password == "" && var.password == "" ? true : false
  }

  user {
    username = var.username
    password = var.password != "" ? var.password : random_password.admin_password.result
    console_access = true
    groups     = ["administrators"]
  }

  maintenance_window_start_time {
    day_of_week = "SUNDAY"
    time_of_day = "03:00"
    time_zone   = "UTC"
  }

  logs {
    general = true
    audit   = true
  }

  tags = merge(local.common_tags, {
    Name = var.broker_name
  })
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "general" {
  name              = "/aws/mq/${var.broker_name}/general"
  retention_in_days = 30

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "audit" {
  name              = "/aws/mq/${var.broker_name}/audit"
  retention_in_days = 30

  tags = local.common_tags
}

# Outputs
output "broker_id" {
  value = aws_mq_broker.main.id
}

output "broker_arn" {
  value = aws_mq_broker.main.arn
}

output "broker_endpoints" {
  value = aws_mq_broker.main.endpoints
}

output "broker_amqp_endpoints" {
  value = aws_mq_broker.main.amqp_endpoints
}

output "broker_mqtt_endpoints" {
  value = aws_mq_broker.main.mqtt_endpoints
}

output "broker_stomp_endpoints" {
  value = aws_mq_broker.main.stomp_endpoints
}

output "broker_wss_endpoints" {
  value = aws_mq_broker.main.wss_endpoints
}

output "username" {
  value = var.username
}

output "password" {
  value     = var.password != "" ? var.password : random_password.admin_password.result
  sensitive = true
}