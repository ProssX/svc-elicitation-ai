#!/bin/bash
# Database Setup Script
# This script sets up PostgreSQL and runs migrations

set -e  # Exit on error

echo "🔍 Checking if Docker is running..."
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop first."
    exit 1
fi

echo "✅ Docker is running"
echo ""

echo "🐘 Starting PostgreSQL..."
docker-compose up -d postgres

echo ""
echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 5

# Wait for PostgreSQL to be healthy
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if docker-compose ps postgres | grep -q "healthy"; then
        echo "✅ PostgreSQL is ready!"
        break
    fi
    echo "   Still waiting... (attempt $((attempt + 1))/$max_attempts)"
    sleep 2
    attempt=$((attempt + 1))
done

if [ $attempt -eq $max_attempts ]; then
    echo "❌ PostgreSQL failed to start. Check logs with: docker-compose logs postgres"
    exit 1
fi

echo ""
echo "📊 Running database migrations..."
python -m alembic upgrade head

echo ""
echo "✅ Database setup complete!"
echo ""
echo "📝 Useful commands:"
echo "   - View PostgreSQL logs: docker-compose logs -f postgres"
echo "   - Connect to database: docker exec -it postgres-elicitation psql -U postgres -d elicitation_ai"
echo "   - Stop PostgreSQL: docker-compose stop postgres"
echo "   - Remove database (WARNING - deletes data): docker-compose down -v"
