terraform {
  required_version = ">= 1.15"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}

resource "aws_s3_bucket" "pipeline_data" {
  bucket        = "${var.project_name}-${data.aws_caller_identity.current.account_id}"
  force_destroy = true

  tags = {
    Project = var.project_name
    Purpose = "mlops-learning-portfolio"
  }
}

resource "aws_s3_bucket_public_access_block" "pipeline_data" {
  bucket = aws_s3_bucket.pipeline_data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_secretsmanager_secret" "teams_webhook" {
  name        = "${var.project_name}/teams-webhook-url"
  description = "Teams Workflows webhook URL used by the Prefect flow's failure alert"

  tags = {
    Project = var.project_name
  }
}

resource "aws_secretsmanager_secret_version" "teams_webhook" {
  secret_id     = aws_secretsmanager_secret.teams_webhook.id
  secret_string = var.teams_webhook_url
}
