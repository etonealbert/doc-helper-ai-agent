resource "aws_security_group" "ecs_service" {
  name        = "doc-helper-ai-agent-sg"
  description = "Public access to Doc Helper API"
  vpc_id      = data.aws_vpc.current.id

  ingress {
    description = "FastAPI demo endpoint"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
