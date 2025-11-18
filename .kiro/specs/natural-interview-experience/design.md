# Design Document

## Overview

Este documento describe el diseño para mejorar la experiencia de entrevista del sistema de elicitación de IA, haciéndola más natural, accesible y precisa. El diseño se enfoca en dos áreas principales:

1. **Mejora del System Prompt**: Hacer la presentación y el lenguaje del agente más accesible para cualquier tipo de usuario
2. **Mejora de la Detección de Procesos**: Reemplazar el sistema de keywords hardcodeadas por análisis semántico basado en IA

### Current State

**System Prompt Actual**:
- El agente se presenta como "Analista de Sistemas Senior"
- Usa terminología técnica como "proceso", "procedimiento", "flujo"
- Asume que el usuario entiende conceptos de análisis de sistemas

**Detección de Procesos Actual**:
- Función `_mentions_process()` en `agent_service.py` usa keywords hardcodeadas
- Lista fija de palabras en español, inglés y portugués
- No tolera errores de tipeo ni sinónimos
- No comprende contexto ni descripciones indirectas

### Proposed State

**System Prompt Mejorado**:
- Presentación sin títulos técnicos, más como "asistente" o "ayudante"
- Preguntas abiertas sobre "día a día" y "tareas" en lugar de "procesos"
- Adaptación dinámica al vocabulario del usuario
- Lenguaje más natural y conversacional

**Detección de Procesos Mejorada**:
- El `ProcessMatchingAgent` existente se reutiliza para detección en tiempo real
- Análisis semántico de cada respuesta del usuario
- Tolerancia a errores, sinónimos y lenguaje informal
- Confidence scoring para decisiones informadas

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Interview Service                         │
│                                                              │
│  ┌────────────────┐         ┌──────────────────────┐       │
│  │ Interview      │         │ Process Detection    │       │
│  │ Agent          │────────▶│ Agent                │       │
│  │                │         │ (Semantic Analysis)  │       │
│  └────────────────┘         └──────────────────────┘       │
│         │                              │                    │
│         │                              │                    │
│         ▼                              ▼                    │
│  ┌────────────────┐         ┌──────────────────────┐       │
│  │ Improved       │         │ Process Matching     │       │
│  │ System Prompts │         │ Results              │       │
│  └────────────────┘         └──────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

### Component Interaction Flow

```
User Response
     │
     ▼
┌─────────────────────────┐
│ Interview Service       │
│ continue_interview()    │
└─────────────────────────┘
     │
     ├──────────────────────────────────────┐
     │                                      │
     ▼                                      ▼
┌─────────────────────────┐    ┌──────────────────────────┐
│ Interview Agent         │    │ Process Detection Agent  │
│ (with improved prompt)  │    │ (semantic analysis)      │
└─────────────────────────┘    └──────────────────────────┘
     │                                      │
     │                                      │
     ▼                                      ▼
┌─────────────────────────┐    ┌──────────────────────────┐
│ Next Question           │    │ Process Match Result     │
│ (natural language)      │    │ (with confidence)        │
└─────────────────────────┘    └──────────────────────────┘
```

## Components and Interfaces

### 1. Improved System Prompts

**Location**: `prompts/system_prompts.py`

**Changes Required**:

```python
# BEFORE (Current)
"Sos un **Analista de Sistemas Senior** especializado en..."

# AFTER (Improved)
"Soy tu asistente para entender mejor tu trabajo en {organization}..."
```

**Key Modifications**:

1. **Presentación sin títulos técnicos**:
   - Eliminar "Analista de Sistemas Senior"
   - Usar "asistente", "ayudante" o simplemente el nombre "Agente ProssX"

2. **Preguntas más abiertas**:
   - Cambiar "¿Qué procesos ejecutás?" por "¿Cómo es tu día a día?"
   - Cambiar "¿Qué procedimientos seguís?" por "¿Qué tareas realizás habitualmente?"
   - Usar "actividades" en lugar de "procesos" inicialmente

3. **Adaptación dinámica**:
   - Instrucción al agente: "Si el usuario usa la palabra 'proceso', podés usarla también"
   - Instrucción al agente: "Adaptá tu vocabulario al que usa el usuario"

4. **Control dinámico de finalización** (NUEVO):
   - **Eliminar límites mínimos y máximos de preguntas hardcodeados**
   - El agente decide cuándo finalizar basándose en:
     - Completitud de la información recopilada (al menos 2-3 procesos con detalles)
     - Señales explícitas del usuario ("eso es todo", "quiero finalizar", "no tengo más")
     - Señales implícitas (respuestas muy cortas, falta de detalles nuevos)
   - **Instrucciones al agente**:
     - "Si detectás que el usuario quiere terminar o sus respuestas indican que ya no tiene más información, preguntá: '¿Hay algo más que quieras contarme o ya cubrimos todo?'"
     - "Si el usuario dice explícitamente que ya terminó o quiere finalizar, finalizá la entrevista inmediatamente sin insistir"
     - "Tu objetivo es obtener información completa de al menos 2-3 procesos, pero si el usuario no tiene más o quiere parar, respetá su decisión"
     - "Usá tu criterio profesional para determinar cuándo tenés suficiente información"
   - **Eliminación de límites rígidos**:
     - Remover `min_questions` y `max_questions` del prompt
     - El agente usa su inteligencia para determinar la completitud
     - Solo mantener un límite absoluto de seguridad en el código (ej: 50 preguntas) para evitar loops infinitos

**Interface**:

```python
def get_interviewer_prompt(
    user_name: str,
    user_role: str,
    organization: str,
    technical_level: str = "unknown",
    language: str = "es"
) -> str:
    """
    Genera system prompt con lenguaje natural y accesible
    
    Returns:
        str: System prompt sin terminología técnica innecesaria
    """
```

### 2. Process Detection Agent

**Location**: `app/services/agent_service.py`

**Current Implementation**:

```python
def _mentions_process(self, text: str) -> bool:
    """Keyword-based detection"""
    process_keywords = [
        "proceso", "procedimiento", "flujo", ...
    ]
    return any(keyword in text.lower() for keyword in process_keywords)
```

**New Implementation**:

```python
async def _detect_process_mention(
    self,
    user_response: str,
    language: str,
    context: Optional[InterviewContextData] = None
) -> ProcessDetectionResult:
    """
    Semantic analysis-based detection using ProcessMatchingAgent
    
    Args:
        user_response: User's response text
        language: Interview language
        context: Interview context (optional, for matching)
        
    Returns:
        ProcessDetectionResult with:
        - is_process_mentioned: bool
        - confidence_score: float
        - process_type: str (new/existing/unclear)
        - matched_process_id: Optional[str]
    """
```

**Strategy - DETECCIÓN RIGUROSA Y PROFESIONAL**:

La detección de procesos es el núcleo del sistema y debe ser **extremadamente rigurosa** sin comprometer performance. Estrategia de múltiples capas:

**Capa 1: Pre-filtro Heurístico Amplio (Sincrónico, <1ms)**
- **Objetivo**: Capturar TODO lo que podría ser un proceso
- **Estrategia**: Usar keywords MUY amplias y permisivas
- **Keywords expandidas**:
  - Verbos de acción: "hacer", "realizo", "ejecuto", "trabajo", "gestiono", "manejo", "administro", "coordino", "superviso"
  - Sustantivos: "tarea", "actividad", "responsabilidad", "función", "operación", "rutina"
  - Contextuales: "cuando", "si", "cada vez que", "todos los días", "semanalmente"
- **Umbral**: MUY bajo - si hay cualquier indicio, pasar a Capa 2
- **Falsos positivos**: Aceptables aquí, se filtran en Capa 2

**Capa 2: Análisis Semántico Completo (Asíncrono, ~500ms-1s)**
- **Objetivo**: Determinar con precisión si es un proceso
- **Estrategia**: Invocar `ProcessMatchingAgent` con prompt especializado
- **Análisis profundo**:
  - ¿Describe una secuencia de pasos?
  - ¿Menciona inputs/outputs?
  - ¿Involucra decisiones o aprobaciones?
  - ¿Es repetible y estructurado?
- **Tolerancia a errores**:
  - Typos: "procezo", "proseso", "proceo"
  - Sinónimos: "flujo de trabajo", "procedimiento", "metodología"
  - Descripciones indirectas: "lo que hago es...", "mi trabajo consiste en..."
- **Confidence scoring**: 0.0 a 1.0
  - >0.8: Definitivamente un proceso
  - 0.5-0.8: Probablemente un proceso
  - <0.5: Poco claro o no es un proceso

**Capa 3: Validación Contextual (Opcional)**
- Si confidence < 0.7, considerar contexto de conversación
- Analizar respuestas anteriores para contexto adicional
- Si aún no está claro, marcar para seguimiento

**Garantías de No Pérdida**:
1. **Timeout generoso**: 3 segundos (vs 2s anterior) para análisis completo
2. **Retry en errores**: Un reintento automático si falla la primera vez
3. **Fallback inteligente**: Si falla todo, asumir que SÍ es un proceso (mejor falso positivo que perder información)
4. **Logging exhaustivo**: Registrar TODAS las detecciones para auditoría posterior

**Performance**:
- Capa 1 ejecuta en TODAS las respuestas (<1ms, no impacta)
- Capa 2 ejecuta solo cuando Capa 1 detecta algo (~50-70% de respuestas)
- Ejecución en paralelo con generación de siguiente pregunta
- Timeout de 3s garantiza que no bloquea la conversación

### 3. Process Detection Result Model

**Location**: `app/models/interview.py`

**New Model**:

```python
class ProcessDetectionResult(BaseModel):
    """
    Result of process detection analysis
    
    Attributes:
        is_process_mentioned: Whether user mentioned a process
        confidence_score: Confidence level (0.0 to 1.0)
        process_type: Type of process (new/existing/unclear)
        matched_process_id: ID if matched to existing process
        matched_process_name: Name if matched
        reasoning: Explanation of detection
    """
    is_process_mentioned: bool
    confidence_score: float
    process_type: str  # "new", "existing", "unclear"
    matched_process_id: Optional[str] = None
    matched_process_name: Optional[str] = None
    reasoning: str
```

### 4. Dynamic Interview Completion Logic

**Location**: `app/services/agent_service.py`

**Current Implementation**:

```python
def _should_finish_interview(
    self,
    question_number: int,
    context: InterviewContext,
    user_response: str,
    agent_question: str
) -> bool:
    """Checks min/max questions and explicit user signals"""
    if question_number >= settings.max_questions:
        return True
    if question_number < settings.min_questions:
        return False
    # ... more logic
```

**New Implementation - CONTROL DINÁMICO INTELIGENTE**:

```python
def _should_finish_interview(
    self,
    question_number: int,
    context: InterviewContext,
    user_response: str,
    agent_question: str,
    conversation_history: List[ConversationMessage]
) -> bool:
    """
    Intelligent dynamic completion - agent decides based on content quality
    
    NO MORE MIN/MAX QUESTIONS - Agent uses professional judgment
    
    Args:
        question_number: Current question number (for safety limit only)
        context: Interview context with processes identified
        user_response: Latest user response
        agent_question: Agent's generated question
        conversation_history: Full conversation for analysis
        
    Returns:
        bool: True if interview should end
    """
    # 1. SAFETY LIMIT: Absolute maximum to prevent infinite loops
    if question_number >= settings.max_questions_safety_limit:
        logger.warning(f"Safety limit reached: {question_number} questions")
        return True
    
    # 2. EXPLICIT USER SIGNALS: User wants to finish
    end_keywords = {
        "es": ["quiero terminar", "vamos a terminar", "terminemos", 
               "finalizar", "eso es todo", "no tengo más", "ya está"],
        "en": ["let's finish", "i want to finish", "that's all", 
               "nothing more", "i'm done"],
        "pt": ["vamos terminar", "quero terminar", "é tudo", 
               "não tenho mais", "já chega"]
    }
    
    response_lower = user_response.lower()
    for lang_keywords in end_keywords.values():
        if any(keyword in response_lower for keyword in lang_keywords):
            logger.info("User explicitly requested to finish")
            return True
    
    # 3. AGENT SIGNALS: Agent generated closing message
    closing_signals = {
        "es": ["gracias por tu tiempo", "muchas gracias", "quedó registrada"],
        "en": ["thank you for your time", "has been recorded"],
        "pt": ["obrigado pelo seu tempo", "foi registrada"]
    }
    
    question_lower = agent_question.lower()
    for lang_signals in closing_signals.values():
        if any(signal in question_lower for signal in lang_signals):
            logger.info("Agent signaled completion")
            return True
    
    # 4. NO MINIMUM - Agent decides based on content quality
    # The agent's system prompt instructs it to gather 2-3 complete processes
    # but respects user's decision if they want to stop earlier
    
    return False  # Continue by default - trust agent's judgment
```

**Key Changes**:
- Eliminar `min_questions` del código
- Eliminar `max_questions` del código (reemplazar con `max_questions_safety_limit`)
- El agente decide cuándo tiene suficiente información
- Respetar señales explícitas del usuario inmediatamente
- Detectar señales del agente (mensajes de cierre)
- Safety limit solo para prevenir loops infinitos (50 preguntas)

### 4. Enhanced ProcessMatchingAgent

**Location**: `app/services/process_matching_agent.py`

**Current Capability**:
- Ya existe y funciona bien
- Hace matching contra procesos existentes
- Retorna confidence score y reasoning

**Enhancement Required**:

Agregar un método adicional para detección sin matching:

```python
async def detect_process_mention(
    self,
    user_response: str,
    language: str = "es"
) -> ProcessDetectionResult:
    """
    Detect if user response mentions a process (without matching)
    
    This is a lighter operation than full matching, used when
    there are no existing processes or we just want to detect
    if a process is being described.
    
    Args:
        user_response: User's response text
        language: Interview language
        
    Returns:
        ProcessDetectionResult indicating if a process was mentioned
    """
```

**Prompt for Detection**:

```python
def _build_detection_prompt(user_response: str, language: str) -> str:
    """
    Build prompt for process detection (without matching)
    
    Asks LLM to determine if the user is describing a business
    process, workflow, or activity that should be captured.
    """
```

## Data Models

### ProcessDetectionResult

```python
class ProcessDetectionResult(BaseModel):
    """Result of semantic process detection"""
    is_process_mentioned: bool
    confidence_score: float  # 0.0 to 1.0
    process_type: str  # "new", "existing", "unclear"
    matched_process_id: Optional[str] = None
    matched_process_name: Optional[str] = None
    reasoning: str
    suggested_follow_up: Optional[str] = None  # Suggested question
```

### Updated InterviewResponse

```python
class InterviewResponse(BaseModel):
    """Response from interview agent"""
    question: str
    question_number: int
    is_final: bool
    context: InterviewContext
    process_matches: List[ProcessMatchInfo]
    
    # NEW: Add detection result
    process_detection: Optional[ProcessDetectionResult] = None
```

## Error Handling

### Timeout Handling

**Scenario**: Process detection takes too long

**Strategy - RIGUROSA Y SIN PÉRDIDA**:
- Timeout generoso: 3 segundos (configurable)
- **Fallback inteligente**: En caso de timeout, **asumir que SÍ es un proceso** (mejor falso positivo que perder información)
- Retry automático: Un intento adicional antes de timeout final
- Log detallado para análisis posterior

```python
try:
    # Primer intento
    result = await asyncio.wait_for(
        self._detect_process_mention(...),
        timeout=settings.process_detection_timeout
    )
except asyncio.TimeoutError:
    logger.warning("Process detection timeout - retrying once")
    try:
        # Segundo intento con timeout más corto
        result = await asyncio.wait_for(
            self._detect_process_mention(...),
            timeout=1.5
        )
    except asyncio.TimeoutError:
        logger.error("Process detection timeout after retry - assuming process mention")
        # FALLBACK INTELIGENTE: Asumir que es un proceso
        return ProcessDetectionResult(
            is_process_mentioned=True,  # Mejor falso positivo que perder info
            confidence_score=0.5,  # Confidence medio por incertidumbre
            process_type="unclear",
            reasoning="Detection timeout - assumed process for safety"
        )
```

### LLM Errors

**Scenario**: LLM returns invalid JSON or fails

**Strategy - RIGUROSA Y SIN PÉRDIDA**:
- Catch JSON parsing errors
- **Fallback inteligente**: Asumir que SÍ es un proceso (no perder información)
- Retry con prompt simplificado
- Log error para debugging
- Continue interview sin interrupciones

```python
try:
    detection_data = self._parse_json_response(response_text)
except Exception as e:
    logger.error(f"Failed to parse detection response: {e}")
    # Retry con prompt más simple
    try:
        simplified_result = await self._simple_detection_fallback(user_response, language)
        return simplified_result
    except Exception as e2:
        logger.error(f"Fallback detection also failed: {e2}")
        # FALLBACK FINAL: Asumir proceso
        return ProcessDetectionResult(
            is_process_mentioned=True,  # No perder información
            confidence_score=0.5,
            process_type="unclear",
            reasoning="Parse error - assumed process for safety"
        )
```

### Graceful Degradation

**Scenario**: Process detection feature fails completely

**Strategy**:
- Feature flag: `enable_semantic_process_detection`
- If disabled or fails, fall back to keyword-based detection
- Interview continues normally
- User experience not impacted

```python
if settings.enable_semantic_process_detection:
    try:
        result = await self._detect_process_mention(...)
    except Exception as e:
        logger.error(f"Semantic detection failed: {e}")
        # Fallback to keyword detection
        result = self._keyword_based_detection(...)
else:
    result = self._keyword_based_detection(...)
```

## Testing Strategy

### Unit Tests

**Test Coverage**:

1. **System Prompt Generation**:
   - Test that prompts don't contain "Analista Senior"
   - Test that prompts use natural language
   - Test multi-language support (es/en/pt)

2. **Process Detection**:
   - Test detection with clear process mentions
   - Test detection with typos ("procezo", "proseso")
   - Test detection with synonyms ("actividad", "tarea", "flujo")
   - Test detection with indirect descriptions
   - Test false positives (non-process mentions)

3. **Confidence Scoring**:
   - Test high confidence scenarios (>0.8)
   - Test medium confidence scenarios (0.5-0.8)
   - Test low confidence scenarios (<0.5)

4. **Error Handling**:
   - Test timeout scenarios
   - Test JSON parsing errors
   - Test LLM failures
   - Test graceful degradation

### Integration Tests

**Test Scenarios**:

1. **Full Interview Flow with Improved Prompts**:
   - Start interview with new prompt
   - Verify agent doesn't use technical titles
   - Verify questions are open-ended

2. **Process Detection in Interview**:
   - User mentions process with typo
   - Verify detection works
   - Verify interview continues smoothly

3. **Process Matching Integration**:
   - User mentions existing process
   - Verify detection + matching works together
   - Verify process reference is created

### Manual Testing

**Test Cases**:

1. **User with No Technical Background**:
   - Conduct interview as non-technical user
   - Verify language is accessible
   - Verify no confusion about terminology

2. **User with Typos and Informal Language**:
   - Provide responses with typos
   - Use colloquial expressions
   - Verify detection still works

3. **Multi-Language Testing**:
   - Test in Spanish, English, Portuguese
   - Verify prompts are natural in each language
   - Verify detection works in each language

## Performance Considerations

### Latency Impact

**Current State**:
- Keyword detection: <1ms (synchronous)
- Process matching: ~500ms-1s (when invoked)

**New State**:
- Phase 1 (heuristic): <1ms (synchronous)
- Phase 2 (semantic): ~500ms-1s (only when Phase 1 triggers)

**Optimization Strategy**:
- Use heuristic filter to reduce LLM calls
- Set aggressive timeout (2s) for detection
- Cache detection results per response
- Run detection in parallel with agent response generation

### Token Usage

**Impact**:
- Detection prompt: ~200-300 tokens
- Detection response: ~100-150 tokens
- Total per detection: ~300-450 tokens

**Mitigation**:
- Only invoke when heuristic suggests process mention
- Use smaller model for detection if available
- Batch multiple detections if possible

### Scalability

**Considerations**:
- Detection adds one LLM call per user response (when triggered)
- With 100 concurrent interviews, ~50 detection calls/minute (assuming 50% trigger rate)
- Current infrastructure should handle this load

**Monitoring**:
- Track detection invocation rate
- Monitor detection latency
- Alert on high timeout rates

## Configuration

### Feature Flags

```python
# config.py

# Enable semantic process detection (vs keyword-based)
enable_semantic_process_detection: bool = True

# Timeout for process detection (seconds) - AUMENTADO para detección rigurosa
process_detection_timeout: float = 3.0

# Confidence threshold for process detection
process_detection_confidence_threshold: float = 0.6

# Enable improved system prompts
enable_improved_prompts: bool = True

# Enable dynamic interview completion (agent decides when to finish)
enable_dynamic_completion: bool = True

# Safety limit for maximum questions (to prevent infinite loops)
max_questions_safety_limit: int = 50

# Enable retry on detection failures
enable_detection_retry: bool = True
```

### Environment Variables

```bash
# .env

# Feature flags
ENABLE_SEMANTIC_PROCESS_DETECTION=true
ENABLE_IMPROVED_PROMPTS=true
ENABLE_DYNAMIC_COMPLETION=true
ENABLE_DETECTION_RETRY=true

# Timeouts (aumentado para detección rigurosa)
PROCESS_DETECTION_TIMEOUT=3.0

# Thresholds
PROCESS_DETECTION_CONFIDENCE_THRESHOLD=0.6

# Safety limits
MAX_QUESTIONS_SAFETY_LIMIT=50
```

## Migration Strategy

### Phase 1: Improved Prompts (Low Risk)

1. Update `system_prompts.py` with new prompts
2. Add feature flag `enable_improved_prompts`
3. Deploy with flag disabled
4. Enable for 10% of interviews (A/B test)
5. Monitor user feedback and completion rates
6. Gradually increase to 100%

### Phase 2: Semantic Detection (Medium Risk)

1. Implement `detect_process_mention()` in `ProcessMatchingAgent`
2. Add feature flag `enable_semantic_process_detection`
3. Deploy with flag disabled
4. Enable for 10% of interviews
5. Monitor detection accuracy and latency
6. Gradually increase to 100%
7. Remove keyword-based detection after validation

### Rollback Plan

**If Issues Arise**:
1. Disable feature flag immediately
2. System reverts to previous behavior
3. No data loss or corruption
4. Investigate and fix issues
5. Re-enable when ready

## Security Considerations

### Input Validation

**User Responses**:
- Validate max length (prevent token overflow)
- Sanitize for injection attacks
- Rate limit detection calls per user

### LLM Output Validation

**Detection Results**:
- Validate JSON structure
- Validate confidence score range (0.0-1.0)
- Validate process_type enum values
- Sanitize reasoning text

### Data Privacy

**User Data**:
- User responses sent to LLM for detection
- Ensure compliance with data privacy policies
- Log only necessary information
- Redact sensitive data in logs

## Monitoring and Observability

### Metrics to Track

1. **Prompt Effectiveness**:
   - Interview completion rate (before/after)
   - Average questions per interview
   - User satisfaction (if available)

2. **Detection Performance**:
   - Detection invocation rate
   - Detection latency (p50, p95, p99)
   - Timeout rate
   - Error rate

3. **Detection Accuracy**:
   - True positive rate (manual validation)
   - False positive rate
   - Confidence score distribution

### Logging

**Log Events**:
- Process detection invoked
- Detection result (with confidence)
- Detection timeout
- Detection error
- Fallback to keyword detection

**Log Format**:
```python
logger.info(
    "[PROCESS_DETECTION] Semantic detection completed",
    extra={
        "interview_id": str(interview_id),
        "is_detected": result.is_process_mentioned,
        "confidence": result.confidence_score,
        "process_type": result.process_type,
        "latency_ms": elapsed_ms,
        "success": True
    }
)
```

## Future Enhancements

### 1. Adaptive Prompts

**Concept**: Adjust prompt based on user's responses

**Implementation**:
- Track user's vocabulary usage
- Dynamically adjust prompt mid-interview
- Use more technical terms if user does
- Use simpler terms if user struggles

### 2. Multi-Turn Detection

**Concept**: Detect processes across multiple responses

**Implementation**:
- Maintain conversation context
- Detect when user describes process over multiple turns
- Aggregate information before creating process reference

### 3. Confidence-Based Follow-Up

**Concept**: Ask clarifying questions when confidence is low

**Implementation**:
- If confidence < 0.6, generate clarifying question
- Agent asks: "¿Te referís a un proceso específico o es parte de tu rutina diaria?"
- Improves detection accuracy

### 4. Learning from Corrections

**Concept**: Learn from user corrections and feedback

**Implementation**:
- Track when users correct the agent
- Use corrections to improve prompts
- Fine-tune detection model over time

## Dependencies

### External Libraries

- `strands`: Agent framework (already in use)
- `asyncio`: Async operations (already in use)
- `pydantic`: Data validation (already in use)

### Internal Services

- `ProcessMatchingAgent`: Reused for detection
- `PromptBuilder`: Enhanced with new prompts
- `InterviewService`: Orchestrates detection flow

### Configuration

- Feature flags in `config.py`
- Environment variables in `.env`
- Timeout and threshold settings

## Risks and Mitigation

### Risk 1: Increased Latency

**Impact**: Medium
**Probability**: Medium

**Mitigation**:
- Aggressive timeouts (2s)
- Heuristic pre-filter
- Parallel execution
- Monitoring and alerts

### Risk 2: Detection Accuracy

**Impact**: High
**Probability**: Low

**Mitigation**:
- Extensive testing
- Confidence thresholds
- Manual validation
- Gradual rollout

### Risk 3: User Confusion

**Impact**: Medium
**Probability**: Low

**Mitigation**:
- A/B testing
- User feedback collection
- Quick rollback capability
- Iterative improvements

### Risk 4: Cost Increase

**Impact**: Low
**Probability**: High

**Mitigation**:
- Heuristic filter reduces LLM calls
- Use smaller model for detection
- Monitor token usage
- Set budget alerts

## Success Criteria

### Quantitative Metrics

1. **Interview Completion Rate**: Increase by 10%
2. **Detection Accuracy**: >85% true positive rate
3. **Detection Latency**: p95 < 1.5s
4. **Timeout Rate**: <5%
5. **Error Rate**: <1%

### Qualitative Metrics

1. **User Feedback**: Positive sentiment about natural language
2. **Agent Behavior**: More natural and accessible conversations
3. **Process Coverage**: Better detection of informal process descriptions
4. **Developer Experience**: Easier to maintain and extend

## Conclusion

Este diseño proporciona una solución completa para mejorar la experiencia de entrevista mediante:

1. **Prompts más naturales y accesibles** que eliminan barreras de terminología técnica
2. **Detección semántica de procesos** que es más robusta y flexible que keywords hardcodeadas
3. **Reutilización del `ProcessMatchingAgent` existente** para minimizar cambios arquitectónicos
4. **Estrategia de rollout gradual** con feature flags para mitigar riesgos
5. **Monitoreo y observabilidad** para validar mejoras y detectar problemas

La implementación será incremental, comenzando con los prompts mejorados (bajo riesgo) y luego agregando la detección semántica (riesgo medio), con capacidad de rollback en cada fase.
