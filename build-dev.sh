#!/bin/bash

set -e

echo "========================================="
echo " Building Nowlert Development Image"
echo "========================================="

docker build \
    -f Dockerfile.dev \
    -t notifinho-dev:local \
    .

echo
echo "Restarting development container..."

docker restart notifinho-dev

echo
echo "✅ Development environment updated."
