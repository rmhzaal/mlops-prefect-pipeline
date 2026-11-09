variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "eu-west-2"
}

variable "project_name" {
  description = "Short name used to tag and name resources for this project"
  type        = string
  default     = "mlops-prefect-pipeline"
}

variable "teams_webhook_url" {
  description = "Teams Workflows webhook URL"
  type        = string
  sensitive   = true
}
