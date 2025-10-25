# Documento de Diseño - Persistencia de Entrevistas

## Overview

Este documento describe el diseño técnico para implementar persistencia de entrevistas en el microservicio `svc-elicitation-ai`. La solución migra el almacenamiento desde session/local storage del navegador hacia una base de datos PostgreSQL, siguiendo los patrones arquitectónicos establecidos en el ecosistema ProssX.

**Objetivos principales:**
- Persistir entrevistas y mensajes en PostgreSQL 17.6
- Mantener compatibilidad con la arquitectura stateless actual
- Seguir los patrones del microservicio `svc-organizations-php`
- Implementar CRUD completo con filtros y paginación
- Garantizar integridad referencial con la tabla `employee`

**Tecnologías seleccionadas:**
- **PostgreSQL 17.6-alpine**: Base de datos (misma versión que backend PHP)
- **SQLAlchemy 2.0**: ORM asíncrono para Python
- **Alembic**: Gestión de migraciones (equivalente a Doctrine Migrations)
- **asyncpg**: Driver PostgreSQL asíncrono de alto rendimiento
- **Pydantic**: Validación de datos y serialización

## Architecture

### Diagrama de Arquitectura General

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (React)                         │
│  - Chat UI con persistencia automática                     │
│  - Elimina dependencia de localStorage                     │
└────────────────┬────────────────────────────────────────────┘
                 │ HTTP/REST + JWT
                 │
┌────────────────▼────────────────────────────────────────────┐
│           svc-elicitation-ai (FastAPI)                      │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Routers (app/routers/)                             │   │
│  │  - interviews.py (CRUD + export)                    │   │
│  │  - health.py                                        │   │
│  └──────────────┬──────────────────────────────────────┘   │
│                 │                                           │
│  ┌──────────────▼──────────────────────────────────────┐   │
│  │  Services (app/services/)                           │   │
│  │  - agent_service.py (lógica de entrevista)          │   │
│  │  - interview_service.py (NEW - persistencia)        │   │
│  │  - context_service.py                               │   │
│  └──────────────┬──────────────────────────────────────┘   │
│                 │                                           │
│  ┌──────────────▼──────────────────────────────────────┐   │
│  │  Repositories (app/repositories/) NEW               │   │
│  │  - interview_repository.py                          │   │
│  │  - message_repository.py                            │   │
│  └──────────────┬──────────────────────────────────────┘   │
│                 │                                           │
│  ┌──────────────▼──────────────────────────────────────┐   │
│  │  Models (app/models/)                               │   │
│  │  - interview.py (Pydantic - API)                    │   │
│  │  - db_models.py (NEW - SQLAlchemy)                  │   │
│  └──────────────┬──────────────────────────────────────┘   │
│                 │                                           │
│  ┌──────────────▼──────────────────────────────────────┐   │
│  │  Database (app/database.py) NEW                     │   │
│  │  - Connection pool                                  │   │
│  │  - Session management                               │   │
│  └──────────────┬──────────────────────────────────────┘   │
└─────────────────┼───────────────────────────────────────────┘
                  │
                  │
┌─────────────────▼───────────────────────────────────────────┐
│              PostgreSQL 17.6-alpine                         │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Tables                                             │   │
│  │  - interview (entrevistas)                          │   │
│  │  - interview_message (preguntas y respuestas)       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  External References                                │   │
│  │  - employee (desde svc-organizations-php)           │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Flujo de Datos

**1. Inicio de Entrevista (POST /api/v1/interviews/start):**
```
Frontend → Router → AgentService (genera pregunta) → InterviewService (crea Interview + Message) → DB
                                                    ↓
Frontend ← Router ← InterviewService (retorna interview_id + question)
```

**2. Continuar Entrevista (POST /api/v1/interviews/continue):**
```
Frontend → Router → InterviewService (valida interview_id + guarda respuesta user)
                                    ↓
                    AgentService (genera siguiente pregunta)
                                    ↓
                    InterviewService (guarda pregunta agent) → DB
                                    ↓
Frontend ← Router ← InterviewService (retorna question + question_number)
```

**3. Consultar Entrevista (GET /api/v1/interviews/{id}):**
```
Frontend → Router → InterviewService → InterviewRepository → DB
                                                            ↓
Frontend ← Router ← InterviewService (retorna Interview + Messages ordenados)
```

## Components and Interfaces

### 1. Database Models (app/models/db_models.py)

**Interview Model:**
```python
from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime

class Interview(Base):
    __tablename__ = "interview"
    
    # Primary Key
    id_interview = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid7)
    
    # Foreign Key to Employee (svc-organizations-php)
    employee_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Metadata
    language = Column(String(2), nullable=False)  # 'es', 'en', 'pt'
    technical_level = Column(String(20), nullable=False, default='unknown')
    status = Column(Enum('in_progress', 'completed', 'cancelled'), default='in_progress')
    
    # Timestamps
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    messages = relationship("InterviewMessage", back_populates="interview", cascade="all, delete-orphan")
```

**InterviewMessage Model:**
```python
class InterviewMessage(Base):
    __tablename__ = "interview_message"
    
    # Primary Key
    id_message = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid7)
    
    # Foreign Key to Interview
    interview_id = Column(UUID(as_uuid=True), ForeignKey('interview.id_interview', ondelete='CASCADE'), nullable=False)
    
    # Message Data
    role = Column(Enum('assistant', 'user', 'system'), nullable=False)
    content = Column(String, nullable=False)
    sequence_number = Column(Integer, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    interview = relationship("Interview", back_populates="messages")
    
    # Constraints
    __table_args__ = (
        Index('idx_interview_sequence', 'interview_id', 'sequence_number'),
    )
```

### 2. Pydantic Models (app/models/interview.py - ACTUALIZAR)

**InterviewCreate (Request):**
```python
class InterviewCreate(BaseModel):
    language: str = Field(default="es", pattern="^(es|en|pt)$")
    technical_level: str = Field(default="unknown")
```

**InterviewResponse (Response):**
```python
class InterviewResponse(BaseModel):
    id_interview: str
    employee_id: str
    language: str
    technical_level: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    total_messages: int
    
    class Config:
        from_attributes = True
```

**InterviewWithMessages (Response detallada):**
```python
class MessageResponse(BaseModel):
    id_message: str
    role: str
    content: str
    sequence_number: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class InterviewWithMessages(InterviewResponse):
    messages: List[MessageResponse] = []
```

### 3. Repository Layer (app/repositories/)

**InterviewRepository:**
```python
class InterviewRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, interview: Interview) -> Interview:
        """Crear nueva entrevista"""
        
    async def get_by_id(self, interview_id: UUID, employee_id: UUID) -> Optional[Interview]:
        """Obtener entrevista por ID (validando employee_id)"""
        
    async def get_by_employee(
        self, 
        employee_id: UUID, 
        status: Optional[str] = None,
        language: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Interview], int]:
        """Listar entrevistas con filtros y paginación"""
        
    async def update_status(self, interview_id: UUID, status: str) -> Interview:
        """Actualizar estado de entrevista"""
        
    async def mark_completed(self, interview_id: UUID) -> Interview:
        """Marcar entrevista como completada"""
```

**MessageRepository:**
```python
class MessageRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, message: InterviewMessage) -> InterviewMessage:
        """Crear nuevo mensaje"""
        
    async def get_by_interview(self, interview_id: UUID) -> List[InterviewMessage]:
        """Obtener todos los mensajes de una entrevista ordenados por sequence_number"""
        
    async def get_last_sequence(self, interview_id: UUID) -> int:
        """Obtener el último sequence_number de una entrevista"""
        
    async def count_by_interview(self, interview_id: UUID) -> int:
        """Contar mensajes de una entrevista"""
```

### 4. Service Layer (app/services/interview_service.py - NEW)

```python
class InterviewService:
    def __init__(self, db: AsyncSession):
        self.interview_repo = InterviewRepository(db)
        self.message_repo = MessageRepository(db)
    
    async def start_interview(
        self,
        employee_id: UUID,
        language: str,
        technical_level: str,
        first_question: str
    ) -> Tuple[Interview, InterviewMessage]:
        """
        Crear nueva entrevista y guardar primera pregunta del agente
        """
        
    async def continue_interview(
        self,
        interview_id: UUID,
        employee_id: UUID,
        user_response: str,
        agent_question: str,
        is_final: bool = False
    ) -> Tuple[Interview, InterviewMessage, InterviewMessage]:
        """
        Guardar respuesta del usuario y siguiente pregunta del agente
        Retorna: (interview, user_message, agent_message)
        """
        
    async def get_interview(
        self,
        interview_id: UUID,
        employee_id: UUID
    ) -> Optional[InterviewWithMessages]:
        """Obtener entrevista completa con mensajes"""
        
    async def list_interviews(
        self,
        employee_id: UUID,
        filters: InterviewFilters,
        pagination: PaginationParams
    ) -> Tuple[List[InterviewResponse], PaginationMeta]:
        """Listar entrevistas con filtros y paginación"""
        
    async def migrate_from_localstorage(
        self,
        employee_id: UUID,
        session_id: str,
        conversation_history: List[ConversationMessage],
        language: str
    ) -> Interview:
        """Migrar entrevista desde localStorage"""
```

### 5. Router Updates (app/routers/interviews.py - MODIFICAR)

**Cambios principales:**
- Inyectar `db: AsyncSession` en cada endpoint
- Llamar a `InterviewService` para persistir datos
- Mantener compatibilidad con lógica actual de `AgentService`

**Ejemplo - POST /start:**
```python
@router.post("/start")
async def start_interview(
    request: StartInterviewRequest,
    current_user: TokenPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Obtener contexto del usuario
    context_service = get_context_service()
    user_context = await context_service.get_user_context(current_user.user_id)
    
    # 2. Generar primera pregunta con AgentService (lógica actual)
    agent = get_agent()
    interview_response = agent.start_interview(
        user_name=user_context.get("name"),
        user_role=user_context.get("role"),
        organization=user_context.get("organization"),
        technical_level=user_context.get("technical_level", "unknown"),
        language=request.language
    )
    
    # 3. Persistir en DB (NUEVO)
    interview_service = InterviewService(db)
    interview, first_message = await interview_service.start_interview(
        employee_id=UUID(current_user.user_id),
        language=request.language,
        technical_level=user_context.get("technical_level", "unknown"),
        first_question=interview_response.question
    )
    
    # 4. Retornar respuesta
    return success_response(
        data={
            "interview_id": str(interview.id_interview),  # NUEVO
            "question": interview_response.question,
            "question_number": 1,
            "is_final": False
        },
        message="Interview started successfully"
    )
```

## Data Models

### Database Schema (PostgreSQL)

**Tabla: interview**
```sql
CREATE TABLE interview (
    id_interview UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    employee_id UUID NOT NULL,
    language VARCHAR(2) NOT NULL CHECK (language IN ('es', 'en', 'pt')),
    technical_level VARCHAR(20) NOT NULL DEFAULT 'unknown',
    status VARCHAR(20) NOT NULL DEFAULT 'in_progress' 
        CHECK (status IN ('in_progress', 'completed', 'cancelled')),
    started_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_employee_id (employee_id),
    INDEX idx_status (status),
    INDEX idx_started_at (started_at)
);
```

**Tabla: interview_message**
```sql
CREATE TABLE interview_message (
    id_message UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    interview_id UUID NOT NULL REFERENCES interview(id_interview) ON DELETE CASCADE,
    role VARCHAR(10) NOT NULL CHECK (role IN ('assistant', 'user', 'system')),
    content TEXT NOT NULL,
    sequence_number INTEGER NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Indexes
    INDEX idx_interview_sequence (interview_id, sequence_number),
    
    -- Constraints
    UNIQUE (interview_id, sequence_number)
);
```

### Relaciones entre Tablas

```
┌─────────────────────────────────────────────────────────────┐
│  svc-organizations-php (PostgreSQL)                         │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  employee                                            │  │
│  │  - id_employee (UUID, PK)                            │  │
│  │  - organization_id (UUID, FK)                        │  │
│  │  - first_name, last_name                             │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                          │
                          │ (Referencia lógica, NO FK física)
                          │
┌─────────────────────────▼───────────────────────────────────┐
│  svc-elicitation-ai (PostgreSQL)                            │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  interview                                           │  │
│  │  - id_interview (UUID, PK)                           │  │
│  │  - employee_id (UUID, indexed)  ◄────┐              │  │
│  │  - language, status, timestamps       │              │  │
│  └──────────────────────────────────────┼──────────────┘  │
│                                          │                  │
│                                          │ 1:N              │
│                                          │                  │
│  ┌──────────────────────────────────────▼──────────────┐  │
│  │  interview_message                                   │  │
│  │  - id_message (UUID, PK)                             │  │
│  │  - interview_id (UUID, FK CASCADE)                   │  │
│  │  - role, content, sequence_number                    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Decisión de diseño: NO usar FK física a `employee`**

**Razones:**
1. Las tablas están en **bases de datos diferentes** (microservicios separados)
2. PostgreSQL no soporta FK entre bases de datos distintas
3. Mantiene **independencia entre microservicios**
4. La validación de `employee_id` se hace a nivel de aplicación

**Validación en código:**
```python
# En InterviewService.start_interview()
context_service = get_context_service()
user_context = await context_service.get_user_context(employee_id)
if not user_context:
    raise HTTPException(status_code=404, detail="Employee not found")
```

## Error Handling

### Estrategia de Manejo de Errores

**1. Errores de Validación (400 Bad Request):**
```python
# Ejemplo: Idioma inválido
{
    "status": "error",
    "code": 400,
    "message": "Validation error",
    "errors": [
        {
            "field": "language",
            "error": "Language must be one of: es, en, pt"
        }
    ]
}
```

**2. Errores de Autenticación (401 Unauthorized):**
```python
# Token inválido o expirado
{
    "status": "error",
    "code": 401,
    "message": "Authentication required",
    "errors": [
        {
            "field": "authorization",
            "error": "Invalid or expired token"
        }
    ]
}
```

**3. Errores de Autorización (403 Forbidden):**
```python
# Intentar acceder a entrevista de otro empleado
{
    "status": "error",
    "code": 403,
    "message": "Access denied",
    "errors": [
        {
            "field": "interview_id",
            "error": "You don't have permission to access this interview"
        }
    ]
}
```

**4. Errores de Recurso No Encontrado (404 Not Found):**
```python
# Entrevista inexistente
{
    "status": "error",
    "code": 404,
    "message": "Interview not found",
    "errors": [
        {
            "field": "interview_id",
            "error": "Interview with ID xxx does not exist"
        }
    ]
}
```

**5. Errores de Conflicto (409 Conflict):**
```python
# Intentar migrar entrevista duplicada
{
    "status": "error",
    "code": 409,
    "message": "Interview already exists",
    "errors": [
        {
            "field": "session_id",
            "error": "An interview with this session_id already exists"
        }
    ]
}
```

**6. Errores de Base de Datos (500 Internal Server Error):**
```python
# Error de conexión o query
{
    "status": "error",
    "code": 500,
    "message": "Database error occurred",
    "errors": [
        {
            "field": "database",
            "error": "Unable to process request. Please try again later."
        }
    ]
}
```

### Exception Handlers

```python
# app/exceptions.py (NEW)

class InterviewNotFoundError(Exception):
    """Entrevista no encontrada"""
    pass

class InterviewAccessDeniedError(Exception):
    """Acceso denegado a entrevista"""
    pass

class InterviewAlreadyExistsError(Exception):
    """Entrevista duplicada"""
    pass

class DatabaseConnectionError(Exception):
    """Error de conexión a base de datos"""
    pass

# app/main.py - Registrar handlers

@app.exception_handler(InterviewNotFoundError)
async def interview_not_found_handler(request: Request, exc: InterviewNotFoundError):
    return JSONResponse(
        status_code=404,
        content=error_response(
            message="Interview not found",
            code=404,
            errors=[{"field": "interview_id", "error": str(exc)}]
        ).model_dump()
    )
```

## Testing Strategy

### 1. Unit Tests

**Repositories (tests/unit/repositories/):**
- `test_interview_repository.py`
  - ✅ Crear entrevista con UUID v7
  - ✅ Obtener entrevista por ID
  - ✅ Listar entrevistas con filtros
  - ✅ Actualizar estado
  - ✅ Validar employee_id en queries

- `test_message_repository.py`
  - ✅ Crear mensaje con sequence_number
  - ✅ Obtener mensajes ordenados
  - ✅ Cascade delete al eliminar entrevista

**Services (tests/unit/services/):**
- `test_interview_service.py`
  - ✅ start_interview crea Interview + Message
  - ✅ continue_interview guarda user + agent messages
  - ✅ get_interview retorna datos completos
  - ✅ list_interviews aplica filtros correctamente
  - ✅ migrate_from_localstorage valida duplicados

**Models (tests/unit/models/):**
- `test_db_models.py`
  - ✅ Validación de enums (language, status, role)
  - ✅ Timestamps automáticos
  - ✅ Relaciones bidireccionales

### 2. Integration Tests

**Database (tests/integration/database/):**
- `test_database_connection.py`
  - ✅ Conexión exitosa a PostgreSQL
  - ✅ Pool de conexiones funciona
  - ✅ Reintentos en caso de fallo

**Repositories (tests/integration/repositories/):**
- `test_interview_repository_integration.py`
  - ✅ CRUD completo contra DB real
  - ✅ Transacciones y rollback
  - ✅ Índices mejoran performance

### 3. Functional Tests (E2E)

**API Endpoints (tests/functional/):**
- `test_interview_api.py`
  - ✅ POST /start crea entrevista en DB
  - ✅ POST /continue persiste mensajes
  - ✅ GET /interviews/{id} retorna datos correctos
  - ✅ GET /interviews lista con paginación
  - ✅ POST /migrate importa desde localStorage
  - ✅ Validación de JWT en todos los endpoints
  - ✅ Errores 403 al acceder a entrevista ajena

### 4. Performance Tests

**Load Testing (tests/performance/):**
- `test_concurrent_interviews.py`
  - ✅ 100 entrevistas simultáneas
  - ✅ Tiempo de respuesta < 500ms (p95)
  - ✅ Pool de conexiones no se agota

### Test Coverage Goal

- **Mínimo aceptable:** 80%
- **Objetivo:** 90%
- **Crítico (100%):** Repositories, Services, Error Handlers

## Configuration

### Environment Variables

```bash
# Database Configuration (NEW)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/elicitation_ai
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600

# Existing variables
AUTH_SERVICE_URL=http://localhost:8000
BACKEND_PHP_URL=http://localhost:8000/api/v1
MODEL_PROVIDER=local
OLLAMA_BASE_URL=http://ollama:11434
```

### Database Connection (app/database.py - NEW)

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings

# Engine con pool de conexiones
engine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    pool_recycle=settings.db_pool_recycle,
    echo=settings.app_env == "development"
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

# Dependency para FastAPI
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

### Alembic Configuration

**alembic.ini:**
```ini
[alembic]
script_location = alembic
sqlalchemy.url = postgresql+asyncpg://user:password@localhost:5432/elicitation_ai

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic
```

**alembic/env.py:**
```python
from app.models.db_models import Base
from app.config import settings

target_metadata = Base.metadata

def run_migrations_online():
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = settings.database_url
    # ... resto de configuración
```

## Migration Plan

### Fase 1: Setup Inicial (Sin impacto en producción)

1. Agregar dependencias a `requirements.txt`
2. Crear estructura de carpetas
3. Configurar Alembic
4. Crear modelos SQLAlchemy
5. Generar migración inicial

### Fase 2: Implementación Core (Desarrollo)

1. Implementar Repositories
2. Implementar InterviewService
3. Escribir unit tests
4. Escribir integration tests

### Fase 3: Integración con API (Desarrollo)

1. Modificar routers para usar InterviewService
2. Mantener compatibilidad con lógica actual
3. Agregar endpoint de migración
4. Escribir functional tests

### Fase 4: Despliegue Gradual (Producción)

1. **Modo híbrido:** Frontend sigue usando localStorage + llama a endpoint de migración
2. **Validación:** Comparar datos localStorage vs DB
3. **Switchover:** Frontend deja de usar localStorage
4. **Cleanup:** Remover código de migración después de 30 días

## Design Decisions

### 1. ¿Por qué NO usar FK física a `employee`?

**Decisión:** Usar referencia lógica (UUID) sin constraint de FK

**Razones:**
- Microservicios en bases de datos separadas
- PostgreSQL no soporta FK cross-database
- Mantiene independencia entre servicios
- Validación a nivel de aplicación es suficiente

**Trade-offs:**
- ❌ No hay integridad referencial automática
- ✅ Microservicios desacoplados
- ✅ Cada servicio puede escalar independientemente

### 2. ¿Por qué SQLAlchemy async en lugar de sync?

**Decisión:** Usar SQLAlchemy 2.0 con asyncio

**Razones:**
- FastAPI es asíncrono por naturaleza
- Mejor performance con I/O concurrente
- No bloquea el event loop
- Preparado para alto tráfico

**Trade-offs:**
- ✅ Mejor throughput
- ✅ Menor latencia
- ❌ Código más complejo (async/await)

### 3. ¿Por qué separar Interview y InterviewMessage?

**Decisión:** Dos tablas normalizadas

**Razones:**
- Normalización 3NF
- Facilita queries de mensajes individuales
- Permite agregar metadata a cada mensaje
- Mejor para análisis de conversaciones

**Alternativa descartada:** JSON column con todos los mensajes
- ❌ Dificulta queries
- ❌ No aprovecha índices
- ❌ Límite de tamaño

### 4. ¿Por qué UUID v7 en lugar de UUID v4?

**Decisión:** Usar UUID v7 (timestamp-based)

**Razones:**
- Ordenamiento natural por tiempo de creación
- Mejor performance en índices B-tree
- Compatible con UUID v4 (mismo tamaño)
- Estándar moderno (RFC 9562)

**Comparación:**
- UUID v4: `550e8400-e29b-41d4-a716-446655440000` (random)
- UUID v7: `018e5f8b-2a78-7890-b123-456789abcdef` (timestamp prefix)

### 5. ¿Por qué mantener stateless en el backend?

**Decisión:** Backend sigue siendo stateless, DB es solo persistencia

**Razones:**
- Facilita escalado horizontal
- No requiere sticky sessions
- Cualquier instancia puede manejar cualquier request
- Simplifica deployment

**Implicación:**
- Frontend debe enviar `interview_id` en cada request
- No hay sesiones en memoria

## Diagrams

### Sequence Diagram - Start Interview

```mermaid
sequenceDiagram
    participant F as Frontend
    participant R as Router
    participant A as AgentService
    participant IS as InterviewService
    participant DB as PostgreSQL

    F->>R: POST /start (JWT + language)
    R->>A: start_interview()
    A-->>R: first_question
    R->>IS: start_interview(employee_id, language, question)
    IS->>DB: INSERT INTO interview
    IS->>DB: INSERT INTO interview_message (assistant)
    DB-->>IS: interview + message
    IS-->>R: interview_id, question
    R-->>F: {interview_id, question, question_number: 1}
```

### Sequence Diagram - Continue Interview

```mermaid
sequenceDiagram
    participant F as Frontend
    participant R as Router
    participant IS as InterviewService
    participant A as AgentService
    participant DB as PostgreSQL

    F->>R: POST /continue (interview_id, user_response)
    R->>IS: continue_interview(interview_id, user_response)
    IS->>DB: INSERT INTO interview_message (user)
    IS->>A: generate_next_question(conversation_history)
    A-->>IS: next_question
    IS->>DB: INSERT INTO interview_message (assistant)
    IS->>DB: UPDATE interview SET updated_at
    DB-->>IS: messages
    IS-->>R: question, question_number
    R-->>F: {question, question_number, is_final}
```

## Summary

Este diseño implementa persistencia de entrevistas siguiendo los patrones establecidos en el ecosistema ProssX:

**✅ Alineado con svc-organizations-php:**
- Misma versión de PostgreSQL (17.6-alpine)
- Patrón Repository similar
- UUID v7 para IDs
- Timestamps automáticos
- Formato de respuesta estándar

**✅ Mantiene arquitectura actual:**
- Backend stateless
- AgentService sin cambios
- JWT authentication
- Multi-idioma

**✅ Escalable y mantenible:**
- Modelo normalizado
- Índices optimizados
- Migraciones versionadas
- Tests comprehensivos

**✅ Migración sin downtime:**
- Endpoint de migración desde localStorage
- Modo híbrido durante transición
- Rollback plan incluido
