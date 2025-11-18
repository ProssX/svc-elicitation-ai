# Plan de Implementación - Autorización y Control de Permisos

## Tareas de Implementación

- [x] 1. Crear enum de permisos
  - Crear archivo `app/models/permissions.py`
  - Definir enum `InterviewPermission` con todos los permisos
  - Implementar métodos helper (`values()`, `is_valid()`)
  - Agregar docstrings explicando cada permiso
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8_

- [x] 2. Actualizar TokenPayload para incluir permisos
  - Modificar `app/services/token_validator.py`
  - Agregar campo `permissions: List[str]` a `TokenPayload`
  - Implementar método `has_permission(permission: str) -> bool`
  - Implementar método `has_any_permission(permissions: List[str]) -> bool`
  - Implementar método `has_all_permissions(permissions: List[str]) -> bool`
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 3. Actualizar auth middleware para extraer permisos del JWT
  - Modificar función `get_current_user()` en `app/middleware/auth_middleware.py`
  - Extraer campo `permissions` del JWT payload
  - Validar que `permissions` sea un array de strings
  - Filtrar permisos inválidos usando `InterviewPermission.is_valid()`
  - Registrar warnings cuando JWT no contiene permisos o contiene permisos inválidos
  - Pasar permisos validados al `TokenPayload`
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 4. Crear dependencies de validación de permisos
  - Crear archivo `app/dependencies/permissions.py`
  - Implementar función `require_permission(permission: str) -> Callable`
  - Implementar función `require_any_permission(permissions: List[str]) -> Callable`
  - Implementar función `require_all_permissions(permissions: List[str]) -> Callable`
  - Implementar función helper `require_interview_ownership()`
  - Configurar respuestas HTTP 403 con formato estándar ProssX
  - Agregar logging de intentos de acceso denegado
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 5. Proteger endpoint POST /interviews/start
  - Modificar `app/routers/interviews.py`
  - Agregar dependency `require_permission(InterviewPermission.CREATE)`
  - Actualizar docstring con permiso requerido
  - Agregar ejemplo de error 403 en documentación
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 6. Proteger endpoint POST /interviews/continue
  - Modificar `app/routers/interviews.py`
  - Agregar dependency `require_permission(InterviewPermission.CREATE)`
  - Validar ownership: interview.employee_id == current_user.user_id
  - Permitir acceso si usuario tiene `InterviewPermission.READ_ALL`
  - Retornar 403 si intenta continuar entrevista ajena
  - Actualizar docstring con permiso requerido
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 7. Proteger endpoint GET /interviews (listar)
  - Modificar `app/routers/interviews.py`
  - Agregar dependency `require_permission(InterviewPermission.READ)`
  - Implementar lógica de filtrado por alcance de permiso:
    - Si solo tiene `interviews:read`: filtrar por employee_id del usuario
    - Si tiene `interviews:read_all`: retornar todas las entrevistas de la organización
  - Agregar campo `scope` en metadata de respuesta ("own" o "organization")
  - Actualizar docstring con permisos requeridos
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 8. Proteger endpoint GET /interviews/{id}
  - Modificar `app/routers/interviews.py`
  - Agregar dependency `require_permission(InterviewPermission.READ)`
  - Validar ownership usando `require_interview_ownership()`
  - Permitir acceso si usuario tiene `InterviewPermission.READ_ALL`
  - Retornar 404 (no 403) si entrevista no existe
  - Retornar 403 si entrevista existe pero no tiene acceso
  - Actualizar docstring con permisos requeridos
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 9. Proteger endpoint PATCH /interviews/{id}
  - Modificar `app/routers/interviews.py`
  - Agregar dependency `require_permission(InterviewPermission.UPDATE)`
  - Validar ownership: interview.employee_id == current_user.user_id
  - Permitir acceso si usuario tiene `InterviewPermission.READ_ALL`
  - Registrar en logs todas las actualizaciones con user_id
  - Actualizar docstring con permiso requerido
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 10. Proteger endpoint POST /interviews/export
  - Modificar `app/routers/interviews.py`
  - Agregar dependency `require_permission(InterviewPermission.EXPORT)`
  - Validar ownership: interview.employee_id == current_user.user_id
  - Permitir acceso si usuario tiene `InterviewPermission.READ_ALL`
  - Registrar en logs todas las exportaciones con timestamp y user_id
  - Actualizar docstring con permiso requerido
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [x] 11. Actualizar documentación OpenAPI/Swagger
  - Modificar `app/main.py` para agregar información de permisos en OpenAPI
  - Documentar permisos requeridos en descripción de cada endpoint
  - Agregar ejemplos de respuestas 403 en especificación
  - Crear sección explicando el sistema de permisos
  - Documentar diferencia entre `interviews:read` y `interviews:read_all`
  - Agrupar endpoints por nivel de permiso en tags
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [x] 12. Crear endpoint GET /api/v1/permissions
  - Crear nuevo endpoint en `app/routers/interviews.py`
  - Retornar lista de todos los permisos disponibles
  - Incluir descripción de cada permiso
  - No requiere autenticación (información pública)
  - Formato de respuesta:
    ```json
    {
      "status": "success",
      "data": {
        "permissions": [
          {
            "name": "interviews:create",
            "description": "Create and continue interviews"
          },
          ...
        ]
      }
    }
    ```
  - _Requirements: 12.5_

- [x] 13. Actualizar exception handlers
  - Modificar `app/main.py`
  - Asegurar que errores 403 usen formato estándar ProssX
  - Agregar handler específico para `HTTPException` con status 403
  - Incluir información de permiso requerido en respuesta de error
  - NO exponer información sensible en errores
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

- [x] 14. Agregar logging de autorización
  - Modificar `app/dependencies/permissions.py`
  - Registrar todos los intentos de acceso denegado (nivel WARNING)
  - Incluir: user_id, endpoint, permiso requerido, permisos actuales
  - Registrar accesos exitosos a recursos sensibles (nivel INFO)
  - Configurar formato de log consistente
  - _Requirements: 11.4, 11.5_

- [ ]* 15. Escribir tests unitarios para dependencies
  - Crear `tests/unit/dependencies/test_permissions.py`
  - Test `require_permission()` con permiso válido
  - Test `require_permission()` sin permiso (debe lanzar 403)
  - Test `require_any_permission()` con al menos un permiso válido
  - Test `require_any_permission()` sin ningún permiso válido
  - Test `require_all_permissions()` con todos los permisos
  - Test `require_all_permissions()` faltando algún permiso
  - Test `require_interview_ownership()` como dueño
  - Test `require_interview_ownership()` con `read_all` permission
  - Test `require_interview_ownership()` sin acceso
  - _Requirements: 13.1, 13.2, 13.3_

- [ ]* 16. Escribir tests unitarios para TokenPayload
  - Crear `tests/unit/services/test_token_validator.py`
  - Test `has_permission()` con permiso existente
  - Test `has_permission()` con permiso inexistente
  - Test `has_any_permission()` con múltiples permisos
  - Test `has_all_permissions()` con todos los permisos
  - Test `has_all_permissions()` faltando permisos
  - Test creación de TokenPayload con permisos vacíos
  - _Requirements: 13.1_

- [ ]* 17. Escribir tests funcionales para endpoints protegidos
  - Crear `tests/functional/test_interview_authorization.py`
  - Test POST /start sin permiso `interviews:create` (403)
  - Test POST /start con permiso válido (200)
  - Test POST /continue intentando continuar entrevista ajena (403)
  - Test GET /interviews con `interviews:read` (solo ve propias)
  - Test GET /interviews con `interviews:read_all` (ve todas)
  - Test GET /interviews/{id} intentando ver entrevista ajena (403)
  - Test GET /interviews/{id} con `read_all` viendo entrevista ajena (200)
  - Test PATCH /interviews/{id} intentando actualizar entrevista ajena (403)
  - Test POST /export intentando exportar entrevista ajena (403)
  - Test usuario sin permisos no puede acceder a ningún endpoint (403)
  - _Requirements: 13.2, 13.3, 13.4, 13.5_

- [ ]* 18. Escribir tests de integración con JWT
  - Crear `tests/integration/test_jwt_permissions.py`
  - Test extracción de permisos desde JWT válido
  - Test JWT sin campo `permissions` (debe asumir array vacío)
  - Test JWT con `permissions` en formato inválido (debe registrar warning)
  - Test JWT con permisos inválidos (debe filtrarlos)
  - Test JWT con mix de permisos válidos e inválidos
  - _Requirements: 13.1, 13.2_

- [x] 19. Crear documentación para equipo de Auth
  - Crear archivo `docs/PERMISSIONS.md`
  - Documentar todos los permisos disponibles
  - Explicar formato `resource:action`
  - Proveer ejemplos de JWT con permisos
  - Documentar mapeo sugerido de roles a permisos:
    ```
    Role: Admin → [interviews:create, interviews:read_all, interviews:update, interviews:export]
    Role: Manager → [interviews:create, interviews:read_all, interviews:export]
    Role: User → [interviews:create, interviews:read, interviews:export]
    ```
  - Incluir instrucciones para agregar permisos al JWT en `svc-users-python`
  - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

- [x] 20. Actualizar README con información de permisos
  - Modificar `README.md`
  - Agregar sección "Authorization & Permissions"
  - Documentar sistema de permisos
  - Explicar cómo probar con diferentes permisos
  - Incluir ejemplos de curl con JWT
  - Documentar cómo generar JWTs de prueba con permisos
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

## Notas de Implementación

### Orden de Ejecución

**Fase 1: Setup (Tareas 1-4)**
- No rompe nada existente
- Prepara la infraestructura
- Se puede hacer sin coordinación con otros equipos

**Fase 2: Protección de Endpoints (Tareas 5-10)**
- **BREAKING CHANGE**: Endpoints empiezan a requerir permisos
- Coordinar con equipo de Auth antes de deployar
- Probar con JWTs mock que contengan permisos

**Fase 3: Documentación y Testing (Tareas 11-20)**
- Documentar para otros equipos
- Tests aseguran que todo funciona
- README actualizado para developers

### Testing sin JWT Real

Durante desarrollo, puedes crear JWTs mock:

```python
# tests/conftest.py
@pytest.fixture
def jwt_with_create_permission():
    return create_mock_jwt({
        "sub": "user-123",
        "email": "test@example.com",
        "organization_id": "org-1",
        "permissions": ["interviews:create", "interviews:read"]
    })

@pytest.fixture
def jwt_with_admin_permissions():
    return create_mock_jwt({
        "sub": "admin-123",
        "email": "admin@example.com",
        "organization_id": "org-1",
        "permissions": [
            "interviews:create",
            "interviews:read",
            "interviews:read_all",
            "interviews:update",
            "interviews:export"
        ]
    })
```

### Coordinación con svc-users-python

Antes de deployar a producción:

1. ✅ Compartir `docs/PERMISSIONS.md` con equipo de Auth
2. ✅ Acordar mapeo de roles a permisos
3. ✅ Auth service actualiza JWT para incluir permisos
4. ✅ Probar end-to-end en staging
5. ✅ Deploy coordinado de ambos servicios

### Rollback Plan

Si algo falla en producción:

1. **Opción 1:** Revertir deployment (volver a versión sin autorización)
2. **Opción 2:** Feature flag para deshabilitar validación de permisos temporalmente
3. **Opción 3:** Auth service agrega todos los permisos a todos los usuarios temporalmente

### Performance Considerations

- ✅ Validación de permisos es O(1) (lookup en array)
- ✅ No hay queries adicionales a DB para permisos (vienen en JWT)
- ✅ Ownership validation requiere 1 query extra (ya optimizado con índices)

### Security Considerations

- ✅ Permisos vienen firmados en JWT (no se pueden falsificar)
- ✅ Validación en cada request (stateless)
- ✅ Logs de todos los intentos de acceso denegado
- ✅ No exponer información sensible en errores 403

