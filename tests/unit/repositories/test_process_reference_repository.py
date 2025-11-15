"""
Unit tests for ProcessReferenceRepository
"""
import pytest
import uuid
from datetime import datetime, timedelta

from app.repositories.process_reference_repository import ProcessReferenceRepository
from app.repositories.interview_repository import InterviewRepository
from app.models.db_models import Interview, LanguageEnum, InterviewStatusEnum


@pytest.mark.asyncio
class TestProcessReferenceRepository:
    """Test suite for ProcessReferenceRepository"""
    
    async def test_create_process_reference(self, db_session):
        """Test creating a new process reference"""
        # Create an interview first
        interview_repo = InterviewRepository(db_session)
        employee_id = uuid.uuid4()
        interview = Interview(
            employee_id=employee_id,
            language=LanguageEnum.es,
            technical_level="intermediate",
            status=InterviewStatusEnum.in_progress
        )
        await interview_repo.create(interview)
        await db_session.commit()
        
        # Create process reference
        repo = ProcessReferenceRepository(db_session)
        process_id = uuid.uuid4()
        
        process_ref = await repo.create(
            interview_id=interview.id_interview,
            process_id=process_id,
            is_new_process=True,
            confidence_score=0.95
        )
        await db_session.commit()
        
        # Assertions
        assert process_ref is not None
        assert process_ref.id_reference is not None
        assert process_ref.interview_id == interview.id_interview
        assert process_ref.process_id == process_id
        assert process_ref.is_new_process is True
        assert float(process_ref.confidence_score) == 0.95
        assert process_ref.mentioned_at is not None
        assert process_ref.created_at is not None
    
    async def test_create_with_custom_mentioned_at(self, db_session):
        """Test creating a process reference with custom mentioned_at timestamp"""
        # Create an interview first
        interview_repo = InterviewRepository(db_session)
        employee_id = uuid.uuid4()
        interview = Interview(
            employee_id=employee_id,
            language=LanguageEnum.en,
            technical_level="beginner",
            status=InterviewStatusEnum.in_progress
        )
        await interview_repo.create(interview)
        await db_session.commit()
        
        # Create process reference with custom timestamp
        repo = ProcessReferenceRepository(db_session)
        process_id = uuid.uuid4()
        custom_time = datetime.utcnow() - timedelta(hours=2)
        
        process_ref = await repo.create(
            interview_id=interview.id_interview,
            process_id=process_id,
            is_new_process=False,
            confidence_score=0.75,
            mentioned_at=custom_time
        )
        await db_session.commit()
        
        # Assertions
        assert process_ref is not None
        assert process_ref.mentioned_at == custom_time
        assert process_ref.is_new_process is False
    
    async def test_get_by_interview(self, db_session):
        """Test retrieving all process references for an interview"""
        # Create an interview
        interview_repo = InterviewRepository(db_session)
        employee_id = uuid.uuid4()
        interview = Interview(
            employee_id=employee_id,
            language=LanguageEnum.pt,
            technical_level="advanced",
            status=InterviewStatusEnum.in_progress
        )
        await interview_repo.create(interview)
        await db_session.commit()
        
        # Create multiple process references
        repo = ProcessReferenceRepository(db_session)
        process_id_1 = uuid.uuid4()
        process_id_2 = uuid.uuid4()
        process_id_3 = uuid.uuid4()
        
        time_1 = datetime.utcnow() - timedelta(minutes=10)
        time_2 = datetime.utcnow() - timedelta(minutes=5)
        time_3 = datetime.utcnow()
        
        await repo.create(
            interview_id=interview.id_interview,
            process_id=process_id_1,
            is_new_process=True,
            confidence_score=0.90,
            mentioned_at=time_1
        )
        await repo.create(
            interview_id=interview.id_interview,
            process_id=process_id_2,
            is_new_process=False,
            confidence_score=0.85,
            mentioned_at=time_2
        )
        await repo.create(
            interview_id=interview.id_interview,
            process_id=process_id_3,
            is_new_process=True,
            confidence_score=0.95,
            mentioned_at=time_3
        )
        await db_session.commit()
        
        # Retrieve all references for the interview
        references = await repo.get_by_interview(interview.id_interview)
        
        # Assertions
        assert len(references) == 3
        # Should be ordered by mentioned_at ascending
        assert references[0].process_id == process_id_1
        assert references[1].process_id == process_id_2
        assert references[2].process_id == process_id_3
    
    async def test_get_by_interview_empty(self, db_session):
        """Test retrieving process references for an interview with no references"""
        # Create an interview without process references
        interview_repo = InterviewRepository(db_session)
        employee_id = uuid.uuid4()
        interview = Interview(
            employee_id=employee_id,
            language=LanguageEnum.es,
            technical_level="intermediate",
            status=InterviewStatusEnum.in_progress
        )
        await interview_repo.create(interview)
        await db_session.commit()
        
        # Try to retrieve references
        repo = ProcessReferenceRepository(db_session)
        references = await repo.get_by_interview(interview.id_interview)
        
        # Assertions
        assert len(references) == 0
    
    async def test_get_by_process(self, db_session):
        """Test retrieving all interview references for a process"""
        # Create multiple interviews
        interview_repo = InterviewRepository(db_session)
        employee_id = uuid.uuid4()
        
        interview_1 = Interview(
            employee_id=employee_id,
            language=LanguageEnum.es,
            technical_level="intermediate",
            status=InterviewStatusEnum.completed
        )
        interview_2 = Interview(
            employee_id=employee_id,
            language=LanguageEnum.es,
            technical_level="intermediate",
            status=InterviewStatusEnum.completed
        )
        interview_3 = Interview(
            employee_id=employee_id,
            language=LanguageEnum.es,
            technical_level="intermediate",
            status=InterviewStatusEnum.in_progress
        )
        
        await interview_repo.create(interview_1)
        await interview_repo.create(interview_2)
        await interview_repo.create(interview_3)
        await db_session.commit()
        
        # Create process references for the same process across different interviews
        repo = ProcessReferenceRepository(db_session)
        process_id = uuid.uuid4()
        
        time_1 = datetime.utcnow() - timedelta(days=2)
        time_2 = datetime.utcnow() - timedelta(days=1)
        time_3 = datetime.utcnow()
        
        await repo.create(
            interview_id=interview_1.id_interview,
            process_id=process_id,
            is_new_process=True,
            confidence_score=0.90,
            mentioned_at=time_1
        )
        await repo.create(
            interview_id=interview_2.id_interview,
            process_id=process_id,
            is_new_process=False,
            confidence_score=0.95,
            mentioned_at=time_2
        )
        await repo.create(
            interview_id=interview_3.id_interview,
            process_id=process_id,
            is_new_process=False,
            confidence_score=0.88,
            mentioned_at=time_3
        )
        await db_session.commit()
        
        # Retrieve all references for the process
        references = await repo.get_by_process(process_id)
        
        # Assertions
        assert len(references) == 3
        # Should be ordered by mentioned_at descending (most recent first)
        assert references[0].interview_id == interview_3.id_interview
        assert references[1].interview_id == interview_2.id_interview
        assert references[2].interview_id == interview_1.id_interview
    
    async def test_get_by_process_empty(self, db_session):
        """Test retrieving interview references for a process with no references"""
        repo = ProcessReferenceRepository(db_session)
        process_id = uuid.uuid4()
        
        # Try to retrieve references for non-existent process
        references = await repo.get_by_process(process_id)
        
        # Assertions
        assert len(references) == 0
    
    async def test_unique_constraint_violation(self, db_session):
        """Test that creating duplicate process references returns None"""
        # Create an interview
        interview_repo = InterviewRepository(db_session)
        employee_id = uuid.uuid4()
        interview = Interview(
            employee_id=employee_id,
            language=LanguageEnum.es,
            technical_level="intermediate",
            status=InterviewStatusEnum.in_progress
        )
        await interview_repo.create(interview)
        await db_session.commit()
        
        # Store IDs before any potential rollback
        interview_id = interview.id_interview
        
        # Create first process reference
        repo = ProcessReferenceRepository(db_session)
        process_id = uuid.uuid4()
        
        first_ref = await repo.create(
            interview_id=interview_id,
            process_id=process_id,
            is_new_process=True,
            confidence_score=0.90
        )
        await db_session.commit()
        
        assert first_ref is not None
        first_ref_id = first_ref.id_reference
        
        # Try to create duplicate reference (same interview_id and process_id)
        duplicate_ref = await repo.create(
            interview_id=interview_id,
            process_id=process_id,
            is_new_process=False,
            confidence_score=0.95
        )
        
        # Should return None due to unique constraint
        assert duplicate_ref is None
        
        # Verify only one reference exists
        references = await repo.get_by_interview(interview_id)
        assert len(references) == 1
        assert references[0].id_reference == first_ref_id
    
    async def test_get_by_id(self, db_session):
        """Test retrieving a specific process reference by ID"""
        # Create an interview
        interview_repo = InterviewRepository(db_session)
        employee_id = uuid.uuid4()
        interview = Interview(
            employee_id=employee_id,
            language=LanguageEnum.en,
            technical_level="beginner",
            status=InterviewStatusEnum.in_progress
        )
        await interview_repo.create(interview)
        await db_session.commit()
        
        # Create process reference
        repo = ProcessReferenceRepository(db_session)
        process_id = uuid.uuid4()
        
        created_ref = await repo.create(
            interview_id=interview.id_interview,
            process_id=process_id,
            is_new_process=True,
            confidence_score=0.92
        )
        await db_session.commit()
        
        # Retrieve by ID
        retrieved_ref = await repo.get_by_id(created_ref.id_reference)
        
        # Assertions
        assert retrieved_ref is not None
        assert retrieved_ref.id_reference == created_ref.id_reference
        assert retrieved_ref.interview_id == interview.id_interview
        assert retrieved_ref.process_id == process_id
        assert retrieved_ref.is_new_process is True
        assert float(retrieved_ref.confidence_score) == 0.92
    
    async def test_get_by_id_not_found(self, db_session):
        """Test retrieving a non-existent process reference by ID"""
        repo = ProcessReferenceRepository(db_session)
        non_existent_id = uuid.uuid4()
        
        # Try to retrieve non-existent reference
        retrieved_ref = await repo.get_by_id(non_existent_id)
        
        # Assertions
        assert retrieved_ref is None
    
    async def test_exists(self, db_session):
        """Test checking if a process reference exists"""
        # Create an interview
        interview_repo = InterviewRepository(db_session)
        employee_id = uuid.uuid4()
        interview = Interview(
            employee_id=employee_id,
            language=LanguageEnum.pt,
            technical_level="advanced",
            status=InterviewStatusEnum.in_progress
        )
        await interview_repo.create(interview)
        await db_session.commit()
        
        # Create process reference
        repo = ProcessReferenceRepository(db_session)
        process_id = uuid.uuid4()
        
        await repo.create(
            interview_id=interview.id_interview,
            process_id=process_id,
            is_new_process=True,
            confidence_score=0.88
        )
        await db_session.commit()
        
        # Check if exists
        exists = await repo.exists(interview.id_interview, process_id)
        assert exists is True
        
        # Check with non-existent process
        non_existent_process = uuid.uuid4()
        not_exists = await repo.exists(interview.id_interview, non_existent_process)
        assert not_exists is False
    
    async def test_multiple_processes_per_interview(self, db_session):
        """Test that an interview can reference multiple processes"""
        # Create an interview
        interview_repo = InterviewRepository(db_session)
        employee_id = uuid.uuid4()
        interview = Interview(
            employee_id=employee_id,
            language=LanguageEnum.es,
            technical_level="intermediate",
            status=InterviewStatusEnum.completed
        )
        await interview_repo.create(interview)
        await db_session.commit()
        
        # Create multiple process references
        repo = ProcessReferenceRepository(db_session)
        process_id_1 = uuid.uuid4()
        process_id_2 = uuid.uuid4()
        process_id_3 = uuid.uuid4()
        
        ref1 = await repo.create(
            interview_id=interview.id_interview,
            process_id=process_id_1,
            is_new_process=True,
            confidence_score=0.90
        )
        ref2 = await repo.create(
            interview_id=interview.id_interview,
            process_id=process_id_2,
            is_new_process=False,
            confidence_score=0.85
        )
        ref3 = await repo.create(
            interview_id=interview.id_interview,
            process_id=process_id_3,
            is_new_process=True,
            confidence_score=0.92
        )
        await db_session.commit()
        
        # Verify all references exist
        references = await repo.get_by_interview(interview.id_interview)
        assert len(references) == 3
        
        # Verify each reference is unique
        ref_ids = {ref.id_reference for ref in references}
        assert len(ref_ids) == 3
        assert ref1.id_reference in ref_ids
        assert ref2.id_reference in ref_ids
        assert ref3.id_reference in ref_ids
