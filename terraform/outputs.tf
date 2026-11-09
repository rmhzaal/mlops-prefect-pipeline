output "bucket_name" {
  description = "S3 bucket holding this project's data/model artifacts"
  value       = aws_s3_bucket.pipeline_data.bucket
}

output "teams_webhook_secret_name" {
  description = "Secrets Manager secret holding the Teams webhook URL"
  value       = aws_secretsmanager_secret.teams_webhook.name
}
