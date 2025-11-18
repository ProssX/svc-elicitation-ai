# Requirements Document

## Introduction

Este documento define los requerimientos para mejorar la experiencia de entrevista del sistema de elicitación de IA, haciéndola más natural, accesible y precisa para cualquier tipo de usuario. El sistema actual presenta al agente como "Analista Senior" y utiliza terminología técnica que puede no ser comprensible para todos los usuarios. Además, la detección de procesos se basa en palabras clave hardcodeadas, lo cual limita la precisión y flexibilidad del sistema.

## Glossary

- **Interview Agent**: El agente conversacional de IA que conduce las entrevistas con los usuarios
- **Process Detection**: El mecanismo que identifica cuando un usuario menciona un proceso de negocio durante la entrevista
- **System Prompt**: Las instrucciones que definen el comportamiento, personalidad y estilo del agente
- **Process Matching Agent**: Agente especializado en analizar respuestas y detectar menciones de procesos
- **Hardcoded Keywords**: Lista fija de palabras clave en múltiples idiomas usada actualmente para detectar procesos
- **Semantic Analysis**: Análisis basado en IA que comprende el significado del texto más allá de palabras clave específicas

## Requirements

### Requirement 1

**User Story:** Como usuario siendo entrevistado, quiero que el agente se presente de manera accesible y comprensible, para que me sienta cómodo independientemente de mi nivel técnico o conocimiento de terminología de análisis de sistemas

#### Acceptance Criteria

1. WHEN THE Interview Agent inicia una entrevista, THE Interview Agent SHALL presentarse sin usar títulos técnicos como "Analista Senior"
2. WHEN THE Interview Agent se presenta, THE Interview Agent SHALL usar un lenguaje amigable y accesible que cualquier usuario pueda comprender
3. THE Interview Agent SHALL evitar usar terminología técnica de análisis de sistemas en su presentación inicial
4. THE Interview Agent SHALL mantener un tono profesional pero cercano sin referencias a jerarquías o niveles de experiencia

### Requirement 2

**User Story:** Como usuario siendo entrevistado, quiero que el agente me pregunte sobre mi trabajo de manera natural y abierta, para que pueda describir mis actividades con mis propias palabras sin necesidad de conocer términos como "proceso"

#### Acceptance Criteria

1. WHEN THE Interview Agent solicita información sobre actividades del usuario, THE Interview Agent SHALL usar preguntas abiertas sobre el día a día y tareas cotidianas
2. THE Interview Agent SHALL evitar usar la palabra "proceso" directamente en las preguntas iniciales
3. WHEN el usuario menciona la palabra "proceso" en su respuesta, THE Interview Agent SHALL adaptar su lenguaje para incluir ese término en preguntas subsecuentes
4. THE Interview Agent SHALL formular preguntas como "¿cómo es tu día a día?" o "¿qué tareas realizás?" en lugar de "¿qué procesos ejecutás?"
5. THE Interview Agent SHALL mantener flexibilidad en el lenguaje adaptándose al vocabulario que usa el usuario

### Requirement 3

**User Story:** Como desarrollador del sistema, quiero reemplazar la detección de procesos basada en palabras clave hardcodeadas por un agente especializado, para que el sistema pueda detectar procesos de manera más precisa y flexible

#### Acceptance Criteria

1. THE System SHALL implementar un Process Matching Agent dedicado para analizar respuestas del usuario
2. THE Process Matching Agent SHALL usar Semantic Analysis en lugar de keyword matching para detectar menciones de procesos
3. THE Process Matching Agent SHALL analizar cada respuesta del usuario en tiempo real durante la entrevista
4. THE Process Matching Agent SHALL identificar procesos incluso cuando el usuario use sinónimos, errores de tipeo o descripciones indirectas
5. THE System SHALL eliminar las listas hardcodeadas de palabras clave en español, inglés y portugués

### Requirement 4

**User Story:** Como desarrollador del sistema, quiero que el Process Matching Agent sea capaz de detectar procesos con alta precisión, para que no perdamos información valiosa debido a variaciones en el lenguaje del usuario

#### Acceptance Criteria

1. WHEN el usuario menciona un proceso con errores de tipeo, THE Process Matching Agent SHALL detectar la mención del proceso
2. WHEN el usuario describe un proceso sin usar la palabra "proceso", THE Process Matching Agent SHALL identificar la descripción como una mención de proceso
3. THE Process Matching Agent SHALL asignar un confidence score a cada detección de proceso
4. WHEN el confidence score es menor a un umbral configurable, THE Process Matching Agent SHALL solicitar clarificación al Interview Agent
5. THE Process Matching Agent SHALL funcionar correctamente en español, inglés y portugués

### Requirement 5

**User Story:** Como usuario siendo entrevistado, quiero que el agente entienda mis respuestas incluso si cometo errores o uso lenguaje informal, para que la entrevista sea más natural y menos estresante

#### Acceptance Criteria

1. THE Process Matching Agent SHALL tolerar errores ortográficos comunes en las respuestas del usuario
2. THE Process Matching Agent SHALL comprender lenguaje coloquial y expresiones informales
3. THE Process Matching Agent SHALL identificar procesos mencionados en contexto sin requerir palabras clave específicas
4. WHEN el usuario usa sinónimos o paráfrasis, THE Process Matching Agent SHALL reconocer la referencia al mismo proceso
5. THE Process Matching Agent SHALL mantener contexto de la conversación para mejorar la detección

### Requirement 6

**User Story:** Como administrador del sistema, quiero que el nuevo sistema de detección de procesos sea configurable y monitoreable, para que pueda ajustar su comportamiento y evaluar su efectividad

#### Acceptance Criteria

1. THE System SHALL permitir configurar el confidence threshold para la detección de procesos
2. THE System SHALL registrar métricas de performance del Process Matching Agent en los logs
3. THE System SHALL incluir el confidence score en los logs de detección de procesos
4. THE System SHALL permitir habilitar o deshabilitar el Process Matching Agent mediante feature flag
5. WHEN el Process Matching Agent está deshabilitado, THE System SHALL usar el mecanismo de detección anterior como fallback

### Requirement 7

**User Story:** Como desarrollador del sistema, quiero que los cambios en el system prompt sean mantenibles y versionados, para que podamos iterar y mejorar el comportamiento del agente de manera controlada

#### Acceptance Criteria

1. THE System SHALL mantener los system prompts en archivos de configuración separados del código
2. THE System SHALL versionar los cambios en los system prompts
3. THE System SHALL permitir A/B testing de diferentes versiones de system prompts
4. THE System SHALL documentar los cambios realizados en cada versión del system prompt
5. THE System SHALL mantener compatibilidad con los tres idiomas soportados (español, inglés, portugués)

### Requirement 8

**User Story:** Como usuario siendo entrevistado, quiero que el agente respete mi decisión cuando quiero finalizar la entrevista, para que no me sienta presionado a continuar cuando ya no tengo más información que compartir

#### Acceptance Criteria

1. WHEN el usuario indica explícitamente que quiere terminar, THE Interview Agent SHALL finalizar la entrevista inmediatamente sin insistir
2. THE Interview Agent SHALL eliminar límites mínimos de preguntas obligatorias
3. THE Interview Agent SHALL usar su criterio profesional para determinar cuándo tiene suficiente información
4. WHEN el usuario da respuestas muy cortas o indica falta de información adicional, THE Interview Agent SHALL preguntar si desea continuar o finalizar
5. THE System SHALL mantener un límite de seguridad absoluto para prevenir loops infinitos

### Requirement 9

**User Story:** Como administrador del sistema, quiero que la detección de procesos sea extremadamente rigurosa y no pierda información, para que capturemos todos los procesos mencionados por los usuarios

#### Acceptance Criteria

1. THE Process Detection Agent SHALL usar una estrategia de múltiples capas para maximizar la detección
2. THE Process Detection Agent SHALL tolerar errores de tipeo, sinónimos y descripciones indirectas
3. WHEN la detección falla por timeout o error, THE System SHALL asumir que es un proceso para no perder información
4. THE System SHALL implementar retry automático en caso de fallos de detección
5. THE System SHALL registrar todas las detecciones en logs para auditoría posterior
6. THE Process Detection Agent SHALL completar el análisis en menos de 3 segundos
7. THE System SHALL ejecutar la detección en paralelo con la generación de la siguiente pregunta para no impactar performance
