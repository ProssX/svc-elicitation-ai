# Documento de Requerimientos - Persistencia de Entrevistas

## Introducción

Este documento especifica los requerimientos para implementar un sistema de persistencia de entrevistas en el microservicio `svc-elicitation-ai`. Actualmente, las entrevistas se almacenan temporalmente en session/local storage del navegador, lo que limita la capacidad de análisis, auditoría y recuperación de datos. La solución propuesta implementará una base de datos PostgreSQL con un modelo de datos escalable que siga los patrones arquitectónicos establecidos en el ecosistema de microservicios ProssX.

## Glosario

- **Sistema de Entrevistas**: El microservicio `svc-elicitation-ai` que conduce entrevistas conversacionales con usuarios
- **Entrevista**: Una sesión completa de preguntas y respuestas entre el agente de IA y un empleado
- **Pregunta**: Un mensaje generado por el agente de IA durante una entrevista
- **Respuesta**: Un mensaje enviado por el usuario en respuesta a una pregunta del agente
- **Empleado**: Usuario del sistema que pertenece a una organización y tiene roles asignados (definido en `svc-organizations-php`)
- **Organización**: Entidad empresarial que agrupa empleados y roles (definida en `svc-organizations-php`)
- **Session Storage**: Almacenamiento temporal del navegador que se pierde al cerrar la pestaña
- **Local Storage**: Almacenamiento persistente del navegador limitado a 5-10MB
- **PostgreSQL**: Sistema de gestión de base de datos relacional utilizado en el ecosistema ProssX
- **SQLAlchemy**: ORM (Object-Relational Mapping) para Python que facilita la interacción con bases de datos
- **Alembic**: Herramienta de migración de base de datos para SQLAlchemy
- **UUID v7**: Identificador único universal con ordenamiento temporal incorporado
- **Formato de Respuesta Estándar**: Estructura JSON acordada entre microservicios ProssX (status, code, message, data, errors, meta)

## Requerimientos

### Requirement 1: Modelo de Datos de Entrevistas

**User Story:** Como desarrollador del sistema, quiero un modelo de datos escalable y normalizado para almacenar entrevistas, de manera que pueda mantener la integridad referencial y facilitar consultas eficientes.

#### Acceptance Criteria

1. WHEN se crea una nueva entrevista, THE Sistema de Entrevistas SHALL generar un UUID v7 único como identificador primario
2. THE Sistema de Entrevistas SHALL almacenar la relación entre Entrevista y Empleado mediante una clave foránea al campo `id_employee` de la tabla `employee` en `svc-organizations-php`
3. THE Sistema de Entrevistas SHALL registrar los metadatos de la entrevista incluyendo fecha de inicio, fecha de finalización, idioma (es/en/pt), nivel técnico del usuario, y estado de completitud
4. THE Sistema de Entrevistas SHALL mantener timestamps automáticos de creación y actualización para cada entrevista
5. WHEN se elimina un empleado en `svc-organizations-php`, THE Sistema de Entrevistas SHALL mantener las entrevistas existentes mediante una estrategia de eliminación en cascada configurada como RESTRICT o SET NULL

### Requirement 2: Modelo de Datos de Preguntas y Respuestas

**User Story:** Como desarrollador del sistema, quiero almacenar el historial completo de conversación de cada entrevista, de manera que pueda reconstruir el flujo de diálogo y analizar las interacciones.

#### Acceptance Criteria

1. THE Sistema de Entrevistas SHALL crear una entidad separada para almacenar cada mensaje (pregunta o respuesta) de la conversación
2. WHEN se registra un mensaje, THE Sistema de Entrevistas SHALL almacenar el rol del mensaje (assistant/user/system), el contenido textual, el número de secuencia, y el timestamp
3. THE Sistema de Entrevistas SHALL mantener la relación entre cada mensaje y su entrevista mediante una clave foránea
4. WHEN se elimina una entrevista, THE Sistema de Entrevistas SHALL eliminar automáticamente todos los mensajes asociados mediante eliminación en cascada
5. THE Sistema de Entrevistas SHALL ordenar los mensajes por número de secuencia para garantizar la reconstrucción correcta del flujo conversacional

### Requirement 3: API REST para Gestión de Entrevistas

**User Story:** Como desarrollador frontend, quiero endpoints REST para crear, consultar, actualizar y exportar entrevistas, de manera que pueda integrar la persistencia en la interfaz de usuario.

#### Acceptance Criteria

1. THE Sistema de Entrevistas SHALL exponer un endpoint POST `/api/v1/interviews` para crear una nueva entrevista con los datos del empleado autenticado
2. THE Sistema de Entrevistas SHALL exponer un endpoint GET `/api/v1/interviews/{interview_id}` para recuperar una entrevista específica con su historial completo de mensajes
3. THE Sistema de Entrevistas SHALL exponer un endpoint GET `/api/v1/interviews` para listar las entrevistas del empleado autenticado con paginación
4. THE Sistema de Entrevistas SHALL exponer un endpoint PATCH `/api/v1/interviews/{interview_id}` para actualizar el estado de una entrevista (ej: marcar como completada)
5. THE Sistema de Entrevistas SHALL retornar respuestas en el Formato de Respuesta Estándar de ProssX con códigos HTTP apropiados (200, 201, 400, 404, 500)

### Requirement 4: Persistencia de Mensajes en Tiempo Real

**User Story:** Como desarrollador frontend, quiero que cada pregunta y respuesta se persista inmediatamente en la base de datos, de manera que no se pierdan datos si el usuario cierra el navegador accidentalmente.

#### Acceptance Criteria

1. WHEN el agente genera una nueva pregunta, THE Sistema de Entrevistas SHALL persistir el mensaje en la base de datos antes de retornar la respuesta al cliente
2. WHEN el usuario envía una respuesta, THE Sistema de Entrevistas SHALL persistir el mensaje en la base de datos antes de generar la siguiente pregunta
3. IF ocurre un error de base de datos durante la persistencia, THEN THE Sistema de Entrevistas SHALL retornar un error HTTP 500 con detalles del problema
4. THE Sistema de Entrevistas SHALL incluir el `interview_id` en la respuesta del endpoint `/start` para que el frontend pueda asociar mensajes subsecuentes
5. THE Sistema de Entrevistas SHALL validar que el `interview_id` proporcionado en `/continue` pertenezca al empleado autenticado

### Requirement 5: Migración desde Almacenamiento del Navegador

**User Story:** Como usuario del sistema, quiero que mis entrevistas en progreso se migren automáticamente desde local storage a la base de datos, de manera que no pierda mi trabajo al actualizar el sistema.

#### Acceptance Criteria

1. THE Sistema de Entrevistas SHALL exponer un endpoint POST `/api/v1/interviews/migrate` para importar entrevistas desde local storage
2. WHEN se recibe una solicitud de migración, THE Sistema de Entrevistas SHALL validar que la estructura de datos sea compatible con el modelo actual
3. THE Sistema de Entrevistas SHALL crear registros de entrevista y mensajes a partir de los datos de `conversation_history` proporcionados
4. IF ya existe una entrevista con el mismo `session_id`, THEN THE Sistema de Entrevistas SHALL retornar un error HTTP 409 (Conflict)
5. THE Sistema de Entrevistas SHALL retornar el `interview_id` generado para que el frontend pueda actualizar su referencia local

### Requirement 6: Consultas y Filtros de Entrevistas

**User Story:** Como empleado del sistema, quiero filtrar y buscar mis entrevistas por fecha, estado y organización, de manera que pueda encontrar rápidamente entrevistas específicas.

#### Acceptance Criteria

1. THE Sistema de Entrevistas SHALL soportar filtrado de entrevistas por rango de fechas mediante parámetros `start_date` y `end_date`
2. THE Sistema de Entrevistas SHALL soportar filtrado de entrevistas por estado (in_progress/completed/cancelled) mediante parámetro `status`
3. THE Sistema de Entrevistas SHALL soportar filtrado de entrevistas por idioma (es/en/pt) mediante parámetro `language`
4. THE Sistema de Entrevistas SHALL implementar paginación con parámetros `page` y `page_size` (default: page=1, page_size=20, max: 100)
5. THE Sistema de Entrevistas SHALL retornar metadatos de paginación incluyendo `total_items`, `total_pages`, `current_page`, y `page_size`

### Requirement 7: Configuración de Base de Datos

**User Story:** Como DevOps, quiero configurar la conexión a PostgreSQL mediante variables de entorno, de manera que pueda desplegar el servicio en diferentes ambientes sin modificar código.

#### Acceptance Criteria

1. THE Sistema de Entrevistas SHALL leer la URL de conexión a PostgreSQL desde la variable de entorno `DATABASE_URL`
2. THE Sistema de Entrevistas SHALL soportar el formato de URL `postgresql://user:password@host:port/database`
3. THE Sistema de Entrevistas SHALL configurar un pool de conexiones con tamaño mínimo de 5 y máximo de 20 conexiones
4. THE Sistema de Entrevistas SHALL implementar reintentos automáticos de conexión con backoff exponencial (máximo 3 intentos)
5. THE Sistema de Entrevistas SHALL validar la conexión a la base de datos durante el startup y fallar rápidamente si no puede conectarse

### Requirement 8: Migraciones de Base de Datos

**User Story:** Como desarrollador del sistema, quiero gestionar cambios en el esquema de base de datos mediante migraciones versionadas, de manera que pueda evolucionar el modelo de datos de forma controlada.

#### Acceptance Criteria

1. THE Sistema de Entrevistas SHALL utilizar Alembic para gestionar migraciones de base de datos
2. THE Sistema de Entrevistas SHALL incluir una migración inicial que cree las tablas `interview` y `interview_message`
3. THE Sistema de Entrevistas SHALL nombrar las migraciones con timestamp y descripción (formato: `YYYYMMDDHHMMSS_descripcion.py`)
4. THE Sistema de Entrevistas SHALL incluir scripts de rollback (`downgrade()`) para cada migración
5. THE Sistema de Entrevistas SHALL documentar en el README cómo ejecutar migraciones en desarrollo y producción

### Requirement 9: Validación y Manejo de Errores

**User Story:** Como desarrollador del sistema, quiero validaciones robustas y mensajes de error claros, de manera que pueda diagnosticar problemas rápidamente.

#### Acceptance Criteria

1. WHEN se recibe un request con datos inválidos, THE Sistema de Entrevistas SHALL retornar HTTP 400 con detalles específicos de los campos erróneos
2. WHEN se solicita una entrevista inexistente, THE Sistema de Entrevistas SHALL retornar HTTP 404 con mensaje "Interview not found"
3. WHEN un empleado intenta acceder a una entrevista de otro empleado, THE Sistema de Entrevistas SHALL retornar HTTP 403 con mensaje "Access denied"
4. WHEN ocurre un error de base de datos, THE Sistema de Entrevistas SHALL retornar HTTP 500 sin exponer detalles internos de la base de datos
5. THE Sistema de Entrevistas SHALL registrar todos los errores en logs con nivel ERROR incluyendo stack trace y contexto de la operación

### Requirement 10: Integración con Autenticación JWT

**User Story:** Como desarrollador del sistema, quiero que todos los endpoints de persistencia requieran autenticación JWT, de manera que solo empleados autorizados puedan acceder a sus entrevistas.

#### Acceptance Criteria

1. THE Sistema de Entrevistas SHALL validar el token JWT en todos los endpoints de entrevistas (excepto health check)
2. THE Sistema de Entrevistas SHALL extraer el `user_id` del token JWT para asociar entrevistas con empleados
3. THE Sistema de Entrevistas SHALL extraer el `organization_id` del token JWT para validación de contexto
4. WHEN un token es inválido o ha expirado, THE Sistema de Entrevistas SHALL retornar HTTP 401 con mensaje "Authentication required"
5. THE Sistema de Entrevistas SHALL verificar que el `employee_id` en la base de datos corresponda al `user_id` del token antes de retornar datos
