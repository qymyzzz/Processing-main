# Docker Deployment Guide

This guide explains how to build and run the Ticket Management Bot using Docker.

## Prerequisites

- Docker 20.10+
- Docker Compose 1.29+ (for compose commands)

## Quick Start

### 1. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your credentials
# Required variables:
# - TELEGRAM_BOT_TOKEN
# - GEMINI_API_KEY
# - AWS_ACCESS_KEY_ID
# - AWS_SECRET_ACCESS_KEY
# - S3_BUCKET
```

### 2. Build Docker Image

```bash
# Build locally
docker build -t ticket-bot:1.0.0 .

# Or with docker-compose
docker-compose build
```

### 3. Run the Container

#### Using Docker Compose (Recommended)

```bash
# Start in foreground (to see logs)
docker-compose up

# Start in background
docker-compose up -d

# Stop
docker-compose down

# View logs
docker-compose logs -f

# Rebuild and restart
docker-compose up --build
```

#### Using Docker CLI

```bash
# Run with environment file
docker run --env-file .env \
  -p 8080:8080 \
  -p 8443:8443 \
  --name ticket-bot \
  ticket-bot:1.0.0

# Stop
docker stop ticket-bot

# Start stopped container
docker start ticket-bot

# Remove
docker rm ticket-bot
```

## Development

### Hot Reloading with Volume Mount

For development with hot reloading:

```bash
docker run --env-file .env \
  -v $(pwd):/app \
  -p 8080:8080 \
  -p 8443:8443 \
  --name ticket-bot \
  ticket-bot:1.0.0
```

Or with docker-compose override:

```bash
# Use docker-compose with override for development
docker-compose -f docker-compose.yml -f docker-compose.override.yml up

# The override file allows local development customizations
# without changing the main compose file
```

### Interactive Mode

```bash
# Run with bash shell for debugging
docker run -it --env-file .env \
  -p 8080:8080 \
  -p 8443:8443 \
  ticket-bot:1.0.0 \
  /bin/bash
```

## Docker Image Details

### Base Image
- `python:3.13.7-slim` - Lightweight Python image

### Security Features
- **Non-root user**: Runs as `botuser` (UID 1000)
- **Multi-stage build**: Smaller final image
- **Read-only filesystem**: Applied at runtime if needed
- **Health checks**: Automatic restart on failures

### Exposed Ports
- `8080`: Bot API port
- `8443`: Health check port

### Health Check

The container includes a health check that:
- Checks every 30 seconds
- Timeout: 10 seconds
- Start period: 40 seconds (allows startup time)
- Retries: 3 times before marking unhealthy

Check health status:
```bash
docker ps --filter "name=ticket-bot"
# Status should show "Up X seconds (healthy)"
```

## Production Deployment

### Image Tagging and Registry

```bash
# Build with version tag
docker build -t ticket-bot:1.0.0 .

# Tag for registry
docker tag ticket-bot:1.0.0 your-registry.com/ticket-bot:1.0.0

# Push to registry
docker push your-registry.com/ticket-bot:1.0.0
```

### Running in Production

```bash
# Use docker-compose with production override
docker-compose -f docker-compose.yml \
  up -d

# Or with explicit configuration
docker run -d \
  --name ticket-bot \
  --restart unless-stopped \
  --env-file .env.production \
  -p 8080:8080 \
  -p 8443:8443 \
  -v bot-data:/app/data \
  --log-driver json-file \
  --log-opt max-size=10m \
  --log-opt max-file=3 \
  ticket-bot:1.0.0
```

### Environment Variables

Essential variables for production:

```env
TELEGRAM_BOT_TOKEN=xxx
GEMINI_API_KEY=xxx
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
AWS_REGION=us-east-1
S3_BUCKET=xxx
LOG_LEVEL=INFO
```

## Monitoring

### View Logs

```bash
# Current logs
docker logs ticket-bot

# Follow logs (tail -f)
docker logs -f ticket-bot

# Last 50 lines
docker logs --tail 50 ticket-bot

# With timestamps
docker logs -t ticket-bot
```

### Container Status

```bash
# Full status
docker ps -a --filter "name=ticket-bot"

# Inspect container details
docker inspect ticket-bot

# Resource usage
docker stats ticket-bot
```

### Health Check

```bash
# Check if health endpoint responds
docker exec ticket-bot curl -f http://localhost:8443/health

# Or from outside
curl -f http://localhost:8443/health
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs ticket-bot

# Inspect the image
docker inspect ticket-bot:1.0.0

# Run with debugging
docker run -it ticket-bot:1.0.0 /bin/bash
```

### Environment Variables Not Set

```bash
# Verify env file exists
cat .env

# Check what's passed to container
docker inspect ticket-bot | grep -A 20 "Env"

# Run with explicit env vars
docker run --env TELEGRAM_BOT_TOKEN=xxx ticket-bot:1.0.0
```

### Port Already in Use

```bash
# Find what's using port 8080
lsof -i :8080

# Use different port
docker run -p 8090:8080 ticket-bot:1.0.0

# Or stop conflicting container
docker stop <container-name>
```

### Health Check Failing

```bash
# Check if endpoint is working
docker exec ticket-bot curl -v http://localhost:8443/health

# Check application logs
docker logs ticket-bot

# Check if port is open inside container
docker exec ticket-bot netstat -tlnp
```

## Maintenance

### Update Image

```bash
# Pull latest source
git pull

# Rebuild image
docker build -t ticket-bot:1.0.1 .

# Stop old container
docker-compose down

# Start new version
docker-compose up -d
```

### Cleanup

```bash
# Remove stopped containers
docker container prune

# Remove unused images
docker image prune

# Remove unused volumes
docker volume prune

# Clean everything (caution!)
docker system prune -a
```

### Backup Data

```bash
# Backup volume data
docker run --rm \
  -v bot-data:/data \
  -v $(pwd):/backup \
  ubuntu tar cvf /backup/bot-data.tar /data

# Restore from backup
docker run --rm \
  -v bot-data:/data \
  -v $(pwd):/backup \
  ubuntu tar xvf /backup/bot-data.tar -C /
```

## Docker Compose Commands

```bash
# Start services
docker-compose up

# Start in background
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs

# Follow logs
docker-compose logs -f

# Rebuild images
docker-compose build

# Remove containers and volumes
docker-compose down -v

# Execute command in running container
docker-compose exec ticket-bot curl http://localhost:8443/health

# Scale service (if configured)
docker-compose up -d --scale ticket-bot=3
```

## Best Practices

1. **Always use .env file**: Don't pass secrets as command-line arguments
2. **Use specific image tags**: Never use `latest` in production
3. **Configure resource limits**: Set memory and CPU limits
4. **Enable health checks**: Let Docker manage container lifecycle
5. **Use named volumes**: For persistent data
6. **Configure logging**: Prevent disk space issues
7. **Security**: Run as non-root user (default in this Dockerfile)
8. **Network isolation**: Use networks instead of linking
9. **Use compose for multi-container**: Better organization
10. **Monitor regularly**: Check logs and resource usage

## References

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Python Docker Best Practices](https://docs.docker.com/language/python/)
