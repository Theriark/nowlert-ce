#!/bin/bash

set -euo pipefail

echo "========================================="
echo " Building Nowlert Development Environment"
echo "========================================="

docker compose     -f docker-compose.yml     up -d --build nowlert-ce-dev

echo
echo "========================================="
echo " Nowlert Development Environment"
echo "========================================="

docker compose     -f docker-compose.yml     ps nowlert-ce-dev

echo
echo "Development environment updated."
