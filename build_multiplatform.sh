#!/bin/bash
# Script to build multi-platform Linux Docker/Podman images
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
    echo "Build a multi-platform Linux Docker/Podman image"
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

# ---------------------------------------------------------------------------
# Detect container engine: prefer podman if available, fall back to docker.
# Set CONTAINER_ENGINE to the resolved binary path.
# ---------------------------------------------------------------------------
detect_engine() {
    if command -v podman &>/dev/null; then
        CONTAINER_ENGINE="podman"
        ENGINE_TYPE="podman"
    elif command -v docker &>/dev/null; then
        CONTAINER_ENGINE="docker"
        ENGINE_TYPE="docker"
    else
        echo "ERROR: Neither podman nor docker was found in PATH."
        exit 1
    fi
    echo "Using container engine: $CONTAINER_ENGINE ($($CONTAINER_ENGINE --version 2>&1 | head -1))"
}

detect_engine

# Full image name with registry and tag
FULL_IMAGE_NAME="${REGISTRY}${IMAGE_NAME}:${IMAGE_TAG}"

# ---------------------------------------------------------------------------
# PODMAN path
# ---------------------------------------------------------------------------
if [ "$ENGINE_TYPE" = "podman" ]; then

    # Ensure the podman machine is running (macOS only)
    if [[ "$(uname)" == "Darwin" ]]; then
        # Discover the first machine name rather than assuming "podman-machine-default"
        PODMAN_MACHINE=$(podman machine list --format '{{.Name}}' 2>/dev/null | head -1)
        if [[ -z "$PODMAN_MACHINE" ]]; then
            echo "ERROR: No podman machine found. Create one with: podman machine init"
            exit 1
        fi
        MACHINE_STATE=$(podman machine inspect "$PODMAN_MACHINE" --format '{{.State}}' 2>/dev/null || true)
        if [[ "$MACHINE_STATE" != "running" ]]; then
            echo "Starting podman machine: $PODMAN_MACHINE"
            podman machine start "$PODMAN_MACHINE"
        else
            echo "Podman machine '$PODMAN_MACHINE' is already running."
        fi
    fi

    # Register QEMU binfmt handlers inside the podman machine for cross-arch builds
    echo "Setting up QEMU for cross-compilation..."
    podman run --privileged --rm tonistiigi/binfmt --install all 2>/dev/null || true

    if [ "$PUSH" = true ]; then
        echo "Building and pushing multi-platform image: $FULL_IMAGE_NAME"
        echo "Platforms: $LINUX_PLATFORMS"

        # podman build supports --platform and --manifest natively (no buildx needed).
        # Build each platform and collect them into a manifest list, then push.
        MANIFEST_NAME="$FULL_IMAGE_NAME"
        podman manifest rm "$MANIFEST_NAME" 2>/dev/null || true
        podman manifest create "$MANIFEST_NAME"

        IFS=',' read -ra PLATFORM_LIST <<< "$LINUX_PLATFORMS"
        for PLATFORM in "${PLATFORM_LIST[@]}"; do
            echo "Building for platform: $PLATFORM"
            ARCH_TAG="${FULL_IMAGE_NAME}-$(echo $PLATFORM | tr '/' '-')"
            podman build \
                --platform "$PLATFORM" \
                -t "$ARCH_TAG" \
                -f Dockerfile \
                --no-cache \
                .
            if [ $? -ne 0 ]; then
                echo "Build failed for platform $PLATFORM!"
                exit 1
            fi
            podman manifest add "$MANIFEST_NAME" "$ARCH_TAG"
        done

        podman manifest push "$MANIFEST_NAME" "docker://$MANIFEST_NAME"

        echo "Multi-architecture image pushed as: $FULL_IMAGE_NAME"
        echo "Verifying manifest..."
        podman manifest inspect "$FULL_IMAGE_NAME"

        echo "Testing image pull for different architectures..."
        podman pull --platform=linux/amd64 "$FULL_IMAGE_NAME"
        podman pull --platform=linux/arm64 "$FULL_IMAGE_NAME"

        echo "Image successfully built and pushed for multiple architectures"
    else
        echo "WARNING: Cannot load multi-platform images locally. Use --push to create multi-platform images."
        echo "Building only for the current platform..."
        # Derive current Linux platform from the podman machine or uname fallback
        CURRENT_PLATFORM=$(podman machine inspect --format '{{.VMType}}' 2>/dev/null \
            && echo "linux/$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/')" \
            || echo "linux/$(uname -m | sed 's/x86_64/amd64/;s/aarch64/arm64/')")
        echo "Building for platform: $CURRENT_PLATFORM"
        podman build \
            --platform "$CURRENT_PLATFORM" \
            -t "$FULL_IMAGE_NAME" \
            -f Dockerfile \
            --no-cache \
            .

        if [ $? -ne 0 ]; then
            echo "Linux build failed!"
            exit 1
        fi

        echo "Image was built locally but not pushed. Use --push to create multi-platform images."
    fi

# ---------------------------------------------------------------------------
# DOCKER path (original behaviour, unchanged)
# ---------------------------------------------------------------------------
else

    # Set up QEMU for cross-compilation
    echo "Setting up QEMU for cross-compilation..."
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

    BUILD_CMD="docker buildx build --platform $LINUX_PLATFORMS -t $FULL_IMAGE_NAME -f Dockerfile --progress=plain --no-cache --provenance=false --sbom=false"

    if [ "$PUSH" = true ]; then
        BUILD_CMD="$BUILD_CMD --push"
        echo "Linux images will be pushed to registry"
    else
        echo "WARNING: Cannot load multi-platform images locally. Use --push flag to create multi-platform images."
        echo "Building only for the current platform..."
        CURRENT_PLATFORM=$(docker version -f '{{.Server.Os}}/{{.Server.Arch}}' | tr '[:upper:]' '[:lower:]')
        if [[ $CURRENT_PLATFORM == linux/* ]]; then
            BUILD_CMD="docker buildx build --platform $CURRENT_PLATFORM -t $FULL_IMAGE_NAME -f Dockerfile --load --provenance=false --sbom=false"
        else
            echo "Falling back to plain 'docker build' for local single-arch image..."
            BUILD_CMD="docker build -t $FULL_IMAGE_NAME -f Dockerfile"
        fi
    fi

    if [ ! -z "$BUILD_CMD" ]; then
        BUILD_CMD="$BUILD_CMD ."

        echo "Executing: $BUILD_CMD"
        eval $BUILD_CMD

        if [ $? -ne 0 ]; then
            echo "Linux build failed!"
            exit 1
        fi
    fi

    if [ "$PUSH" = true ]; then
        echo "Multi-architecture image pushed as: $FULL_IMAGE_NAME"
        echo "Verifying manifest..."
        docker manifest inspect $FULL_IMAGE_NAME

        echo "Testing image pull for different architectures..."
        docker pull --platform=linux/amd64 $FULL_IMAGE_NAME
        docker pull --platform=linux/arm64 $FULL_IMAGE_NAME

        echo "Image successfully built and pushed for multiple architectures"
    else
        echo "Image was built locally but not pushed. Use --push to create multi-platform images."
    fi

fi

echo "Build process completed!"
