variable "aws_region" {
  description = "AWS region containing the existing application infrastructure."
  type        = string
  default     = "us-east-1"
}

variable "vpc_id" {
  description = "ID of the existing VPC used by the ECS service."
  type        = string

  validation {
    condition     = can(regex("^vpc-[0-9a-f]+$", var.vpc_id))
    error_message = "vpc_id must be an AWS VPC ID."
  }
}

variable "subnet_ids" {
  description = "Existing public subnet IDs used by the ECS service."
  type        = list(string)

  validation {
    condition     = length(var.subnet_ids) > 0 && alltrue([for id in var.subnet_ids : can(regex("^subnet-[0-9a-f]+$", id))])
    error_message = "subnet_ids must contain at least one AWS subnet ID."
  }
}

variable "ecs_security_group_id" {
  description = "ID of the existing ECS service security group to import."
  type        = string

  validation {
    condition     = can(regex("^sg-[0-9a-f]+$", var.ecs_security_group_id))
    error_message = "ecs_security_group_id must be an AWS security group ID."
  }
}

variable "github_oidc_provider_arn" {
  description = "ARN of the existing token.actions.githubusercontent.com IAM OIDC provider."
  type        = string
  default     = "arn:aws:iam::964866958896:oidc-provider/token.actions.githubusercontent.com"
}

variable "github_repository" {
  description = "GitHub owner/repository allowed to assume the deployment role."
  type        = string
  default     = "etonealbert/doc-helper-ai-agent"
}
