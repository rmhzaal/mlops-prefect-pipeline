data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

resource "aws_security_group" "prefect_server" {
  name        = "${var.project_name}-prefect-server"
  description = "Allow Prefect UI/API access from my IP only"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "Prefect UI/API"
    from_port   = 4200
    to_port     = 4200
    protocol    = "tcp"
    cidr_blocks = [var.my_ip_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Project = var.project_name }
}

resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"
  tags = { Project = var.project_name }
}

resource "aws_iam_role" "ecs_task_execution" {
  name = "${var.project_name}-ecs-task-execution"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution" {
  role       = aws_iam_role.ecs_task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_cloudwatch_log_group" "prefect_server" {
  name              = "/ecs/${var.project_name}-prefect-server"
  retention_in_days = 7
}

resource "aws_ecs_task_definition" "prefect_server" {
  family                   = "${var.project_name}-prefect-server"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.ecs_task_execution.arn

  container_definitions = jsonencode([{
    name      = "prefect-server"
    image     = "prefecthq/prefect:3-latest"
    essential = true
    command   = ["prefect", "server", "start", "--host", "0.0.0.0"]
    portMappings = [{ containerPort = 4200, hostPort = 4200, protocol = "tcp" }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.prefect_server.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "prefect-server"
      }
    }
  }])

  tags = { Project = var.project_name }
}

resource "aws_ecs_service" "prefect_server" {
  name            = "${var.project_name}-prefect-server"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.prefect_server.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = data.aws_subnets.default.ids
    security_groups  = [aws_security_group.prefect_server.id]
    assign_public_ip = true
  }

  tags = { Project = var.project_name }
}
