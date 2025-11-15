# Requirements Document

## Introduction

This feature enhances the AI interview system to be context-aware by leveraging existing data from the database and backend services. Currently, the interview agent operates with minimal context about the employee, organization, and previously identified processes. This improvement will enable the agent to conduct higher-quality interviews by understanding the employee's history, previously identified processes from other interviews, and organizational context.

The system will integrate with the existing svc-organizations-php backend to retrieve process information, employee details, and organizational data, allowing the agent to make intelligent decisions about whether a user is describing an existing process or a new one.

## Glossary

- **Interview Agent**: The AI system that conducts requirements elicitation interviews with employees
- **Context Service**: Service responsible for fetching and aggregating contextual information from backend services
- **Process Repository**: Backend service (svc-organizations-php) that stores identified business processes
- **Employee Context**: Aggregated information about an employee including their role, organization, and interview history
- **Process Matching Agent**: Specialized agent that determines if a described process matches existing processes
- **Interview History**: Collection of previous interviews conducted by the same employee or within the same organization
- **System Prompt**: Instructions provided to the AI agent that define its behavior and available context
- **svc-elicitation-ai**: The Python FastAPI service that handles AI interviews
- **svc-organizations-php**: The PHP Symfony service that manages organizations, employees, roles, and processes

## Requirements

### Requirement 1: Employee Context Enrichment

**User Story:** As an interviewer agent, I want to have complete information about the employee I'm interviewing, so that I can personalize the conversation and reference their role and responsibilities.

#### Acceptance Criteria

1. WHEN an interview starts, THE Interview Agent SHALL retrieve the employee's complete profile including first name, last name, role names, and organization details from svc-organizations-php
2. WHEN an interview starts, THE Interview Agent SHALL retrieve the employee's previous interview count and most recent interview date from the local database
3. WHEN generating the system prompt, THE Interview Agent SHALL include the employee's full name, role descriptions, and organization information
4. WHERE the employee has previous interviews, THE Interview Agent SHALL include a summary of topics covered in past interviews in the system prompt
5. IF the backend service is unavailable, THEN THE Interview Agent SHALL proceed with minimal context and log a warning

### Requirement 2: Organization Process Context

**User Story:** As an interviewer agent, I want to know what processes have already been identified in the organization, so that I can recognize when an employee is describing an existing process versus a new one.

#### Acceptance Criteria

1. WHEN an interview starts, THE Interview Agent SHALL retrieve all active processes for the employee's organization from svc-organizations-php
2. WHEN an interview starts, THE Interview Agent SHALL include a list of existing process names and types in the system prompt
3. WHILE conducting an interview, THE Interview Agent SHALL have access to process descriptions to compare against employee responses
4. WHERE the organization has more than 10 processes, THE Interview Agent SHALL prioritize the most recently created or updated processes
5. IF no processes exist for the organization, THEN THE Interview Agent SHALL proceed knowing this is likely the first interview

### Requirement 3: Process Matching Intelligence

**User Story:** As an interviewer agent, I want to determine if an employee is describing an existing process or a new one, so that I can ask appropriate follow-up questions and avoid duplicate process identification.

#### Acceptance Criteria

1. WHEN an employee describes a process during an interview, THE Interview Agent SHALL analyze the description against existing processes in the organization
2. WHEN a potential match is found, THE Interview Agent SHALL ask clarifying questions to confirm if it's the same process
3. IF a process match is confirmed, THEN THE Interview Agent SHALL note this in the interview context and focus on gathering additional details about that process
4. IF a process is determined to be new, THEN THE Interview Agent SHALL proceed with standard elicitation questions
5. WHEN the interview is exported, THE Interview Agent SHALL include process matching results indicating which existing processes were referenced

### Requirement 4: Interview History Awareness

**User Story:** As an interviewer agent, I want to know about previous interviews conducted in the organization, so that I can build upon existing knowledge and avoid redundant questions.

#### Acceptance Criteria

1. WHEN an interview starts, THE Interview Agent SHALL retrieve the count of completed interviews for the organization
2. WHERE the employee has conducted previous interviews, THE Interview Agent SHALL retrieve summaries of those interviews
3. WHEN generating questions, THE Interview Agent SHALL avoid topics that were thoroughly covered in the employee's recent interviews
4. WHERE other employees in the organization have been interviewed, THE Interview Agent SHALL be aware of commonly discussed processes
5. IF this is the employee's first interview, THEN THE Interview Agent SHALL provide more introductory context about the interview purpose

### Requirement 5: Enhanced Context Service

**User Story:** As a system component, I want a robust context service that aggregates information from multiple sources, so that the interview agent has comprehensive context without complex integration logic.

#### Acceptance Criteria

1. THE Context Service SHALL provide a single method to retrieve complete employee context including profile, organization, roles, and interview history
2. THE Context Service SHALL provide a method to retrieve organization processes with filtering and sorting capabilities
3. THE Context Service SHALL cache backend responses for 5 minutes to reduce API calls
4. THE Context Service SHALL handle backend service failures gracefully and return partial context when possible
5. THE Context Service SHALL log all backend integration errors with sufficient detail for debugging

### Requirement 6: Process Context in System Prompt

**User Story:** As an interviewer agent, I want existing process information included in my system prompt, so that I can reference it naturally during the conversation.

#### Acceptance Criteria

1. WHEN the system prompt is generated, THE Interview Agent SHALL include a section listing existing processes with their names and types
2. WHEN the system prompt is generated, THE Interview Agent SHALL include instructions on how to handle process matching
3. WHERE existing processes exist, THE Interview Agent SHALL be instructed to ask if the employee's described process relates to any listed processes
4. THE System Prompt SHALL include examples of how to phrase process matching questions naturally
5. THE System Prompt SHALL remain under 4000 tokens even with process context included

### Requirement 7: Interview Export Enhancement

**User Story:** As a system administrator, I want interview exports to include process matching information, so that I can understand which processes were discussed and whether they were new or existing.

#### Acceptance Criteria

1. WHEN an interview is exported, THE Interview Export SHALL include a list of referenced existing processes with their IDs
2. WHEN an interview is exported, THE Interview Export SHALL include a list of newly identified processes described by the employee
3. WHEN an interview is exported, THE Interview Export SHALL include confidence scores for process matches
4. THE Interview Export SHALL include the employee's full context that was used during the interview
5. THE Interview Export SHALL maintain backward compatibility with existing export format

### Requirement 8: Multi-Agent Architecture Support

**User Story:** As a system architect, I want the ability to use specialized agents for specific tasks, so that the system can handle complex reasoning like process matching more effectively.

#### Acceptance Criteria

1. THE System SHALL support creating specialized agents with different system prompts and purposes
2. THE System SHALL provide a Process Matching Agent that can be invoked to compare process descriptions
3. THE Process Matching Agent SHALL accept an employee's process description and a list of existing processes as input
4. THE Process Matching Agent SHALL return a match result with confidence score and reasoning
5. THE Main Interview Agent SHALL be able to invoke the Process Matching Agent during the conversation when needed

### Requirement 9: Database Schema for Process References

**User Story:** As a data analyst, I want interview data to include references to identified processes, so that I can track which interviews contributed to process discovery.

#### Acceptance Criteria

1. THE Interview Database Schema SHALL include a table to store process references linked to interviews
2. THE Interview Database Schema SHALL store the process ID, interview ID, and whether the process was newly identified or existing
3. WHEN an interview references a process, THE System SHALL create a record in the process reference table
4. THE Interview Repository SHALL provide methods to query interviews by referenced process
5. THE Interview Repository SHALL provide methods to query all interviews that contributed to a specific process

### Requirement 10: Performance and Scalability

**User Story:** As a system operator, I want the context enrichment to perform efficiently, so that interview start times remain under 3 seconds.

#### Acceptance Criteria

1. WHEN an interview starts, THE System SHALL retrieve all context information within 2 seconds
2. THE Context Service SHALL make backend API calls in parallel where possible
3. THE Context Service SHALL implement request timeouts of 5 seconds for backend calls
4. WHERE backend calls exceed timeout, THE System SHALL proceed with cached or minimal context
5. THE System SHALL log performance metrics for context retrieval to enable monitoring
