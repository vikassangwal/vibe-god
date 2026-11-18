# RDS Module for Vibe-God
# Creates a production-grade PostgreSQL RDS instance with read replicas

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

variable "identifier" {
  type        = string
  description = "RDS instance identifier"
  default     = "vibe-god"
}

variable "engine_version" {
  type        = string
  description = "PostgreSQL version"
  default     = "16.3"
}

variable "instance_class" {
  type        = string
  description = "Instance class"
  default     = "db.r6g.xlarge"
}

variable "allocated_storage" {
  type        = number
  description = "Allocated storage in GB"
  default     = 100
}

variable "max_allocated_storage" {
  type        = number
  description = "Max allocated storage for autoscaling"
  default     = 500
}

variable "db_name" {
  type        = string
  description = "Database name"
  default     = "vibe_god"
}

variable "username" {
  type        = string
  description = "Master username"
  default     = "postgres"
}

variable "password" {
  type        = string
  description = "Master password"
  sensitive   = true
}

variable "vpc_id" {
  type        = string
  description = "VPC ID"
}

variable "database_subnet_ids" {
  type        = list(string)
  description = "Database subnet IDs"
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

variable "backup_retention_period" {
  type        = number
  description = "Backup retention period in days"
  default     = 30
}

variable "backup_window" {
  type        = string
  description = "Backup window"
  default     = "03:00-04:00"
}

variable "maintenance_window" {
  type        = string
  description = "Maintenance window"
  default     = "sun:04:00-sun:05:00"
}

variable "replica_count" {
  type        = number
  description = "Number of read replicas"
  default     = 2
}

variable "replica_instance_class" {
  type        = string
  description = "Read replica instance class"
  default     = "db.r6g.large"
}

locals {
  common_tags = merge(var.tags, {
    Project     = "vibe-god"
    Environment = "production"
    ManagedBy   = "terraform"
  })
}

# Random password for initial creation (if not provided)
resource "random_password" "db_password" {
  length  = 32
  special = false
}

# DB Subnet Group
resource "aws_db_subnet_group" "main" {
  name       = "${var.identifier}-subnet-group"
  subnet_ids = var.database_subnet_ids

  tags = local.common_tags
}

# DB Parameter Group
resource "aws_db_parameter_group" "main" {
  name        = "${var.identifier}-params"
  family      = "postgres16"
  description = "Parameter group for ${var.identifier}"

  parameter {
    name  = "shared_preload_libraries"
    value = "pg_stat_statements,auto_explain"
  }

  parameter {
    name  = "pg_stat_statements.track"
    value = "all"
  }

  parameter {
    name  = "pg_stat_statements.max"
    value = "10000"
  }

  parameter {
    name  = "auto_explain.log_min_duration"
    value = "1000"
  }

  parameter {
    name  = "auto_explain.log_analyze"
    value = "true"
  }

  parameter {
    name  = "log_statement"
    value = "ddl"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }

  parameter {
    name  = "idle_in_transaction_session_timeout"
    value = "300000"
  }

  parameter {
    name  = "max_connections"
    value = "200"
  }

  tags = local.common_tags
}

# KMS Key for Encryption
resource "aws_kms_key" "rds" {
  description             = "KMS key for RDS encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Allow RDS Service"
        Effect = "Allow"
        Principal = {
          Service = "rds.amazonaws.com"
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

# Primary RDS Instance
resource "aws_db_instance" "primary" {
  identifier             = var.identifier
  engine                 = "postgres"
  engine_version         = var.engine_version
  instance_class         = var.instance_class
  allocated_storage      = var.allocated_storage
  max_allocated_storage  = var.max_allocated_storage
  storage_type           = "gp3"
  storage_encrypted      = true
  kms_key_id             = aws_kms_key.rds.arn
  db_name                = var.db_name
  username               = var.username
  password               = var.password != "" ? var.password : random_password.db_password.result

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = var.security_group_ids
  parameter_group_name   = aws_db_parameter_group.main.name

  backup_retention_period = var.backup_retention_period
  backup_window           = var.backup_window
  maintenance_window      = var.maintenance_window

  copy_tags_to_snapshot   = true
  deletion_protection     = true
  skip_final_snapshot     = false
  final_snapshot_identifier = "${var.identifier}-final-snapshot-${formatdate("YYYYMMDDHHmmss", timestamp())}"

  monitoring_interval     = 60
  monitoring_role_arn     = aws_iam_role.enhanced_monitoring.arn

  performance_insights_enabled = true
  performance_insights_kms_key_id = aws_kms_key.rds.arn
  performance_insights_retention_period = 7

  enabled_cloudwatch_logs_exports = ["postgresql", "upgrade"]

  apply_immediately = false

  tags = merge(local.common_tags, {
    Name = var.identifier
    Role = "primary"
  })
}

# Read Replicas
resource "aws_db_instance" "replica" {
  count = var.replica_count

  identifier             = "${var.identifier}-replica-${count.index + 1}"
  engine                 = "postgres"
  engine_version         = var.engine_version
  instance_class         = var.replica_instance_class
  replicate_source_db    = aws_db_instance.primary.identifier

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = var.security_group_ids
  parameter_group_name   = aws_db_parameter_group.main.name

  monitoring_interval     = 60
  monitoring_role_arn     = aws_iam_role.enhanced_monitoring.arn

  performance_insights_enabled = true
  performance_insights_kms_key_id = aws_kms_key.rds.arn

  enabled_cloudwatch_logs_exports = ["postgresql"]

  apply_immediately = false

  tags = merge(local.common_tags, {
    Name = "${var.identifier}-replica-${count.index + 1}"
    Role = "replica"
  })
}

# IAM Role for Enhanced Monitoring
resource "aws_iam_role" "enhanced_monitoring" {
  name = "${var.identifier}-enhanced-monitoring"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "monitoring.rds.amazonaws.com"
      }
    }]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "enhanced_monitoring" {
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
  role       = aws_iam_role.enhanced_monitoring.name
}

# DB Option Group (for extensions)
resource "aws_db_option_group" "main" {
  name        = "${var.identifier}-options"
  engine_name = "postgres"
  major_engine_version = "16"
  description = "Option group for ${var.identifier}"

  option {
    option_name = "pg_stat_statements"
  }

  tags = local.common_tags
}

# Outputs
output "primary_endpoint" {
  value = aws_db_instance.primary.endpoint
}

output "primary_port" {
  value = aws_db_instance.primary.port
}

output "primary_arn" {
  value = aws_db_instance.primary.arn
}

output "replica_endpoints" {
  value = [for r in aws_db_instance.replica : r.endpoint]
}

output "replica_arns" {
  value = [for r in aws_db_instance.replica : r.arn]
}

output "db_name" {
  value = var.db_name
}

output "username" {
  value = var.username
}

output "password" {
  value     = var.password != "" ? var.password : random_password.db_password.result
  sensitive = true
}