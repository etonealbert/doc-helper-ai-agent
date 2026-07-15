data "aws_iam_policy_document" "ecs_task_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }

    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["arn:aws:ecs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:*"]
    }
  }
}

resource "aws_iam_role" "ecs_task" {
  name               = "DocHelperEcsTaskRole"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume_role.json
}

data "aws_iam_policy_document" "dynamodb_write" {
  statement {
    effect    = "Allow"
    actions   = ["dynamodb:PutItem"]
    resources = [aws_dynamodb_table.crm_records.arn]
  }
}

resource "aws_iam_role_policy" "ecs_task_dynamodb" {
  name   = "DocHelperDynamoDBPutItem"
  role   = aws_iam_role.ecs_task.id
  policy = data.aws_iam_policy_document.dynamodb_write.json
}

data "aws_iam_policy_document" "github_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [data.aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repository}:ref:refs/heads/main"]
    }
  }
}

resource "aws_iam_role" "github_deploy" {
  name               = "GitHubActionsDeployRole"
  assume_role_policy = data.aws_iam_policy_document.github_assume_role.json
}

data "aws_iam_policy_document" "github_pass_roles" {
  statement {
    effect  = "Allow"
    actions = ["iam:PassRole"]
    resources = [
      "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/ecsTaskExecutionRole",
      aws_iam_role.ecs_task.arn,
    ]

    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role_policy" "github_pass_roles" {
  name   = "GitHubActionsPassEcsRoles"
  role   = aws_iam_role.github_deploy.id
  policy = data.aws_iam_policy_document.github_pass_roles.json
}

data "aws_iam_policy_document" "ecs_execution_ssm" {
  statement {
    sid    = "ReadDocHelperOpenAiParameter"
    effect = "Allow"

    actions = [
      "ssm:GetParameters",
    ]

    resources = [
      data.aws_ssm_parameter.openai_api_key.arn,
    ]
  }
}

resource "aws_iam_role_policy" "ecs_execution_ssm" {
  name   = "DocHelperReadOpenAiParameter"
  role   = data.aws_iam_role.ecs_execution.id
  policy = data.aws_iam_policy_document.ecs_execution_ssm.json
}
