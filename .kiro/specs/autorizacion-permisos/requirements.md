# Documento de Requerimientos - Autorización y Control de Permisos

## Introducción

Este documento especifica los requerimientos para implementar un sistema de autorización basado en permisos en el microservicio `svc-elicitation-ai`. Actualmente, el sistema solo valida autenticación (verificar que el usuario esté logueado) pero no autorización (verificar qué puede hacer el usuario). La solución propuesta implementará control de acceso basado en permisos (PBAC - Permission-Based Access Control) siguiendo el mismo patrón establecido en `svc-organizations-php`.

## Glosario

- **Sistema de Entrevistas**: El microservicio `svc-elicitation-ai` que conduce entrevistas conversacionales con usuarios
- **Autenticación**: Proceso de verificar la identidad del usuario (¿quién sos?)
- **Autorización**: Proceso de verificar qué puede hacer el usuario (¿qué podés hacer?)
- **Permiso**: Capacidad específica otorgada a un usuario para realizar una acción sobre un recurso (formato: `resource:action`)
- **JWT (JSON Web Token)**: Token de autenticación que contiene información del usuario incluyendo sus permisos
- **PBAC (Permission-Based Access Control)**: Control de acceso basado en permisos específicos
- **Recurso**: Entidad del sistema sobre la cual se aplican permisos (ej: `interview`, `export`)
- **Acción**: Operación que se puede realizar sobre un recurso (ej: `read`, `create`, `update`, `delete`)
- **Dependency Injection**: Patrón de diseño usado en FastAPI para inyectar dependencias en endpoints

## Requerimientos

### Requirement 1: Definición de Permisos del Sistema

**User Story:** Como arquitecto del sistema, quiero definir todos los permisos disponibles para entrevistas, de manera que pueda controlar granularmente qué usuarios pueden hacer qué acciones.

#### Acceptance Criteria

1. THE Sistema de Entrevistas SHALL definir permisos siguiendo el patrón `resource:action` consistente con `svc-organizations-php`
2. THE Sistema de Entrevistas SHALL definir el permiso `interviews:create` para crear nuevas entrevistas
3. THE Sistema de Entrevistas SHALL definir el permiso `interviews:read` para leer entrevistas propias
4. THE Sistema de Entrevistas SHALL definir el permiso `interviews:read_all` para leer entrevistas de cualquier usuario de la organización
5. THE Sistema de Entrevistas SHALL definir el permiso `interviews:update` para actualizar estado de entrevistas propias
6. THE Sistema de Entrevistas SHALL definir el permiso `interviews:delete` para eliminar entrevistas propias (soft delete - futuro)
7. THE Sistema de Entrevistas SHALL definir el permiso `interviews:export` para exportar entrevistas propias
8. THE Sistema de Entrevistas SHALL mantener los permisos en un enum Python para type safety y documentación

### Requirement 2: Extracción de Permisos desde JWT

**User Story:** Como desarrollador del sistema, quiero extraer los permisos del JWT automáticamente, de manera que estén disponibles para validación en cada request.

#### Acceptance Criteria

1. THE Sistema de Entrevistas SHALL extraer el campo `permissions` del payload del JWT decodificado
2. WHEN el JWT no contiene el campo `permissions`, THE Sistema de Entrevistas SHALL asumir un array vacío
3. THE Sistema de Entrevistas SHALL almacenar los permisos en el objeto `TokenPayload` para acceso en endpoints
4. THE Sistema de Entrevistas SHALL validar que `permissions` sea un array de strings
5. THE Sistema de Entrevistas SHALL registrar en logs cuando un JWT no contenga permisos (nivel WARNING)

### Requirement 3: Dependency para Validación de Permisos

**User Story:** Como desarrollador del sistema, quiero una dependency reutilizable para validar permisos, de manera que pueda proteger endpoints fácilmente sin duplicar código.

#### Acceptance Criteria

1. THE Sistema de Entrevistas SHALL implementar una función `require_permission(permission: str)` que retorne una dependency de FastAPI
2. WHEN un usuario no tiene el permiso requerido, THE Sistema de Entrevistas SHALL retornar HTTP 403 con mensaje "Insufficient permissions"
3. THE Sistema de Entrevistas SHALL incluir en el error 403 el permiso requerido y los permisos que tiene el usuario
4. THE Sistema de Entrevistas SHALL permitir validar múltiples permisos con operador OR mediante `require_any_permission(permissions: List[str])`
5. THE Sistema de Entrevistas SHALL permitir validar múltiples permisos con operador AND mediante `require_all_permissions(permissions: List[str])`

### Requirement 4: Protección de Endpoint POST /interviews/start

**User Story:** Como administrador del sistema, quiero controlar quién puede iniciar entrevistas, de manera que solo usuarios autorizados puedan crear nuevas entrevistas.

#### Acceptance Criteria

1. THE Sistema de Entrevistas SHALL requerir el permiso `interviews:create` para acceder a POST `/api/v1/interviews/start`
2. WHEN un usuario sin el permiso intenta iniciar una entrevista, THE Sistema de Entrevistas SHALL retornar HTTP 403
3. THE Sistema de Entrevistas SHALL registrar en logs los intentos de acceso denegado con nivel WARNING
4. THE Sistema de Entrevistas SHALL mantener la validación de autenticación JWT existente
5. THE Sistema de Entrevistas SHALL documentar el permiso requerido en la especificación OpenAPI/Swagger

### Requirement 5: Protección de Endpoint POST /interviews/continue

**User Story:** Como administrador del sistema, quiero controlar quién puede continuar entrevistas, de manera que solo el dueño de la entrevista pueda agregar respuestas.

#### Acceptance Criteria

1. THE Sistema de Entrevistas SHALL requerir el permiso `interviews:create` para acceder a POST `/api/v1/interviews/continue`
2. THE Sistema de Entrevistas SHALL validar que el `employee_id` de la entrevista coincida con el `user_id` del JWT
3. WHEN un usuario intenta continuar una entrevista que no le pertenece, THE Sistema de Entrevistas SHALL retornar HTTP 403 con mensaje "Access denied to this interview"
4. THE Sistema de Entrevistas SHALL permitir el acceso si el usuario tiene el permiso `interviews:read_all` (para admins)
5. THE Sistema de Entrevistas SHALL registrar en logs los intentos de acceso a entrevistas ajenas

### Requirement 6: Protección de Endpoint GET /interviews

**User Story:** Como administrador del sistema, quiero controlar quién puede listar entrevistas, de manera que usuarios normales solo vean sus propias entrevistas y admins vean todas.

#### Acceptance Criteria

1. THE Sistema de Entrevistas SHALL requerir el permiso `interviews:read` para acceder a GET `/api/v1/interviews`
2. WHEN un usuario tiene solo `interviews:read`, THE Sistema de Entrevistas SHALL filtrar resultados por su `employee_id`
3. WHEN un usuario tiene `interviews:read_all`, THE Sistema de Entrevistas SHALL retornar entrevistas de todos los usuarios de su organización
4. THE Sistema de Entrevistas SHALL incluir en la metadata de respuesta el alcance del permiso (`scope: "own"` o `scope: "organization"`)
5. THE Sistema de Entrevistas SHALL permitir filtrar por `employee_id` solo si el usuario tiene `interviews:read_all`

### Requirement 7: Protección de Endpoint GET /interviews/{id}

**User Story:** Como administrador del sistema, quiero controlar quién puede ver entrevistas específicas, de manera que usuarios solo vean sus propias entrevistas completas.

#### Acceptance Criteria

1. THE Sistema de Entrevistas SHALL requerir el permiso `interviews:read` para acceder a GET `/api/v1/interviews/{id}`
2. THE Sistema de Entrevistas SHALL validar que el `employee_id` de la entrevista coincida con el `user_id` del JWT
3. WHEN un usuario intenta ver una entrevista que no le pertenece, THE Sistema de Entrevistas SHALL retornar HTTP 403
4. THE Sistema de Entrevistas SHALL permitir el acceso si el usuario tiene el permiso `interviews:read_all`
5. THE Sistema de Entrevistas SHALL retornar HTTP 404 en lugar de 403 si la entrevista no existe (para no revelar existencia)

### Requirement 8: Protección de Endpoint PATCH /interviews/{id}

**User Story:** Como administrador del sistema, quiero controlar quién puede actualizar entrevistas, de manera que solo el dueño pueda cambiar el estado.

#### Acceptance Criteria

1. THE Sistema de Entrevistas SHALL requerir el permiso `interviews:update` para acceder a PATCH `/api/v1/interviews/{id}`
2. THE Sistema de Entrevistas SHALL validar que el `employee_id` de la entrevista coincida con el `user_id` del JWT
3. WHEN un usuario intenta actualizar una entrevista que no le pertenece, THE Sistema de Entrevistas SHALL retornar HTTP 403
4. THE Sistema de Entrevistas SHALL permitir el acceso si el usuario tiene el permiso `interviews:read_all` (para admins)
5. THE Sistema de Entrevistas SHALL registrar en logs todas las actualizaciones de estado con el user_id que las realizó

### Requirement 9: Protección de Endpoint POST /interviews/export

**User Story:** Como administrador del sistema, quiero controlar quién puede exportar entrevistas, de manera que solo usuarios autorizados puedan generar documentos.

#### Acceptance Criteria

1. THE Sistema de Entrevistas SHALL requerir el permiso `interviews:export` para acceder a POST `/api/v1/interviews/export`
2. THE Sistema de Entrevistas SHALL validar que el `employee_id` de la entrevista coincida con el `user_id` del JWT
3. WHEN un usuario intenta exportar una entrevista que no le pertenece, THE Sistema de Entrevistas SHALL retornar HTTP 403
4. THE Sistema de Entrevistas SHALL permitir el acceso si el usuario tiene el permiso `interviews:read_all`
5. THE Sistema de Entrevistas SHALL registrar en logs todas las exportaciones con timestamp y user_id

### Requirement 10: Documentación de Permisos en OpenAPI

**User Story:** Como desarrollador frontend, quiero ver qué permisos requiere cada endpoint en Swagger, de manera que pueda entender qué funcionalidades están disponibles para cada rol.

#### Acceptance Criteria

1. THE Sistema de Entrevistas SHALL documentar en la descripción de cada endpoint los permisos requeridos
2. THE Sistema de Entrevistas SHALL incluir ejemplos de respuestas 403 en la especificación OpenAPI
3. THE Sistema de Entrevistas SHALL agrupar endpoints por nivel de permiso en la documentación
4. THE Sistema de Entrevistas SHALL incluir una sección en Swagger explicando el sistema de permisos
5. THE Sistema de Entrevistas SHALL documentar la diferencia entre `interviews:read` y `interviews:read_all`

### Requirement 11: Manejo de Errores de Autorización

**User Story:** Como desarrollador del sistema, quiero mensajes de error claros cuando falla la autorización, de manera que pueda diagnosticar problemas rápidamente.

#### Acceptance Criteria

1. WHEN un usuario no tiene permisos suficientes, THE Sistema de Entrevistas SHALL retornar HTTP 403 con formato estándar ProssX
2. THE Sistema de Entrevistas SHALL incluir en el error el permiso requerido y los permisos actuales del usuario
3. THE Sistema de Entrevistas SHALL NO exponer información sensible en errores de autorización
4. THE Sistema de Entrevistas SHALL registrar en logs todos los errores 403 con contexto completo (user_id, endpoint, permiso requerido)
5. THE Sistema de Entrevistas SHALL diferenciar entre "no autenticado" (401) y "no autorizado" (403)

### Requirement 12: Coordinación con Microservicio de Auth

**User Story:** Como arquitecto del sistema, quiero que el microservicio de auth incluya los permisos de entrevistas en el JWT, de manera que estén disponibles para validación.

#### Acceptance Criteria

1. THE Sistema de Entrevistas SHALL documentar los permisos requeridos para compartir con el equipo de `svc-users-python`
2. THE Sistema de Entrevistas SHALL funcionar correctamente cuando el JWT no contenga permisos (denegar acceso por defecto)
3. THE Sistema de Entrevistas SHALL validar que los permisos en el JWT sean strings válidos del enum `InterviewPermission`
4. THE Sistema de Entrevistas SHALL registrar en logs cuando detecte permisos desconocidos en el JWT
5. THE Sistema de Entrevistas SHALL proveer un endpoint GET `/api/v1/permissions` que liste todos los permisos disponibles

### Requirement 13: Testing de Autorización

**User Story:** Como desarrollador del sistema, quiero tests automatizados para validar el sistema de permisos, de manera que pueda asegurar que la autorización funciona correctamente.

#### Acceptance Criteria

1. THE Sistema de Entrevistas SHALL incluir tests unitarios para cada dependency de validación de permisos
2. THE Sistema de Entrevistas SHALL incluir tests funcionales que verifiquen respuestas 403 en cada endpoint protegido
3. THE Sistema de Entrevistas SHALL incluir tests que verifiquen el comportamiento con diferentes combinaciones de permisos
4. THE Sistema de Entrevistas SHALL incluir tests que verifiquen la diferencia entre `interviews:read` y `interviews:read_all`
5. THE Sistema de Entrevistas SHALL incluir tests que verifiquen que usuarios sin permisos no puedan acceder a ningún endpoint

