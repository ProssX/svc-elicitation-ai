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

## 🚀 **Setup Rápido**

### **Prerrequisitos**
- Python 3.11+
- pip
- **Opción A**: Ollama instalado (para modelo local)
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

---

## ⚙️ **Configuración**

### **Opción A: Modelo Local con Ollama** ⚡ (Recomendado para desarrollo)

**Ventajas:**
- ✅ Gratis, sin costos
- ✅ Privacidad total (los datos no salen de tu máquina)
- ✅ Sin límites de requests

**Desventajas:**
- ❌ Requiere GPU para buen rendimiento
- ❌ Calidad menor que GPT-4o

#### **Paso 1: Instalar Ollama**
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

## 🐳 **Docker**

### **Opción 1: docker-compose (Recomendado)**

#### **Con Ollama (Local)**
```bash
# 1. Asegurarse de que Ollama esté corriendo en host
ollama serve

# 2. Configurar .env
MODEL_PROVIDER=local

# 3. Levantar servicio
docker-compose up -d

# 4. Ver logs
docker-compose logs -f elicitation-ai
```

#### **Con OpenAI (Cloud)**
```bash
# 1. Configurar .env
MODEL_PROVIDER=openai
OPENAI_API_KEY=sk-proj-XXXXXXXX

# 2. Levantar servicio
docker-compose up -d

# 3. Ver logs
docker-compose logs -f elicitation-ai
```

### **Opción 2: Docker standalone**
```bash
# Build
docker build -t svc-elicitation-ai:latest .

# Run con Ollama
docker run -d \
  -p 8001:8001 \
  -e MODEL_PROVIDER=local \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  --name elicitation-ai \
  svc-elicitation-ai:latest

# Run con OpenAI
docker run -d \
  -p 8001:8001 \
  -e MODEL_PROVIDER=openai \
  -e OPENAI_API_KEY=sk-proj-XXXXXXXX \
  --name elicitation-ai \
  svc-elicitation-ai:latest
```

---

## 📡 **API Endpoints**

### **1. Health Check**
```bash
GET /api/v1/health

# Respuesta:
{
  "status": "healthy",
  "model_provider": "openai",
  "model_id": "gpt-4o"
}
```

### **2. Iniciar Entrevista**
```bash
POST /api/v1/interviews/start
Content-Type: application/json

{
  "user_id": "user-123",
  "organization_id": "org-456",
  "role_id": 1,
  "language": "es"
}

# Respuesta:
{
  "status": "success",
  "data": {
    "session_id": "uuid",
    "question": "Hola Juan! ¿Cómo andás? Soy el Agente ProssX...",
    "question_number": 1,
    "is_final": false,
    "context": {
      "processes_identified": [],
      "topics_discussed": [],
      "completeness": 0.0
    }
  }
}
```

### **3. Continuar Entrevista**
```bash
POST /api/v1/interviews/continue
Content-Type: application/json

{
  "session_id": "uuid",
  "user_response": "Soy analista de compras...",
  "conversation_history": [
    {"role": "assistant", "content": "..."},
    {"role": "user", "content": "..."}
  ],
  "language": "es"
}
```

### **4. Exportar Entrevista**
```bash
POST /api/v1/interviews/export
Content-Type: application/json

{
  "session_id": "uuid"
}

# Retorna:
# - Conversación completa
# - Metadata del usuario
# - Métricas (duración, completeness, etc.)
# - NO incluye análisis de procesos (eso es responsabilidad de otro servicio)
```

---

## 🔍 **Troubleshooting**

### **Problema: "Module 'openai' not found"**
```bash
# Solución: Instalar openai
pip install openai>=1.0.0
```

### **Problema: "OpenAI API key not set"**
```bash
# Solución 1: Verificar .env
cat .env | grep OPENAI_API_KEY

# Solución 2: Exportar manualmente
export OPENAI_API_KEY="sk-proj-XXXXX"
```

### **Problema: "Cannot connect to Ollama"**
```bash
# Solución 1: Verificar que Ollama esté corriendo
curl http://localhost:11434/api/tags

# Solución 2: Iniciar Ollama
ollama serve

# Solución 3: Verificar modelo descargado
ollama list
```

### **Problema: Respuestas lentas con Ollama**
```bash
# Causa: Modelo muy grande para tu hardware
# Solución: Usar modelo más pequeño
ollama pull llama3.2:3b  # En vez de 8b o 70b
```

### **Problema: "Interview completed" pero sigue preguntando**
```bash
# Causa: Bug conocido (ya resuelto en última versión)
# Solución: Hacer git pull para obtener el fix
git pull origin main
```

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
| `OLLAMA_BASE_URL` | URL de Ollama | `http://localhost:11434` | Solo si `local` |
| `OLLAMA_MODEL` | Modelo de Ollama | `llama3.2:3b` | No |
| `MIN_QUESTIONS` | Mínimo de preguntas | `7` | No |
| `MAX_QUESTIONS` | Máximo de preguntas | `20` | No |

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

**¡Listo para empezar! 🚀**
