#!/bin/bash
# Script to build multi-platform Linux Docker images
# This script builds Linux images for multiple architectures

# Default values
IMAGE_NAME="mcp-instana"
IMAGE_TAG="latest"
REGISTRY=""
LINUX_PLATFORMS="linux/amd64,linux/arm64"
PUSH=false

# Display help
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo "Build a multi-platform Linux Docker image"
    echo ""
    echo "Options:"
    echo "  -n, --name NAME       Image name (default: mcp-instana)"
    echo "  -t, --tag TAG         Image tag (default: latest)"
    echo "  -r, --registry REG    Registry prefix (e.g., 'username/' or 'registry.example.com/')"
    echo "  -p, --platforms PLAT  Comma-separated list of platforms (default: linux/amd64,linux/arm64)"
    echo "  --push                Push the images to the registry"
    echo "  -h, --help            Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --name mcp-instana --tag v1.0 --registry username/ --push"
    echo "  $0 --platforms linux/amd64,linux/arm64 --registry username/ --push"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -n|--name)
            IMAGE_NAME="$2"
            shift 2
            ;;
        -t|--tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        -r|--registry)
            REGISTRY="$2"
            shift 2
            ;;
        -p|--platforms)
            LINUX_PLATFORMS="$2"
            shift 2
            ;;
        --push)
            PUSH=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Full image names with registry and tag
FULL_IMAGE_NAME="${REGISTRY}${IMAGE_NAME}:${IMAGE_TAG}"

# Set up QEMU for cross-compilation
echo "Setting up QEMU for cross-compilation..."
# Use a different approach to set up QEMU that works better on macOS
docker run --privileged --rm tonistiigi/binfmt --install all

# Disable default attestations
echo "Disabling default attestations..."
export BUILDX_NO_DEFAULT_ATTESTATIONS=1

# Set up Docker BuildKit builder
echo "Setting up Docker BuildKit builder..."
docker buildx create --name multiplatform --driver docker-container --use 2>/dev/null || true
docker buildx inspect --bootstrap

# Build Linux images
echo "Building Linux images: $FULL_IMAGE_NAME"
echo "Platforms: $LINUX_PLATFORMS"

# Build command for Linux with additional options for better cross-compilation
BUILD_CMD="docker buildx build --platform $LINUX_PLATFORMS -t $FULL_IMAGE_NAME -f Dockerfile --progress=plain --no-cache --provenance=false --sbom=false"

# Add push flag if requested
if [ "$PUSH" = true ]; then
    BUILD_CMD="$BUILD_CMD --push"
    echo "Linux images will be pushed to registry"
else
    echo "WARNING: Cannot load multi-platform images locally. Use --push flag to create multi-platform images."
    echo "Building only for the current platform..."
    # Get current platform
    CURRENT_PLATFORM=$(docker version -f '{{.Server.Os}}/{{.Server.Arch}}' | tr '[:upper:]' '[:lower:]')
    if [[ $CURRENT_PLATFORM == linux/* ]]; then
        BUILD_CMD="docker buildx build --platform $CURRENT_PLATFORM -t $FULL_IMAGE_NAME -f Dockerfile --load --provenance=false --sbom=false"
    else
        echo "Current platform is not Linux. Skipping local build."
        BUILD_CMD=""
    fi
fi

# Add context
if [ ! -z "$BUILD_CMD" ]; then
    BUILD_CMD="$BUILD_CMD ."
    
    # Execute build
    echo "Executing: $BUILD_CMD"
    eval $BUILD_CMD
    
    if [ $? -ne 0 ]; then
        echo "Linux build failed!"
        exit 1
    fi
fi

if [ "$PUSH" = true ]; then
    echo "Multi-architecture image pushed as: $FULL_IMAGE_NAME"
    
    # Verify the manifest
    echo "Verifying manifest..."
    docker manifest inspect $FULL_IMAGE_NAME
    
    # Test pulling the image for different architectures
    echo "Testing image pull for different architectures..."
    docker pull --platform=linux/amd64 $FULL_IMAGE_NAME
    docker pull --platform=linux/arm64 $FULL_IMAGE_NAME
    
    echo "Image successfully built and pushed for multiple architectures"
else
    echo "Image was built locally but not pushed. Use --push to create multi-platform images."
fi

echo "Build process completed!"