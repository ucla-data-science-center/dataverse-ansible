# ==============================================================================
# INSTRUCTIONS
# This snippet contains the code required to add RDS to your Terraform module.
# You will need to modify three files in 'modules/dataverse_stack/':
# 1. variables.tf (Add the new variables)
# 2. rds.tf (Create this file with the resource blocks)
# 3. outputs.tf (Add the endpoint output)
# ==============================================================================

# ------------------------------------------------------------------------------
# 1. Add these to modules/dataverse_stack/variables.tf
# ------------------------------------------------------------------------------

variable "vpc_id" {
  description = "The VPC ID where resources will be created. Required for the RDS Security Group."
  type        = string
}

variable "subnet_ids" {
  description = "List of Subnet IDs for the RDS Subnet Group. Must verify these exist in the chosen VPC and span at least 2 Availability Zones."
  type        = list(string)
}

variable "db_password" {
  description = "Master password for the RDS PostgreSQL instance."
  type        = string
  sensitive   = true
}

variable "rds_engine_version" {
  description = "The version of the PostgreSQL engine to use."
  type        = string
  default     = "16.3" # Updated to a more recent minor version, verify availability in your region
}

variable "rds_instance_class" {
  description = "The instance type of the RDS database."
  type        = string
  default     = "db.t3.medium"
}

# ------------------------------------------------------------------------------
# 2. Create modules/dataverse_stack/rds.tf
# ------------------------------------------------------------------------------

# Security Group for RDS
resource "aws_security_group" "rds" {
  name        = "${var.environment}-dataverse-rds-sg"
  description = "Allow inbound PostgreSQL traffic from Dataverse App Server"
  vpc_id      = var.vpc_id

  ingress {
    description     = "PostgreSQL from App Server SG"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.dataverse.id] # References the App Server SG defined in main.tf
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.environment}-dataverse-rds-sg"
    Environment = var.environment
  }
}

# RDS Subnet Group
resource "aws_db_subnet_group" "dataverse" {
  name       = "${var.environment}-dataverse-subnet-group"
  subnet_ids = var.subnet_ids

  tags = {
    Name = "${var.environment}-dataverse-subnet-group"
  }
}

# The Database Instance
resource "aws_db_instance" "dataverse" {
  identifier        = "${var.environment}-dataverse-db"
  engine            = "postgres"
  engine_version    = var.rds_engine_version
  instance_class    = var.rds_instance_class
  allocated_storage = 50
  storage_type      = "gp3" # General Purpose SSD

  db_name  = "dvndb"
  username = "postgres"
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.dataverse.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  # Snapshot configuration
  skip_final_snapshot       = var.environment == "prod" ? false : true
  final_snapshot_identifier = "${var.environment}-dataverse-final-snapshot"
  backup_retention_period   = var.environment == "prod" ? 7 : 0

  publicly_accessible = false
  performance_insights_enabled = true

  tags = {
    Name        = "${var.environment}-dataverse-db"
    Environment = var.environment
  }
}

# ------------------------------------------------------------------------------
# 3. Add to modules/dataverse_stack/outputs.tf
# ------------------------------------------------------------------------------

output "rds_endpoint" {
  description = "The connection endpoint for the RDS database"
  value       = aws_db_instance.dataverse.address
}

output "rds_port" {
  description = "The port for the RDS database"
  value       = aws_db_instance.dataverse.port
}

# ==============================================================================
# HOW TO USE IN YOUR ENVIRONMENT (e.g. environments/tim/main.tf)
# ==============================================================================
#
# 1. FIND YOUR DEFAULT VPC & SUBNETS (Run these commands):
#    aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query "Vpcs[0].VpcId" --output text
#    aws ec2 describe-subnets --filters Name=vpc-id,Values=<YOUR_VPC_ID> --query "Subnets[*].SubnetId" --output json
#
# 2. UPDATE YOUR MODULE CALL:
#
# module "dataverse_stack" {
#   source = "../../modules/dataverse_stack"
#
#   # Existing variables...
#   environment = "test"
#   # ...
#
#   # NEW VARIABLES
#   vpc_id      = "vpc-0123456789abcdef0"
#   subnet_ids  = ["subnet-11111111", "subnet-22222222"] # Must pick at least 2
#   db_password = var.db_password # Define this in your environment's variables.tf too!
# }