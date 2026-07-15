# Import blocks are intentionally retained as adoption documentation. Populate
# terraform.tfvars with discovered IDs and review an imports-only plan.
import {
  to = aws_ecr_repository.app
  id = "doc-helper-ai-agent"
}

import {
  to = aws_ecr_lifecycle_policy.app
  id = "doc-helper-ai-agent"
}

import {
  to = aws_dynamodb_table.crm_records
  id = "doc-helper-records"
}

import {
  to = aws_cloudwatch_log_group.ecs
  id = "/ecs/doc-helper-ai-task"
}

import {
  to = aws_ecs_cluster.app
  id = "doc-helper-cluster"
}

import {
  to = aws_ecs_service.app
  id = "doc-helper-cluster/doc-helper-ai-task-service-ao2opdat"
}

import {
  to = aws_security_group.ecs_service
  id = var.ecs_security_group_id
}

import {
  to = aws_iam_role.ecs_task
  id = "DocHelperEcsTaskRole"
}

import {
  to = aws_iam_role_policy.ecs_task_dynamodb
  id = "DocHelperEcsTaskRole:DocHelperDynamoDBPutItem"
}

import {
  to = aws_iam_role.github_deploy
  id = "GitHubActionsDeployRole"
}

import {
  to = aws_iam_role_policy.github_pass_roles
  id = "GitHubActionsDeployRole:GitHubActionsPassEcsRoles"
}

import {
  to = aws_cloudfront_distribution.api
  id = "E1EBNESOJHEJB0"
}

import {
  to = aws_cloudfront_origin_request_policy.api
  id = "doc-helper-api-origin-request"
}
