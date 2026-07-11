resource "aws_ecs_cluster" "app" {
  name = "doc-helper-cluster"
}

resource "aws_ecs_service" "app" {
  name            = "doc-helper-ai-task-service-ao2opdat"
  cluster         = aws_ecs_cluster.app.id
  task_definition = data.aws_ecs_task_definition.current.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    assign_public_ip = true
    subnets          = var.subnet_ids
    security_groups  = [aws_security_group.ecs_service.id]
  }

  lifecycle {
    # Application CD registers and deploys immutable task-definition revisions.
    ignore_changes = [task_definition]
  }
}
