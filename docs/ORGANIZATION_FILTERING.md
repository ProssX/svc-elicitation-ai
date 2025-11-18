# Organization Filtering for Interviews

## Overview

This document describes the changes made to filter interviews by organization, ensuring that users only see interviews from their own organization.

## Changes Made

### 1. Database Schema Changes

**New Column:** `organization_id` added to `interview` table

```sql
ALTER TABLE interview 
ADD COLUMN organization_id UUID;

CREATE INDEX idx_interview_organization ON interview(organization_id);
```

**Migration File:** `alembic/versions/20251117_1500_e5f6g7h8i9j0_add_organization_id_to_interview.py`

### 2. Model Changes

**File:** `app/models/db_models.py`

Added `organization_id` field to the `Interview` model:

```python
organization_id = Column(
    UUID(as_uuid=True),
    nullable=True,
    index=True,
    comment="Reference to organization in svc-organizations-php"
)
```

### 3. Repository Changes

**File:** `app/repositories/interview_repository.py`

#### Modified Methods:

1. **`get_by_organization()`** - Now filters by `organization_id`
   - Previously returned ALL interviews (security issue)
   - Now returns only interviews from the specified organization

2. **New Method: `get_by_employee_in_organization()`**
   - Lists interviews for a specific employee within an organization
   - Used by the new endpoint `/interviews/employees/{employee_id}`

### 4. Service Changes

**File:** `app/services/interview_service.py`

#### Modified Methods:

1. **`start_interview()`** - Now saves `organization_id` when creating interviews
   ```python
   interview = Interview(
       employee_id=employee_id,
       organization_id=UUID(organization_id) if organization_id else None,
       ...
   )
   ```

2. **New Method: `list_interviews_by_employee()`**
   - Service layer method for listing interviews by employee
   - Ensures organization-level authorization

### 5. Router/Endpoint Changes

**File:** `app/routers/interviews.py`

#### New Endpoint:

**`GET /interviews/employees/{employee_id}`**

- **Purpose:** List interviews for a specific employee
- **Permission Required:** `interviews:read` (any authenticated user)
- **Authorization Rules:**
  - Regular users can only access their own interviews (`employee_id` must match their `user_id`)
  - Admins/Managers with `interviews:read_all` can access any employee's interviews in their organization
- **Filters:** Same as main list endpoint (status, language, dates, pagination)
- **Security:** Always filters by organization (users can't see interviews from other organizations)

**Example Requests:**

```bash
# Employee checking their own interviews
GET /api/v1/interviews/employees/01932e5f-8b2a-7890-b123-456789abcdef?status=in_progress
Authorization: Bearer <employee_token>

# Manager checking an employee's interviews (requires interviews:read_all)
GET /api/v1/interviews/employees/01932e5f-8b2a-7890-b123-456789abcdef?status=completed&page=1&page_size=20
Authorization: Bearer <manager_token>
```

**Example Response:**
```json
{
  "status": "success",
  "code": 200,
  "message": "Interviews retrieved successfully",
  "data": [
    {
      "id_interview": "018e5f8b-1234-7890-abcd-123456789abc",
      "employee_id": "01932e5f-8b2a-7890-b123-456789abcdef",
      "language": "es",
      "status": "completed",
      "started_at": "2025-10-25T10:00:00Z",
      "completed_at": "2025-10-25T10:15:00Z",
      "total_messages": 12
    }
  ],
  "meta": {
    "pagination": {
      "total_items": 5,
      "total_pages": 1,
      "current_page": 1,
      "page_size": 20
    },
    "employee_id": "01932e5f-8b2a-7890-b123-456789abcdef",
    "organization_id": "01932e5f-8b2a-7890-b123-456789abcdef"
  }
}
```

#### Modified Endpoint:

**`GET /interviews`** - Now correctly filters by organization

- Users with `interviews:read` → See only their own interviews
- Users with `interviews:read_all` → See all interviews **from their organization only**

## Security Improvements

### Before:
- ❌ `GET /interviews` with `interviews:read_all` returned ALL interviews from ALL organizations
- ❌ No organization-level isolation

### After:
- ✅ `GET /interviews` with `interviews:read_all` returns only interviews from user's organization
- ✅ New endpoint `/interviews/employees/{employee_id}` for admin access to specific employee interviews
- ✅ Organization-level data isolation enforced at database query level

## Migration Steps

### 1. Run Database Migration

```bash
# Apply the migration
alembic upgrade head
```

### 2. Backfill Existing Data (Optional)

For existing interviews without `organization_id`:

**Option A: Manual SQL Update** (if you have employee-organization mapping)
```sql
UPDATE interview i
SET organization_id = e.organization_id
FROM employee e
WHERE i.employee_id = e.id_employee
AND i.organization_id IS NULL;
```

**Option B: Use Backfill Script** (requires service account token)
```bash
python scripts/backfill-organization-id.py
```

**Option C: Leave as NULL**
- Interviews with `NULL` organization_id won't appear in organization-filtered queries
- New interviews will have organization_id set automatically

### 3. Test the Changes

```bash
# Test the main list endpoint (should filter by organization)
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/interviews

# Test the new employee-specific endpoint
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/interviews/employees/<employee_id>
```

## API Changes Summary

| Endpoint | Method | Change | Permission Required | Notes |
|----------|--------|--------|-------------------|-------|
| `/interviews` | GET | Now filters by organization | `interviews:read` or `interviews:read_all` | Returns user's own interviews or all org interviews |
| `/interviews/employees/{employee_id}` | GET | **NEW** - List interviews for specific employee | `interviews:read` | Regular users: own only. Admins: any employee |

## Backward Compatibility

- ✅ Existing interviews without `organization_id` will not appear in filtered queries
- ✅ API response format unchanged
- ✅ No breaking changes to request/response structure
- ⚠️ Behavior change: `interviews:read_all` now scoped to organization (was global before)

## Testing Checklist

- [ ] Run database migration successfully
- [ ] Create new interview - verify `organization_id` is saved
- [ ] Test `GET /interviews` as regular user - see only own interviews
- [ ] Test `GET /interviews` as admin - see only organization's interviews
- [ ] Test `GET /interviews/employees/{employee_id}` as admin - see employee's interviews
- [ ] Test `GET /interviews/employees/{employee_id}` as regular user - get 403 error
- [ ] Verify cross-organization access is blocked

## Notes

- The `organization_id` field is nullable to support existing data
- Consider making it NOT NULL after backfilling existing interviews
- The new endpoint requires `interviews:read_all` permission for security
- Organization filtering happens at the database query level for performance
