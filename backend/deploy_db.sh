#!/bin/bash

set -e

echo "🚀 Booting Sankalp X Database Deployer..."

source venv/bin/activate

echo "🔄 Generating Prisma Client..."
prisma generate

echo "☁️ Pushing Schema to AWS RDS PostgreSQL..."
prisma db push

echo "✅ Sovereign Vault Deployment Complete!"
