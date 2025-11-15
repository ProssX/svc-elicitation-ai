"""
Context Data Models for Context-Aware Interviews

These models represent contextual information gathered from multiple sources
to enrich the interview agent's understanding of the employee, organization,
and existing processes.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from uuid import UUID


class RoleContextData(BaseModel):
    """
    Role information for an employee
    
    Represents a role assigned to an employee within their organization.
    """
    id: UUID = Field(description="Role UUID")
    name: str = Field(description="Role name")
    description: Optional[str] = Field(default=None, description="Role description")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "018e5f8b-1234-7890-abcd-123456789abc",
                "name": "Gerente de Operaciones",
                "description": "Responsable de supervisar las operaciones diarias"
            }
        }


class EmployeeContextData(BaseModel):
    """
    Complete employee context information
    
    Aggregates employee profile data including personal information,
    organizational affiliation, and assigned roles.
    """
    id: UUID = Field(description="Employee UUID")
    first_name: str = Field(description="Employee first name")
    last_name: str = Field(description="Employee last name")
    full_name: str = Field(description="Employee full name (computed)")
    organization_id: str = Field(description="Organization UUID")
    organization_name: str = Field(description="Organization name")
    roles: List[RoleContextData] = Field(
        default_factory=list,
        description="List of roles assigned to the employee"
    )
    is_active: bool = Field(default=True, description="Whether the employee is active")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "018e5f8b-1234-7890-abcd-123456789abc",
                "first_name": "Juan",
                "last_name": "Pérez",
                "full_name": "Juan Pérez",
                "organization_id": "018e5f8b-5678-7890-abcd-123456789abc",
                "organization_name": "ProssX Demo",
                "roles": [
                    {
                        "id": "018e5f8b-9012-7890-abcd-123456789abc",
                        "name": "Gerente de Operaciones",
                        "description": "Responsable de supervisar las operaciones diarias"
                    }
                ],
                "is_active": True
            }
        }


class ProcessContextData(BaseModel):
    """
    Process information for context enrichment
    
    Represents an existing business process in the organization that can be
    referenced during interviews for process matching.
    """
    id: UUID = Field(description="Process UUID")
    name: str = Field(description="Process name")
    type: str = Field(description="Process type code (e.g., 'operational', 'strategic')")
    type_label: str = Field(description="Human-readable process type label")
    is_active: bool = Field(default=True, description="Whether the process is active")
    created_at: datetime = Field(description="Process creation timestamp")
    updated_at: datetime = Field(description="Process last update timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "018e5f8b-3456-7890-abcd-123456789abc",
                "name": "Proceso de Aprobación de Compras",
                "type": "operational",
                "type_label": "Operacional",
                "is_active": True,
                "created_at": "2025-01-15T10:00:00Z",
                "updated_at": "2025-01-20T14:30:00Z"
            }
        }


class InterviewHistorySummary(BaseModel):
    """
    Summary of employee's interview history
    
    Provides aggregated information about previous interviews conducted by
    the employee, including counts, dates, and topics covered.
    """
    total_interviews: int = Field(
        default=0,
        ge=0,
        description="Total number of interviews conducted by the employee"
    )
    completed_interviews: int = Field(
        default=0,
        ge=0,
        description="Number of completed interviews"
    )
    last_interview_date: Optional[datetime] = Field(
        default=None,
        description="Date of the most recent interview"
    )
    topics_covered: List[str] = Field(
        default_factory=list,
        description="List of topics discussed in previous interviews"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_interviews": 3,
                "completed_interviews": 2,
                "last_interview_date": "2025-01-20T15:00:00Z",
                "topics_covered": [
                    "Proceso de compras",
                    "Gestión de inventario",
                    "Aprobaciones financieras"
                ]
            }
        }


class InterviewContextData(BaseModel):
    """
    Complete context for conducting an interview
    
    Aggregates all contextual information needed by the interview agent:
    - Employee profile and roles
    - Organization's existing processes
    - Employee's interview history
    
    This comprehensive context enables the agent to conduct personalized,
    context-aware interviews.
    """
    employee: EmployeeContextData = Field(
        description="Complete employee profile and organizational information"
    )
    organization_processes: List[ProcessContextData] = Field(
        default_factory=list,
        description="List of existing processes in the employee's organization"
    )
    interview_history: InterviewHistorySummary = Field(
        description="Summary of the employee's previous interviews"
    )
    context_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when this context was assembled"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "employee": {
                    "id": "018e5f8b-1234-7890-abcd-123456789abc",
                    "first_name": "Juan",
                    "last_name": "Pérez",
                    "full_name": "Juan Pérez",
                    "organization_id": "018e5f8b-5678-7890-abcd-123456789abc",
                    "organization_name": "ProssX Demo",
                    "roles": [
                        {
                            "id": "018e5f8b-9012-7890-abcd-123456789abc",
                            "name": "Gerente de Operaciones",
                            "description": "Responsable de supervisar las operaciones diarias"
                        }
                    ],
                    "is_active": True
                },
                "organization_processes": [
                    {
                        "id": "018e5f8b-3456-7890-abcd-123456789abc",
                        "name": "Proceso de Aprobación de Compras",
                        "type": "operational",
                        "type_label": "Operacional",
                        "is_active": True,
                        "created_at": "2025-01-15T10:00:00Z",
                        "updated_at": "2025-01-20T14:30:00Z"
                    }
                ],
                "interview_history": {
                    "total_interviews": 3,
                    "completed_interviews": 2,
                    "last_interview_date": "2025-01-20T15:00:00Z",
                    "topics_covered": [
                        "Proceso de compras",
                        "Gestión de inventario"
                    ]
                },
                "context_timestamp": "2025-01-25T10:00:00Z"
            }
        }
