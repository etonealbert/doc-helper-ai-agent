resource "aws_cloudwatch_log_group" "ecs" {
  name              = "/ecs/doc-helper-ai-task"
  retention_in_days = 14
}
