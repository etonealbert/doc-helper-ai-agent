output "state_bucket_name" {
  description = "S3 bucket used by the dev Terraform backend."
  value       = aws_s3_bucket.terraform_state.id
}

output "state_bucket_arn" {
  description = "ARN of the S3 Terraform state bucket."
  value       = aws_s3_bucket.terraform_state.arn
}
