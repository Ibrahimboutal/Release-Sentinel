# Deployment Guide

Release Sentinel can be deployed locally for development or to production cloud environments. This guide covers both scenarios.

## Table of Contents

1. [Local Development](#local-development)
2. [Docker Deployment](#docker-deployment)
3. [Cloud Deployment](#cloud-deployment)
4. [Environment Configuration](#environment-configuration)
5. [Monitoring and Health Checks](#monitoring-and-health-checks)
6. [Troubleshooting](#troubleshooting)

---

## Local Development

### Prerequisites

- Python 3.11 or higher
- pip package manager

### Installation

```bash
git clone https://github.com/Ibrahimboutal/Release-Sentinel.git
cd Release-Sentinel
python -m pip install -e ".[dev]"
```

### Running the Application

#### CLI Mode (for testing scenarios)

```bash
# Run with default "happy" scenario
python -m releasesentinel run --scenario happy --pretty

# Run with specific scenario
python -m releasesentinel run --scenario failing --pretty

# Run with custom manifest
python -m releasesentinel run --manifest data/fixtures/low_risk_manifest.json --pretty
```

#### Web Server Mode (interactive dashboard)

```bash
# Start the web server
python -m releasesentinel serve --port 8000

# Open browser to http://127.0.0.1:8000/dashboard
```

#### Tests

```bash
export PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
python -m pytest -v
```

---

## Docker Deployment

### Quick Start with Docker Compose

```bash
# Build and start the service
docker-compose up --build

# Access the dashboard at http://localhost:8000/dashboard
```

### Manual Docker Build and Run

```bash
# Build the image
docker build -t release-sentinel:latest .

# Run the container
docker run -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/artifacts:/app/artifacts \
  release-sentinel:latest
```

### Docker with UiPath Cloud Integration

```bash
docker run -p 8000:8000 \
  -e RELEASE_SENTINEL_RUNNER=uipath \
  -e RELEASE_SENTINEL_ORCHESTRATOR_URL=$ORCHESTRATOR_URL \
  -e RELEASE_SENTINEL_ORCHESTRATOR_TOKEN=$ORCHESTRATOR_TOKEN \
  -e RELEASE_SENTINEL_TEST_MANAGER_FOLDER_KEY=$FOLDER_KEY \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/artifacts:/app/artifacts \
  release-sentinel:latest
```

---

## Cloud Deployment

### Kubernetes Deployment

Example deployment manifest (`k8s-deployment.yaml`):

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: release-sentinel
  labels:
    app: release-sentinel
spec:
  replicas: 2
  selector:
    matchLabels:
      app: release-sentinel
  template:
    metadata:
      labels:
        app: release-sentinel
    spec:
      containers:
      - name: release-sentinel
        image: your-registry/release-sentinel:latest
        ports:
        - containerPort: 8000
        env:
        - name: RELEASE_SENTINEL_RUNNER
          value: "local"
        - name: RELEASE_SENTINEL_FLAKINESS_THRESHOLD
          value: "0.35"
        livenessProbe:
          httpGet:
            path: /docs
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /docs
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        volumeMounts:
        - name: data
          mountPath: /app/data
        - name: artifacts
          mountPath: /app/artifacts
      volumes:
      - name: data
        emptyDir: {}
      - name: artifacts
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: release-sentinel-service
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8000
    protocol: TCP
  selector:
    app: release-sentinel
```

Deploy with:

```bash
kubectl apply -f k8s-deployment.yaml
kubectl port-forward svc/release-sentinel-service 8000:80
```

### AWS Deployment (ECS/Fargate)

Create `ecs-task-definition.json`:

```json
{
  "family": "release-sentinel",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "containerDefinitions": [
    {
      "name": "release-sentinel",
      "image": "your-aws-account-id.dkr.ecr.region.amazonaws.com/release-sentinel:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "hostPort": 8000,
          "protocol": "tcp"
        }
      ],
      "essential": true,
      "environment": [
        {
          "name": "RELEASE_SENTINEL_RUNNER",
          "value": "local"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/release-sentinel",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/docs || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 10
      }
    }
  ]
}
```

Register and run:

```bash
aws ecs register-task-definition --cli-input-json file://ecs-task-definition.json
aws ecs run-task --cluster your-cluster --task-definition release-sentinel
```

### Google Cloud Run

```bash
# Build and push to Google Cloud Registry
gcloud builds submit --tag gcr.io/$PROJECT_ID/release-sentinel

# Deploy to Cloud Run
gcloud run deploy release-sentinel \
  --image gcr.io/$PROJECT_ID/release-sentinel \
  --platform managed \
  --region us-central1 \
  --port 8000 \
  --memory 512Mi \
  --set-env-vars RELEASE_SENTINEL_RUNNER=local
```

---

## Environment Configuration

### Required Variables

None - Release Sentinel works with defaults out of the box.

### Optional Variables

#### Local Development

```bash
# Choose runner mode
export RELEASE_SENTINEL_RUNNER='local'  # or 'uipath'

# Flakiness threshold (0.0-1.0)
export RELEASE_SENTINEL_FLAKINESS_THRESHOLD='0.35'

# Test Manager folder filter
export RELEASE_SENTINEL_TEST_MANAGER_FOLDER_KEY='<uuid>'
```

#### UiPath Cloud Integration

```bash
# Orchestrator connection
export RELEASE_SENTINEL_ORCHESTRATOR_URL='https://cloud.uipath.com/org/tenant/orchestrator_'
export RELEASE_SENTINEL_ORCHESTRATOR_TOKEN='<bearer-token>'

# Action Center task catalog
export RELEASE_SENTINEL_TASK_CATALOG='ReleaseGateReviews'

# Test Manager project
export RELEASE_SENTINEL_TEST_MANAGER_PROJECT_KEY='REL_SENTINEL'
```

#### Advanced Options

```bash
# Custom manifest path
export RELEASE_SENTINEL_MANIFEST_PATH='data/change_manifest.json'

# Custom verdict output path
export RELEASE_SENTINEL_VERDICT_PATH='artifacts/release_verdict.json'

# Risk score thresholds
export RELEASE_SENTINEL_RISK_SMOKE_THRESHOLD='25'
export RELEASE_SENTINEL_RISK_TARGETED_THRESHOLD='50'
export RELEASE_SENTINEL_RISK_CRITICAL_THRESHOLD='75'
```

---

## Monitoring and Health Checks

### Health Endpoints

```bash
# Basic health check
curl http://localhost:8000/docs

# Latest verdict
curl http://localhost:8000/api/latest-verdict

# Run history
curl http://localhost:8000/api/run-history?limit=10
```

### Metrics Collection

The API endpoints can be monitored with standard tools:

- **Prometheus**: Export metrics via FastAPI middleware
- **DataDog**: Monitor HTTP latency and error rates
- **CloudWatch**: Log events via container logs

### Log Aggregation

Logs are output to stdout. Capture with your logging infrastructure:

```bash
# Docker logs
docker logs -f <container-id>

# Kubernetes logs
kubectl logs -f deployment/release-sentinel

# CloudWatch logs (configured in ECS task definition)
aws logs tail /ecs/release-sentinel --follow
```

---

## Troubleshooting

### Container won't start

**Problem**: `ModuleNotFoundError: No module named 'releasesentinel'`

**Solution**: Ensure `pyproject.toml` is copied before running pip install:

```bash
docker build --build-arg BUILDKIT_INLINE_CACHE=1 -t release-sentinel:latest .
```

### Port already in use

**Problem**: `Address already in use`

**Solution**: Use a different port:

```bash
docker run -p 9000:8000 release-sentinel:latest
# Then access at http://localhost:9000
```

Or stop the existing process:

```bash
lsof -i :8000
kill -9 <PID>
```

### UiPath integration fails

**Problem**: `Orchestrator authentication failed` or `Test Manager unavailable`

**Steps**:

1. Verify credentials:
   ```bash
   uip login status
   ```

2. Check folder key:
   ```bash
   uip tm testsets list --project-key REL_SENTINEL
   ```

3. Verify network connectivity to UiPath cloud

4. Check token expiration:
   ```bash
   uip refresh
   ```

### Tests fail in CI

**Problem**: Tests pass locally but fail in GitHub Actions

**Steps**:

1. Check Python version in CI matches local
2. Ensure `PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'` is set
3. Run the same command locally as in CI:
   ```bash
   PYTEST_DISABLE_PLUGIN_AUTOLOAD='1' python -m pytest -v
   ```

### Dashboard won't load

**Problem**: Blank screen or "Cannot GET /"

**Steps**:

1. Check server is running:
   ```bash
   curl http://localhost:8000/
   ```

2. Check browser console for JavaScript errors

3. Verify web assets are present:
   ```bash
   ls -la web/templates/ web/static/
   ```

4. Try with explicit paths:
   ```bash
   curl http://localhost:8000/dashboard
   ```

### High memory usage

**Problem**: Container using too much memory

**Solution**: Set resource limits:

```bash
docker run -m 512m --memswap 512m release-sentinel:latest
```

Or in docker-compose.yml:

```yaml
services:
  release-sentinel:
    # ... other config
    mem_limit: 512m
    memswap_limit: 512m
```

---

## Performance Tuning

### Optimize for High-Volume Runs

```bash
# Run with custom worker count (if using gunicorn)
gunicorn releasesentinel.api:app --workers 4 --worker-class uvicorn.workers.UvicornWorker
```

### Scale with Kubernetes

```bash
# Increase replicas
kubectl scale deployment release-sentinel --replicas=3

# Use horizontal pod autoscaler
kubectl autoscale deployment release-sentinel --min=1 --max=5 --cpu-percent=80
```

---

## Security Considerations

### Secrets Management

Never commit secrets. Use environment variables or secret managers:

```bash
# GitHub Actions
echo "ORCHESTRATOR_TOKEN=${{ secrets.ORCHESTRATOR_TOKEN }}" >> .env

# Kubernetes Secrets
kubectl create secret generic release-sentinel-secrets \
  --from-literal=orchestrator-token=$ORCHESTRATOR_TOKEN

# AWS Secrets Manager
aws secretsmanager create-secret --name release-sentinel/orchestrator-token \
  --secret-string $ORCHESTRATOR_TOKEN
```

### Network Security

- Always use HTTPS in production
- Restrict access to dashboards with authentication middleware
- Use network policies to limit inter-service communication

### Container Security

- Run with read-only root filesystem:
  ```bash
  docker run --read-only release-sentinel:latest
  ```

- Drop unnecessary capabilities:
  ```bash
  docker run --cap-drop=ALL --cap-add=NET_BIND_SERVICE release-sentinel:latest
  ```

---

## Support

For issues or questions:

- GitHub Issues: https://github.com/Ibrahimboutal/Release-Sentinel/issues
- Documentation: https://github.com/Ibrahimboutal/Release-Sentinel/tree/main/docs
