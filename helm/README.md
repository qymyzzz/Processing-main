# Ticket Bot Helm Chart

A production-ready Helm chart for deploying the Ticket Management Bot on Kubernetes.

## Overview

This chart deploys the Telegram ticket management bot with:
- Kubernetes Deployment with configurable replicas
- Service exposure for bot and health check ports
- Secrets management for sensitive credentials
- ConfigMap for environment variables
- Horizontal Pod Autoscaling (HPA)
- Persistent volume support
- Network policies
- Pod disruption budgets
- Health checks (liveness and readiness probes)
- Security best practices

## Prerequisites

- Kubernetes 1.19+
- Helm 3.0+
- Docker image of the ticket bot available in your registry

## Installation

### 1. Build and Push Docker Image

```bash
# From project root
docker build -t your-registry/ticket-bot:1.0.0 .
docker push your-registry/ticket-bot:1.0.0
```

### 2. Create values file

```bash
cp helm/values.yaml helm/values-production.yaml
```

Edit `helm/values-production.yaml`:

```yaml
image:
  repository: your-registry/ticket-bot
  tag: "1.0.0"

secrets:
  TELEGRAM_BOT_TOKEN: "your-token"
  GEMINI_API_KEY: "your-key"
  AWS_ACCESS_KEY_ID: "your-id"
  AWS_SECRET_ACCESS_KEY: "your-secret"
  AWS_REGION: "us-east-1"
  S3_BUCKET: "your-bucket"

resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

### 3. Install the chart

```bash
# Dry run first
helm install ticket-bot ./helm -f helm/values-production.yaml --dry-run --debug

# Install
helm install ticket-bot ./helm -f helm/values-production.yaml --namespace default

# Or upgrade if already installed
helm upgrade ticket-bot ./helm -f helm/values-production.yaml
```

## Configuration

### Key Values

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of replicas | `1` |
| `image.repository` | Image repository | `ticket-bot` |
| `image.tag` | Image tag | `latest` |
| `service.port` | Bot service port | `8080` |
| `service.healthCheckPort` | Health check port | `8443` |
| `resources.requests.memory` | Memory request | `256Mi` |
| `resources.limits.memory` | Memory limit | `512Mi` |
| `resources.requests.cpu` | CPU request | `250m` |
| `resources.limits.cpu` | CPU limit | `500m` |
| `autoscaling.enabled` | Enable HPA | `false` |
| `autoscaling.minReplicas` | HPA min replicas | `1` |
| `autoscaling.maxReplicas` | HPA max replicas | `3` |
| `persistence.enabled` | Enable persistent storage | `false` |

### Environment Variables

```yaml
env:
  LOG_LEVEL: "INFO"
  HEALTH_CHECK_PORT: "8443"
```

### Secrets

Configure these sensitive values via `values.yaml` or use external secret management:

```yaml
secrets:
  TELEGRAM_BOT_TOKEN: ""
  GEMINI_API_KEY: ""
  AWS_ACCESS_KEY_ID: ""
  AWS_SECRET_ACCESS_KEY: ""
  AWS_REGION: "us-east-1"
  S3_BUCKET: ""
```

## Using External Secrets

For production, use a secret management solution:

### With Sealed Secrets

```bash
# Install sealed-secrets controller
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.18.0/controller.yaml

# Create and seal secret
kubectl create secret generic ticket-bot-secrets \
  --from-literal=TELEGRAM_BOT_TOKEN=xxx \
  --from-literal=GEMINI_API_KEY=xxx \
  -o yaml | kubeseal -f - > sealed-secret.yaml

kubectl apply -f sealed-secret.yaml
```

### With External Secrets Operator

```bash
# Install external-secrets
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets -n external-secrets-system --create-namespace

# Create SecretStore and ExternalSecret resources
```

## Advanced Configuration

### Enable Autoscaling

```yaml
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 5
  targetCPUUtilizationPercentage: 70
```

### Enable Persistent Storage

```yaml
persistence:
  enabled: true
  storageClassName: standard
  size: 5Gi
  mountPath: /data
```

### Enable Network Policies

```yaml
networkPolicy:
  enabled: true
```

### Enable Pod Disruption Budget

```yaml
podDisruptionBudget:
  enabled: true
  minAvailable: 1
```

## Monitoring & Health Checks

The chart includes:
- **Liveness Probe**: Checks pod health every 30 seconds (initial delay: 30s)
- **Readiness Probe**: Checks pod readiness every 10 seconds (initial delay: 10s)
- **Health Endpoint**: `/health` on port 8443

## Deployment Examples

### Development Environment

```bash
helm install ticket-bot ./helm \
  --set replicaCount=1 \
  --set resources.requests.memory=128Mi \
  --set resources.limits.memory=256Mi
```

### Production with High Availability

```bash
helm install ticket-bot ./helm -f helm/values-production.yaml \
  --set replicaCount=3 \
  --set autoscaling.enabled=true \
  --set autoscaling.minReplicas=3 \
  --set autoscaling.maxReplicas=10 \
  --set podDisruptionBudget.enabled=true \
  --set networkPolicy.enabled=true
```

### With Persistent Storage

```bash
helm install ticket-bot ./helm -f helm/values-production.yaml \
  --set persistence.enabled=true \
  --set persistence.storageClassName=fast-ssd \
  --set persistence.size=10Gi
```

## Verification

```bash
# Check deployment
kubectl get deployment,pods,svc

# Check logs
kubectl logs -l app.kubernetes.io/name=ticket-bot -f

# Port forward to test locally
kubectl port-forward svc/ticket-bot 8080:8080

# Test health endpoint
curl http://localhost:8443/health
```

## Upgrading

```bash
# Update values
helm upgrade ticket-bot ./helm -f helm/values-production.yaml

# Rollback if needed
helm rollback ticket-bot 1
```

## Uninstalling

```bash
helm uninstall ticket-bot
```

## Troubleshooting

### Pod not starting

```bash
kubectl describe pod -l app.kubernetes.io/name=ticket-bot
kubectl logs -l app.kubernetes.io/name=ticket-bot --all-containers=true
```

### ImagePullBackOff

Ensure image repository is accessible and image tag is correct:
```bash
helm get values ticket-bot
```

### Secrets not loading

```bash
# Check secret exists
kubectl get secrets

# Verify secret data
kubectl get secret ticket-bot -o jsonpath='{.data}' | base64 -d
```

### Health check failures

```bash
# Check health endpoint
kubectl exec -it <pod-name> -- curl localhost:8443/health

# Check application logs
kubectl logs <pod-name>
```

## Best Practices

1. **Always use specific image tags** - Never use `latest` in production
2. **Set resource requests and limits** - Helps scheduler and prevents resource exhaustion
3. **Use security contexts** - Run as non-root user (enabled by default)
4. **Enable health checks** - Catches unhealthy pods early
5. **Use Network Policies** - Restrict traffic in production environments
6. **Backup secrets** - Use encrypted secret management solutions
7. **Monitor resources** - Use tools like Prometheus to track usage
8. **Plan for scaling** - Enable HPA based on observed load

## Support

For issues or questions, refer to:
- [Helm Documentation](https://helm.sh/docs/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Project Repository](https://github.com/qymyzzz/Processing-main)
