data "aws_region" "current" {}

locals {
  secret_arns = distinct([
    for value in values(var.secrets) : replace(value, "/:[^:]+::$/", "")
  ])

  object_storage_statements = var.object_storage_bucket_arn == null ? [] : [
    {
      Effect   = "Allow"
      Action   = ["s3:DeleteObject", "s3:GetObject", "s3:PutObject"]
      Resource = "${var.object_storage_bucket_arn}/*"
    },
    {
      Effect   = "Allow"
      Action   = ["s3:ListBucket"]
      Resource = var.object_storage_bucket_arn
    },
    {
      Effect = "Allow"
      Action = [
        "kms:Decrypt",
        "kms:DescribeKey",
        "kms:Encrypt",
        "kms:GenerateDataKey",
      ]
      Resource = var.kms_key_arn
    },
  ]

  email_statements = var.ses_identity_arn == null ? [] : [
    {
      Effect   = "Allow"
      Action   = ["ses:SendEmail", "ses:SendRawEmail"]
      Resource = var.ses_identity_arn
    }
  ]

  tracing_statements = var.enable_xray ? [
    {
      Effect   = "Allow"
      Action   = ["xray:PutTraceSegments", "xray:PutTelemetryRecords"]
      Resource = "*"
    }
  ] : []

  application_statements = concat(
    [
      {
        Effect = "Allow"
        Action = [
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:ReceiveMessage",
          "sqs:SendMessage",
        ]
        Resource = var.queue_arn
      },
    ],
    var.enable_execute_command ? [
      {
        Effect = "Allow"
        Action = [
          "ssmmessages:CreateControlChannel",
          "ssmmessages:CreateDataChannel",
          "ssmmessages:OpenControlChannel",
          "ssmmessages:OpenDataChannel",
        ]
        Resource = "*"
      }
    ] : [],
    local.email_statements,
    local.object_storage_statements,
    local.tracing_statements,
  )

  tmp_initializer = {
    name                   = "init-tmp"
    image                  = var.image
    essential              = false
    user                   = "0"
    readonlyRootFilesystem = true
    command                = ["sh", "-c", "chmod 1777 /tmp"]
    mountPoints = [
      {
        sourceVolume  = "tmp"
        containerPath = "/tmp"
        readOnly      = false
      }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.this.name
        "awslogs-region"        = data.aws_region.current.name
        "awslogs-stream-prefix" = "init"
      }
    }
  }

  application_container = {
    name                   = var.name
    image                  = var.image
    essential              = true
    readonlyRootFilesystem = true
    stopTimeout            = 30
    dependsOn = [
      {
        containerName = "init-tmp"
        condition     = "SUCCESS"
      }
    ]
    linuxParameters = {
      initProcessEnabled = true
    }
    mountPoints = [
      {
        sourceVolume  = "tmp"
        containerPath = "/tmp"
        readOnly      = false
      }
    ]
    portMappings = var.expose_port ? [
      {
        containerPort = var.container_port
        protocol      = "tcp"
      }
    ] : []
    command = length(var.command) == 0 ? null : var.command
    environment = [
      for key, value in var.environment : {
        name  = key
        value = value
      }
    ]
    secrets = [
      for key, value in var.secrets : {
        name      = key
        valueFrom = value
      }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.this.name
        "awslogs-region"        = data.aws_region.current.name
        "awslogs-stream-prefix" = "ecs"
      }
    }
  }

  health_check = {
    healthCheck = {
      command = [
        "CMD-SHELL",
        "python -c 'import urllib.request; urllib.request.urlopen(\"http://localhost:${var.container_port}/api/health/live/\", timeout=3)' || exit 1",
      ]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
  }

  xray_container = {
    name                   = "xray-daemon"
    image                  = var.xray_image
    essential              = false
    readonlyRootFilesystem = true
    user                   = "1337"
    portMappings = [
      {
        containerPort = 2000
        protocol      = "udp"
      }
    ]
    command = ["-o"]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.this.name
        "awslogs-region"        = data.aws_region.current.name
        "awslogs-stream-prefix" = "xray"
      }
    }
  }

  application_with_health = merge(
    local.application_container,
    var.enable_health_check ? local.health_check : {},
  )

  container_definitions = var.enable_xray ? [
    local.tmp_initializer,
    local.application_with_health,
    local.xray_container,
  ] : [
    local.tmp_initializer,
    local.application_with_health,
  ]
}

data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "execution" {
  name               = "${var.name}-exec"
  assume_role_policy = data.aws_iam_policy_document.assume.json
  tags               = var.tags
}

resource "aws_iam_role_policy_attachment" "execution" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "secrets" {
  role = aws_iam_role.execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = local.secret_arns
      },
      {
        Effect   = "Allow"
        Action   = ["kms:Decrypt"]
        Resource = var.kms_key_arn
      },
    ]
  })
}

resource "aws_iam_role" "task" {
  name               = "${var.name}-task"
  assume_role_policy = data.aws_iam_policy_document.assume.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "task" {
  role = aws_iam_role.task.id
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = local.application_statements
  })
}

resource "aws_cloudwatch_log_group" "this" {
  name              = "/aws/ecs/${var.name}"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.kms_key_arn
  tags              = var.tags
}

resource "aws_ecs_task_definition" "this" {
  family                   = var.name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = tostring(var.cpu)
  memory                   = tostring(var.memory)
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn
  container_definitions    = jsonencode(local.container_definitions)

  volume {
    name = "tmp"
  }

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  tags = var.tags
}

resource "aws_ecs_service" "this" {
  name                               = var.name
  cluster                            = var.cluster_arn
  task_definition                    = aws_ecs_task_definition.this.arn
  desired_count                      = var.desired_count
  launch_type                        = "FARGATE"
  enable_execute_command             = var.enable_execute_command
  deployment_minimum_healthy_percent = var.desired_count == 0 ? 0 : 100
  deployment_maximum_percent         = 200
  health_check_grace_period_seconds  = var.target_group_arn == null ? null : 120
  wait_for_steady_state               = true
  propagate_tags                      = "SERVICE"

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = var.security_group_ids
    assign_public_ip = false
  }

  dynamic "load_balancer" {
    for_each = var.target_group_arn == null ? [] : [1]
    content {
      target_group_arn = var.target_group_arn
      container_name   = var.name
      container_port   = var.container_port
    }
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  depends_on = [
    aws_iam_role_policy_attachment.execution,
    aws_iam_role_policy.secrets,
    aws_iam_role_policy.task,
  ]

  tags = var.tags
}

resource "aws_appautoscaling_target" "this" {
  count              = var.enable_autoscaling && var.desired_count > 0 ? 1 : 0
  max_capacity       = max(var.desired_count * 4, 2)
  min_capacity       = max(var.desired_count, 1)
  resource_id        = "service/${element(reverse(split("/", var.cluster_arn)), 0)}/${aws_ecs_service.this.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "cpu" {
  count              = length(aws_appautoscaling_target.this)
  name               = "${var.name}-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.this[0].resource_id
  scalable_dimension = aws_appautoscaling_target.this[0].scalable_dimension
  service_namespace  = aws_appautoscaling_target.this[0].service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 60
  }
}
