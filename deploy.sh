#!/bin/bash
set -e

# Default image name and tag
IMAGE_NAME="budgetbot_v2"
IMAGE_TAG="latest"
CONTAINER_NAME="budgetbot_v2-container"
DATA_DIR="user_data"  # Directory containing user data to persist
DOCKER_USERNAME="cleversol"  # Set your Docker Hub username here

# Display help information
show_help() {
    echo "Usage: ./deploy.sh [options]"
    echo "Options:"
    echo "  --build              Build the Docker image locally"
    echo "  --build-multi        Build for multiple architectures (amd64, arm64) and push to Docker Hub"
    echo "  --run                Run a local container after building"
    echo "  --deploy-remote      Generate command to deploy to a remote server"
    echo "  --image-name NAME    Set custom image name (default: budgetbot_v2)"
    echo "  --image-tag TAG      Set custom image tag (default: latest)"
    echo "  --data-dir DIR       Set custom data directory (default: user_data)"
    echo "  --username NAME      Set Docker Hub username (default: cleversol)"
    echo "  --help               Show this help message"
    exit 0
}

# Check for .env file and load environment variables
if [ -f .env ]; then
    echo "Loading environment variables from .env file..."
    source .env
else
    echo "Warning: .env file not found. Creating a template .env file..."
    echo "# Telegram Bot API Token" > .env
    echo "API_KEY=" >> .env
    echo "Please edit the .env file and add your API_KEY, then run this script again."
    exit 1
fi

# Check if API_KEY is set
if [ -z "$API_KEY" ]; then
    echo "Error: API_KEY not set in .env file."
    echo "Please add your Telegram Bot API key to the .env file."
    exit 1
fi

# Parse command line arguments
BUILD=false
BUILD_MULTI=false
RUN=false
DEPLOY_REMOTE=false

while [ "$#" -gt 0 ]; do
    case "$1" in
        --build)
            BUILD=true
            shift
            ;;
        --build-multi)
            BUILD_MULTI=true
            shift
            ;;
        --run)
            RUN=true
            shift
            ;;
        --deploy-remote)
            DEPLOY_REMOTE=true
            shift
            ;;
        --image-name)
            IMAGE_NAME="$2"
            shift 2
            ;;
        --image-tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        --data-dir)
            DATA_DIR="$2"
            shift 2
            ;;
        --username)
            DOCKER_USERNAME="$2"
            shift 2
            ;;
        --help)
            show_help
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            ;;
    esac
done

# If no actions specified, show help
if [[ "$BUILD" == "false" && "$BUILD_MULTI" == "false" && "$RUN" == "false" && "$DEPLOY_REMOTE" == "false" ]]; then
    show_help
fi

# Build for multiple architectures and push to Docker Hub
if [ "$BUILD_MULTI" = true ]; then
    echo "Building multi-architecture image for linux/amd64 and linux/arm64..."
    
    # Enable BuildKit
    export DOCKER_BUILDKIT=1
    
    # Set up buildx
    docker buildx create --name multiarch-builder --use || true
    docker buildx inspect --bootstrap
    
    # Build and push directly to Docker Hub
    echo "Building and pushing to Docker Hub as $DOCKER_USERNAME/$IMAGE_NAME:$IMAGE_TAG"
    echo "This might take several minutes..."
    
    docker buildx build --platform linux/amd64,linux/arm64 \
      -t $DOCKER_USERNAME/$IMAGE_NAME:$IMAGE_TAG \
      --push .
    
    echo "Multi-architecture image built and pushed successfully!"
fi

# Build the Docker image for local use
if [ "$BUILD" = true ]; then
    echo "Building Docker image: $IMAGE_NAME:$IMAGE_TAG..."
    echo "Note: Files in .dockerignore will be excluded from the build"

    # For ARM-based Macs, explicitly build for amd64 for compatibility with most servers
    if [[ $(uname -m) == "arm64" ]]; then
        echo "Detected ARM architecture. Building for amd64 compatibility..."
        docker build --platform=linux/amd64 -t $IMAGE_NAME:$IMAGE_TAG .
    else
        docker build -t $IMAGE_NAME:$IMAGE_TAG .
    fi
    
    echo "Image built successfully: $IMAGE_NAME:$IMAGE_TAG"
    
    # Tag with Docker Hub username
    echo "Tagging image for Docker Hub: $DOCKER_USERNAME/$IMAGE_NAME:$IMAGE_TAG"
    docker tag $IMAGE_NAME:$IMAGE_TAG $DOCKER_USERNAME/$IMAGE_NAME:$IMAGE_TAG
    
    echo "You can push this image to Docker Hub with:"
    echo "docker push $DOCKER_USERNAME/$IMAGE_NAME:$IMAGE_TAG"
fi

# Run the container locally
if [ "$RUN" = true ]; then
    echo "Stopping any existing container..."
    docker stop $CONTAINER_NAME 2>/dev/null || true
    docker rm $CONTAINER_NAME 2>/dev/null || true
    
    # Create data directory if it doesn't exist
    mkdir -p "./$DATA_DIR"
    
    echo "Running container locally with persistent data volume..."
    docker run -d \
      --name $CONTAINER_NAME \
      -e API_KEY="$API_KEY" \
      -v "$(pwd)/$DATA_DIR:/app/$DATA_DIR" \
      --restart unless-stopped \
      $IMAGE_NAME:$IMAGE_TAG
    
    echo "Container started successfully as $CONTAINER_NAME"
    echo "User data is persisted in the ./$DATA_DIR directory"
    echo "View logs with: docker logs $CONTAINER_NAME"
fi

# Generate deployment commands for remote server
if [ "$DEPLOY_REMOTE" = true ]; then
    echo "================================================================"
    echo "DEPLOYMENT INSTRUCTIONS FOR REMOTE SERVER:"
    echo "================================================================"
    echo ""
    echo "Option 1: Deploy using Docker Hub (recommended)"
    echo "-----------------------------------------------"
    echo "1. Push your image to Docker Hub (if you haven't with --build-multi):"
    echo "   $ docker login"
    echo "   $ docker push $DOCKER_USERNAME/$IMAGE_NAME:$IMAGE_TAG"
    echo ""
    echo "2. On your remote server, prepare the environment:"
    echo "   $ mkdir -p ~/budgetbot/$DATA_DIR"
    echo "   $ echo \"API_KEY=your_telegram_bot_token\" > ~/budgetbot/.env"
    echo ""
    echo "3. On your remote server, pull and run the image with persistent storage:"
    echo "   $ docker pull $DOCKER_USERNAME/$IMAGE_NAME:$IMAGE_TAG"
    echo "   $ docker run -d --name $CONTAINER_NAME \\"
    echo "       -e API_KEY=\"YOUR_API_KEY\" \\"
    echo "       -v ~/budgetbot/$DATA_DIR:/app/$DATA_DIR \\"
    echo "       --restart unless-stopped \\"
    echo "       $DOCKER_USERNAME/$IMAGE_NAME:$IMAGE_TAG"
    echo ""
    echo "Option 2: Deploy using direct image transfer"
    echo "--------------------------------------------"
    echo "1. Save the Docker image to a tar file:"
    echo "   $ docker save $DOCKER_USERNAME/$IMAGE_NAME:$IMAGE_TAG | gzip > $IMAGE_NAME-$IMAGE_TAG.tar.gz"
    echo ""
    echo "2. Transfer the tar file to your remote server:"
    echo "   $ scp $IMAGE_NAME-$IMAGE_TAG.tar.gz user@your-server:/tmp/"
    echo ""
    echo "3. On your remote server, prepare the environment:"
    echo "   $ mkdir -p ~/budgetbot/$DATA_DIR"
    echo "   $ echo \"API_KEY=your_telegram_bot_token\" > ~/budgetbot/.env"
    echo ""
    echo "4. On your remote server, load and run the image with persistent storage:"
    echo "   $ docker load < /tmp/$IMAGE_NAME-$IMAGE_TAG.tar.gz"
    echo "   $ docker run -d --name $CONTAINER_NAME \\"
    echo "       -e API_KEY=\"YOUR_API_KEY\" \\"
    echo "       -v ~/budgetbot/$DATA_DIR:/app/$DATA_DIR \\"
    echo "       --restart unless-stopped \\"
    echo "       $DOCKER_USERNAME/$IMAGE_NAME:$IMAGE_TAG"
    echo ""
    echo "Option 3: Deploy using docker-compose"
    echo "------------------------------------"
    echo "1. Create these files on your remote server in ~/budgetbot/:"
    echo ""
    echo "   docker-compose.yml:"
    echo "   -------------------"
    echo "   version: '3'"
    echo "   services:"
    echo "     budgetbot:"
    echo "       image: $DOCKER_USERNAME/$IMAGE_NAME:$IMAGE_TAG"
    echo "       container_name: $CONTAINER_NAME"
    echo "       restart: unless-stopped"
    echo "       env_file:"
    echo "         - .env"
    echo "       volumes:"
    echo "         - ./$DATA_DIR:/app/$DATA_DIR"
    echo ""
    echo "   .env:"
    echo "   ------"
    echo "   API_KEY=your_telegram_bot_token"
    echo ""
    echo "2. Run the container with docker-compose:"
    echo "   $ cd ~/budgetbot"
    echo "   $ docker-compose up -d"
    echo "================================================================"
fi

echo "Deployment script completed successfully!" 