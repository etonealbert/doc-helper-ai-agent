# Dev Terraform Adoption

This stack adopts the existing Doc Helper AWS infrastructure. It is not a
greenfield deployment. Do not apply until the import plan contains imports only
and reports `0 to add, 0 to change, 0 to destroy`.

## Ownership Boundary

Terraform owns the ECR repository and lifecycle policy, ECS cluster and service
baseline, ECS security group, CloudWatch log group, DynamoDB table and TTL,
`DocHelperEcsTaskRole`, the application-specific IAM policies,
`GitHubActionsDeployRole`, and remote state infrastructure.

Application CD continues to own image builds, immutable Git SHA image tags, ECS
task-definition revisions, ECS deployments, public-IP discovery, the
`api.albertlukmanovlabs.lol` A record, and deployment health checks. For that
reason this stack does not define `aws_ecs_task_definition` or
`aws_route53_record`, and the ECS service ignores `task_definition` changes.

The existing default VPC and public subnets are inputs/data sources. This stack
does not add a VPC, private subnets, NAT Gateway, load balancer, API Gateway, or
certificate. Port 8000 remains public HTTP and must carry fake demo data only.

## Discover Live Configuration

Run these read-only commands before editing `terraform.tfvars` or planning. They
do not mutate AWS resources.

```powershell
$Cluster = "doc-helper-cluster"
$Service = "doc-helper-ai-task-service-ao2opdat"

# Current ECS network configuration, including subnet and security group IDs.
aws ecs describe-services `
  --cluster $Cluster `
  --services $Service `
  --query "services[0].networkConfiguration.awsvpcConfiguration"

# VPC ID for the first service subnet.
$SubnetId = aws ecs describe-services `
  --cluster $Cluster `
  --services $Service `
  --query "services[0].networkConfiguration.awsvpcConfiguration.subnets[0]" `
  --output text
aws ec2 describe-subnets --subnet-ids $SubnetId --query "Subnets[0].VpcId"

# All service subnet IDs.
aws ecs describe-services `
  --cluster $Cluster `
  --services $Service `
  --query "services[0].networkConfiguration.awsvpcConfiguration.subnets"

# Security group ID and complete ingress/egress rules.
$SecurityGroupId = aws ecs describe-services `
  --cluster $Cluster `
  --services $Service `
  --query "services[0].networkConfiguration.awsvpcConfiguration.securityGroups[0]" `
  --output text
aws ec2 describe-security-groups --group-ids $SecurityGroupId

# Current service task-definition ARN and full task definition.
$TaskDefinitionArn = aws ecs describe-services `
  --cluster $Cluster `
  --services $Service `
  --query "services[0].taskDefinition" `
  --output text
aws ecs describe-task-definition --task-definition $TaskDefinitionArn

# IAM trust, managed-policy attachments, and inline policy documents.
aws iam get-role --role-name DocHelperEcsTaskRole
aws iam list-attached-role-policies --role-name DocHelperEcsTaskRole
aws iam list-role-policies --role-name DocHelperEcsTaskRole
aws iam get-role --role-name GitHubActionsDeployRole
aws iam list-attached-role-policies --role-name GitHubActionsDeployRole
aws iam list-role-policies --role-name GitHubActionsDeployRole
aws iam get-role-policy --role-name DocHelperEcsTaskRole --policy-name DocHelperDynamoDBPutItem
aws iam get-role-policy --role-name GitHubActionsDeployRole --policy-name GitHubActionsPassEcsRoles

# DynamoDB schema, billing mode, and TTL status.
aws dynamodb describe-table --table-name doc-helper-records
aws dynamodb describe-time-to-live --table-name doc-helper-records

# CloudWatch log group and retention.
aws logs describe-log-groups --log-group-name-prefix /ecs/doc-helper-ai-task

# Public Route 53 hosted zone used only as a Terraform data source.
aws route53 list-hosted-zones-by-name --dns-name albertlukmanovlabs.lol

# ECR repository and lifecycle policy.
aws ecr describe-repositories --repository-names doc-helper-ai-agent
aws ecr get-lifecycle-policy --repository-name doc-helper-ai-agent
```

If either inline IAM policy has a different live name, update both its `name` in
`iam.tf` and its import ID in `imports.tf`. If a lifecycle policy or named inline
policy does not exist, this is not yet an imports-only adoption; stop and decide
whether a separately reviewed post-adoption addition is appropriate.

## Import IDs

| Terraform address | Import ID |
| --- | --- |
| `aws_ecr_repository.app` | `doc-helper-ai-agent` |
| `aws_ecr_lifecycle_policy.app` | `doc-helper-ai-agent` |
| `aws_dynamodb_table.crm_records` | `doc-helper-records` |
| `aws_cloudwatch_log_group.ecs` | `/ecs/doc-helper-ai-task` |
| `aws_ecs_cluster.app` | `doc-helper-cluster` |
| `aws_ecs_service.app` | `doc-helper-cluster/doc-helper-ai-task-service-ao2opdat` |
| `aws_security_group.ecs_service` | discovered `sg-...` value |
| `aws_iam_role.ecs_task` | `DocHelperEcsTaskRole` |
| `aws_iam_role_policy.ecs_task_dynamodb` | `DocHelperEcsTaskRole:DocHelperDynamoDBPutItem` |
| `aws_iam_role.github_deploy` | `GitHubActionsDeployRole` |
| `aws_iam_role_policy.github_pass_roles` | `GitHubActionsDeployRole:GitHubActionsPassEcsRoles` |

These IDs are encoded as declarative import blocks in `imports.tf`. No separate
`terraform import` command is required.

## Safe Execution Guide

### 1. Bootstrap remote state

The state bucket is a separate root stack because an S3 backend cannot use a
bucket before it exists. Confirm the globally unique bucket name, then run:

```powershell
terraform -chdir=infra/terraform/bootstrap init
terraform -chdir=infra/terraform/bootstrap fmt -check
terraform -chdir=infra/terraform/bootstrap validate
terraform -chdir=infra/terraform/bootstrap plan -out=bootstrap.tfplan
terraform -chdir=infra/terraform/bootstrap apply bootstrap.tfplan
```

The bucket has versioning, AES256 encryption, a full public-access block, and
`prevent_destroy`. Bootstrap is the only step expected to create infrastructure.

### 2. Prepare the dev inputs

Copy `terraform.tfvars.example` to uncommitted `terraform.tfvars` and replace the
example VPC, subnet, and security group IDs with discovery results. Compare every
resource argument, tag, IAM trust statement, and policy name with the live output.
The checked-in HCL must describe the live configuration exactly before adoption.

### 3. Initialize and plan imports

```powershell
terraform -chdir=infra/terraform/environments/dev init
terraform -chdir=infra/terraform/environments/dev fmt -check
terraform -chdir=infra/terraform/environments/dev validate
terraform -chdir=infra/terraform/environments/dev plan -out=tfplan
terraform -chdir=infra/terraform/environments/dev show tfplan
```

Proceed only when the plan reports all expected imports and exactly:

```text
0 to add, 0 to change, 0 to destroy
```

Do not apply a plan that replaces or modifies the ECS service, DynamoDB table,
ECR repository, IAM roles/policies, log group, or security group. Correct the HCL
to match live AWS and generate a new saved plan. Never use `-target` to hide drift.

### 4. Apply the reviewed import plan

```powershell
terraform -chdir=infra/terraform/environments/dev apply tfplan
terraform -chdir=infra/terraform/environments/dev plan -detailed-exitcode
```

The second command must exit `0` and report no changes. Exit `2` means drift is
present and must be investigated.

### 5. Complete adoption and verify health

After Terraform owns `/ecs/doc-helper-ai-task`, remove
`awslogs-create-group` from `.aws/ecs-task-definition.json` in a separate reviewed
application deployment. Then verify both the direct service and DNS health paths:

```powershell
Invoke-RestMethod http://api.albertlukmanovlabs.lol:8000/health
```

The application deployment workflow remains responsible for resolving the newest
task public IP, testing `/health`, and updating Route 53 after task replacement.

## Automation

`.github/workflows/terraform.yml` performs formatting and backend-free validation
when Terraform files change. It never applies. A future manual apply job must use
GitHub OIDC, save the reviewed plan, and target a protected GitHub Environment
with required approval. Do not add Terraform apply steps to `deploy.yml`.
