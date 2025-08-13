FROM mcr.microsoft.com/devcontainers/python:3.13-bookworm

# Update package lists, install dependencies, and clean up in one layer
RUN apt-get update && \
    apt-get install -y git npm && \
    rm -rf /var/lib/apt/lists/*

# Clone the repository. It's good practice to clone to a specific directory.
RUN git clone https://github.com/cyanheads/filesystem-mcp-server.git /app 

# Set the working directory for subsequent Dockerfile commands (e.g., RUN, CMD, COPY)
WORKDIR /app

RUN npm install && npm run build
