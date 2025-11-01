# Requirements Document

## Introduction

Este documento define los requerimientos para optimizar el servicio de entrevistas de IA (svc-elicitation-ai), enfocándose en tres áreas críticas:

1. **Optimización de comunicación frontend-backend**: Eliminar el envío redundante de todo el historial de conversación en cada iteración
2. **Revisión del modelo de datos**: Evaluar y limpiar atributos innecesarios o confusos en el modelo Interview
3. **Estandarización del manejo de errores**: Implementar un manejo consistente de errores de validación siguiendo el patrón del servicio de autenticación

**IMPORTANTE**: Los cambios se implementarán SOLO en el microservicio svc-elicitation-ai. Se generará documentación (README) para que el equipo de frontend implemente los cambios necesarios en su lado.

## Glossary

- **Interview Service**: Microservicio svc-elicitation-ai que gestiona entrevistas de elicitación de requerimientos con IA
- **Frontend**: Aplicación React (web-frontend-react) que consume el Interview Service
- **Backend**: Servicio FastAPI que procesa las entrevistas y persiste datos en PostgreSQL
- **Conversation History**: Historial completo de mensajes (preguntas y respuestas) de una entrevista
- **Session ID**: Identificador legacy de sesión usado para compatibilidad con localStorage
- **Interview ID**: Identificador UUID de la entrevista en la base de datos PostgreSQL
- **Pydantic**: Librería de validación de datos usada por FastAPI
- **RequestValidationError**: Excepción de FastAPI cuando los datos de entrada no cumplen el esquema Pydantic
- **ProssX Standard Format**: Formato estándar de respuestas usado en todos los microservicios del proyecto

## Requirements

### Requirement 1: Optimización de Comunicación Frontend-Backend

**User Story:** Como desarrollador del sistema, quiero que el frontend solo envíe la información mínima necesaria en cada request, para reducir el payload de red y mejorar el rendimiento del sistema.

#### Acceptance Criteria

1. WHEN el frontend continúa una entrevista, THE Interview Service SHALL aceptar solo el interview_id y la respuesta del usuario sin requerir el historial completo de conversación
2. WHEN el Interview Service recibe un request de continuación, THE Interview Service SHALL recuperar el historial de conversación desde la base de datos PostgreSQL usando el interview_id
3. WHEN el Interview Service genera la siguiente pregunta, THE Interview Service SHALL persistir tanto la respuesta del usuario como la nueva pregunta en la base de datos antes de retornar la respuesta
4. WHEN el frontend inicia una entrevista, THE Interview Service SHALL retornar el interview_id en la respuesta para que el frontend lo use en requests subsecuentes
5. WHERE el frontend necesita el historial completo, THE Interview Service SHALL proveer un endpoint GET /interviews/{interview_id} que retorne todos los mensajes ordenados por sequence_number

### Requirement 2: Limpieza del Modelo de Datos

**User Story:** Como desarrollador del sistema, quiero que el modelo Interview contenga solo atributos necesarios y bien documentados, para evitar confusión y mantener un esquema de base de datos limpio.

#### Acceptance Criteria

1. THE Interview Service SHALL evaluar cada atributo del modelo Interview para determinar si es necesario o redundante
2. WHEN se identifica un atributo redundante o innecesario, THE Interview Service SHALL remover el atributo del modelo y crear una migración de base de datos
3. THE Interview Service SHALL documentar claramente el propósito de cada atributo que permanezca en el modelo
4. WHEN existen dos identificadores (session_id e interview_id), THE Interview Service SHALL usar interview_id como identificador primario y deprecar session_id
5. THE Interview Service SHALL mantener session_id solo si es necesario para compatibilidad con datos legacy en localStorage

### Requirement 3: Estandarización del Manejo de Errores

**User Story:** Como desarrollador frontend, quiero que todos los errores de validación sigan el mismo formato estándar ProssX, para poder manejarlos de manera consistente en la interfaz de usuario.

#### Acceptance Criteria

1. WHEN FastAPI lanza un RequestValidationError por datos inválidos, THE Interview Service SHALL capturar la excepción y transformarla al formato estándar ProssX
2. THE Interview Service SHALL retornar errores de validación con la estructura: `{"status": "error", "code": 400, "message": "Validation error", "errors": [{"field": "campo", "error": "descripción"}]}`
3. WHEN múltiples campos tienen errores de validación, THE Interview Service SHALL incluir todos los errores en el array "errors" de la respuesta
4. THE Interview Service SHALL implementar un exception handler global para RequestValidationError similar al implementado en svc-users-python
5. WHEN un error de validación ocurre, THE Interview Service SHALL registrar el error en los logs con el nivel WARNING incluyendo el endpoint y los campos afectados
6. THE Interview Service SHALL mantener consistencia con el formato de error usado en otros exception handlers existentes (HTTPException, InterviewNotFoundError, etc.)

### Requirement 4: Documentación para Frontend

**User Story:** Como desarrollador frontend, quiero documentación clara sobre los cambios en la API, para poder actualizar el código del frontend correctamente.

#### Acceptance Criteria

1. THE Interview Service SHALL generar un documento README que describa todos los cambios en los endpoints de la API
2. THE README SHALL incluir ejemplos de requests y responses antes y después de los cambios
3. THE README SHALL especificar qué campos son ahora opcionales y cuáles son requeridos
4. THE README SHALL incluir una guía de migración paso a paso para actualizar el código del frontend
5. THE README SHALL documentar el manejo de datos legacy en localStorage si el frontend decide mantener compatibilidad temporal
