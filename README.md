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

**Request:**
```json
POST /api/v1/interviews/start
Content-Type: application/json

{
  "language": "es",              // "es" | "en" | "pt"
  "organization_id": "1",         // String (ID de organización)
  "role_id": "1"                  // String (ID del rol del usuario)
}
```

**Ejemplo con PowerShell:**
```powershell
$body = @{ 
  language = 'es'
  organization_id = '1'
  role_id = '1' 
} | ConvertTo-Json

Invoke-RestMethod -Uri http://localhost:8001/api/v1/interviews/start `
  -Method Post -Body $body -ContentType 'application/json'
```

**Ejemplo con cURL:**
```bash
curl -X POST http://localhost:8001/api/v1/interviews/start \
  -H "Content-Type: application/json" \
  -d '{"language":"es","organization_id":"1","role_id":"1"}'
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
    "is_final": false,
    "context": {}
  },
  "errors": [],
  "meta": {
    "user_name": "Juan Pérez",
    "organization": "ProssX Demo"
  }
}
```

#### **3. Continuar Entrevista**
**Descripción:** Envía la respuesta del usuario y recibe la siguiente pregunta.

**Request:**
```json
POST /api/v1/interviews/continue
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
$body = @{ 
  session_id = '1add3c4a-8730-4140-888b-59ac47fcac43'
  user_response = 'Soy gerente de operaciones, coordino equipos y apruebo compras'
  conversation_history = @()
  language = 'es'
} | ConvertTo-Json -Depth 3

Invoke-RestMethod -Uri http://localhost:8001/api/v1/interviews/continue `
  -Method Post -Body $body -ContentType 'application/json'
```

**Ejemplo con cURL:**
```bash
curl -X POST http://localhost:8001/api/v1/interviews/continue \
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
    "context": {},
    "corrected_response": "..."
  },
  "errors": [],
  "meta": {
    "session_id": "1add3c4a-8730-4140-888b-59ac47fcac43",
    "question_count": 2
  }
}
```

---

#### **4. Exportar Entrevista**
**Descripción:** Exporta los datos completos de la entrevista para análisis posterior.

**Request:**
```json
POST /api/v1/interviews/export
Content-Type: application/json

{
  "session_id": "1add3c4a-8730-4140-888b-59ac47fcac43"
}
```

**Ejemplo con PowerShell:**
```powershell
$body = @{ session_id = '1add3c4a-8730-4140-888b-59ac47fcac43' } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8001/api/v1/interviews/export `
  -Method Post -Body $body -ContentType 'application/json'
```

**Ejemplo con cURL:**
```bash
curl -X POST http://localhost:8001/api/v1/interviews/export \
  -H "Content-Type: application/json" \
  -d '{"session_id":"1add3c4a-8730-4140-888b-59ac47fcac43"}'
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "session_id": "uuid",
    "conversation": [
      {"role": "assistant", "content": "..."},
      {"role": "user", "content": "..."}
    ],
    "metadata": {
      "user_name": "Juan Pérez",
      "organization": "ProssX Demo",
      "start_time": "2025-10-05T10:30:00Z",
      "duration_minutes": 15
    }
  }
}
```

**⚠️ Nota:** Este endpoint retorna **solo los datos en crudo**. El análisis de procesos (extracción, estructuración, BPMN) es responsabilidad de otro microservicio que consumirá estos datos.

---

## 🔍 **Troubleshooting**

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
├── data/
│   └── mock_users.json         # Mock user data (MVP)
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
docker logs svc-elicitation-ai --tail 50               # Ver últimos 50 logs

# 🧪 TESTING
# PowerShell:
Invoke-RestMethod http://localhost:8001/api/v1/health
$body = @{ language = 'es'; organization_id = '1'; role_id = '1' } | ConvertTo-Json
Invoke-RestMethod -Uri http://localhost:8001/api/v1/interviews/start -Method Post -Body $body -ContentType 'application/json'

# Linux/Mac/Git Bash:
curl http://localhost:8001/api/v1/health
curl -X POST http://localhost:8001/api/v1/interviews/start -H "Content-Type: application/json" -d '{"language":"es","organization_id":"1","role_id":"1"}'
```

---

**¡Listo para empezar! 🚀**
