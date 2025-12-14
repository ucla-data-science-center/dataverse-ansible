# CloudWatch Monitoring Setup Guide

This guide explains how to set up AWS CloudWatch monitoring for your Dataverse deployment.

## Overview

CloudWatch provides monitoring and observability for your Dataverse infrastructure and application:
- **Infrastructure Metrics**: CPU, memory, disk, network (EC2-level)
- **Application Logs**: Payara, Apache, PostgreSQL, Solr logs
- **Custom Metrics**: Dataverse-specific metrics (optional)
- **Alarms**: Automated alerts for issues

## Part 1: Infrastructure Monitoring (Terraform)

These changes should be made in your `terraform-dataverse/` directory.

### 1.1 CloudWatch Log Groups

Add to your Terraform configuration:

```hcl
# cloudwatch.tf

# Log group for system logs
resource "aws_cloudwatch_log_group" "dataverse_system" {
  name              = "/aws/ec2/dataverse-${var.environment}/system"
  retention_in_days = 30

  tags = {
    Name        = "dataverse-${var.environment}-system-logs"
    Environment = var.environment
    Application = "dataverse"
  }
}

# Log group for application logs
resource "aws_cloudwatch_log_group" "dataverse_application" {
  name              = "/aws/ec2/dataverse-${var.environment}/application"
  retention_in_days = 30

  tags = {
    Name        = "dataverse-${var.environment}-app-logs"
    Environment = var.environment
    Application = "dataverse"
  }
}

# Log group for database logs
resource "aws_cloudwatch_log_group" "dataverse_database" {
  name              = "/aws/ec2/dataverse-${var.environment}/database"
  retention_in_days = 30

  tags = {
    Name        = "dataverse-${var.environment}-db-logs"
    Environment = var.environment
    Application = "dataverse"
  }
}
```

### 1.2 IAM Role for CloudWatch Agent

```hcl
# iam.tf

# IAM role for EC2 instance to send logs to CloudWatch
resource "aws_iam_role" "dataverse_cloudwatch" {
  name = "dataverse-${var.environment}-cloudwatch-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "dataverse-${var.environment}-cloudwatch-role"
    Environment = var.environment
  }
}

# Attach CloudWatch Agent policy
resource "aws_iam_role_policy_attachment" "cloudwatch_agent" {
  role       = aws_iam_role.dataverse_cloudwatch.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

# Attach SSM policy (for parameter store access)
resource "aws_iam_role_policy_attachment" "ssm_managed" {
  role       = aws_iam_role.dataverse_cloudwatch.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Instance profile
resource "aws_iam_instance_profile" "dataverse_cloudwatch" {
  name = "dataverse-${var.environment}-cloudwatch-profile"
  role = aws_iam_role.dataverse_cloudwatch.name
}
```

### 1.3 Update EC2 Instance

Update your EC2 instance resource to use the IAM instance profile:

```hcl
# main.tf (or ec2.tf)

resource "aws_instance" "dataverse" {
  # ... existing configuration ...

  iam_instance_profile = aws_iam_instance_profile.dataverse_cloudwatch.name

  # ... rest of configuration ...
}
```

### 1.4 CloudWatch Alarms

```hcl
# alarms.tf

# CPU utilization alarm
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "dataverse-${var.environment}-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Triggered when CPU exceeds 80%"
  alarm_actions       = [aws_sns_topic.dataverse_alerts.arn]

  dimensions = {
    InstanceId = aws_instance.dataverse.id
  }
}

# Disk usage alarm
resource "aws_cloudwatch_metric_alarm" "high_disk" {
  alarm_name          = "dataverse-${var.environment}-high-disk"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "disk_used_percent"
  namespace           = "CWAgent"
  period              = 300
  statistic           = "Average"
  threshold           = 80
  alarm_description   = "Triggered when disk usage exceeds 80%"
  alarm_actions       = [aws_sns_topic.dataverse_alerts.arn]

  dimensions = {
    InstanceId = aws_instance.dataverse.id
    path       = "/"
    fstype     = "xfs"
  }
}

# Memory utilization alarm
resource "aws_cloudwatch_metric_alarm" "high_memory" {
  alarm_name          = "dataverse-${var.environment}-high-memory"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "mem_used_percent"
  namespace           = "CWAgent"
  period              = 300
  statistic           = "Average"
  threshold           = 85
  alarm_description   = "Triggered when memory usage exceeds 85%"
  alarm_actions       = [aws_sns_topic.dataverse_alerts.arn]

  dimensions = {
    InstanceId = aws_instance.dataverse.id
  }
}

# Instance status check alarm
resource "aws_cloudwatch_metric_alarm" "instance_status" {
  alarm_name          = "dataverse-${var.environment}-instance-status"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "StatusCheckFailed"
  namespace           = "AWS/EC2"
  period              = 60
  statistic           = "Maximum"
  threshold           = 0
  alarm_description   = "Triggered when instance status checks fail"
  alarm_actions       = [aws_sns_topic.dataverse_alerts.arn]

  dimensions = {
    InstanceId = aws_instance.dataverse.id
  }
}

# SNS topic for alerts
resource "aws_sns_topic" "dataverse_alerts" {
  name = "dataverse-${var.environment}-alerts"

  tags = {
    Name        = "dataverse-${var.environment}-alerts"
    Environment = var.environment
  }
}

# SNS topic subscription (email)
resource "aws_sns_topic_subscription" "dataverse_alerts_email" {
  topic_arn = aws_sns_topic.dataverse_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email  # Add this variable
}
```

### 1.5 Variables

Add to `variables.tf`:

```hcl
variable "alert_email" {
  description = "Email address for CloudWatch alarms"
  type        = string
  default     = "devops@ucla.edu"
}
```

### 1.6 Apply Terraform Changes

```bash
cd /path/to/terraform-dataverse
terraform plan
terraform apply
```

## Part 2: CloudWatch Agent Installation (Ansible)

The CloudWatch Agent collects system and application metrics from the EC2 instance.

This is already included in this Ansible role via the task file `tasks/dataverse-cloudwatch.yml`.

To enable CloudWatch monitoring, add to your `group_vars/staging.yml`:

```yaml
cloudwatch:
  enabled: true
  region: us-west-2  # Your AWS region
  log_group_prefix: "/aws/ec2/dataverse-staging"

  # Metrics collection interval (in seconds)
  metrics_collection_interval: 60

  # Logs to collect
  logs:
    - log_group_name: "/aws/ec2/dataverse-staging/system"
      log_stream_name: "{instance_id}/messages"
      file_path: "/var/log/messages"
      timestamp_format: "%b %d %H:%M:%S"

    - log_group_name: "/aws/ec2/dataverse-staging/application"
      log_stream_name: "{instance_id}/payara"
      file_path: "/usr/local/payara6/glassfish/domains/domain1/logs/server.log"
      timestamp_format: "%Y-%m-%dT%H:%M:%S"

    - log_group_name: "/aws/ec2/dataverse-staging/application"
      log_stream_name: "{instance_id}/apache"
      file_path: "/var/log/httpd/error_log"
      timestamp_format: "[%a %b %d %H:%M:%S.%f %Y]"

    - log_group_name: "/aws/ec2/dataverse-staging/database"
      log_stream_name: "{instance_id}/postgresql"
      file_path: "/var/lib/pgsql/16/data/log/postgresql-*.log"
      timestamp_format: "%Y-%m-%d %H:%M:%S"
```

Then run the playbook:

```bash
ansible-playbook -i inventory/staging.yml site.yml --tags cloudwatch
```

## Part 3: Viewing Metrics and Logs

### AWS Console

1. **Metrics**: CloudWatch Console → Metrics → CWAgent, AWS/EC2
2. **Logs**: CloudWatch Console → Log groups → `/aws/ec2/dataverse-*/`
3. **Alarms**: CloudWatch Console → Alarms

### AWS CLI

```bash
# View metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/EC2 \
  --metric-name CPUUtilization \
  --dimensions Name=InstanceId,Value=i-xxxxx \
  --start-time 2024-12-01T00:00:00Z \
  --end-time 2024-12-02T00:00:00Z \
  --period 3600 \
  --statistics Average

# View logs
aws logs tail /aws/ec2/dataverse-staging/application --follow

# Check alarm status
aws cloudwatch describe-alarms \
  --alarm-names dataverse-staging-high-cpu
```

## Part 4: CloudWatch Dashboards

Create a custom dashboard to visualize all metrics:

```hcl
# dashboard.tf

resource "aws_cloudwatch_dashboard" "dataverse" {
  dashboard_name = "dataverse-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/EC2", "CPUUtilization", { stat = "Average", label = "CPU" }]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "CPU Utilization"
          yAxis = {
            left = {
              min = 0
              max = 100
            }
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["CWAgent", "mem_used_percent", { stat = "Average", label = "Memory" }]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "Memory Utilization"
          yAxis = {
            left = {
              min = 0
              max = 100
            }
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["CWAgent", "disk_used_percent", { stat = "Average", label = "Disk" }]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "Disk Utilization"
        }
      },
      {
        type = "log"
        properties = {
          query   = "SOURCE '/aws/ec2/dataverse-${var.environment}/application' | fields @timestamp, @message | filter @message like /ERROR/ | sort @timestamp desc | limit 20"
          region  = var.aws_region
          title   = "Recent Application Errors"
        }
      }
    ]
  })
}
```

## Cost Estimates

CloudWatch costs for a typical Dataverse deployment:

- **Metrics**: First 10 custom metrics free, then $0.30/metric/month
- **Logs Ingestion**: $0.50/GB
- **Logs Storage**: $0.03/GB/month
- **Alarms**: $0.10/alarm/month (first 10 free)
- **Dashboards**: $3/dashboard/month

**Estimated monthly cost for staging**: $10-20/month
**Estimated monthly cost for production**: $30-50/month

## Troubleshooting

### CloudWatch Agent Not Sending Metrics

```bash
# Check agent status
sudo systemctl status amazon-cloudwatch-agent

# Check agent logs
sudo tail -f /opt/aws/amazon-cloudwatch-agent/logs/amazon-cloudwatch-agent.log

# Restart agent
sudo systemctl restart amazon-cloudwatch-agent
```

### Logs Not Appearing in CloudWatch

1. Verify IAM role has `CloudWatchAgentServerPolicy`
2. Check log file permissions (agent needs read access)
3. Verify log group exists in CloudWatch
4. Check agent configuration: `/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json`

### High Costs

- Reduce log retention period (default: 30 days)
- Filter logs before sending (exclude debug/info level)
- Increase metrics collection interval
- Use metric filters sparingly

## References

- [CloudWatch Agent Documentation](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Install-CloudWatch-Agent.html)
- [CloudWatch Pricing](https://aws.amazon.com/cloudwatch/pricing/)
- [CloudWatch Logs Insights Query Syntax](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax.html)
