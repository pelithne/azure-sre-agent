#!/bin/bash
# Build and Deploy Script for Memory Leak Test Application
# Optimized for Azure Container Registry (ACR) and Azure Kubernetes Service (AKS)

set -euo pipefail

# Configuration
APP_NAME="memory-leak-app"
NAMESPACE="default"
ACR_NAME="${ACR_NAME:-your-acr-name}"  # Set your ACR name
RESOURCE_GROUP="${RESOURCE_GROUP:-your-resource-group}"  # Set your resource group

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if Docker is available
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    # Check if kubectl is available
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    # Check if Azure CLI is available
    if ! command -v az &> /dev/null; then
        log_error "Azure CLI is not installed or not in PATH"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Function to build Docker image
build_image() {
    log_info "Building Docker image..."
    
    local image_tag="${ACR_NAME}.azurecr.io/${APP_NAME}:latest"
    
    docker build -t "${APP_NAME}:latest" -t "${image_tag}" .
    
    if [ $? -eq 0 ]; then
        log_success "Docker image built successfully: ${image_tag}"
        echo "${image_tag}"
    else
        log_error "Docker build failed"
        exit 1
    fi
}

# Function to push image to Azure Container Registry
push_to_acr() {
    local image_tag="$1"
    
    log_info "Pushing image to Azure Container Registry..."
    
    # Login to ACR
    az acr login --name "${ACR_NAME}"
    
    # Push image
    docker push "${image_tag}"
    
    if [ $? -eq 0 ]; then
        log_success "Image pushed to ACR successfully"
    else
        log_error "Failed to push image to ACR"
        exit 1
    fi
}

# Function to update Kubernetes manifest with correct image
update_manifest() {
    local image_tag="$1"
    
    log_info "Updating Kubernetes manifest..."
    
    # Create a temporary manifest with the correct image
    sed "s|image: memory-leak-app:latest|image: ${image_tag}|g" memory-leak-deployment.yaml > temp-deployment.yaml
    
    log_success "Manifest updated with image: ${image_tag}"
}

# Function to deploy to Kubernetes
deploy_to_k8s() {
    log_info "Deploying to Kubernetes..."
    
    # Apply the manifest
    kubectl apply -f temp-deployment.yaml
    
    if [ $? -eq 0 ]; then
        log_success "Application deployed to Kubernetes"
        
        # Wait for deployment to be ready
        log_info "Waiting for deployment to be ready..."
        kubectl wait --for=condition=available --timeout=300s deployment/${APP_NAME} -n ${NAMESPACE}
        
        # Show status
        show_status
    else
        log_error "Failed to deploy to Kubernetes"
        exit 1
    fi
    
    # Clean up temporary file
    rm -f temp-deployment.yaml
}

# Function to show application status
show_status() {
    log_info "Application Status:"
    echo
    
    # Show pods
    echo "Pods:"
    kubectl get pods -l app=${APP_NAME} -n ${NAMESPACE}
    echo
    
    # Show service
    echo "Service:"
    kubectl get svc memory-leak-service -n ${NAMESPACE}
    echo
    
    # Show HPA
    echo "Horizontal Pod Autoscaler:"
    kubectl get hpa memory-leak-hpa -n ${NAMESPACE} 2>/dev/null || echo "HPA not found"
    echo
    
    # Get service endpoint
    SERVICE_IP=$(kubectl get svc memory-leak-service -n ${NAMESPACE} -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)
    if [ -n "${SERVICE_IP}" ]; then
        log_success "Application accessible at: http://${SERVICE_IP}"
        echo "Endpoints:"
        echo "  Health Check: http://${SERVICE_IP}/health"
        echo "  Metrics: http://${SERVICE_IP}/metrics"
        echo "  Memory Cleanup: http://${SERVICE_IP}/cleanup"
    else
        log_warning "Service external IP not yet assigned"
    fi
}

# Function to enable memory leak
enable_memory_leak() {
    log_info "Enabling memory leak behavior..."
    
    kubectl patch deployment ${APP_NAME} -n ${NAMESPACE} -p '{"spec":{"template":{"spec":{"containers":[{"name":"memory-leak-app","env":[{"name":"LEAK","value":"TRUE"}]}]}}}}'
    
    log_success "Memory leak enabled. Monitor with: kubectl top pods -l app=${APP_NAME}"
}

# Function to disable memory leak
disable_memory_leak() {
    log_info "Disabling memory leak behavior..."
    
    kubectl patch deployment ${APP_NAME} -n ${NAMESPACE} -p '{"spec":{"template":{"spec":{"containers":[{"name":"memory-leak-app","env":[{"name":"LEAK","value":"FALSE"}]}]}}}}'
    
    log_success "Memory leak disabled"
}

# Function to cleanup resources
cleanup() {
    log_info "Cleaning up resources..."
    
    kubectl delete -f memory-leak-deployment.yaml 2>/dev/null || true
    
    log_success "Resources cleaned up"
}

# Function to show usage
usage() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo
    echo "Commands:"
    echo "  build                 Build Docker image"
    echo "  deploy                Build, push and deploy application"
    echo "  status                Show application status"
    echo "  enable-leak           Enable memory leak behavior"
    echo "  disable-leak          Disable memory leak behavior"
    echo "  cleanup               Remove all resources"
    echo "  help                  Show this help message"
    echo
    echo "Environment Variables:"
    echo "  ACR_NAME             Azure Container Registry name"
    echo "  RESOURCE_GROUP       Azure Resource Group name"
    echo
    echo "Examples:"
    echo "  ACR_NAME=myacr RESOURCE_GROUP=myrg $0 deploy"
    echo "  $0 enable-leak"
    echo "  $0 status"
}

# Main script logic
main() {
    case "${1:-help}" in
        "build")
            check_prerequisites
            build_image
            ;;
        "deploy")
            check_prerequisites
            image_tag=$(build_image)
            push_to_acr "${image_tag}"
            update_manifest "${image_tag}"
            deploy_to_k8s
            ;;
        "status")
            show_status
            ;;
        "enable-leak")
            enable_memory_leak
            ;;
        "disable-leak")
            disable_memory_leak
            ;;
        "cleanup")
            cleanup
            ;;
        "help"|*)
            usage
            ;;
    esac
}

# Run main function with all arguments
main "$@"
