# Implementation Plan

- [x] 1. Update System Prompts for Natural Language






  - [x] 1.1 Modificar `prompts/system_prompts.py` para eliminar títulos técnicos

    - Remover "Analista de Sistemas Senior" de todos los prompts (es/en/pt)
    - Cambiar presentación a lenguaje más accesible ("asistente", "Agente ProssX")
    - Actualizar las tres versiones de idioma (español, inglés, portugués)
    - _Requirements: 1.1, 1.2, 1.3, 1.4_



  - [x] 1.2 Actualizar preguntas para usar lenguaje más abierto





    - Cambiar "¿Qué procesos ejecutás?" por "¿Cómo es tu día a día?"
    - Cambiar "¿Qué procedimientos seguís?" por "¿Qué tareas realizás habitualmente?"
    - Usar "actividades" en lugar de "procesos" en preguntas iniciales
    - Agregar instrucciones de adaptación dinámica al vocabulario del usuario
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_



  - [x] 1.3 Implementar control dinámico de finalización en prompts





    - Eliminar referencias a `min_questions` y `max_questions` de los prompts
    - Agregar instrucciones para que el agente decida cuándo finalizar
    - Agregar instrucciones para respetar señales explícitas del usuario
    - Agregar instrucciones para preguntar si el usuario quiere continuar cuando detecta señales implícitas

    - Actualizar en los tres idiomas (es/en/pt)

    - _Requirements: 8.1, 8.2, 8.3, 8.4_

  - [x] 1.4 Actualizar `PromptBuilder` para soportar prompts mejorados





    - Modificar `_build_spanish_prompt()` con nuevas instrucciones
    - Modificar `_build_english_prompt()` con nuevas instrucciones
    - Modificar `_build_portuguese_prompt()` con nuevas instrucciones
    - Asegurar que los prompts contextuales también usen lenguaje natural
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 2. Implement Dynamic Interview Completion Logic






  - [x] 2.1 Agregar configuración para control dinámico

    - Agregar `enable_dynamic_completion` a `config.py`
    - Agregar `max_questions_safety_limit` a `config.py` (default: 50)
    - Agregar variables de entorno correspondientes
    - Documentar nuevas configuraciones
    - _Requirements: 8.5_


  - [x] 2.2 Refactorizar `_should_finish_interview()` en `agent_service.py`

    - Eliminar lógica de `min_questions`
    - Reemplazar `max_questions` con `max_questions_safety_limit`
    - Implementar detección de señales explícitas del usuario
    - Implementar detección de señales del agente (mensajes de cierre)
    - Agregar logging detallado de decisiones de finalización
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_


  - [x] 2.3 Actualizar lógica de finalización en `continue_interview()`

    - Pasar `conversation_history` a `_should_finish_interview()`
    - Asegurar que el agente puede finalizar en cualquier momento
    - Mantener safety limit para prevenir loops infinitos
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [ ]* 2.4 Escribir tests para control dinámico de finalización
    - Test: Usuario dice "quiero terminar" → finaliza inmediatamente
    - Test: Usuario dice "eso es todo" → finaliza inmediatamente
    - Test: Agente genera mensaje de cierre → finaliza
    - Test: Safety limit alcanzado → finaliza
    - Test: Conversación normal → continúa
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 3. Implement Multi-Layer Process Detection






  - [x] 3.1 Crear modelo `ProcessDetectionResult` en `app/models/interview.py`

    - Definir campos: `is_process_mentioned`, `confidence_score`, `process_type`
    - Agregar campos opcionales: `matched_process_id`, `matched_process_name`, `reasoning`
    - Agregar validación de confidence_score (0.0 a 1.0)
    - Agregar validación de process_type enum ("new", "existing", "unclear")
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4, 4.5_


  - [x] 3.2 Implementar Capa 1: Pre-filtro heurístico amplio

    - Crear método `_heuristic_process_filter()` en `agent_service.py`
    - Implementar keywords expandidas (verbos de acción, sustantivos, contextuales)
    - Usar umbral muy bajo (capturar TODO lo que podría ser un proceso)
    - Optimizar para ejecución sincrónica (<1ms)
    - Soportar español, inglés y portugués
    - _Requirements: 9.1, 9.2, 9.7_


  - [x] 3.3 Implementar Capa 2: Análisis semántico completo

    - Crear método `_detect_process_mention()` en `agent_service.py`
    - Reutilizar `ProcessMatchingAgent` para análisis semántico
    - Implementar análisis profundo (secuencia de pasos, inputs/outputs, decisiones)
    - Implementar tolerancia a errores (typos, sinónimos, descripciones indirectas)
    - Retornar `ProcessDetectionResult` con confidence score
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4, 4.5, 9.1, 9.2_


  - [x] 3.4 Implementar detección en `ProcessMatchingAgent`

    - Agregar método `detect_process_mention()` en `process_matching_agent.py`
    - Crear prompt especializado para detección sin matching
    - Implementar análisis de características de proceso (pasos, inputs/outputs, decisiones)
    - Soportar los tres idiomas (es/en/pt)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 4. Implement Rigorous Error Handling and Retry Logic




  - [x] 4.1 Agregar configuración para detección rigurosa


    - Agregar `process_detection_timeout` a `config.py` (default: 3.0 segundos)
    - Agregar `enable_detection_retry` a `config.py` (default: true)
    - Agregar `process_detection_confidence_threshold` a `config.py` (default: 0.6)
    - Agregar variables de entorno correspondientes
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 9.4, 9.6_

  - [x] 4.2 Implementar timeout handling con retry


    - Implementar primer intento con timeout de 3 segundos
    - Implementar segundo intento con timeout de 1.5 segundos en caso de fallo
    - Fallback inteligente: asumir proceso en caso de timeout (no perder información)
    - Logging detallado de timeouts y retries
    - _Requirements: 9.3, 9.4, 9.5, 9.6_

  - [x] 4.3 Implementar error handling con fallback


    - Catch JSON parsing errors
    - Implementar `_simple_detection_fallback()` con prompt simplificado
    - Fallback final: asumir proceso en caso de error (no perder información)
    - Logging exhaustivo de errores y fallbacks
    - _Requirements: 9.3, 9.4, 9.5_

  - [x] 4.4 Implementar ejecución en paralelo


    - Ejecutar detección de procesos en paralelo con generación de siguiente pregunta
    - Usar `asyncio.gather()` para ejecución concurrente
    - Asegurar que la detección no bloquea la conversación
    - _Requirements: 9.6, 9.7_

  - [ ]* 4.5 Escribir tests para error handling
    - Test: Timeout en primer intento → retry exitoso
    - Test: Timeout en ambos intentos → fallback a proceso detectado
    - Test: JSON parsing error → fallback simplificado
    - Test: Fallback simplificado falla → asumir proceso
    - Test: Ejecución en paralelo no bloquea conversación
    - _Requirements: 9.3, 9.4, 9.5, 9.6, 9.7_

- [x] 5. Integrate Detection into Interview Flow





  - [x] 5.1 Integrar detección en `continue_interview()`


    - Invocar `_heuristic_process_filter()` en cada respuesta del usuario
    - Si el filtro detecta posible proceso, invocar `_detect_process_mention()`
    - Ejecutar detección en paralelo con generación de pregunta
    - Agregar resultado de detección a `InterviewResponse`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 9.1, 9.2, 9.7_

  - [x] 5.2 Actualizar modelo `InterviewResponse`


    - Agregar campo opcional `process_detection: Optional[ProcessDetectionResult]`
    - Mantener compatibilidad con código existente
    - Documentar nuevo campo
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 5.3 Implementar logging exhaustivo


    - Registrar todas las invocaciones de detección
    - Registrar resultados con confidence scores
    - Registrar timeouts, errores y fallbacks
    - Registrar latencia de detección
    - Usar formato estructurado para análisis posterior
    - _Requirements: 9.5, 6.2, 6.3_

  - [ ]* 5.4 Escribir tests de integración
    - Test: Detección con proceso claro → detectado correctamente
    - Test: Detección con typo → detectado correctamente
    - Test: Detección con sinónimo → detectado correctamente
    - Test: Detección con descripción indirecta → detectado correctamente
    - Test: No proceso → no detectado
    - Test: Detección + matching de proceso existente → funciona correctamente
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4, 4.5, 9.1, 9.2_

- [x] 6. Implement Feature Flags





  - [x] 6.1 Agregar feature flags a `config.py`


    - `enable_improved_prompts` (default: false)
    - `enable_semantic_process_detection` (default: false)
    - `enable_dynamic_completion` (default: false)
    - Documentar cada feature flag
    - _Requirements: 6.4, 6.5, 7.3_

  - [x] 6.2 Implementar lógica condicional para prompts mejorados


    - En `get_interviewer_prompt()`, verificar `enable_improved_prompts`
    - Si está deshabilitado, usar prompts originales
    - Si está habilitado, usar prompts mejorados
    - _Requirements: 6.4, 6.5, 7.3_

  - [x] 6.3 Implementar lógica condicional para detección semántica


    - En `continue_interview()`, verificar `enable_semantic_process_detection`
    - Si está deshabilitado, usar detección por keywords original
    - Si está habilitado, usar detección semántica
    - _Requirements: 6.4, 6.5_

  - [x] 6.4 Implementar lógica condicional para finalización dinámica


    - En `_should_finish_interview()`, verificar `enable_dynamic_completion`
    - Si está deshabilitado, usar lógica original con min/max questions
    - Si está habilitado, usar lógica dinámica
    - _Requirements: 6.4, 6.5_

  - [ ]* 6.5 Escribir tests para feature flags
    - Test: `enable_improved_prompts=false` → usa prompts originales
    - Test: `enable_improved_prompts=true` → usa prompts mejorados
    - Test: `enable_semantic_process_detection=false` → usa keywords
    - Test: `enable_semantic_process_detection=true` → usa semántica
    - Test: `enable_dynamic_completion=false` → usa min/max questions
    - Test: `enable_dynamic_completion=true` → usa lógica dinámica
    - _Requirements: 6.4, 6.5_

- [x] 7. Documentation and Monitoring




  - [x] 7.1 Documentar cambios en README


    - Documentar nuevos prompts y su propósito
    - Documentar detección semántica y su estrategia
    - Documentar control dinámico de finalización
    - Documentar feature flags y cómo usarlos
    - _Requirements: 7.4, 7.5_

  - [x] 7.2 Agregar métricas de monitoreo


    - Métrica: Tasa de invocación de detección
    - Métrica: Latencia de detección (p50, p95, p99)
    - Métrica: Tasa de timeout
    - Métrica: Tasa de error
    - Métrica: Distribución de confidence scores
    - Métrica: Tasa de finalización temprana (con dynamic completion)
    - _Requirements: 6.2, 6.3_

  - [x] 7.3 Crear dashboard de monitoreo


    - Dashboard con métricas de detección
    - Dashboard con métricas de finalización
    - Alertas para tasas de timeout altas (>5%)
    - Alertas para tasas de error altas (>1%)
    - _Requirements: 6.2, 6.3_

  - [ ]* 7.4 Escribir guía de troubleshooting
    - Qué hacer si la detección tiene alta tasa de timeout
    - Qué hacer si la detección tiene alta tasa de error
    - Qué hacer si los usuarios se quejan de prompts
    - Cómo revertir cambios con feature flags
    - _Requirements: 6.4, 6.5_

- [ ] 8. Manual Testing and Validation
  - [ ] 8.1 Realizar pruebas manuales con prompts mejorados
    - Probar entrevista con usuario no técnico
    - Verificar que el lenguaje es accesible
    - Verificar que no hay confusión sobre terminología
    - Probar en los tres idiomas (es/en/pt)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 2.5_

  - [ ] 8.2 Realizar pruebas manuales de detección semántica
    - Probar con typos ("procezo", "proseso")
    - Probar con sinónimos ("actividad", "tarea", "flujo")
    - Probar con descripciones indirectas
    - Probar con lenguaje informal
    - Verificar que no se pierden procesos
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 5.4, 9.1, 9.2_

  - [ ] 8.3 Realizar pruebas manuales de finalización dinámica
    - Probar diciendo "quiero terminar" → debe finalizar inmediatamente
    - Probar diciendo "eso es todo" → debe finalizar inmediatamente
    - Probar dando respuestas cortas → debe preguntar si quiere continuar
    - Probar entrevista normal → debe continuar hasta tener información completa
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [ ] 8.4 Validar performance de detección
    - Medir latencia de detección en condiciones normales
    - Verificar que p95 < 1.5 segundos
    - Verificar que la detección no bloquea la conversación
    - Verificar que el retry funciona correctamente
    - _Requirements: 9.6, 9.7_

  - [ ] 8.5 Realizar pruebas de carga
    - Simular 100 entrevistas concurrentes
    - Verificar que la detección escala correctamente
    - Verificar que no hay degradación de performance
    - Verificar que los timeouts son raros (<5%)
    - _Requirements: 9.6, 9.7_
