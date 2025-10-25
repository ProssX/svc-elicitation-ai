# Database Setup Script (PowerShell)
# This script sets up PostgreSQL and runs migrations

$ErrorActionPreference = "Stop"

Write-Host "🔍 Checking if Docker is running..." -ForegroundColor Cyan
try {
    docker info | Out-Null
    Write-Host "✅ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "🐘 Starting PostgreSQL..." -ForegroundColor Cyan
docker-compose up -d postgres

Write-Host ""
Write-Host "⏳ Waiting for PostgreSQL to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Wait for PostgreSQL to be healthy
$maxAttempts = 30
$attempt = 0
$isHealthy = $false

while ($attempt -lt $maxAttempts) {
    $status = docker-compose ps postgres | Select-String "healthy"
    if ($status) {
        Write-Host "✅ PostgreSQL is ready!" -ForegroundColor Green
        $isHealthy = $true
        break
    }
    $attempt++
    Write-Host "   Still waiting... (attempt $attempt/$maxAttempts)" -ForegroundColor Yellow
    Start-Sleep -Seconds 2
}

if (-not $isHealthy) {
    Write-Host "❌ PostgreSQL failed to start. Check logs with: docker-compose logs postgres" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "📊 Running database migrations..." -ForegroundColor Cyan
python -m alembic upgrade head

Write-Host ""
Write-Host "✅ Database setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📝 Useful commands:" -ForegroundColor Cyan
Write-Host "   - View PostgreSQL logs: docker-compose logs -f postgres"
Write-Host "   - Connect to database: docker exec -it postgres-elicitation psql -U postgres -d elicitation_ai"
Write-Host "   - Stop PostgreSQL: docker-compose stop postgres"
Write-Host "   - Remove database (WARNING - deletes data): docker-compose down -v"
