output "bucket_name" {
  description = "S3 bucket for Terraform remote state."
  value       = aws_s3_bucket.state.id
}

output "dynamodb_table" {
  description = "DynamoDB table for state locking."
  value       = aws_dynamodb_table.lock.name
}

output "region" {
  value = var.region
}
