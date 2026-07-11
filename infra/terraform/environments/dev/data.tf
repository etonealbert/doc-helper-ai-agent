data "aws_caller_identity" "current" {}

data "aws_vpc" "current" {
  id = var.vpc_id
}

data "aws_subnet" "public" {
  for_each = toset(var.subnet_ids)
  id       = each.value
}

data "aws_route53_zone" "main" {
  name         = "albertlukmanovlabs.lol."
  private_zone = false
}

data "aws_iam_openid_connect_provider" "github" {
  arn = var.github_oidc_provider_arn
}

data "aws_ecs_task_definition" "current" {
  task_definition = "doc-helper-ai-task"
}

locals {
  common_tags = {
    Project     = "doc-helper-ai-agent"
    Environment = "dev"
    ManagedBy   = "terraform"
  }
}
