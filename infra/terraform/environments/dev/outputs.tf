output "ecr_repository_url" {
  description = "ECR repository URL used by application CD."
  value       = aws_ecr_repository.app.repository_url
}

output "dynamodb_table_name" {
  description = "DynamoDB table used by the CRM adapter."
  value       = aws_dynamodb_table.crm_records.name
}

output "ecs_cluster_name" {
  description = "ECS cluster deployed to by application CD."
  value       = aws_ecs_cluster.app.name
}

output "ecs_service_name" {
  description = "ECS service deployed to by application CD."
  value       = aws_ecs_service.app.name
}

output "route53_zone_id" {
  description = "Existing hosted zone read by Terraform but updated by application CD."
  value       = data.aws_route53_zone.main.zone_id
}
