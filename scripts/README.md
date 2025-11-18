# Database Setup Scripts

Scripts para facilitar la configuración de la base de datos PostgreSQL.

## 🚀 Uso Rápido

### Windows (PowerShell)

```powershell
cd svc-elicitation-ai
.\scripts\setup-database.ps1
```

### Linux/Mac (Bash)

```bash
cd svc-elicitation-ai
chmod +x scripts/setup-database.sh
./scripts/setup-database.sh
```

## 📋 ¿Qué hace el script?

1. ✅ Verifica que Docker Desktop esté corriendo
2. 🐘 Inicia PostgreSQL en Docker
3. ⏳ Espera a que PostgreSQL esté listo (healthy)
4. 📊 Ejecuta las migraciones de Alembic (`alembic upgrade head`)
5. ✅ Confirma que todo está configurado correctamente

## 🔧 Comandos Manuales

Si prefieres ejecutar los pasos manualmente:

```bash
# 1. Verificar que Docker está corriendo
docker info

# 2. Iniciar PostgreSQL
docker-compose up -d postgres

# 3. Ver logs de PostgreSQL
docker-compose logs -f postgres
# Presiona Ctrl+C cuando veas: "database system is ready to accept connections"

# 4. Verificar que está corriendo
docker ps | grep postgres

# 5. Aplicar migraciones
python -m alembic upgrade head
```

## 📊 Comandos Útiles de Base de Datos

### Ver estado de PostgreSQL

```bash
docker-compose ps postgres
```

### Ver logs en tiempo real

```bash
docker-compose logs -f postgres
```

### Conectarse a la base de datos

```bash
docker exec -it postgres-elicitation psql -U postgres -d elicitation_ai
```

Comandos SQL útiles una vez conectado:

```sql
-- Ver todas las tablas
\dt

-- Describir una tabla
\d interview
\d interview_message

-- Ver datos
SELECT * FROM interview;
SELECT * FROM interview_message;

-- Salir
\q
```

### Detener PostgreSQL

```bash
docker-compose stop postgres
```

### Reiniciar PostgreSQL

```bash
docker-compose restart postgres
```

### Eliminar PostgreSQL y datos (⚠️ CUIDADO)

```bash
# Esto eliminará TODOS los datos de la base de datos
docker-compose down -v
```

## 🔄 Gestión de Migraciones

### Ver historial de migraciones

```bash
python -m alembic history
```

### Ver versión actual

```bash
python -m alembic current
```

### Aplicar todas las migraciones pendientes

```bash
python -m alembic upgrade head
```

### Revertir última migración

```bash
python -m alembic downgrade -1
```

### Revertir todas las migraciones

```bash
python -m alembic downgrade base
```

### Crear nueva migración (después de modificar modelos)

```bash
python -m alembic revision --autogenerate -m "descripcion_del_cambio"
```

## ❌ Troubleshooting

### Error: "Docker is not running"

**Solución:** Abre Docker Desktop y espera a que diga "Docker Desktop is running"

### Error: "No config file 'alembic.ini' found"

**Solución:** Asegúrate de estar en el directorio `svc-elicitation-ai`:

```bash
cd ~/Desktop/repos-tesis/svc-elicitation-ai
```

### Error: "ConnectionRefusedError"

**Solución:** PostgreSQL no está corriendo. Ejecuta:

```bash
docker-compose up -d postgres
```

### Error: "database does not exist"

**Solución:** El contenedor de PostgreSQL crea la base de datos automáticamente. Si el error persiste:

```bash
# Recrear el contenedor
docker-compose down
docker-compose up -d postgres
```

### PostgreSQL no inicia (unhealthy)

**Solución:** Ver los logs para diagnosticar:

```bash
docker-compose logs postgres
```

Causas comunes:
- Puerto 5432 ya en uso por otra instancia de PostgreSQL
- Permisos insuficientes en el volumen de datos
- Corrupción de datos (solución: `docker-compose down -v` y volver a crear)

## 📚 Recursos Adicionales

- [Documentación de Alembic](https://alembic.sqlalchemy.org/)
- [Documentación de PostgreSQL](https://www.postgresql.org/docs/)
- [Docker Compose Reference](https://docs.docker.com/compose/)
