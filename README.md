# Azure SRE Agent - Kubernetes Load Testing

This repository contains tools for simulating errors and load testing in Azure Kubernetes Service (AKS) clusters.

## Projects

### 1. Nginx Web Server
- Simple nginx deployment with LoadBalancer service
- Configured for high CPU load testing
- File: `nginx-deployment.yaml`

### 2. Memory Leak Test Application
- Python application with configurable memory leak behavior
- Designed for testing Kubernetes resource limits and autoscaling
- Files: `memory-leak-app.py`, `Dockerfile`, `memory-leak-deployment.yaml`

## Memory Leak Test Application

A containerized Python application designed for testing Kubernetes resource limits, monitoring, and autoscaling behavior in Azure Kubernetes Service (AKS).

### Features

- **Configurable Memory Leak**: Enable/disable memory leak behavior via environment variables
- **HTTP Health Endpoints**: Liveness, readiness, and metrics endpoints for Kubernetes integration
- **Security Hardened**: Runs as non-root user with minimal privileges
- **Azure Optimized**: Designed for Azure Container Registry (ACR) and AKS
- **Resource Monitoring**: Built-in memory usage tracking and reporting
- **Graceful Shutdown**: Proper signal handling and resource cleanup

### Application Endpoints

| Endpoint | Purpose | Description |
|----------|---------|-------------|
| `/health` | Liveness Probe | Returns application health status |
| `/ready` | Readiness Probe | Returns readiness status |
| `/metrics` | Monitoring | Returns detailed memory usage metrics |
| `/cleanup` | Maintenance | Manually trigger memory cleanup |
| `/` | Information | Application info and configuration |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LEAK` | `FALSE` | Enable memory leak when set to `TRUE` |
| `LEAK_RATE` | `1` | Memory allocation rate in MB per second (1-100) |
| `LEAK_INTERVAL` | `1` | Interval between allocations in seconds (0.1-10) |
| `MAX_MEMORY` | `500` | Maximum memory to allocate in MB (10-2048) |
| `PORT` | `8080` | HTTP server port |

### Quick Start

#### Prerequisites

- Docker
- kubectl (configured for your AKS cluster)
- Azure CLI
- Azure Container Registry (ACR)

#### 1. Set Environment Variables

```bash
export ACR_NAME="your-acr-name"
export RESOURCE_GROUP="your-resource-group"
```

#### 2. Build and Deploy

```bash
# Build, push, and deploy the application
./deploy.sh deploy
```

#### 3. Monitor the Application

```bash
# Check application status
./deploy.sh status

# Monitor resource usage
kubectl top pods -l app=memory-leak-app

# Check application logs
kubectl logs -l app=memory-leak-app -f
```

### Usage Examples

#### Enable Memory Leak for Testing

```bash
# Enable memory leak behavior
./deploy.sh enable-leak

# Monitor memory consumption
watch kubectl top pods -l app=memory-leak-app
```

#### Manual Testing with curl

```bash
# Get service IP
SERVICE_IP=$(kubectl get svc memory-leak-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Check health
curl http://$SERVICE_IP/health

# Monitor metrics
curl http://$SERVICE_IP/metrics

# Trigger manual cleanup
curl http://$SERVICE_IP/cleanup
```

### Testing Scenarios

#### 1. Resource Limit Testing

1. Deploy with low memory limits
2. Enable memory leak
3. Watch pod get OOMKilled
4. Observe Kubernetes restart behavior

#### 2. Horizontal Pod Autoscaler Testing

1. Deploy with HPA configured
2. Enable memory leak
3. Watch HPA scale up pods
4. Disable leak and watch scale down

#### 3. Memory Pressure Testing

1. Deploy multiple replicas
2. Enable memory leak on all pods
3. Monitor node memory pressure
4. Test pod eviction behavior

## Integration with Azure Tools

- **Azure LoadTest**: Use for generating HTTP load against the nginx deployment
- **Azure Chaos Studio**: Integrate with the memory leak app for controlled failure testing
- **Azure Monitor**: Collect metrics from both applications for SRE analysis
- **Azure Application Insights**: Monitor application performance and errors

## File Structure

```
.
├── memory-leak-app.py           # Main Python application
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Container image definition
├── memory-leak-deployment.yaml  # Kubernetes manifests for memory leak app
├── deploy.sh                    # Build and deployment script
├── nginx-deployment.yaml        # Nginx web server manifest
└── README.md                    # This documentation
```

Get SRE-agent to push issue to github

Get Github copilot to fix problem.

Build app to use Azure Postgre database



