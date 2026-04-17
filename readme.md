# Data Engineering Assessment — Sai Shirish Katady

## Overview

This project is a serverless data pipeline built on AWS. The idea is simple — whenever a new CSV file with order data gets uploaded to an S3 bucket, it automatically triggers a Lambda function that processes the data and writes analytics reports to a separate output S3 bucket.

Everything is provisioned using Terraform and the Lambda runs inside a Docker container.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          AWS Account                                │
│                                                                     │
│   ┌─────────────┐    S3 Event     ┌──────────────────────────────┐  │
│   │  S3 Input   │ ─────────────► │     Lambda Function          │  │
│   │   Bucket    │                │     (Docker Container)        │  │
│   │             │                │                               │  │
│   │ orders.csv  │                │  1. Read CSV from S3          │  │
│   └─────────────┘                │  2. Calculate profit          │  │
│                                  │  3. Generate analytics reports │  │
│   ┌─────────────┐                │  4. Write CSVs to output      │  │
│   │  ECR Repo   │ ── image ────► │                               │  │
│   │             │                └──────────────┬───────────────┘  │
│   └─────────────┘                               │                  │
│                                                 ▼                  │
│                                  ┌──────────────────────────────┐  │
│                                  │       S3 Output Bucket       │  │
│                                  │                              │  │
│                                  │  analytics/                  │  │
│                                  │  ├── most_profitable_        │  │
│                                  │  │   region.csv              │  │
│                                  │  ├── most_common_ship_       │  │
│                                  │  │   method.csv              │  │
│                                  │  └── orders_by_category.csv  │  │
│                                  └──────────────────────────────┘  │
│                                                                     │
│  Provisioned with Terraform  │  IAM Least Privilege Enforced       │
└─────────────────────────────────────────────────────────────────────┘
```

This architecture follows an event-driven serverless design where S3 triggers a containerized Lambda function to process order data and generate analytics reports.

- **S3 Input Bucket** — where you drop the raw order CSV files
- **Lambda Function** — reads the file, runs the analytics, writes the results
- **S3 Output Bucket** — where the 3 analytics reports land as CSV files
- **ECR** — stores the Docker image for the Lambda function

---

## Analytics Reports

The Lambda function generates 3 reports on every run:

### 1. Most Profitable Region (`analytics/most_profitable_region.csv`)
Finds which region generated the most total profit across all orders.

Profit is calculated as:
```
Profit = (List Price - cost price) * Quantity * (1 - Discount Percent / 100)
```

### 2. Most Common Shipping Method per Category (`analytics/most_common_ship_method.csv`)
For each product category, finds which shipping method was used most often.

### 3. Orders by Category and Sub-Category (`analytics/orders_by_category.csv`)
Counts how many orders exist for every category and sub-category combination.

---

## Output Partitioning

All 3 output files are written to the `analytics/` prefix in the output S3 bucket. The files are not date-partitioned since each run processes a single uploaded file and overwrites the previous results. If the pipeline were extended to run on historical data or scheduled runs, partitioning by date (e.g. `analytics/year=2024/month=01/`) would make sense.

---

## Project Structure

```
.
├── app/
│   ├── lambda.py              # Lambda handler — reads S3, runs analytics, writes output
│   ├── orders_analytics.py    # Analytics logic — profit, shipping, category counts
│   └── requirements.txt       # Python dependencies
├── terraform/
│   └── assignment/
│       ├── main.tf            # S3 buckets, Lambda, IAM policy, S3 trigger
│       ├── aws.tf             # AWS provider and S3 backend config
│       ├── variables.tf       # Variable definitions
│       ├── locals.tf          # Local values (app name, tags)
│       └── vars.tfvars        # Your actual variable values
│   └── modules/
│       ├── lambda/            # Reusable Lambda module
│       └── ecr-repo/          # Reusable ECR module
├── Dockerfile                 # Docker image definition for Lambda
├── sample_orders.csv          # Sample data for testing
└── readme.md
```

---

## Prerequisites

- AWS CLI installed and configured
- Terraform installed (v1.0+)
- Docker installed and running

---

## Deployment Steps

### Step 1 — Configure AWS credentials

```bash
aws configure --profile nmd-assessment
```

Enter your access key, secret key, region (`us-west-2`), and output format (`json`).

### Step 2 — Update vars file

Open `terraform/assignment/vars.tfvars` and set:

```hcl
candidate_name = "your_aws_username"
aws_profile    = "nmd-assessment"
```

### Step 3 — Initialize Terraform

```bash
cd terraform/assignment
terraform init -backend-config="key=nmd-assignment-<your-name>.tfstate"
```

### Step 4 — Deploy ECR repo first

```bash
terraform apply -var-file="vars.tfvars" -target=module.ecr_repo
```

### Step 5 — Build and push Docker image

```bash
# Set your values
LOCAL_IMAGE_NAME="nmd-lambda"
AWS_ACCOUNT_ID="<your-account-id>"
REGION="us-west-2"
ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/nmd-assignment-sai_shirish-ecr"

# Build
docker build --platform linux/arm64 --no-cache --provenance=false -t "$LOCAL_IMAGE_NAME" .

# Login to ECR
aws ecr get-login-password --profile nmd-assessment | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"

# Tag and push
docker tag "$LOCAL_IMAGE_NAME" "$ECR_URI:latest"
docker push "$ECR_URI:latest"
```

### Step 6 — Deploy everything

```bash
terraform apply -var-file="vars.tfvars"
```

### Step 7 — Force update Lambda if you pushed a new image

```bash
aws lambda update-function-code \
  --function-name "nmd-assignment-sai_shirish-file-processor" \
  --image-uri "$ECR_URI:latest" \
  --profile nmd-assessment
```

---

## Testing

### Upload the sample file

```bash
aws s3 cp sample_orders.csv s3://nmd-assignment-sai-shirish-input-bucket/ --profile nmd-assessment
```

### Check the output bucket for results

```bash
aws s3 ls s3://nmd-assignment-sai-shirish-output-bucket/ --recursive --profile nmd-assessment
```

You should see:
```
analytics/most_profitable_region.csv
analytics/most_common_ship_method.csv
analytics/orders_by_category.csv
```

### Download and view results

```bash
aws s3 cp s3://nmd-assignment-sai-shirish-output-bucket/analytics/most_profitable_region.csv . --profile nmd-assessment
aws s3 cp s3://nmd-assignment-sai-shirish-output-bucket/analytics/most_common_ship_method.csv . --profile nmd-assessment
aws s3 cp s3://nmd-assignment-sai-shirish-output-bucket/analytics/orders_by_category.csv . --profile nmd-assessment
```

### Check Lambda logs if something goes wrong

```bash
aws logs tail /aws/lambda/nmd-assignment-sai-shirish-file-processor --follow --profile nmd-assessment
```

---

## IAM — Least Privilege

The Lambda function's IAM role is given only the permissions it actually needs:

- `s3:GetObject` on the input bucket — so it can read the uploaded CSV
- `s3:PutObject` on the output bucket — so it can write the analytics reports

It cannot list buckets, delete files, or access any other AWS service. This follows the principle of least privilege.

---

## Assumptions

- Each Lambda invocation processes a single uploaded CSV file
- Input data schema is consistent with the provided sample
- Outputs overwrite previous results on each run

---

## Improvements

- Add partitioned output (e.g., by date) for scalability
- Add retry logic for failed S3 reads
- Add monitoring using CloudWatch metrics and alerts

---

## Notes

- Do not commit AWS credentials to the repo
- The `vars.tfvars` file contains your profile name but no secrets — it is safe to commit
- If you push a new Docker image, you must force-update the Lambda function using the command in Step 7
