import logging
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from strands import Agent
from app.models.db_models import InterviewProcessReference
from app.clients.backend_client import BackendClient
from app.repositories.interview_repository import InterviewRepository
from app.services.model_factory import create_model

logger = logging.getLogger(__name__)


class ProcessExtractionService:
    def __init__(
        self,
        db: AsyncSession,
        backend_client: BackendClient,
        interview_repository: InterviewRepository
    ):
        self.db = db
        self.backend_client = backend_client
        self.interview_repository = interview_repository
        self.model = create_model()
    
    async def extract_and_create_processes(
        self,
        interview_id: int,
        organization_id: int,
        auth_token: str
    ):
        logger.info(
            f"Starting process extraction for interview {interview_id}",
            extra={"interview_id": interview_id, "organization_id": organization_id}
        )
        
        try:
            from uuid import UUID
            interview_with_messages = await self.interview_repository.get_by_id_no_filter(UUID(interview_id))
            
            if not interview_with_messages or interview_with_messages.status != "completed":
                logger.warning(
                    f"Interview {interview_id} not found or not completed",
                    extra={"interview_id": interview_id}
                )
                return
            
            from app.repositories.message_repository import MessageRepository
            message_repo = MessageRepository(self.db)
            messages = await message_repo.get_by_interview(UUID(interview_id))
            
            extracted_processes = await self._extract_processes_from_messages(
                messages,
                organization_id
            )
            
            if not extracted_processes:
                logger.info(
                    f"No processes extracted from interview {interview_id}",
                    extra={"interview_id": interview_id}
                )
                return
            
            existing_processes = await self.backend_client.get_organization_processes(
                organization_id=str(organization_id),
                auth_token=auth_token,
                active_only=False,
                limit=1000
            )
            
            deduplicated_processes = await self._deduplicate_processes(
                extracted_processes,
                existing_processes,
                organization_id
            )
            
            for process_data in deduplicated_processes:
                created_process = await self.backend_client.create_process(
                    organization_id=str(organization_id),
                    auth_token=auth_token,
                    process_data=process_data
                )
                
                if created_process:
                    from uuid import UUID as UUIDType
                    process_ref = InterviewProcessReference(
                        interview_id=UUID(interview_id),
                        process_id=UUIDType(created_process["id"]),
                        is_new_process=True,
                        confidence_score=process_data.get("confidence_score", 0.8)
                    )
                    self.db.add(process_ref)
            
            await self.db.flush()
            
            logger.info(
                f"Successfully extracted and created {len(deduplicated_processes)} processes",
                extra={
                    "interview_id": interview_id,
                    "processes_created": len(deduplicated_processes)
                }
            )
        
        except Exception as e:
            logger.error(
                f"Failed to extract processes for interview {interview_id}: {e}",
                extra={"interview_id": interview_id, "error": str(e)},
                exc_info=True
            )
            raise
    
    async def _extract_processes_from_messages(
        self,
        messages: List,
        organization_id: int
    ) -> List[Dict[str, Any]]:
        if not messages:
            return []
        
        conversation_text = "\n\n".join([
            f"{msg.role.value.upper()}: {msg.content}"
            for msg in messages
        ])
        
        extraction_prompt = f"""Analiza la siguiente entrevista de elicitación de requisitos y extrae TODOS los procesos de negocio mencionados.

Para cada proceso, proporciona:
- name: Nombre descriptivo del proceso (ej: "Gestión de Pedidos", "Aprobación de Facturas")
- description: Descripción detallada del proceso basada en lo discutido en la entrevista
- type: Tipo de proceso. DEBE ser uno de estos valores:
  * "S" = Soporte (procesos que asisten a otros procesos, como IT, RRHH, mantenimiento)
  * "E" = Estratégico (procesos que definen dirección y objetivos, como planificación, gestión)
  * "C" = Crítico (procesos esenciales para el funcionamiento, como producción, ventas, entregas)
- mentioned_count: Número de veces que se menciona o discute el proceso
- confidence_score: Tu confianza de que esto sea realmente un proceso (0.0 a 1.0)

CONVERSACIÓN:
{conversation_text}

Responde ÚNICAMENTE con un JSON array de procesos. Ejemplo:
[
  {{
    "name": "Gestión de Inventario",
    "description": "Proceso para controlar el stock de productos y coordinar reposiciones",
    "type": "C",
    "mentioned_count": 3,
    "confidence_score": 0.95
  }},
  {{
    "name": "Soporte Técnico",
    "description": "Proceso de asistencia técnica a usuarios internos",
    "type": "S",
    "mentioned_count": 2,
    "confidence_score": 0.88
  }}
]

IMPORTANTE: El campo "type" es OBLIGATORIO y DEBE ser "S", "E" o "C".
Si no encuentras procesos, responde con un array vacío: []
"""
        
        agent = Agent(model=self.model, system_prompt="Eres un asistente que extrae procesos de negocio de entrevistas.")
        response = agent(extraction_prompt)
        
        content = response.message.get('content', [])
        text = content[0].get('text', '') if content and len(content) > 0 else ""
        
        if not text:
            text = str(response.message)
        
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        import json
        try:
            processes = json.loads(text)
            if not isinstance(processes, list):
                logger.warning("LLM response is not a list, returning empty")
                return []
            
            return [p for p in processes if p.get("confidence_score", 0) >= 0.7]
        
        except json.JSONDecodeError as e:
            logger.error(
                f"Failed to parse LLM response as JSON: {e}",
                extra={"raw_response": text}
            )
            return []
    
    async def _deduplicate_processes(
        self,
        extracted_processes: List[Dict[str, Any]],
        existing_processes: List[Dict[str, Any]],
        organization_id: int
    ) -> List[Dict[str, Any]]:
        if not existing_processes:
            return extracted_processes
        
        deduplicated = []
        
        for extracted in extracted_processes:
            is_duplicate = await self._is_duplicate_process(
                extracted,
                existing_processes
            )
            
            if not is_duplicate:
                deduplicated.append(extracted)
            else:
                logger.info(
                    f"Skipping duplicate process: {extracted['name']}",
                    extra={"process_name": extracted["name"]}
                )
        
        return deduplicated
    
    async def _is_duplicate_process(
        self,
        extracted_process: Dict[str, Any],
        existing_processes: List[Dict[str, Any]]
    ) -> bool:
        extracted_name = extracted_process["name"].lower()
        
        for existing in existing_processes:
            existing_name = existing.get("name", "").lower()
            
            if extracted_name == existing_name:
                return True
            
            if extracted_name in existing_name or existing_name in extracted_name:
                similarity_prompt = f"""Determina si estos dos procesos son el mismo o muy similares:

PROCESO 1: {extracted_process['name']}
Descripción: {extracted_process.get('description', 'N/A')}

PROCESO 2: {existing['name']}
Descripción: {existing.get('description', 'N/A')}

Responde ÚNICAMENTE con 'yes' si son el mismo proceso o 'no' si son diferentes.
"""
                
                agent = Agent(model=self.model, system_prompt="Eres un asistente que compara procesos de negocio.")
                response = agent(similarity_prompt)
                
                content = response.message.get('content', [])
                answer = content[0].get('text', '') if content and len(content) > 0 else ""
                if not answer:
                    answer = str(response.message)
                answer = answer.strip().lower()
                
                if answer == "yes":
                    return True
        
        return False
