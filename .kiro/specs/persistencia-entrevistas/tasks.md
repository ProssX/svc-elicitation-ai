 # Plan de Implementación - Persistencia de Entrevistas

## Tareas de Implementación

- [x] 1. Configurar infraestructura de base de datos





  - Agregar dependencias de PostgreSQL y SQLAlchemy a `requirements.txt`
  - Configurar variables de entorno para conexión a base de datos
  - Crear módulo `app/database.py` con engine y session factory
  - Configurar Alembic para migraciones
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 1.1 Agregar dependencias a requirements.txt


  - Agregar `sqlalchemy[asyncio]>=2.0.0`
  - Agregar `asyncpg>=0.29.0`
  - Agregar `alembic>=1.13.0`
  - Agregar `greenlet>=3.0.0` (requerido por SQLAlchemy async)
  - _Requirements: 7.1_

- [x] 1.2 Crear módulo de configuración de base de datos


  - Crear archivo `app/database.py`
  - Implementar `create_async_engine` con pool de conexiones
  - Implementar `AsyncSessionLocal` session factory
  - Implementar dependency `get_db()` para FastAPI
  - Agregar validación de conexión en startup
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 1.3 Actualizar configuración con variables de entorno


  - Agregar `DATABASE_URL` a `app/config.py`
  - Agregar `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`, `DB_POOL_RECYCLE`
  - Actualizar `.env.example` con nuevas variables
  - Validar formato de `DATABASE_URL` en startup
  - _Requirements: 7.1, 7.2_

- [x] 1.4 Configurar Alembic para migraciones


  - Ejecutar `alembic init alembic` para crear estructura
  - Configurar `alembic.ini` con `sqlalchemy.url`
  - Actualizar `alembic/env.py` para usar modelos SQLAlchemy
  - Configurar `target_metadata` apuntando a `Base.metadata`
  - _Requirements: 8.1, 8.2_

- [x] 2. Crear modelos de base de datos




  - Crear archivo `app/models/db_models.py` con modelos SQLAlchemy
  - Implementar modelo `Interview` con todos los campos y relaciones
  - Implementar modelo `InterviewMessage` con campos y constraints
  - Configurar índices para optimizar queries
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 2.1 Implementar modelo Interview


  - Crear clase `Interview(Base)` con `__tablename__ = "interview"`
  - Agregar campo `id_interview` (UUID v7, PK)
  - Agregar campo `employee_id` (UUID, indexed)
  - Agregar campos `language`, `technical_level`, `status`
  - Agregar timestamps `started_at`, `completed_at`, `created_at`, `updated_at`
  - Configurar relationship con `InterviewMessage`
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 2.2 Implementar modelo InterviewMessage

  - Crear clase `InterviewMessage(Base)` con `__tablename__ = "interview_message"`
  - Agregar campo `id_message` (UUID v7, PK)
  - Agregar campo `interview_id` (UUID, FK con CASCADE)
  - Agregar campos `role`, `content`, `sequence_number`
  - Agregar timestamp `created_at`
  - Configurar relationship con `Interview`
  - Agregar índice compuesto `(interview_id, sequence_number)`
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 3. Generar y aplicar migración inicial





  - Generar migración con `alembic revision --autogenerate -m "create_interview_tables"`
  - Revisar y ajustar script de migración generado
  - Implementar función `upgrade()` para crear tablas
  - Implementar función `downgrade()` para rollback
  - Aplicar migración con `alembic upgrade head`
  - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [x] 4. Actualizar modelos Pydantic para API





  - Actualizar `app/models/interview.py` con nuevos modelos
  - Crear `InterviewCreate` para request de creación
  - Crear `InterviewResponse` para response básica
  - Crear `MessageResponse` para mensajes individuales
  - Crear `InterviewWithMessages` para response detallada
  - Crear `InterviewFilters` para parámetros de filtrado
  - Crear `PaginationParams` y `PaginationMeta`
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 5. Implementar capa de repositorios





  - Crear directorio `app/repositories/`
  - Implementar `InterviewRepository` con métodos CRUD
  - Implementar `MessageRepository` con métodos CRUD
  - Agregar manejo de transacciones y errores
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 5.1 Implementar InterviewRepository


  - Crear archivo `app/repositories/interview_repository.py`
  - Implementar método `create(interview: Interview) -> Interview`
  - Implementar método `get_by_id(interview_id: UUID, employee_id: UUID) -> Optional[Interview]`
  - Implementar método `get_by_employee()` con filtros y paginación
  - Implementar método `update_status(interview_id: UUID, status: str) -> Interview`
  - Implementar método `mark_completed(interview_id: UUID) -> Interview`
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 5.2 Implementar MessageRepository


  - Crear archivo `app/repositories/message_repository.py`
  - Implementar método `create(message: InterviewMessage) -> InterviewMessage`
  - Implementar método `get_by_interview(interview_id: UUID) -> List[InterviewMessage]`
  - Implementar método `get_last_sequence(interview_id: UUID) -> int`
  - Implementar método `count_by_interview(interview_id: UUID) -> int`
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 6. Implementar capa de servicios





  - Crear archivo `app/services/interview_service.py`
  - Implementar `InterviewService` con lógica de negocio
  - Integrar con `InterviewRepository` y `MessageRepository`
  - Implementar validaciones y manejo de errores
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 5.4, 5.5_


- [x] 6.1 Implementar método start_interview

  - Crear método `start_interview(employee_id, language, technical_level, first_question)`
  - Validar que employee_id exista llamando a `context_service`
  - Crear registro de `Interview` en DB
  - Crear primer mensaje (assistant) en DB
  - Retornar tupla `(Interview, InterviewMessage)`
  - _Requirements: 3.1, 4.1, 4.2, 10.2, 10.5_


- [x] 6.2 Implementar método continue_interview

  - Crear método `continue_interview(interview_id, employee_id, user_response, agent_question, is_final)`
  - Validar que interview pertenezca a employee_id
  - Obtener último sequence_number
  - Crear mensaje de usuario (sequence_number + 1)
  - Crear mensaje de agente (sequence_number + 2)
  - Actualizar `updated_at` de interview
  - Si `is_final=True`, marcar interview como completed
  - Retornar tupla `(Interview, user_message, agent_message)`
  - _Requirements: 3.2, 4.1, 4.2, 4.3, 4.4, 4.5, 10.5_



- [x] 6.3 Implementar método get_interview

  - Crear método `get_interview(interview_id, employee_id)`
  - Validar que interview pertenezca a employee_id
  - Obtener interview con mensajes ordenados por sequence_number
  - Retornar `InterviewWithMessages`
  - _Requirements: 3.2, 10.5_

- [x] 6.4 Implementar método list_interviews

  - Crear método `list_interviews(employee_id, filters, pagination)`
  - Aplicar filtros de status, language, start_date, end_date
  - Aplicar paginación con page y page_size
  - Calcular total_items y total_pages
  - Retornar tupla `(List[InterviewResponse], PaginationMeta)`
  - _Requirements: 3.3, 6.1, 6.2, 6.3, 6.4, 6.5_


- [x] 6.5 Implementar método migrate_from_localstorage

  - Crear método `migrate_from_localstorage(employee_id, session_id, conversation_history, language)`
  - Validar que no exista interview con mismo session_id
  - Crear registro de Interview
  - Iterar conversation_history y crear InterviewMessage para cada mensaje
  - Retornar Interview creada
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 7. Crear custom exceptions





  - Crear archivo `app/exceptions.py`
  - Implementar `InterviewNotFoundError`
  - Implementar `InterviewAccessDeniedError`
  - Implementar `InterviewAlreadyExistsError`
  - Implementar `DatabaseConnectionError`
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ] 8. Registrar exception handlers en FastAPI
  - Actualizar `app/main.py` con exception handlers
  - Registrar handler para `InterviewNotFoundError` (404)
  - Registrar handler para `InterviewAccessDeniedError` (403)
  - Registrar handler para `InterviewAlreadyExistsError` (409)
  - Registrar handler para `DatabaseConnectionError` (500)
  - Registrar handler genérico para `SQLAlchemyError` (500)
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ] 9. Actualizar endpoint POST /interviews/start
  - Modificar `app/routers/interviews.py`
  - Inyectar `db: AsyncSession = Depends(get_db)`
  - Mantener lógica actual de `AgentService.start_interview()`
  - Agregar llamada a `InterviewService.start_interview()` para persistir
  - Retornar `interview_id` en response data
  - Mantener formato de respuesta estándar ProssX
  - _Requirements: 3.1, 4.1, 4.2, 10.1, 10.2, 10.3, 10.4, 10.5_

- [ ] 10. Actualizar endpoint POST /interviews/continue
  - Modificar `app/routers/interviews.py`
  - Inyectar `db: AsyncSession = Depends(get_db)`
  - Validar que `interview_id` esté en request body
  - Mantener lógica actual de `AgentService.continue_interview()`
  - Agregar llamada a `InterviewService.continue_interview()` para persistir
  - Manejar errores de validación (interview no encontrada, acceso denegado)
  - _Requirements: 3.2, 4.1, 4.2, 4.3, 4.4, 4.5, 10.1, 10.2, 10.3, 10.4, 10.5_

- [ ] 11. Crear endpoint GET /interviews/{interview_id}
  - Agregar nuevo endpoint en `app/routers/interviews.py`
  - Inyectar `db: AsyncSession = Depends(get_db)`
  - Validar JWT y extraer employee_id
  - Llamar a `InterviewService.get_interview()`
  - Retornar `InterviewWithMessages` en formato estándar
  - Manejar errores 404 y 403
  - _Requirements: 3.2, 9.2, 9.3, 10.1, 10.2, 10.5_

- [ ] 12. Crear endpoint GET /interviews
  - Agregar nuevo endpoint en `app/routers/interviews.py`
  - Inyectar `db: AsyncSession = Depends(get_db)`
  - Validar JWT y extraer employee_id
  - Parsear query params (status, language, start_date, end_date, page, page_size)
  - Llamar a `InterviewService.list_interviews()`
  - Retornar lista con metadata de paginación
  - _Requirements: 3.3, 6.1, 6.2, 6.3, 6.4, 6.5, 10.1, 10.2, 10.5_

- [ ] 13. Crear endpoint PATCH /interviews/{interview_id}
  - Agregar nuevo endpoint en `app/routers/interviews.py`
  - Inyectar `db: AsyncSession = Depends(get_db)`
  - Validar JWT y extraer employee_id
  - Permitir actualizar solo campo `status`
  - Llamar a `InterviewRepository.update_status()`
  - Retornar interview actualizada
  - _Requirements: 3.4, 9.2, 9.3, 10.1, 10.2, 10.5_

- [ ] 14. Crear endpoint POST /interviews/migrate
  - Agregar nuevo endpoint en `app/routers/interviews.py`
  - Inyectar `db: AsyncSession = Depends(get_db)`
  - Validar JWT y extraer employee_id
  - Recibir `session_id`, `conversation_history`, `language` en body
  - Llamar a `InterviewService.migrate_from_localstorage()`
  - Retornar interview_id generado
  - Manejar error 409 si ya existe
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 9.1, 10.1, 10.2, 10.5_

- [ ] 15. Actualizar endpoint POST /interviews/export
  - Modificar `app/routers/interviews.py`
  - Cambiar para obtener datos desde DB en lugar de request body
  - Recibir solo `interview_id` en body
  - Llamar a `InterviewService.get_interview()` para obtener datos
  - Mantener formato actual de `InterviewExportData`
  - _Requirements: 3.2, 10.1, 10.2, 10.5_

- [ ] 16. Actualizar docker-compose.yml
  - Agregar servicio `postgres` para base de datos
  - Usar imagen `postgres:17.6-alpine`
  - Configurar variables de entorno (POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD)
  - Configurar volumen para persistencia de datos
  - Configurar healthcheck con `pg_isready`
  - Agregar network para comunicación entre servicios
  - Configurar `depends_on` en servicio `elicitation-ai`
  - _Requirements: 7.1, 7.2, 7.5_

- [ ] 17. Actualizar README con instrucciones de base de datos
  - Agregar sección "Database Setup"
  - Documentar cómo ejecutar migraciones con Alembic
  - Documentar variables de entorno de base de datos
  - Agregar comandos para iniciar PostgreSQL con Docker
  - Documentar cómo hacer rollback de migraciones
  - _Requirements: 8.5_

- [ ]* 18. Escribir tests unitarios para repositories
  - Crear `tests/unit/repositories/test_interview_repository.py`
  - Crear `tests/unit/repositories/test_message_repository.py`
  - Usar fixtures con base de datos en memoria (SQLite)
  - Testear todos los métodos CRUD
  - Testear filtros y paginación
  - Testear cascade delete
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5_

- [ ]* 19. Escribir tests unitarios para services
  - Crear `tests/unit/services/test_interview_service.py`
  - Mockear repositories
  - Testear `start_interview()`
  - Testear `continue_interview()`
  - Testear `get_interview()`
  - Testear `list_interviews()`
  - Testear `migrate_from_localstorage()`
  - Testear manejo de errores
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 5.4, 5.5_

- [ ]* 20. Escribir tests de integración con base de datos
  - Crear `tests/integration/test_database_connection.py`
  - Testear conexión exitosa a PostgreSQL
  - Testear pool de conexiones
  - Testear reintentos en caso de fallo
  - Crear `tests/integration/repositories/test_interview_repository_integration.py`
  - Testear CRUD completo contra DB real (testcontainers)
  - _Requirements: 7.4, 7.5_

- [ ]* 21. Escribir tests funcionales (E2E) para API
  - Crear `tests/functional/test_interview_api.py`
  - Testear POST /start crea entrevista en DB
  - Testear POST /continue persiste mensajes
  - Testear GET /interviews/{id} retorna datos correctos
  - Testear GET /interviews lista con paginación
  - Testear POST /migrate importa desde localStorage
  - Testear validación de JWT en todos los endpoints
  - Testear errores 403 al acceder a entrevista ajena
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 5.4, 5.5, 10.1, 10.2, 10.3, 10.4, 10.5_

- [ ]* 22. Escribir tests de validación de modelos
  - Crear `tests/unit/models/test_db_models.py`
  - Testear validación de enums (language, status, role)
  - Testear timestamps automáticos
  - Testear relaciones bidireccionales
  - Testear constraints de unicidad
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5_
