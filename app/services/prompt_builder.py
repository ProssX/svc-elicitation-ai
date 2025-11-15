"""
Prompt Builder Service for Context-Aware Interviews - REFACTORED

This service builds system prompts that include contextual information
about the employee, organization, and existing processes to enable
context-aware interviewing.

REFACTORED: Now uses prompts from system_prompts.py to respect feature flags
for improved natural language prompts vs legacy technical prompts.
"""
from typing import List, Optional
from app.models.context import (
    InterviewContextData,
    ProcessContextData,
    InterviewHistorySummary
)
from app.config import settings
from prompts.system_prompts import get_interviewer_prompt


class PromptBuilder:
    """
    Builds context-aware system prompts for interview agents
    
    This service generates prompts that include:
    - Employee information and roles
    - Organization's existing processes
    - Interview history summary
    - Process matching instructions
    
    Now uses system_prompts.py to respect feature flags for improved prompts.
    """
    
    @staticmethod
    def build_interview_prompt(
        context: InterviewContextData,
        language: str = "es"
    ) -> str:
        """
        Build system prompt with enriched context
        
        Creates a comprehensive system prompt that includes employee context,
        existing processes, and interview history to enable the agent to
        conduct context-aware interviews.
        
        Args:
            context: Complete interview context data
            language: Interview language (es/en/pt)
            
        Returns:
            str: Complete system prompt with context
        """
        # Get base prompt components based on language
        if language == "es":
            return PromptBuilder._build_spanish_prompt(context)
        elif language == "en":
            return PromptBuilder._build_english_prompt(context)
        elif language == "pt":
            return PromptBuilder._build_portuguese_prompt(context)
        else:
            # Default to Spanish
            return PromptBuilder._build_spanish_prompt(context)
    
    @staticmethod
    def build_process_matching_prompt(
        process_description: str,
        existing_processes: List[ProcessContextData],
        language: str = "es"
    ) -> str:
        """
        Build prompt for process matching agent
        
        Creates a specialized prompt for the process matching agent to
        determine if a user's process description matches any existing
        processes in the organization.
        
        Args:
            process_description: User's description of a process
            existing_processes: List of existing processes in organization
            language: Interview language (es/en/pt)
            
        Returns:
            str: System prompt for process matching
        """
        if language == "es":
            return PromptBuilder._build_spanish_matching_prompt(
                process_description, existing_processes
            )
        elif language == "en":
            return PromptBuilder._build_english_matching_prompt(
                process_description, existing_processes
            )
        elif language == "pt":
            return PromptBuilder._build_portuguese_matching_prompt(
                process_description, existing_processes
            )
        else:
            return PromptBuilder._build_spanish_matching_prompt(
                process_description, existing_processes
            )
    
    @staticmethod
    def format_process_list(
        processes: List[ProcessContextData],
        language: str = "es"
    ) -> str:
        """
        Format process list for inclusion in prompt
        
        Creates a formatted list of existing processes that can be
        included in the system prompt.
        
        Args:
            processes: List of processes to format
            language: Interview language (es/en/pt)
            
        Returns:
            str: Formatted process list
        """
        if not processes:
            if language == "es":
                return "No hay procesos registrados aún en la organización."
            elif language == "en":
                return "No processes registered yet in the organization."
            elif language == "pt":
                return "Ainda não há processos registrados na organização."
        
        # Limit to most recent processes to stay under token limit
        limited_processes = processes[:20]
        
        if language == "es":
            header = f"**Procesos existentes en la organización ({len(limited_processes)}):**\n"
            items = []
            for i, proc in enumerate(limited_processes, 1):
                items.append(f"{i}. {proc.name} ({proc.type_label})")
            return header + "\n".join(items)
        
        elif language == "en":
            header = f"**Existing processes in the organization ({len(limited_processes)}):**\n"
            items = []
            for i, proc in enumerate(limited_processes, 1):
                items.append(f"{i}. {proc.name} ({proc.type_label})")
            return header + "\n".join(items)
        
        elif language == "pt":
            header = f"**Processos existentes na organização ({len(limited_processes)}):**\n"
            items = []
            for i, proc in enumerate(limited_processes, 1):
                items.append(f"{i}. {proc.name} ({proc.type_label})")
            return header + "\n".join(items)
        
        return ""
    
    @staticmethod
    def format_interview_history(
        history: InterviewHistorySummary,
        language: str = "es"
    ) -> str:
        """
        Format interview history for inclusion in prompt
        
        Creates a formatted summary of the employee's interview history
        that can be included in the system prompt.
        
        Args:
            history: Interview history summary
            language: Interview language (es/en/pt)
            
        Returns:
            str: Formatted interview history
        """
        if history.total_interviews == 0:
            if language == "es":
                return "Esta es la primera entrevista del empleado."
            elif language == "en":
                return "This is the employee's first interview."
            elif language == "pt":
                return "Esta é a primeira entrevista do funcionário."
        
        if language == "es":
            parts = [
                f"**Historial de entrevistas:**",
                f"- Total de entrevistas: {history.total_interviews}",
                f"- Entrevistas completadas: {history.completed_interviews}"
            ]
            if history.last_interview_date:
                parts.append(f"- Última entrevista: {history.last_interview_date.strftime('%Y-%m-%d')}")
            if history.topics_covered:
                topics = ", ".join(history.topics_covered[:5])
                parts.append(f"- Temas cubiertos: {topics}")
            return "\n".join(parts)
        
        elif language == "en":
            parts = [
                f"**Interview history:**",
                f"- Total interviews: {history.total_interviews}",
                f"- Completed interviews: {history.completed_interviews}"
            ]
            if history.last_interview_date:
                parts.append(f"- Last interview: {history.last_interview_date.strftime('%Y-%m-%d')}")
            if history.topics_covered:
                topics = ", ".join(history.topics_covered[:5])
                parts.append(f"- Topics covered: {topics}")
            return "\n".join(parts)
        
        elif language == "pt":
            parts = [
                f"**Histórico de entrevistas:**",
                f"- Total de entrevistas: {history.total_interviews}",
                f"- Entrevistas concluídas: {history.completed_interviews}"
            ]
            if history.last_interview_date:
                parts.append(f"- Última entrevista: {history.last_interview_date.strftime('%Y-%m-%d')}")
            if history.topics_covered:
                topics = ", ".join(history.topics_covered[:5])
                parts.append(f"- Tópicos cobertos: {topics}")
            return "\n".join(parts)
        
        return ""
    
    # ========================================================================
    # SPANISH PROMPTS
    # ========================================================================
    
    @staticmethod
    def _build_spanish_prompt(context: InterviewContextData) -> str:
        """Build Spanish system prompt with context - Uses system_prompts.py"""
        employee = context.employee
        processes = context.organization_processes
        history = context.interview_history
        
        # Build role description
        role_names = [role.name for role in employee.roles]
        role_desc = ", ".join(role_names) if role_names else "Empleado"
        
        # Format processes and history
        process_list = PromptBuilder.format_process_list(processes, "es")
        history_text = PromptBuilder.format_interview_history(history, "es")
        
        # Build context enrichment section
        context_section = f"""

---

# CONTEXTO ENRIQUECIDO DEL EMPLEADO

- **Nombre**: {employee.full_name}
- **Rol(es)**: {role_desc}
- **Organización**: {employee.organization_name}

{history_text}

---

# PROCESOS EXISTENTES EN LA ORGANIZACIÓN

{process_list}

**IMPORTANTE - DETECCIÓN Y VALIDACIÓN DE PROCESOS EXISTENTES**: 

Cuando {employee.first_name} mencione un proceso, verificá si podría estar relacionado con alguno de los procesos existentes listados arriba. 

**Si detectás una coincidencia:**
1. **Mencioná quién lo reportó originalmente** (si tenés esa información)
2. **Preguntá explícitamente por diferencias** entre la experiencia del usuario actual y la del reportante original
3. **Explorá detalles adicionales** que el usuario pueda aportar desde su perspectiva/rol
4. **No des por sentado que es exactamente igual** - diferentes roles pueden tener perspectivas diferentes del mismo proceso

**Ejemplos de preguntas cuando hay coincidencia:**
- "[Nombre del reportante] ya mencionó el proceso de [nombre]. ¿Tu experiencia coincide con la de [él/ella] o notás alguna diferencia desde tu rol?"
- "Este proceso ya fue reportado por [Nombre]. ¿Hay algo que vos hagas diferente o algún detalle adicional que quieras agregar?"
- "¿Tu forma de trabajar en este proceso es similar a la de [Nombre] o hay pasos distintos desde tu área?"

**Si NO hay coincidencia clara:**
- "¿Te referís al proceso de [nombre del proceso existente] que ya tenemos registrado?"
- "Esto que me contás, ¿es parte del proceso de [nombre] o es algo nuevo?"
- "¿Este proceso es diferente del [nombre del proceso existente]?"

---
"""
        
        # Get base prompt from system_prompts.py (respects feature flags)
        base_prompt = get_interviewer_prompt(
            user_name=employee.full_name,
            user_role=role_desc,
            organization=employee.organization_name,
            technical_level="unknown",
            language="es"
        )
        
        # Combine base prompt with context
        return base_prompt + context_section
    
    @staticmethod
    def _build_english_prompt(context: InterviewContextData) -> str:
        """Build English system prompt with context - Uses system_prompts.py"""
        employee = context.employee
        processes = context.organization_processes
        history = context.interview_history
        
        # Build role description
        role_names = [role.name for role in employee.roles]
        role_desc = ", ".join(role_names) if role_names else "Employee"
        
        # Format processes and history
        process_list = PromptBuilder.format_process_list(processes, "en")
        history_text = PromptBuilder.format_interview_history(history, "en")
        
        # Build context enrichment section
        context_section = f"""

---

# ENRICHED EMPLOYEE CONTEXT

- **Name**: {employee.full_name}
- **Role(s)**: {role_desc}
- **Organization**: {employee.organization_name}

{history_text}

---

# EXISTING PROCESSES IN THE ORGANIZATION

{process_list}

**IMPORTANT - EXISTING PROCESS DETECTION AND VALIDATION**: 

When {employee.first_name} mentions a process, check if it could be related to any of the existing processes listed above.

**If you detect a match:**
1. **Mention who originally reported it** (if you have that information)
2. **Explicitly ask about differences** between the current user's experience and the original reporter's
3. **Explore additional details** the user can contribute from their perspective/role
4. **Don't assume it's exactly the same** - different roles may have different perspectives on the same process

**Examples when there's a match:**
- "[Reporter name] already mentioned the [name] process. Does your experience match theirs or do you notice any differences from your role?"
- "This process was already reported by [Name]. Is there anything you do differently or any additional details you'd like to add?"
- "Is your way of working in this process similar to [Name]'s or are there different steps from your area?"

**If there's NO clear match:**
- "Are you referring to the [existing process name] process we already have registered?"
- "What you're telling me, is it part of the [name] process or is it something new?"
- "Is this process different from the [existing process name]?"

---
"""
        
        # Get base prompt from system_prompts.py (respects feature flags)
        base_prompt = get_interviewer_prompt(
            user_name=employee.full_name,
            user_role=role_desc,
            organization=employee.organization_name,
            technical_level="unknown",
            language="en"
        )
        
        # Combine base prompt with context
        return base_prompt + context_section
    
    @staticmethod
    def _build_portuguese_prompt(context: InterviewContextData) -> str:
        """Build Portuguese system prompt with context - Uses system_prompts.py"""
        employee = context.employee
        processes = context.organization_processes
        history = context.interview_history
        
        # Build role description
        role_names = [role.name for role in employee.roles]
        role_desc = ", ".join(role_names) if role_names else "Funcionário"
        
        # Format processes and history
        process_list = PromptBuilder.format_process_list(processes, "pt")
        history_text = PromptBuilder.format_interview_history(history, "pt")
        
        # Build context enrichment section
        context_section = f"""

---

# CONTEXTO ENRIQUECIDO DO FUNCIONÁRIO

- **Nome**: {employee.full_name}
- **Papel(is)**: {role_desc}
- **Organização**: {employee.organization_name}

{history_text}

---

# PROCESSOS EXISTENTES NA ORGANIZAÇÃO

{process_list}

**IMPORTANTE - DETECÇÃO E VALIDAÇÃO DE PROCESSOS EXISTENTES**: 

Quando {employee.first_name} mencionar um processo, verifique se pode estar relacionado a algum dos processos existentes listados acima.

**Se detectar uma correspondência:**
1. **Mencione quem reportou originalmente** (se tiver essa informação)
2. **Pergunte explicitamente sobre diferenças** entre a experiência do usuário atual e a do reporter original
3. **Explore detalhes adicionais** que o usuário possa contribuir da sua perspectiva/função
4. **Não assuma que é exatamente igual** - diferentes funções podem ter perspectivas diferentes do mesmo processo

**Exemplos quando há correspondência:**
- "[Nome do reporter] já mencionou o processo de [nome]. Sua experiência coincide com a dele ou você nota diferenças da sua função?"
- "Este processo já foi reportado por [Nome]. Há algo que você faça diferente ou algum detalhe adicional que queira adicionar?"
- "Sua forma de trabalhar neste processo é similar à de [Nome] ou há passos diferentes da sua área?"

**Se NÃO houver correspondência clara:**
- "Você está se referindo ao processo de [nome do processo existente] que já temos registrado?"
- "O que você está me contando, faz parte do processo de [nome] ou é algo novo?"
- "Este processo é diferente do [nome do processo existente]?"

---
"""
        
        # Get base prompt from system_prompts.py (respects feature flags)
        base_prompt = get_interviewer_prompt(
            user_name=employee.full_name,
            user_role=role_desc,
            organization=employee.organization_name,
            technical_level="unknown",
            language="pt"
        )
        
        # Combine base prompt with context
        return base_prompt + context_section
    
    # ========================================================================
    # PROCESS MATCHING PROMPTS (kept as-is)
    # ========================================================================
    
    @staticmethod
    def _build_spanish_matching_prompt(
        process_description: str,
        existing_processes: List[ProcessContextData]
    ) -> str:
        """Build Spanish process matching prompt"""
        process_list = "\n".join([
            f"- {proc.name} ({proc.type_label})"
            for proc in existing_processes
        ])
        
        return f"""# ROL

Sos un experto en análisis de procesos de negocio. Tu tarea es determinar si la descripción de un proceso que menciona un usuario coincide con alguno de los procesos existentes en la organización.

---

# PROCESOS EXISTENTES

{process_list}

---

# DESCRIPCIÓN DEL USUARIO

"{process_description}"

---

# TU TAREA

Analizá si la descripción del usuario se refiere a alguno de los procesos existentes listados arriba.

**Criterios de coincidencia**:
1. **Coincidencia exacta**: El nombre es idéntico o muy similar
2. **Coincidencia semántica**: Describe el mismo proceso con palabras diferentes
3. **Coincidencia parcial**: Podría ser parte de un proceso existente

**Responde en formato JSON**:
```json
{{
  "is_match": true/false,
  "matched_process_name": "nombre del proceso" o null,
  "confidence_score": 0.0 a 1.0,
  "reasoning": "explicación breve de por qué coincide o no",
  "suggested_clarifying_questions": ["pregunta 1", "pregunta 2"]
}}
```

**Ejemplos**:

**Ejemplo 1 - Coincidencia exacta**:
Usuario: "Proceso de aprobación de compras"
Proceso existente: "Proceso de Aprobación de Compras"
Respuesta:
```json
{{
  "is_match": true,
  "matched_process_name": "Proceso de Aprobación de Compras",
  "confidence_score": 0.95,
  "reasoning": "El nombre es prácticamente idéntico",
  "suggested_clarifying_questions": [
    "¿Te referís al proceso de aprobación de compras que ya tenemos registrado?",
    "¿Este proceso es el mismo que usamos actualmente?"
  ]
}}
```

**Ejemplo 2 - Coincidencia semántica**:
Usuario: "Cuando tengo que autorizar una solicitud de compra"
Proceso existente: "Proceso de Aprobación de Compras"
Respuesta:
```json
{{
  "is_match": true,
  "matched_process_name": "Proceso de Aprobación de Compras",
  "confidence_score": 0.85,
  "reasoning": "Autorizar solicitud de compra es semánticamente equivalente a aprobar compras",
  "suggested_clarifying_questions": [
    "¿Esto que me contás es parte del proceso de aprobación de compras?",
    "¿Es el mismo proceso o es algo diferente?"
  ]
}}
```

**Ejemplo 3 - No coincide**:
Usuario: "Proceso de gestión de inventario"
Proceso existente: "Proceso de Aprobación de Compras"
Respuesta:
```json
{{
  "is_match": false,
  "matched_process_name": null,
  "confidence_score": 0.0,
  "reasoning": "Son procesos completamente diferentes. Gestión de inventario no tiene relación con aprobación de compras",
  "suggested_clarifying_questions": []
}}
```

---

Analizá la descripción del usuario y respondé en formato JSON."""
        
    @staticmethod
    def _build_english_matching_prompt(
        process_description: str,
        existing_processes: List[ProcessContextData]
    ) -> str:
        """Build English process matching prompt"""
        process_list = "\n".join([
            f"- {proc.name} ({proc.type_label})"
            for proc in existing_processes
        ])
        
        return f"""# ROLE

You are an expert in business process analysis. Your task is to determine if a process description mentioned by a user matches any of the existing processes in the organization.

---

# EXISTING PROCESSES

{process_list}

---

# USER DESCRIPTION

"{process_description}"

---

# YOUR TASK

Analyze if the user's description refers to any of the existing processes listed above.

**Matching criteria**:
1. **Exact match**: The name is identical or very similar
2. **Semantic match**: Describes the same process with different words
3. **Partial match**: Could be part of an existing process

**Respond in JSON format**:
```json
{{
  "is_match": true/false,
  "matched_process_name": "process name" or null,
  "confidence_score": 0.0 to 1.0,
  "reasoning": "brief explanation of why it matches or not",
  "suggested_clarifying_questions": ["question 1", "question 2"]
}}
```

**Examples**:

**Example 1 - Exact match**:
User: "Purchase approval process"
Existing process: "Purchase Approval Process"
Response:
```json
{{
  "is_match": true,
  "matched_process_name": "Purchase Approval Process",
  "confidence_score": 0.95,
  "reasoning": "The name is practically identical",
  "suggested_clarifying_questions": [
    "Are you referring to the purchase approval process we already have registered?",
    "Is this the same process we currently use?"
  ]
}}
```

**Example 2 - Semantic match**:
User: "When I need to authorize a purchase request"
Existing process: "Purchase Approval Process"
Response:
```json
{{
  "is_match": true,
  "matched_process_name": "Purchase Approval Process",
  "confidence_score": 0.85,
  "reasoning": "Authorizing purchase request is semantically equivalent to purchase approval",
  "suggested_clarifying_questions": [
    "Is what you're telling me part of the purchase approval process?",
    "Is it the same process or something different?"
  ]
}}
```

**Example 3 - No match**:
User: "Inventory management process"
Existing process: "Purchase Approval Process"
Response:
```json
{{
  "is_match": false,
  "matched_process_name": null,
  "confidence_score": 0.0,
  "reasoning": "These are completely different processes. Inventory management is not related to purchase approval",
  "suggested_clarifying_questions": []
}}
```

---

Analyze the user's description and respond in JSON format."""
        
    @staticmethod
    def _build_portuguese_matching_prompt(
        process_description: str,
        existing_processes: List[ProcessContextData]
    ) -> str:
        """Build Portuguese process matching prompt"""
        process_list = "\n".join([
            f"- {proc.name} ({proc.type_label})"
            for proc in existing_processes
        ])
        
        return f"""# PAPEL

Você é um especialista em análise de processos de negócio. Sua tarefa é determinar se a descrição de um processo mencionada por um usuário corresponde a algum dos processos existentes na organização.

---

# PROCESSOS EXISTENTES

{process_list}

---

# DESCRIÇÃO DO USUÁRIO

"{process_description}"

---

# SUA TAREFA

Analise se a descrição do usuário se refere a algum dos processos existentes listados acima.

**Critérios de correspondência**:
1. **Correspondência exata**: O nome é idêntico ou muito similar
2. **Correspondência semântica**: Descreve o mesmo processo com palavras diferentes
3. **Correspondência parcial**: Pode ser parte de um processo existente

**Responda em formato JSON**:
```json
{{
  "is_match": true/false,
  "matched_process_name": "nome do processo" ou null,
  "confidence_score": 0.0 a 1.0,
  "reasoning": "explicação breve de por que corresponde ou não",
  "suggested_clarifying_questions": ["pergunta 1", "pergunta 2"]
}}
```

**Exemplos**:

**Exemplo 1 - Correspondência exata**:
Usuário: "Processo de aprovação de compras"
Processo existente: "Processo de Aprovação de Compras"
Resposta:
```json
{{
  "is_match": true,
  "matched_process_name": "Processo de Aprovação de Compras",
  "confidence_score": 0.95,
  "reasoning": "O nome é praticamente idêntico",
  "suggested_clarifying_questions": [
    "Você está se referindo ao processo de aprovação de compras que já temos registrado?",
    "Este processo é o mesmo que usamos atualmente?"
  ]
}}
```

**Exemplo 2 - Correspondência semântica**:
Usuário: "Quando preciso autorizar uma solicitação de compra"
Processo existente: "Processo de Aprovação de Compras"
Resposta:
```json
{{
  "is_match": true,
  "matched_process_name": "Processo de Aprovação de Compras",
  "confidence_score": 0.85,
  "reasoning": "Autorizar solicitação de compra é semanticamente equivalente a aprovar compras",
  "suggested_clarifying_questions": [
    "O que você está me contando faz parte do processo de aprovação de compras?",
    "É o mesmo processo ou é algo diferente?"
  ]
}}
```

**Exemplo 3 - Não corresponde**:
Usuário: "Processo de gestão de estoque"
Processo existente: "Processo de Aprovação de Compras"
Resposta:
```json
{{
  "is_match": false,
  "matched_process_name": null,
  "confidence_score": 0.0,
  "reasoning": "São processos completamente diferentes. Gestão de estoque não tem relação com aprovação de compras",
  "suggested_clarifying_questions": []
}}
```

---

Analise a descrição do usuário e responda em formato JSON."""
