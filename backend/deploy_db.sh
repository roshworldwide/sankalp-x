#!/bin/bash

# Sankalp X Sovereign Vault Migration Script (RDS PostgreSQL)
# This script provisions and deploys the Prisma schema to the AWS RDS instance.

set -e

echo "🚀 Booting Sankalp X Database Deployer..."

# 1. Activate the Python virtual environment
source venv/bin/activate

echo "🔄 Generating Prisma Client..."
# Generate the Prisma client for Python
prisma generate

echo "☁️ Pushing Schema to AWS RDS PostgreSQL..."
# Push schema securely to the Remote RDS Database leveraging $DATABASE_URL
# Using migrate deploy would be ideal for CI/CD, but db push is faster for prototyping to RDS
prisma db push

echo "✅ Sovereign Vault Deployment Complete!"
