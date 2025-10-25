# 🤖 Elicitation AI Service

Microservicio de IA para elicitación de requerimientos mediante entrevistas conversacionales inteligentes.

## 📋 **¿Qué es este servicio?**

Este microservicio utiliza **LLMs (Large Language Models)** para conducir entrevistas automatizadas con usuarios de negocio, extrayendo información relevante sobre procesos, necesidades y requerimientos de manera natural y conversacional.

**Características principales:**
- ✅ Entrevistas adaptativas en **3 idiomas** (Español, Inglés, Portugués)
- ✅ Soporte para modelos **locales (Ollama)** y **cloud (OpenAI)**
- ✅ API REST con FastAPI
- ✅ Arquitectura stateless y escalable
- ✅ Dockerizado para fácil despliegue
- ✅ Multi-tenant con contexto de usuario/organización

---

## 🏗️ **Arquitectura**

```
┌─────────────────────────────────────────────────┐
│         Frontend (React)                        │
│  - Chat UI                                      │
│  - Multi-language selector                     │
│  - localStorage persistence                     │
└────────────────┬────────────────────────────────┘
                 │ HTTP/REST
                 │
┌────────────────▼────────────────────────────────┐
│      Elicitation AI Service (FastAPI)          │
│  ┌─────────────────────────────────────────┐   │
│  │  Routers                                │   │
│  │  - /api/v1/health                       │   │
│  │  - /api/v1/interviews/start             │   │
│  │  - /api/v1/interviews/continue          │   │
│  │  - /api/v1/interviews/export            │   │
│  └──────────────┬──────────────────────────┘   │
│                 │                               │
│  ┌──────────────▼──────────────────────────┐   │
│  │  Agent Service (Strands SDK)            │   │
│  │  - Interview management                 │   │
│  │  - Conversation context analysis        │   │
│  │  - Multi-language support               │   │
│  └──────────────┬──────────────────────────┘   │
│                 │                               │
│  ┌──────────────▼──────────────────────────┐   │
│  │  Model Factory                          │   │
│  │  - OllamaModel (local)                  │   │
│  │  - OpenAIModel (cloud)                  │   │
│  └──────────────┬──────────────────────────┘   │
└─────────────────┼───────────────────────────────┘
                  │
        ┌─────────┴──────────┐
        │                    │
┌───────▼────────┐  ┌────────▼─────────┐
│ Ollama         │  │ OpenAI API       │
│ (Local)        │  │ (Cloud)          │
│ - llama3.2:3b  │  │ - gpt-4o         │
└────────────────┘  └──────────────────┘
```

---

## 🚀 **Inicio Rápido con Docker** (Recomendado)

### **Prerrequisitos**
- Docker Desktop instalado y corriendo
- Git

**✨ Ventaja de usar Docker:**
- ✅ **NO necesitás instalar Ollama** en tu máquina
- ✅ **NO necesitás instalar Python** ni dependencias
- ✅ Todo corre aislado en contenedores
- ✅ Fácil de compartir con el equipo

### **Paso 1: Clonar el repositorio**
```bash
git clone <repo-url>
cd svc-elicitation-ai
```

### **Paso 2: Levantar los servicios**
```bash
# Levantar backend AI + Ollama
docker-compose up -d

# Ver los logs en tiempo real
docker-compose logs -f
```

### **Paso 3: Descargar el modelo de IA (solo primera vez)**
```bash
# Esto puede tardar ~2-3 minutos (descarga 2GB)
docker exec ollama-service ollama pull llama3.2:3b
```

### **Paso 4: Verificar que todo funciona**
```bash
# Windows PowerShell:
Invoke-RestMethod -Uri http://localhost:8001/api/v1/health -Method Get

# Linux/Mac/Git Bash:
curl http://localhost:8001/api/v1/health
```

**Respuesta esperada:**
```json
{
  "status": "success",
  "code": 200,
  "message": "Service is healthy",
  "data": {
    "service": "svc-elicitation-ai",
    "version": "1.0.0",
    "status": "healthy",
    "model_provider": "local",
    "model": "llama3.2:3b",
    "environment": "development"
  }
}
```

### **Paso 5: Probar una entrevista**
```bash
# Windows PowerShell:
$body = @{ language = 'es'; organization_id = '1'; role_id = '1' } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8001/api/v1/interviews/start -Method Post -Body $body -ContentType 'application/json'

# Linux/Mac/Git Bash:
curl -X POST http://localhost:8001/api/v1/interviews/start \
  -H "Content-Type: application/json" \
  -d '{"language":"es","organization_id":"1","role_id":"1"}'
```

**¡Listo! El servicio está corriendo en `http://localhost:8001` 🎉**

**📚 Ver documentación interactiva:** http://localhost:8001/docs

---

## 🛠️ **Setup Manual (Sin Docker)**

<details>
<summary>Click para expandir instrucciones de setup manual</summary>

**⚠️ Con setup manual SÍ necesitás:**
- Instalar Python, pip, y todas las dependencias manualmente
- Instalar Ollama localmente (si usás modelo local)
- Configurar variables de entorno

**Recomendación:** Usá Docker si es tu primera vez.

---

### **Prerrequisitos**
- Python 3.11+
- pip
- **Opción A**: Ollama instalado localmente (para modelo local)
- **Opción B**: API Key de OpenAI (para modelo cloud)

### **1. Clonar el repositorio**
```bash
git clone <repo-url>
cd svc-elicitation-ai
```

### **2. Crear entorno virtual**
```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

### **3. Instalar dependencias**
```bash
pip install -r requirements.txt
```

### **4. Configurar variables de entorno**
```bash
# Copiar archivo de ejemplo
cp env.example .env

# Editar .env con tus valores
# Ver sección "Configuración" más abajo
```

### **5. Ejecutar el servicio**
```bash
# Con hot-reload (desarrollo)
uvicorn app.main:app --reload --port 8001

# Producción
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

### **6. Verificar que funciona**
```bash
# Health check
curl http://localhost:8001/api/v1/health

# Documentación interactiva
# Abrir en navegador: http://localhost:8001/docs
```

</details>

---

## ⚙️ **Configuración**

### **Opción A: Modelo Local con Ollama** ⚡ (Recomendado para desarrollo)

**📦 ¿Cuándo necesito esto?**
- ✅ Si usás **Docker**: Ya está incluido, solo seguí los pasos del "Inicio Rápido"
- ⚠️ Si usás **Setup Manual**: Seguí estos pasos para instalar Ollama localmente

**Ventajas:**
- ✅ Gratis, sin costos
- ✅ Privacidad total (los datos no salen de tu máquina)
- ✅ Sin límites de requests

**Desventajas:**
- ❌ Requiere GPU para buen rendimiento (CPU es muy lento)
- ❌ Calidad menor que GPT-4o

---

#### **Paso 1: Instalar Ollama (Solo si NO usás Docker)**
```bash
# Windows/Mac/Linux
# Descargar de: https://ollama.com/download
```

#### **Paso 2: Descargar modelo**
```bash
# Modelo recomendado (3B parámetros, ~2GB)
ollama pull llama3.2:3b

# O modelo más grande (mejor calidad, requiere más RAM)
ollama pull llama3.1:8b
```

#### **Paso 3: Iniciar Ollama**
```bash
ollama serve
```

#### **Paso 4: Configurar .env**
```bash
MODEL_PROVIDER=local
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
```

---

### **Opción B: Modelo Cloud con OpenAI** 🚀 (Recomendado para producción)

**Ventajas:**
- ✅ Máxima calidad (GPT-4o es muy superior)
- ✅ No requiere GPU local
- ✅ Respuestas más rápidas y contextuales

**Desventajas:**
- ❌ Costo por request (~$0.01 por entrevista)
- ❌ Requiere conexión a internet
- ❌ Los datos se envían a OpenAI

#### **Paso 1: Obtener API Key**
1. Crear cuenta en: https://platform.openai.com/
2. Ir a: https://platform.openai.com/api-keys
3. Crear nueva API key
4. Copiar la key (guárdala, no se vuelve a mostrar)

#### **Paso 2: Configurar .env**
```bash
MODEL_PROVIDER=openai
OPENAI_API_KEY=sk-proj-XXXXXXXXXXXXXXXXXXXXXXXX
OPENAI_MODEL=gpt-4o
```

#### **Paso 3: Ejecutar y probar**
```bash
# Si estás en Windows y el .env no se carga automáticamente:
# PowerShell:
$env:OPENAI_API_KEY="sk-proj-XXXXX"
uvicorn app.main:app --reload --port 8001

# CMD:
set OPENAI_API_KEY=sk-proj-XXXXX
uvicorn app.main:app --reload --port 8001

# Linux/Mac:
export OPENAI_API_KEY="sk-proj-XXXXX"
uvicorn app.main:app --reload --port 8001
```

---

## 🐳 **Gestión con Docker**

### **Comandos Útiles**

#### **Iniciar servicios**
```bash
# Iniciar en background
docker-compose up -d

# Iniciar y ver logs
docker-compose up

# Rebuild completo (si cambiaste código)
docker-compose up -d --build
```

#### **Ver logs**
```bash
# Ambos servicios
docker-compose logs -f

# Solo AI service
docker-compose logs -f elicitation-ai

# Solo Ollama
docker-compose logs -f ollama
```

#### **Detener servicios**
```bash
# Detener (mantiene los datos del modelo)
docker-compose down

# Detener y borrar TODO (incluyendo modelo descargado - 2GB)
docker-compose down -v
```

#### **Verificar estado**
```bash
# Ver contenedores corriendo
docker ps

# Ver salud de los servicios
docker inspect svc-elicitation-ai | grep -A 3 "Health"
docker inspect ollama-service | grep -A 3 "Health"
```

#### **Reiniciar un servicio**
```bash
# Reiniciar solo AI service
docker-compose restart elicitation-ai

# Reiniciar solo Ollama
docker-compose restart ollama
```

#### **Ejecutar comandos dentro de los contenedores**
```bash
# Ver modelos instalados en Ollama
docker exec ollama-service ollama list

# Descargar otro modelo
docker exec ollama-service ollama pull llama3.1:8b

# Verificar configuración del AI service
docker exec svc-elicitation-ai python -c "from app.config import Settings; s = Settings(); print(f'Provider: {s.model_provider}, Model: {s.ollama_model}')"
```

---

### **🔄 Cambiar de Ollama a OpenAI**

Si querés cambiar al modelo cloud de OpenAI:

```bash
# 1. Detener servicios
docker-compose down

# 2. Editar docker-compose.yml, cambiar estas líneas:
# - MODEL_PROVIDER=openai  # Cambiar de 'local' a 'openai'
# - OPENAI_API_KEY=sk-proj-TU_API_KEY_AQUI

# 3. Levantar solo el AI service (no necesitamos Ollama)
docker-compose up -d elicitation-ai

# 4. Verificar
curl http://localhost:8001/api/v1/health
```

---

## ✅ **Estado de Validación**

**Última validación:** 8 de octubre, 2025  
**Estado:** ✅ **TODOS LOS TESTS PASARON**

| Componente | Estado | Observación |
|------------|--------|-------------|
| Multi-idioma (ES/EN/PT) | ✅ | Funcional |
| Eliminación de `context` | ✅ | Implementado |
| `language` en `meta` | ✅ | Persistido correctamente |
| Swagger UI actualizado | ✅ | Documentación clara |
| Docker Services | ✅ | Healthy |
| Estándar Confluence | ✅ | 100% cumplimiento |

📄 **Ver reporte completo:** [`VALIDATION_REPORT.md`](./VALIDATION_REPORT.md)

---

## 🏗️ **Arquitectura - Diseño Stateless**

Este microservicio usa un diseño **stateless** (sin estado):
- ❌ NO guarda sesiones en memoria ni base de datos
- ✅ Cada request debe incluir toda la información necesaria
- ✅ El `language` debe enviarse en CADA request (`/start` y `/continue`)
- ✅ Facilita escalado horizontal y alta disponibilidad

📄 **Documentación completa:** [`STATELESS_DESIGN.md`](./STATELESS_DESIGN.md)

**⚠️ IMPORTANTE para Frontend:**
- Persistir `language` en localStorage
- Enviarlo en cada request a `/continue`
- Ver [`FRONTEND_CHANGES.md`](./FRONTEND_CHANGES.md) para detalles de implementación

---

## 🔐 **Authentication**

This service uses **JWT (JSON Web Token)** authentication provided by the Auth Service (svc-users-python). All interview endpoints require a valid Bearer token.

### **How to Obtain a Token**

#### **Step 1: Login to Auth Service**

The Auth Service must be running at the URL specified in `AUTH_SERVICE_URL` environment variable (default: `http://localhost:8000`).

**Request:**
```bash
# Windows PowerShell:
$body = @{ 
  email = 'admin@example.com'
  password = 'admin123' 
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri http://localhost:8000/api/v1/auth/login `
  -Method Post -Body $body -ContentType 'application/json'

$token = $response.data.access_token
Write-Host "Token: $token"

# Linux/Mac/Git Bash:
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}' \
  | jq -r '.data.access_token'
```

**Response:**
```json
{
  "status": "success",
  "code": 200,
  "message": "Login successful",
  "data": {
    "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6ImF1dGgtMjAyNS0xMC0xNSJ9...",
    "token_type": "bearer",
    "expires_in": 604800
  }
}
```

#### **Step 2: Use Token in Requests**

Include the token in the `Authorization` header with the `Bearer` prefix:

**Request:**
```bash
# Windows PowerShell:
$headers = @{ Authorization = "Bearer $token" }
$body = @{ language = 'es' } | ConvertTo-Json

Invoke-RestMethod -Uri http://localhost:8001/api/v1/interviews/start `
  -Method Post -Headers $headers -Body $body -ContentType 'application/json'

# Linux/Mac/Git Bash:
TOKEN="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6ImF1dGgtMjAyNS0xMC0xNSJ9..."

curl -X POST http://localhost:8001/api/v1/interviews/start \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"language":"es"}'
```

### **Authentication Configuration**

The AI Service needs to know where the Auth Service is located. Configure this in your `.env` file:

```bash
# Authentication Service URL (required)
AUTH_SERVICE_URL=http://localhost:8000

# JWT Configuration (must match Auth Service settings)
JWT_ISSUER=https://api.example.com
JWT_AUDIENCE=https://api.example.com

# JWKS Cache TTL in seconds (default: 3600 = 1 hour)
JWKS_CACHE_TTL=3600
```

**Docker Configuration:**

If using Docker Compose with both services, update `docker-compose.yml`:

```yaml
services:
  elicitation-ai:
    environment:
      - AUTH_SERVICE_URL=http://auth-service:8000  # Use service name for Docker networking
      - JWT_ISSUER=https://api.example.com
      - JWT_AUDIENCE=https://api.example.com
```

### **Authentication Error Responses**

#### **401 Unauthorized - Missing Token**
```json
{
  "status": "error",
  "code": 401,
  "message": "Authentication required",
  "errors": [{
    "field": "authorization",
    "error": "Missing or invalid authorization header"
  }]
}
```

#### **401 Unauthorized - Token Expired**
```json
{
  "status": "error",
  "code": 401,
  "message": "Token expired",
  "errors": [{
    "field": "token",
    "error": "JWT token has expired"
  }]
}
```

#### **401 Unauthorized - Invalid Token**
```json
{
  "status": "error",
  "code": 401,
  "message": "Invalid token",
  "errors": [{
    "field": "token",
    "error": "Token signature verification failed"
  }]
}
```

#### **503 Service Unavailable - Auth Service Down**
```json
{
  "status": "error",
  "code": 503,
  "message": "Authentication service unavailable",
  "errors": [{
    "field": "service",
    "error": "Unable to validate token"
  }]
}
```

### **Which Endpoints Require Authentication?**

| Endpoint | Authentication Required | Description |
|----------|------------------------|-------------|
| `GET /` | ❌ No | Root endpoint |
| `GET /api/v1/health` | ❌ No | Health check |
| `POST /api/v1/interviews/start` | ✅ Yes | Start interview |
| `POST /api/v1/interviews/continue` | ✅ Yes | Continue interview |
| `POST /api/v1/interviews/export` | ✅ Yes | Export interview data |
| `POST /api/v1/interviews/test` | ✅ Yes | Test endpoint |

**Note:** Health check endpoints remain unauthenticated for monitoring purposes.

### **Token Details**

The JWT token contains the following claims:

```json
{
  "sub": "01932e5f-8b2a-7890-b123-456789abcdef",  // User ID
  "organizationId": "01932e5f-1234-5678-9abc-def012345678",  // Organization ID
  "iss": "https://api.example.com",  // Issuer
  "aud": "https://api.example.com",  // Audience
  "iat": 1729526400,  // Issued at
  "exp": 1730131200,  // Expiration (7 days default)
  "jti": "01932e5f-uuid7-generated",  // JWT ID
  "roles": ["admin"],  // User roles
  "permissions": ["users:read", "users:write", "interviews:manage"]  // Permissions
}
```

The AI Service automatically extracts `user_id` and `organization_id` from the token, so you no longer need to send these in the request body.

### **Security Best Practices**

1. **Always use HTTPS in production** - Tokens should never be transmitted over unencrypted connections
2. **Store tokens securely** - Use httpOnly cookies or secure storage (never localStorage for sensitive apps)
3. **Handle token expiration** - Implement token refresh logic or redirect to login
4. **Don't log tokens** - Tokens should never appear in logs or error messages
5. **Validate on every request** - The AI Service validates tokens on every protected endpoint

### **Troubleshooting Authentication**

#### **Problem: "Authentication service unavailable" (503)**

**Cause:** AI Service cannot reach the Auth Service to fetch JWKS public keys.

**Solutions:**
1. Verify Auth Service is running: `curl http://localhost:8000/api/v1/health`
2. Check `AUTH_SERVICE_URL` environment variable is correct
3. If using Docker, ensure services are on the same network
4. Check Auth Service logs: `docker logs svc-users-python`

#### **Problem: "Invalid token" (401)**

**Cause:** Token signature verification failed.

**Solutions:**
1. Ensure `JWT_ISSUER` and `JWT_AUDIENCE` match between services
2. Verify token hasn't been tampered with
3. Check that Auth Service is using the correct private key
4. Ensure JWKS endpoint is accessible: `curl http://localhost:8000/api/v1/auth/jwks`

#### **Problem: "Token expired" (401)**

**Cause:** Token has exceeded its expiration time (default: 7 days).

**Solution:**
1. Login again to obtain a new token
2. Implement token refresh mechanism in your frontend
3. Adjust token expiration time in Auth Service if needed

---

## 💾 **Database Setup**

This service uses **PostgreSQL 17.6** to persist interview data. Interviews and messages are stored in a relational database for analysis, auditing, and recovery.

### **Database Architecture**

```
┌─────────────────────────────────────────┐
│         PostgreSQL 17.6-alpine          │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │  interview                        │ │
│  │  - id_interview (UUID PK)         │ │
│  │  - employee_id (UUID, indexed)    │ │
│  │  - language, status, timestamps   │ │
│  └──────────────┬────────────────────┘ │
│                 │ 1:N                   │
│  ┌──────────────▼────────────────────┐ │
│  │  interview_message                │ │
│  │  - id_message (UUID PK)           │ │
│  │  - interview_id (UUID FK CASCADE) │ │
│  │  - role, content, sequence_number │ │
│  └───────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

### **Database Configuration**

Add these environment variables to your `.env` file:

```bash
# Database Connection (required)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/elicitation_ai

# Connection Pool Settings (optional)
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
```

**Docker Configuration:**

If using Docker Compose, the database service is already configured. Update `docker-compose.yml` if needed:

```yaml
services:
  postgres:
    image: postgres:17.6-alpine
    environment:
      POSTGRES_DB: elicitation_ai
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  elicitation-ai:
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/elicitation_ai
    depends_on:
      postgres:
        condition: service_healthy

volumes:
  postgres_data:
```

### **Database Migrations with Alembic**

This project uses **Alembic** for database schema migrations.

#### **Initial Setup (First Time)**

```bash
# 1. Ensure PostgreSQL is running
docker-compose up -d postgres

# Or without Docker:
# Make sure PostgreSQL 17.6 is installed and running

# 2. Apply migrations
python -m alembic upgrade head
```

#### **Common Migration Commands**

```bash
# Apply all pending migrations
python -m alembic upgrade head

# Rollback last migration
python -m alembic downgrade -1

# Rollback all migrations
python -m alembic downgrade base

# View migration history
python -m alembic history

# View current migration version
python -m alembic current

# Create a new migration (after modifying models)
python -m alembic revision --autogenerate -m "description_of_changes"
```

#### **Migration Files Location**

Migrations are stored in: `alembic/versions/`

Current migrations:
- `20250124_1430_a1b2c3d4e5f6_create_interview_tables.py` - Initial schema

### **Database Schema Details**

#### **Table: interview**

Stores interview metadata and session information.

| Column | Type | Description |
|--------|------|-------------|
| `id_interview` | UUID | Primary key (UUID v7 or v4) |
| `employee_id` | UUID | Reference to employee (indexed) |
| `language` | ENUM | Interview language (es/en/pt) |
| `technical_level` | VARCHAR(20) | User's technical level |
| `status` | ENUM | Interview status (in_progress/completed/cancelled) |
| `started_at` | TIMESTAMP | When interview started |
| `completed_at` | TIMESTAMP | When interview completed (nullable) |
| `created_at` | TIMESTAMP | Record creation timestamp |
| `updated_at` | TIMESTAMP | Record last update timestamp |

**Indexes:**
- `idx_interview_employee_id` on `employee_id`
- `idx_interview_status` on `status`
- `idx_interview_started_at` on `started_at`

#### **Table: interview_message**

Stores individual messages (questions and answers) in the conversation.

| Column | Type | Description |
|--------|------|-------------|
| `id_message` | UUID | Primary key (UUID v7 or v4) |
| `interview_id` | UUID | Foreign key to interview (CASCADE DELETE) |
| `role` | ENUM | Message role (assistant/user/system) |
| `content` | TEXT | Message content |
| `sequence_number` | INTEGER | Message order in conversation (1-based) |
| `created_at` | TIMESTAMP | Message creation timestamp |

**Indexes:**
- `idx_interview_sequence` on `(interview_id, sequence_number)`

**Foreign Keys:**
- `interview_id` → `interview.id_interview` (ON DELETE CASCADE)

### **Database Troubleshooting**

#### **❌ Error: "No module named 'asyncpg'"**

**Solution:**
```bash
pip install asyncpg>=0.29.0
```

#### **❌ Error: "Connection refused" when running migrations**

**Cause:** PostgreSQL is not running

**Solution:**
```bash
# With Docker:
docker-compose up -d postgres
docker ps | grep postgres  # Verify it's running

# Without Docker:
# Start PostgreSQL service on your system
# Windows: services.msc → PostgreSQL → Start
# Linux: sudo systemctl start postgresql
# Mac: brew services start postgresql
```

#### **❌ Error: "Database does not exist"**

**Solution:**
```bash
# Create database manually
docker exec -it postgres-container psql -U postgres -c "CREATE DATABASE elicitation_ai;"

# Or connect and create:
docker exec -it postgres-container psql -U postgres
CREATE DATABASE elicitation_ai;
\q
```

#### **❌ Error: "Migration already exists"**

**Cause:** Trying to apply a migration that's already been applied

**Solution:**
```bash
# Check current version
python -m alembic current

# View history
python -m alembic history

# If needed, mark migration as applied without running it
python -m alembic stamp head
```

### **Database Backup and Restore**

#### **Backup**

```bash
# With Docker:
docker exec postgres-container pg_dump -U postgres elicitation_ai > backup.sql

# Without Docker:
pg_dump -U postgres elicitation_ai > backup.sql
```

#### **Restore**

```bash
# With Docker:
docker exec -i postgres-container psql -U postgres elicitation_ai < backup.sql

# Without Docker:
psql -U postgres elicitation_ai < backup.sql
```

### **Database Connection Validation**

The service automatically validates the database connection on startup. Check the logs:

```bash
# With Docker:
docker logs svc-elicitation-ai | grep -i database

# Expected output:
# ✅ Database connection validated successfully
```

If you see:
```
❌ Database connection failed: ...
```

Check:
1. PostgreSQL is running
2. `DATABASE_URL` is correct
3. Database exists
4. User has proper permissions

---

## 📡 **API Endpoints**

### **📚 Documentación Interactiva**

FastAPI genera documentación automática en dos formatos:

#### **Swagger UI (Recomendado)**
```
🌐 http://localhost:8001/docs
```
- ✅ Interfaz interactiva para probar endpoints
- ✅ Esquemas de request/response
- ✅ Ejecutar requests directamente desde el navegador
- ✅ Ver ejemplos y validaciones

#### **ReDoc (Alternativo)**
```
🌐 http://localhost:8001/redoc
```
- ✅ Documentación limpia y moderna
- ✅ Búsqueda avanzada
- ✅ Descarga de especificación OpenAPI

#### **OpenAPI JSON**
```
🌐 http://localhost:8001/openapi.json
```
- Para integración con herramientas externas (Postman, Insomnia, etc.)

---

### **🔌 Endpoints Disponibles**

#### **1. Health Check**
```bash
GET /api/v1/health

# Respuesta:
{
  "status": "success",
  "code": 200,
  "message": "Service is healthy",
  "data": {
    "service": "svc-elicitation-ai",
    "version": "1.0.0",
    "status": "healthy",
    "model_provider": "local",
    "model": "llama3.2:3b",
    "environment": "development"
  }
}
```

#### **2. Iniciar Entrevista**
**Descripción:** Inicia una nueva sesión de entrevista con el usuario.

**🔐 Authentication Required:** Bearer token in Authorization header

**Request:**
```json
POST /api/v1/interviews/start
Authorization: Bearer <your-jwt-token>
Content-Type: application/json

{
  "language": "es"  // "es" | "en" | "pt" (optional, default: "es")
}
```

**⚠️ IMPORTANT:** `user_id` and `organization_id` are no longer sent in the request body. They are automatically extracted from the JWT token.

**Ejemplo con PowerShell:**
```powershell
# First, obtain token from Auth Service
$loginBody = @{ email = 'admin@example.com'; password = 'admin123' } | ConvertTo-Json
$loginResponse = Invoke-RestMethod -Uri http://localhost:8000/api/v1/auth/login `
  -Method Post -Body $loginBody -ContentType 'application/json'
$token = $loginResponse.data.access_token

# Then, start interview with token
$headers = @{ Authorization = "Bearer $token" }
$body = @{ language = 'es' } | ConvertTo-Json

Invoke-RestMethod -Uri http://localhost:8001/api/v1/interviews/start `
  -Method Post -Headers $headers -Body $body -ContentType 'application/json'
```

**Ejemplo con cURL:**
```bash
# First, obtain token from Auth Service
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}' \
  | jq -r '.data.access_token')

# Then, start interview with token
curl -X POST http://localhost:8001/api/v1/interviews/start \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"language":"es"}'
```

**Response:**
```json
{
  "status": "success",
  "code": 200,
  "message": "Interview started successfully",
  "data": {
    "session_id": "1add3c4a-8730-4140-888b-59ac47fcac43",
    "question": "Hola Juan, ¿cómo vas? Me alegra tenerte aquí hoy...",
    "question_number": 1,
    "is_final": false
  },
  "errors": null,
  "meta": {
    "user_name": "Juan Pérez",
    "organization": "ProssX Demo",
    "language": "es"
  }
}
```

#### **3. Continuar Entrevista**
**Descripción:** Envía la respuesta del usuario y recibe la siguiente pregunta.

**🔐 Authentication Required:** Bearer token in Authorization header

**Request:**
```json
POST /api/v1/interviews/continue
Authorization: Bearer <your-jwt-token>
Content-Type: application/json

{
  "session_id": "1add3c4a-8730-4140-888b-59ac47fcac43",
  "user_response": "Soy gerente de operaciones, coordino equipos...",
  "conversation_history": [],
  "language": "es"
}
```

**Ejemplo con PowerShell:**
```powershell
# Assuming you already have $token from login
$headers = @{ Authorization = "Bearer $token" }
$body = @{ 
  session_id = '1add3c4a-8730-4140-888b-59ac47fcac43'
  user_response = 'Soy gerente de operaciones, coordino equipos y apruebo compras'
  conversation_history = @()
  language = 'es'
} | ConvertTo-Json -Depth 3

Invoke-RestMethod -Uri http://localhost:8001/api/v1/interviews/continue `
  -Method Post -Headers $headers -Body $body -ContentType 'application/json'
```

**Ejemplo con cURL:**
```bash
# Assuming you already have $TOKEN from login
curl -X POST http://localhost:8001/api/v1/interviews/continue \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "1add3c4a-8730-4140-888b-59ac47fcac43",
    "user_response": "Soy gerente de operaciones, coordino equipos",
    "conversation_history": [],
    "language": "es"
  }'
```

**Response:**
```json
{
  "status": "success",
  "code": 200,
  "message": "Question generated successfully",
  "data": {
    "question": "Vamos a profundizar un poco más. ¿Cuál es el primer paso...",
    "question_number": 2,
    "is_final": false,
    "corrected_response": "Soy gerente de operaciones, coordino equipos"
  },
  "errors": null,
  "meta": {
    "session_id": "1add3c4a-8730-4140-888b-59ac47fcac43",
    "question_count": 2,
    "language": "es"
  }
}
```

---

#### **4. Exportar Entrevista**
**Descripción:** Exporta los datos completos de la entrevista para análisis posterior (sin análisis de IA).

**🔐 Authentication Required:** Bearer token in Authorization header

**⚠️ IMPORTANTE:** Como el backend es stateless, debes enviar `conversation_history` completo y `language`.

**Request:**
```json
POST /api/v1/interviews/export
Authorization: Bearer <your-jwt-token>
Content-Type: application/json

{
  "session_id": "1add3c4a-8730-4140-888b-59ac47fcac43",
  "conversation_history": [
    {
      "role": "assistant",
      "content": "¿Cuál es tu función principal?",
      "timestamp": "2025-10-08T14:15:00Z"
    },
    {
      "role": "user",
      "content": "Soy gerente de compras",
      "timestamp": "2025-10-08T14:16:00Z"
    }
  ],
  "language": "es"
}
```

**Ejemplo con PowerShell:**
```powershell
# Assuming you already have $token from login
$headers = @{ Authorization = "Bearer $token" }
$body = @{
  session_id = '1add3c4a-8730-4140-888b-59ac47fcac43'
  conversation_history = @(
    @{ role = 'assistant'; content = '¿Cuál es tu función?'; timestamp = '2025-10-08T14:15:00Z' },
    @{ role = 'user'; content = 'Soy gerente'; timestamp = '2025-10-08T14:16:00Z' }
  )
  language = 'es'
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Uri http://localhost:8001/api/v1/interviews/export `
  -Method Post -Headers $headers -Body $body -ContentType 'application/json'
```

**Ejemplo con cURL:**
```bash
# Assuming you already have $TOKEN from login
curl -X POST http://localhost:8001/api/v1/interviews/export \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id":"1add3c4a-8730-4140-888b-59ac47fcac43",
    "conversation_history":[
      {"role":"assistant","content":"¿Cuál es tu función?","timestamp":"2025-10-08T14:15:00Z"},
      {"role":"user","content":"Soy gerente","timestamp":"2025-10-08T14:16:00Z"}
    ],
    "language":"es"
  }'
```

**Response:**
```json
{
  "status": "success",
  "code": 200,
  "message": "Interview data exported successfully (raw data only)",
  "data": {
    "session_id": "1add3c4a-8730-4140-888b-59ac47fcac43",
    "user_id": "user-123",
    "user_name": "Juan Pérez",
    "user_role": "Gerente de Operaciones",
    "organization": "ProssX Demo",
    "interview_date": "2025-10-08T14:30:00Z",
    "interview_duration_minutes": 15,
    "total_questions": 8,
    "total_user_responses": 8,
    "is_complete": true,
    "conversation_history": [...]
  },
  "errors": null,
  "meta": {
    "session_id": "1add3c4a-8730-4140-888b-59ac47fcac43",
    "export_date": "2025-10-08T14:30:00Z",
    "language": "es",
    "technical_level": "non-technical",
    "note": "This is raw data. Process extraction should be done by a separate service."
  }
}
```

**⚠️ Notas Importantes:**
- ✅ **`language` en `meta`** (no en `metadata` dentro de `data`)
- ✅ **NO incluye `completeness_score`** (métrica interna eliminada)
- ✅ **Datos en crudo solamente** - El análisis de procesos (BPMN) es responsabilidad de otro microservicio
- ✅ **Backend stateless** - Debes enviar `conversation_history` completo y `language`

---

## 🔍 **Troubleshooting**

### **🔐 Authentication Issues**

#### **❌ Error: "Authentication required" (401)**

**Síntoma:** Request rechazado con mensaje "Authentication required"

**Causa:** Falta el token de autenticación o el header Authorization está mal formado

**Solución:**
```bash
# ❌ Incorrecto (sin Authorization header):
curl -X POST http://localhost:8001/api/v1/interviews/start \
  -H "Content-Type: application/json" \
  -d '{"language":"es"}'

# ✅ Correcto (con Bearer token):
curl -X POST http://localhost:8001/api/v1/interviews/start \
  -H "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6ImF1dGgtMjAyNS0xMC0xNSJ9..." \
  -H "Content-Type: application/json" \
  -d '{"language":"es"}'
```

**Verificar formato del header:**
- Debe ser: `Authorization: Bearer <token>`
- NO: `Authorization: <token>` (falta "Bearer ")
- NO: `Bearer <token>` (falta "Authorization:")

---

#### **❌ Error: "Token expired" (401)**

**Síntoma:** Request rechazado con mensaje "Token expired"

**Causa:** El token JWT ha superado su tiempo de expiración (default: 7 días)

**Solución:**
```bash
# Obtener un nuevo token haciendo login nuevamente
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}' \
  | jq -r '.data.access_token'
```

**Prevención:**
- Implementar lógica de refresh token en el frontend
- Verificar expiración antes de hacer requests
- Redirigir a login cuando el token expire

---

#### **❌ Error: "Invalid token" (401)**

**Síntoma:** Request rechazado con mensaje "Invalid token" o "Token signature verification failed"

**Causas posibles:**

1. **Token corrupto o modificado:**
```bash
# Verificar que el token no se haya cortado o modificado
echo $TOKEN | wc -c  # Debe tener ~500-800 caracteres
```

2. **Configuración incorrecta de JWT_ISSUER o JWT_AUDIENCE:**
```bash
# Verificar que coincidan entre Auth Service y AI Service
docker exec svc-elicitation-ai printenv | grep JWT
# Debe mostrar:
# JWT_ISSUER=https://api.example.com
# JWT_AUDIENCE=https://api.example.com
```

3. **JWKS endpoint no accesible:**
```bash
# Verificar que el AI Service pueda acceder al JWKS endpoint
curl http://localhost:8000/api/v1/auth/jwks
# Debe retornar JSON con las public keys
```

---

#### **❌ Error: "Authentication service unavailable" (503)**

**Síntoma:** Request rechazado con mensaje "Authentication service unavailable"

**Causa:** El AI Service no puede conectarse al Auth Service para obtener las public keys (JWKS)

**Soluciones:**

1. **Verificar que Auth Service esté corriendo:**
```bash
# Verificar health del Auth Service
curl http://localhost:8000/api/v1/health

# Con Docker:
docker ps | grep svc-users-python
docker logs svc-users-python --tail 50
```

2. **Verificar AUTH_SERVICE_URL:**
```bash
# Verificar la variable de entorno
docker exec svc-elicitation-ai printenv | grep AUTH_SERVICE_URL

# Debe mostrar:
# - Con Docker: AUTH_SERVICE_URL=http://auth-service:8000
# - Sin Docker: AUTH_SERVICE_URL=http://localhost:8000
```

3. **Verificar conectividad de red (Docker):**
```bash
# Verificar que ambos servicios estén en la misma red
docker network inspect <network-name>

# Probar conectividad desde AI Service a Auth Service
docker exec svc-elicitation-ai curl http://auth-service:8000/api/v1/health
```

4. **Verificar JWKS endpoint:**
```bash
# El endpoint debe estar accesible
curl http://localhost:8000/api/v1/auth/jwks

# Debe retornar algo como:
# {"keys":[{"kty":"RSA","kid":"auth-2025-10-15",...}]}
```

**Nota:** El AI Service cachea las public keys por 1 hora (default). Si el Auth Service está temporalmente caído pero el cache es válido, los requests seguirán funcionando.

---

### **❌ Error: "All connection attempts failed"**

**Síntoma:** El AI service no puede conectarse a Ollama

**Causas y Soluciones:**

1. **Ollama no está corriendo:**
```bash
# Verificar si Ollama está up
docker ps | grep ollama

# Si no aparece, reiniciar servicios
docker-compose restart
```

2. **Modelo no descargado:**
```bash
# Verificar modelos instalados
docker exec ollama-service ollama list

# Si está vacío, descargar el modelo
docker exec ollama-service ollama pull llama3.2:3b
```

3. **Variable de entorno incorrecta:**
```bash
# Verificar la URL dentro del contenedor
docker exec svc-elicitation-ai printenv | grep OLLAMA

# Debe mostrar: OLLAMA_BASE_URL=http://ollama:11434
# Si muestra localhost:11434, hay que editar docker-compose.yml
```

---

### **❌ Error: "422 Unprocessable Entity" en `/start`**

**Síntoma:** Error de validación al iniciar entrevista

**Causa:** Los IDs deben ser strings, no números

**Solución:**
```bash
# ❌ Incorrecto:
{"organization_id": 1, "role_id": 1}

# ✅ Correcto:
{"organization_id": "1", "role_id": "1"}
```

---

### **❌ Error: "Module 'openai' not found"**

**Síntoma:** ImportError al iniciar el servicio

**Solución:**
```bash
# Con Docker (rebuild)
docker-compose up -d --build

# Sin Docker
pip install openai>=1.0.0
```

---

### **❌ Error: "OpenAI API key not set"**

**Síntoma:** AuthenticationError al usar OpenAI

**Soluciones:**

1. **Con Docker:**
```bash
# Editar docker-compose.yml, línea ~42:
- OPENAI_API_KEY=sk-proj-TU_KEY_AQUI

# Recrear contenedor
docker-compose up -d --force-recreate elicitation-ai
```

2. **Sin Docker (Windows PowerShell):**
```powershell
$env:OPENAI_API_KEY="sk-proj-XXXXX"
uvicorn app.main:app --reload --port 8001
```

3. **Sin Docker (Linux/Mac):**
```bash
export OPENAI_API_KEY="sk-proj-XXXXX"
uvicorn app.main:app --reload --port 8001
```

---

### **⚠️ Problema: Respuestas MUY lentas con Ollama**

**Causa:** Modelo muy grande para tu CPU (sin GPU)

**Soluciones:**

1. **Usar modelo más pequeño:**
```bash
# Cambiar a modelo 3B (más rápido, menor calidad)
docker exec ollama-service ollama pull llama3.2:3b

# Editar docker-compose.yml:
# - OLLAMA_MODEL=llama3.2:3b
```

2. **Cambiar a OpenAI (más rápido pero de pago):**
```bash
# Ver sección "Cambiar de Ollama a OpenAI"
```

---

### **⚠️ Problema: "Interview completed" pero sigue preguntando**

**Causa:** Bug en lógica de terminación (resuelto en v1.0.0)

**Solución:**
```bash
# Actualizar código
git pull origin main

# Rebuild servicios
docker-compose up -d --build
```

---

### **⚠️ Problema: Contenedor "unhealthy"**

**Síntoma:** `docker ps` muestra status "unhealthy"

**Solución:**
```bash
# Ver logs del contenedor
docker logs svc-elicitation-ai --tail 50

# Causas comunes:
# 1. Puerto 8001 ya en uso -> cambiar en docker-compose.yml
# 2. Ollama no disponible -> verificar ollama-service
# 3. Dependencias faltantes -> docker-compose up -d --build
```

---

### **⚠️ Problema: PC lenta / Docker consume mucha RAM**

**Causa:** Ollama + modelo cargado en memoria (~4-6GB RAM)

**Soluciones:**

1. **Detener Ollama cuando no lo uses:**
```bash
docker-compose stop ollama
```

2. **Usar OpenAI en lugar de Ollama local**

3. **Aumentar RAM de Docker Desktop:**
   - Docker Desktop → Settings → Resources → Memory → Aumentar a 6GB+

---

## 📁 **Estructura del Proyecto**

```
svc-elicitation-ai/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Entry point FastAPI
│   ├── config.py               # Settings con Pydantic
│   ├── models/
│   │   ├── interview.py        # Pydantic models
│   │   └── responses.py        # API response schemas
│   ├── routers/
│   │   ├── health.py           # Health check endpoint
│   │   └── interviews.py       # Interview endpoints
│   └── services/
│       ├── agent_service.py    # Core interview agent
│       ├── context_service.py  # User context management
│       └── model_factory.py    # LLM factory (Ollama/OpenAI)
├── prompts/
│   └── system_prompts.py       # System prompts (ES/EN/PT)
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker image
├── docker-compose.yml          # Docker Compose config
├── env.example                 # Environment variables template
└── README.md                   # Este archivo
```

---

## 🛠️ **Variables de Entorno (Completas)**

| Variable | Descripción | Default | Requerido |
|----------|-------------|---------|-----------|
| `APP_ENV` | Entorno (development/production) | `development` | No |
| `APP_PORT` | Puerto del servicio | `8001` | No |
| `APP_HOST` | Host bind | `0.0.0.0` | No |
| `LOG_LEVEL` | Nivel de logs | `INFO` | No |
| `FRONTEND_URL` | URL del frontend (CORS) | `http://localhost:5173` | No |
| `BACKEND_PHP_URL` | URL del backend PHP | `http://localhost:8000/api/v1` | No |
| **`AUTH_SERVICE_URL`** | **URL del Auth Service (svc-users-python)** | `http://localhost:8000` | **Sí** |
| **`JWT_ISSUER`** | **Issuer esperado en tokens JWT** | `https://api.example.com` | **Sí** |
| **`JWT_AUDIENCE`** | **Audience esperado en tokens JWT** | `https://api.example.com` | **Sí** |
| `JWKS_CACHE_TTL` | Tiempo de cache de JWKS en segundos | `3600` (1 hora) | No |
| **`MODEL_PROVIDER`** | **Proveedor: `local` o `openai`** | `local` | **Sí** |
| `OPENAI_API_KEY` | API Key de OpenAI | - | Solo si `openai` |
| `OPENAI_MODEL` | Modelo de OpenAI | `gpt-4o` | No |
| `OLLAMA_BASE_URL` | URL de Ollama | `http://ollama:11434` (Docker)<br>`http://localhost:11434` (Local) | Solo si `local` |
| `OLLAMA_MODEL` | Modelo de Ollama | `llama3.2:3b` | No |
| `MIN_QUESTIONS` | Mínimo de preguntas | `7` | No |
| `MAX_QUESTIONS` | Máximo de preguntas | `20` | No |

**⚠️ Nota importante sobre `OLLAMA_BASE_URL`:**
- En Docker: usar `http://ollama:11434` (nombre del servicio)
- Sin Docker: usar `http://localhost:11434` (localhost)
- Si ves error "All connection attempts failed", verificá esta variable

---

## 🧪 **Testing**

```bash
# Test rápido (sin LLM)
curl -X POST http://localhost:8001/api/v1/interviews/test \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","organization_id":"org","role_id":1,"language":"es"}'

# Test completo (con LLM)
curl -X POST http://localhost:8001/api/v1/interviews/start \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user-123","organization_id":"org-456","role_id":1,"language":"es"}'
```

---

## 📊 **Stack Tecnológico**

- **Framework**: FastAPI 0.115.6
- **AI SDK**: Strands Agents >=1.0.0
- **LLM Local**: Ollama + Llama 3.2
- **LLM Cloud**: OpenAI GPT-4o
- **Language**: Python 3.11+
- **Config**: Pydantic Settings
- **HTTP Client**: httpx, requests
- **Containerization**: Docker + Docker Compose

---

## 🤝 **Integración con otros servicios**

Este microservicio es parte de un sistema mayor:

1. **Frontend (React)**: `web-frontend-react/`
   - Consume este servicio para el chat
   - Maneja la UI y persistencia en localStorage

2. **Backend PHP**: `svc-organizations-php/`
   - Provee contexto de usuarios/organizaciones
   - Persistirá entrevistas completadas (futuro)

3. **Análisis de Procesos** (Futuro):
   - Consumirá el endpoint `/export`
   - Extraerá procesos estructurados
   - Generará diagramas BPMN

---

## 📝 **Próximos Pasos**

- [ ] Implementar persistencia en PostgreSQL (actualmente solo localStorage)
- [ ] Agregar análisis de sentimientos
- [ ] Spell checking en español
- [ ] Soporte para más idiomas (FR, IT, DE)
- [ ] Métricas con Prometheus
- [ ] Tests automatizados (pytest)
- [ ] CI/CD pipeline

---

## 📄 **Licencia**

Este proyecto es parte de una tesis de grado.

---

## 👨‍💻 **Autor**

Desarrollado como parte del proyecto de tesis "Sistema de Elicitación de Requerimientos con IA".

---

## 🆘 **Soporte**

Si encontrás algún problema:
1. Verificá la sección **Troubleshooting**
2. Revisá los logs: `docker-compose logs -f elicitation-ai`
3. Consultá la documentación interactiva: http://localhost:8001/docs
4. Revisá las issues en el repositorio

---

## ❓ **Preguntas Frecuentes (FAQ)**

### **1. ¿Necesito instalar Ollama en mi máquina?**

**Con Docker (recomendado):** ❌ NO
- Ollama corre dentro de un contenedor Docker
- El modelo se descarga dentro del contenedor
- Todo está aislado, no "ensucia" tu máquina

**Sin Docker (setup manual):** ✅ SÍ
- Necesitás instalar Ollama desde https://ollama.com/download
- El modelo se descarga en tu máquina (~2GB)

---

### **2. ¿Necesito instalar Python?**

**Con Docker:** ❌ NO
- Python y todas las dependencias están en el contenedor

**Sin Docker:** ✅ SÍ
- Python 3.11+
- pip
- requirements.txt

---

### **3. ¿Cuánto espacio ocupa todo?**

**Docker:**
- Imagen de Python: ~500 MB
- Imagen de Ollama: ~500 MB
- Modelo Llama 3.2 3B: ~2 GB
- **Total: ~3 GB**

---

### **4. ¿Puedo usar esto sin internet?**

**Con Ollama (local):** ✅ SÍ
- Una vez descargado el modelo, funciona 100% offline

**Con OpenAI:** ❌ NO
- Necesita conexión a internet siempre

---

### **5. ¿Es gratis?**

**Ollama:** ✅ 100% gratis, sin límites

**OpenAI:** ❌ ~$0.01 por entrevista (requiere API key de pago)

---

### **6. ¿Qué pasa si apago la PC?**

- Los contenedores se detienen
- Al hacer `docker-compose up -d` de nuevo, todo vuelve como estaba
- **El modelo NO se borra**, queda guardado en un volumen de Docker

---

### **7. ¿Cómo borro todo?**

```bash
# Borrar contenedores y el modelo descargado
docker-compose down -v

# Borrar también las imágenes (libera ~3GB)
docker rmi svc-elicitation-ai-elicitation-ai ollama/ollama
```

---

## 📝 **Comandos más usados (Cheat Sheet)**

```bash
# 🚀 INICIO RÁPIDO
docker-compose up -d                                    # Levantar servicios
docker exec ollama-service ollama pull llama3.2:3b     # Descargar modelo (solo 1ra vez)
curl http://localhost:8001/api/v1/health               # Verificar que funciona

# 🔐 AUTENTICACIÓN
# PowerShell - Obtener token:
$loginBody = @{ email = 'admin@example.com'; password = 'admin123' } | ConvertTo-Json
$response = Invoke-RestMethod -Uri http://localhost:8000/api/v1/auth/login -Method Post -Body $loginBody -ContentType 'application/json'
$token = $response.data.access_token

# Linux/Mac - Obtener token:
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"admin123"}' \
  | jq -r '.data.access_token')

# Verificar JWKS endpoint:
curl http://localhost:8000/api/v1/auth/jwks

# 📊 MONITOREO
docker ps                                               # Ver contenedores corriendo
docker-compose logs -f                                  # Ver logs en vivo
docker stats                                            # Ver uso de recursos (RAM/CPU)

# 🔄 GESTIÓN
docker-compose restart elicitation-ai                   # Reiniciar AI service
docker-compose down                                     # Detener todo
docker-compose up -d --build                            # Rebuild y reiniciar

# 🔍 DEBUG
docker exec ollama-service ollama list                  # Ver modelos instalados
docker exec svc-elicitation-ai printenv | grep MODEL   # Ver config del modelo
docker exec svc-elicitation-ai printenv | grep AUTH    # Ver config de autenticación
docker logs svc-elicitation-ai --tail 50               # Ver últimos 50 logs
docker logs svc-users-python --tail 50                 # Ver logs del Auth Service

# 🧪 TESTING
# PowerShell (con autenticación):
Invoke-RestMethod http://localhost:8001/api/v1/health
$headers = @{ Authorization = "Bearer $token" }
$body = @{ language = 'es' } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8001/api/v1/interviews/start -Method Post -Headers $headers -Body $body -ContentType 'application/json'

# Linux/Mac/Git Bash (con autenticación):
curl http://localhost:8001/api/v1/health
curl -X POST http://localhost:8001/api/v1/interviews/start \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"language":"es"}'
```

---

**¡Listo para empezar! 🚀**
