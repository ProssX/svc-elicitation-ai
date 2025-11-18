# Sistema de Métricas - Elicitation AI

## 📊 Descripción General

Sistema de recolección de métricas en **tiempo real** y **persistencia histórica** para análisis de performance, engagement y comportamiento de entrevistas y detección de procesos.

**Arquitectura:** Dual-write pattern (memoria + PostgreSQL)
- **In-memory:** Métricas en tiempo real (deque + counters)
- **PostgreSQL:** Almacenamiento persistente para análisis histórico

---

## 🗄️ Tabla de Base de Datos

### `metric_event`

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id_event` | UUID | Primary Key |
| `event_type` | ENUM | Tipo de evento: `interview_started`, `interview_completed`, `detection_invoked` |
| `outcome` | ENUM | Resultado: `success`, `timeout`, `error`, `not_applicable` |
| `interview_id` | UUID | FK a `interview` (puede ser NULL en `interview_started`) |
| `employee_id` | UUID | **[DIMENSIONAL]** ID del empleado |
| `organization_id` | UUID | **[DIMENSIONAL]** ID de la organización |
| `language` | VARCHAR(5) | **[DIMENSIONAL]** Idioma de la entrevista (`es`, `en`, `pt`) |
| `latency_ms` | NUMERIC(10,2) | Latencia en milisegundos (detección/completion) |
| `confidence_score` | NUMERIC(4,3) | Score de confianza (0-1) para detección |
| `question_count` | INTEGER | Cantidad de preguntas realizadas |
| `early_finish` | BOOLEAN | Si la entrevista terminó antes del límite |
| `completion_reason` | VARCHAR(50) | Razón de finalización: `user_requested`, `agent_signaled`, `safety_limit` |
| `occurred_at` | TIMESTAMP | Momento del evento |
| `created_at` | TIMESTAMP | Momento de creación del registro |

**Índices optimizados para time-series queries:**
- `idx_metric_event_type_occurred` - (event_type, occurred_at)
- `idx_metric_event_org_type_occurred` - (organization_id, event_type, occurred_at)
- `idx_metric_event_emp_type_occurred` - (employee_id, event_type, occurred_at)
- 5 índices adicionales para filtrado dimensional

---

## 🔄 Cuándo se Activan los Eventos

### 1. `interview_started`
**Trigger:** POST `/api/v1/interviews/start`  
**Momento:** Inmediatamente después de guardar la primera pregunta del agente  
**Datos capturados:**
```python
{
    "event_type": "interview_started",
    "employee_id": "uuid-del-empleado",
    "organization_id": "uuid-de-organizacion",
    "language": "es"
}
```

### 2. `detection_invoked`
**Trigger:** Automático cuando el usuario menciona un proceso durante `POST /api/v1/interviews/continue`  
**Momento:** Después de invocar el servicio de detección semántica  
**Datos capturados:**
```python
{
    "event_type": "detection_invoked",
    "outcome": "success" | "timeout" | "error",
    "latency_ms": 5431.25,
    "confidence_score": 0.850  # Solo en success
}
```

### 3. `interview_completed`
**Trigger:** POST `/api/v1/interviews/continue` cuando `is_final=true`  
**Momento:** Cuando el agente decide finalizar o el usuario solicita terminar  
**Datos capturados:**
```python
{
    "event_type": "interview_completed",
    "employee_id": "uuid-del-empleado",
    "organization_id": "uuid-de-organizacion",
    "language": "es",
    "question_count": 5,
    "early_finish": true,
    "completion_reason": "user_requested"
}
```

---

## 📡 API Endpoints

### Métricas en Tiempo Real (In-Memory)
```bash
GET /api/v1/metrics
```
Retorna contadores actuales desde el inicio del servicio (volátil).

### Métricas Históricas (PostgreSQL)

#### General
```bash
GET /api/v1/metrics/historical?hours=24
```
Agregados de todos los eventos en las últimas N horas (1-720).

#### Detección de Procesos
```bash
GET /api/v1/metrics/detection/historical?hours=168
```
Métricas específicas de detección: latencias, timeouts, confidence scores, percentiles.

#### Completion de Entrevistas
```bash
GET /api/v1/metrics/completion/historical?hours=72
```
Métricas de finalización: question_count promedio, early_finish rate, distribution por completion_reason.

#### Reset (Solo In-Memory)
```bash
POST /api/v1/metrics/reset
```
Resetea contadores en memoria. **NO afecta base de datos.**

---

## 🚀 Cómo Explotar las Métricas a Futuro

### 1. **Dashboards de Performance por Organización**
```sql
SELECT 
    organization_id,
    COUNT(*) as total_interviews,
    AVG(question_count) as avg_questions,
    SUM(CASE WHEN early_finish THEN 1 ELSE 0 END)::float / COUNT(*) as early_finish_rate
FROM metric_event
WHERE event_type = 'interview_completed'
    AND occurred_at > NOW() - INTERVAL '7 days'
GROUP BY organization_id
ORDER BY total_interviews DESC;
```

### 2. **Análisis de Engagement por Empleado**
```sql
SELECT 
    employee_id,
    COUNT(*) as interviews_started,
    COUNT(CASE WHEN event_type = 'interview_completed' THEN 1 END) as interviews_completed,
    ROUND(COUNT(CASE WHEN event_type = 'interview_completed' THEN 1 END)::numeric / COUNT(*) * 100, 2) as completion_rate
FROM metric_event
WHERE event_type IN ('interview_started', 'interview_completed')
GROUP BY employee_id
HAVING COUNT(*) > 5
ORDER BY completion_rate DESC;
```

### 3. **Performance de Detección por Idioma**
```sql
SELECT 
    language,
    COUNT(*) as total_detections,
    AVG(latency_ms) as avg_latency_ms,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) as p95_latency,
    AVG(confidence_score) as avg_confidence
FROM metric_event
WHERE event_type = 'detection_invoked'
    AND outcome = 'success'
GROUP BY language;
```

### 4. **Análisis de Causas de Finalización**
```sql
SELECT 
    completion_reason,
    COUNT(*) as occurrences,
    AVG(question_count) as avg_questions,
    ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER () * 100, 2) as percentage
FROM metric_event
WHERE event_type = 'interview_completed'
    AND occurred_at > NOW() - INTERVAL '30 days'
GROUP BY completion_reason
ORDER BY occurrences DESC;
```

### 5. **Trending Temporal - Interviews por Día**
```sql
SELECT 
    DATE(occurred_at) as date,
    organization_id,
    COUNT(*) as daily_interviews
FROM metric_event
WHERE event_type = 'interview_started'
    AND occurred_at > NOW() - INTERVAL '90 days'
GROUP BY DATE(occurred_at), organization_id
ORDER BY date DESC, daily_interviews DESC;
```

---

## 🔧 Consideraciones Técnicas

### Fire-and-Forget Pattern
Los eventos se persisten usando `asyncio.create_task()` de forma **no bloqueante**:
- ✅ No impacta latencia de respuesta al usuario
- ✅ Errores de persistencia se loggean pero no fallan el request
- ⚠️ Posible pérdida de eventos en caso de crash antes de commit

### Datos Dimensionales
Los campos `employee_id`, `organization_id`, y `language` permiten:
- Segmentación por cliente/organización
- Análisis comparativo entre idiomas
- Tracking de usuarios individuales
- **Evita JOINs costosos** (datos denormalizados)

### Retención de Datos
Actualmente **sin política de retención**. Considerar:
- Particionamiento por fecha (monthly/quarterly)
- Archive a cold storage después de 1 año
- Agregación pre-calculada para queries históricas largas

### Índices Compuestos
Los índices `(organization_id, event_type, occurred_at)` y `(employee_id, event_type, occurred_at)` están optimizados para queries del tipo:
```sql
WHERE organization_id = ? AND event_type = ? AND occurred_at > ?
```

---

## 📝 Migraciones

- **`c3d4e5f6g7h8`**: Creación inicial de tabla `metric_event` con ENUMs
- **`d4e5f6g7h8i9`**: Agregado de columnas dimensionales (employee_id, organization_id, language) + 5 índices

Para aplicar migraciones:
```bash
docker exec svc-elicitation-ai alembic upgrade head
```

---

## 🎯 Roadmap Sugerido

1. **Dashboard en Grafana/Metabase** conectado a PostgreSQL
2. **Alertas automáticas** (ej: latency > 10s, error_rate > 5%)
3. **Export a Data Warehouse** para análisis cross-service
4. **Machine Learning** sobre confidence_scores para optimizar detección
5. **A/B Testing** usando métricas de completion_rate por variante

---

**Última actualización:** 2025-11-15  
**Owner:** Team Elicitation AI
