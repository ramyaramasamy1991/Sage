# Deploying Sage to AWS App Runner

App Runner runs our container directly from ECR, terminates TLS, autoscales, and
gives Bedrock access through an IAM **instance role** — so no AWS keys live in
the app. This is the lowest-effort production target for Sage.

## Prerequisites

- Docker, AWS CLI v2, and credentials with permission to use ECR + App Runner + IAM.
- Claude enabled in Bedrock → *Model access* in your target region.

## 1. Build & push the image to ECR

```bash
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=123456789012
./deploy/push-to-ecr.sh
# → pushes 123456789012.dkr.ecr.us-east-1.amazonaws.com/sage:latest
```

## 2. Create the IAM instance role (Bedrock access)

This role is assumed by the running task, so boto3 picks up Bedrock permissions
automatically — no `AWS_ACCESS_KEY_ID` in the container.

```bash
# Trust policy: App Runner tasks assume this role.
cat > /tmp/trust.json <<'EOF'
{ "Version": "2012-10-17", "Statement": [{
  "Effect": "Allow",
  "Principal": { "Service": "tasks.apprunner.amazonaws.com" },
  "Action": "sts:AssumeRole"
}]}
EOF

aws iam create-role --role-name SageBedrockRole \
  --assume-role-policy-document file:///tmp/trust.json

aws iam put-role-policy --role-name SageBedrockRole \
  --policy-name SageBedrock \
  --policy-document file://deploy/bedrock-iam-policy.json
```

## 3. Create the App Runner service

Use the console (simplest) or the CLI:

- **Source:** Container registry → the ECR image from step 1. Enable
  *automatic deployments* to redeploy on new pushes.
- **Port:** `8000`
- **Health check:** HTTP path `/api/health`
- **Instance role:** `SageBedrockRole` (from step 2)
- **Environment variables:**
  - `AWS_REGION` = your region
  - `BEDROCK_MODEL_ID` = e.g. `us.anthropic.claude-opus-4-8`
  - `KNOWLEDGE_BASE_ID` = your KB id (optional)
  - `API_KEY` = a strong secret (recommended — the service is public)
  - `REDIS_URL` = your Redis endpoint (optional; e.g. an ElastiCache URL)

> Store `API_KEY` (and any Redis auth) in **AWS Secrets Manager** and reference
> it from the service config rather than pasting plaintext.

App Runner returns an HTTPS URL when the service reaches *Running*. Open it and
Sage is live.

## Notes

- **Redis:** App Runner has no built-in Redis. For persistent/shared sessions,
  run ElastiCache (or skip it — in-memory works fine for a single instance).
  Note that with autoscaling > 1 instance, in-memory sessions won't be shared,
  so use Redis if you scale out.
- **Cost guardrails:** set `MAX_TOKENS` conservatively and prefer a Sonnet model
  id for high traffic.
- **Updates:** re-run `push-to-ecr.sh`; with auto-deploy on, App Runner rolls it
  out automatically.
