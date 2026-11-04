# Authorization and Workspace RBAC Design

- **Project:** Smart IoT Platform
- **Version:** 1.0
- **Status:** Draft
- **Phase:** 1
**Last Updated:** 2026-11-04

---

## 1. Purpose

This document defines the authorization architecture and workspace-based Role-Based Access Control (RBAC) for the Smart IoT Platform.

The design establishes:

- Four fixed workspace roles.
- A centralized permission policy.
- Workspace-level data isolation.
- Consistent authorization enforcement across backend modules.
- Secure membership and ownership management.
- Audit requirements for privileged operations.
- Migration and testing strategies.

This document extends the approved Authentication and Session Design.

## 2. Architecture Decision

Phase 1 uses:

**Fixed Roles + Centralized Permissions**

The platform provides four predefined workspace roles:

1. Owner
2. Admin
3. Operator
4. Viewer

Role definitions and permission mappings are maintained centrally in backend code.

Custom roles, user-defined permissions, and database-driven permission configuration are deferred.

Authorization is enforced by the backend. Frontend visibility controls are for user experience only and must never be treated as a security boundary.

## 3. Authorization Principles

The implementation must follow these principles:

- Deny access by default.
- Apply least privilege.
- Authenticate users before performing protected operations.
- Verify active workspace membership for every workspace-scoped operation.
- Verify resource ownership and workspace scope server-side.
- Never trust workspace IDs, role names, or permission claims supplied by the client.
- Prevent privilege escalation.
- Separate authentication from authorization.
- Record security-relevant membership and permission changes.
- Apply the same authorization policy across HTTP APIs and future interfaces.

## 4. Role Definitions

### 4.1 Owner

The Owner has full control over one workspace.

Responsibilities:

- Manage workspace settings.
- Manage all workspace members and roles.
- Manage devices, rooms, and device groups.
- Access telemetry and monitoring data.
- Manage alerts and automation.
- View workspace audit records.
- Transfer workspace ownership.

Ownership transfer must use a dedicated workflow.

### 4.2 Admin

The Admin manages day-to-day workspace administration.

Responsibilities:

- View and update permitted workspace settings.
- Invite, add, deactivate, and manage workspace members.
- Assign and change non-owner roles within the permitted role hierarchy.
- Manage devices, rooms, and device groups.
- Access telemetry and monitoring.
- Manage alerts and automation.
- View permitted workspace audit records.

Restrictions:

- Cannot transfer workspace ownership.
- Cannot assign the Owner role.
- Cannot modify or deactivate the Owner.
- Cannot grant permissions beyond the Admin role's authority.

### 4.3 Operator

The Operator manages operational functions.

Responsibilities:

- View workspace dashboard information.
- View devices, rooms, and device groups.
- Control authorized devices.
- View telemetry and device status.
- Create, update, acknowledge, and resolve alerts where supported.
- Manage automation rules and operational configurations where supported.

Restrictions:

- Cannot manage workspace members or roles.
- Cannot modify workspace security settings.
- Cannot transfer ownership.
- Cannot access administrative operations.

### 4.4 Viewer

The Viewer has read-only access.

Responsibilities:

- View workspace dashboard information.
- View devices, rooms, and device groups.
- View telemetry and device status.
- View alerts.

Restrictions:

- Cannot issue device-control commands.
- Cannot modify devices or workspace settings.
- Cannot manage members or roles.
- Cannot modify alerts or automation.
- Cannot perform administrative operations.

## 5. Permission Matrix

The following matrix defines the initial Phase 1 permission policy.

| Permission | Owner | Admin | Operator | Viewer |
|---|---|---|---|---|
| View dashboard | Yes | Yes | Yes | Yes |
| View workspace settings | Yes | Yes | Yes | Yes |
| Update workspace settings | Yes | Yes | No | No |
| Delete workspace | Yes* | No | No | No |
| View members | Yes | Yes | No | No |
| Invite/add members | Yes | Yes | No | No |
| Deactivate members | Yes | Yes** | No | No |
| Assign Admin role | Yes | Yes** | No | No |
| Assign Operator role | Yes | Yes | No | No |
| Assign Viewer role | Yes | Yes | No | No |
| Assign Owner role | Dedicated workflow | No | No | No |
| Transfer ownership | Yes | No | No | No |
| View devices | Yes | Yes | Yes | Yes |
| Manage devices | Yes | Yes | No | No |
| Control devices | Yes | Yes | Yes | No |
| View rooms and groups | Yes | Yes | Yes | Yes |
| Manage rooms and groups | Yes | Yes | No | No |
| View telemetry | Yes | Yes | Yes | Yes |
| View device status | Yes | Yes | Yes | Yes |
| View alerts | Yes | Yes | Yes | Yes |
| Manage alerts | Yes | Yes | Yes | No |
| View automation | Yes | Yes | Yes | No |
| Manage automation | Yes | Yes | Yes | No |
| View audit records | Yes | Yes | No | No |

Notes:

- *Workspace deletion requires a separate protected workflow and must respect data-retention and ownership policies.
- **Admin operations must not affect the Owner or grant privileges exceeding the acting Admin's authority.
- Device-control permissions remain subject to device availability, device-level safety rules, and operational validation.
- Detailed permission granularity may be refined as API endpoints are implemented.
- Unlisted operations are denied by default.

## 6. Centralized Permission Model

Permissions must use stable identifiers rather than scattered role-name comparisons.

Initial permission identifiers:

### Workspace

- `workspace.read`
- `workspace.update`
- `workspace.delete`

### Members

- `members.read`
- `members.invite`
- `members.update`
- `members.deactivate`
- `members.role.assign`

### Ownership

- `ownership.transfer`

### Devices

- `devices.read`
- `devices.create`
- `devices.update`
- `devices.delete`
- `devices.control`

### Rooms and Groups

- `rooms.read`
- `rooms.manage`
- `device_groups.read`
- `device_groups.manage`

### Telemetry and Monitoring

- `telemetry.read`
- `device_status.read`

### Alerts

- `alerts.read`
- `alerts.manage`

### Automation

- `automation.read`
- `automation.manage`

### Audit

- `audit.read`

The centralized policy maps each role to an explicit set of permissions.

The implementation must not assume that role hierarchy alone determines permission inheritance. Every role's permissions must be explicitly defined and tested.

## 7. Workspace Isolation

Workspace isolation is mandatory.

For every workspace-scoped API operation, the backend must:

1. Authenticate the requesting user.
2. Resolve the requested workspace.
3. Verify that the user has an active membership in that workspace.
4. Verify the required permission for the operation.
5. Restrict all resource queries to the authorized workspace.
6. Validate that referenced resources belong to the same workspace.
7. Reject unauthorized access without exposing sensitive information.

The backend must never rely solely on a workspace ID supplied by the frontend.

Existing composite foreign keys provide additional database-level protection against cross-workspace relationships.

Database constraints complement authorization checks; they do not replace them.

## 8. Authorization Components

The proposed backend organization is:

### 8.1 Central Permission Policy

A centralized policy module defines:

- Supported roles.
- Permission identifiers.
- Role-to-permission mappings.
- Permission evaluation rules.

Business modules must not independently redefine role permissions.

### 8.2 Workspace Authorization Service

The service is responsible for:

- Loading workspace membership.
- Checking user and membership active status.
- Resolving the member's role.
- Checking required permissions.
- Enforcing role-management restrictions.
- Supporting ownership-transfer rules.

Authorization decisions must be based on trusted database state.

### 8.3 FastAPI Dependencies

Reusable API dependencies should provide:

- Authenticated user context.
- Active workspace membership.
- Required permission checks.
- Authorized workspace context.

API routes should declare their required authorization explicitly and delegate business logic to services.

### 8.4 Service-Level Enforcement

Sensitive business operations must enforce authorization even when invoked outside the original HTTP route.

This protects future background tasks, internal service calls, and alternative interfaces from bypassing API-only checks.

## 9. Membership Lifecycle

Workspace membership must support:

- Invitation or member addition.
- Activation.
- Deactivation.
- Role assignment.
- Role changes.
- Membership removal where permitted.

Membership operations must verify:

- The acting user's active membership.
- The acting user's required permission.
- The target membership's workspace.
- The target member's current role.
- The role hierarchy restrictions.

A user must not be able to grant themselves additional privileges.

An Admin must not assign the Owner role or modify the Owner's membership.

Membership changes should be committed atomically with their corresponding audit records.

## 10. Ownership Management

Each active workspace must have exactly one active Owner.

The database and service implementation must preserve this invariant.

### Ownership Transfer

Ownership transfer must:

1. Require the current Owner's authorization.
2. Require the target to be an active member of the same workspace.
3. Verify that the target is eligible to become Owner.
4. Execute the change in one database transaction.
5. Lock the workspace or otherwise serialize concurrent ownership changes.
6. Promote the target to Owner.
7. Assign an appropriate non-owner role to the previous Owner.
8. Record the transfer in the audit log.
9. Commit the operation atomically.

The system must prevent concurrent operations from creating multiple active Owners or leaving a workspace without an Owner.

The previous Owner's replacement role must be explicitly selected or governed by an approved default policy.

Admin users cannot transfer ownership.

Ownership transfer must not be implemented as an ordinary role-update operation.

Workspace deletion, Owner account deactivation, and Owner membership removal must follow dedicated workflows that preserve the ownership invariant.

## 11. Audit Requirements

Security-relevant authorization events must be recorded.

Required events include:

- Member invited or added.
- Membership activated or deactivated.
- Membership removed.
- Member role changed.
- Ownership transferred.
- Workspace security settings changed.
- Administrative operations affecting workspace access.

Audit records should contain:

- Workspace ID when applicable.
- Actor identity.
- Action identifier.
- Target resource type and ID.
- Timestamp.
- Relevant non-sensitive change metadata.

Audit records must never contain:

- Passwords.
- Raw session tokens.
- CSRF tokens.
- Private keys.
- Device credentials.
- Other authentication secrets.

Audit records should be append-only from normal application workflows. Access to audit records must itself be authorized.

## 12. Database and Migration Strategy

The existing `WorkspaceMember.role` column currently permits:

- `owner`
- `admin`
- `member`

The Phase 1 target roles are:

- `owner`
- `admin`
- `operator`
- `viewer`

The existing initial migration must not be modified.

A new migration must follow the current Alembic head:

- `20261103_0001` — Initial schema.
- `20261103_0002` — User sessions.
- `20261103_0003` — Workspace RBAC.

The proposed migration should:

1. Drop the existing role check constraint.
2. Convert existing `member` values to `viewer`.
3. Add a new role check constraint allowing the four approved roles.
4. Preserve existing membership IDs, workspace IDs, user IDs, and other membership data.

The migration must be reviewed before application.

### Downgrade Considerations

Downgrading to the old three-role schema requires converting both `operator` and `viewer` to `member`.

This loses the distinction between those roles.

Therefore:

- Downgrade is semantically lossy.
- A backup is required before applying the migration.
- Downgrade behavior must be documented and tested.
- No migration may be applied to a real database without explicit approval.

### Ownership Constraint Considerations

A partial unique index may enforce at most one active Owner per workspace.

The application service must enforce the requirement for at least one active Owner through transactional ownership workflows.

Any database-level enforcement beyond the existing constraints must be reviewed before implementation.

## 13. Error Handling

Authorization failures must return safe, consistent responses.

Suggested behavior:

- `401 Unauthorized`: Authentication is missing or invalid.
- `403 Forbidden`: The authenticated user lacks the required permission.
- `404 Not Found`: A resource is unavailable or intentionally concealed to avoid disclosing cross-workspace resource existence.
- `409 Conflict`: A membership or ownership operation conflicts with current state.

Internal exceptions and sensitive authorization details must not be exposed to clients.

## 14. Testing Strategy

### Permission Policy Tests

Test every role against every defined permission.

Verify that:

- Owner has the intended full permission set.
- Admin cannot transfer ownership or assign Owner.
- Operator cannot manage workspace membership.
- Viewer cannot perform state-changing operations.
- Unknown roles and permissions are denied.

### Workspace Isolation Tests

Test that:

- A user cannot access another workspace without membership.
- Inactive memberships are rejected.
- Inactive users are rejected.
- Resource IDs from another workspace cannot be accessed or modified.
- Cross-workspace relationships are rejected.

### Membership Tests

Test:

- Member creation and activation.
- Role changes.
- Deactivation.
- Privilege escalation attempts.
- Admin restrictions.
- Self-role escalation attempts.

### Ownership Tests

Test:

- Successful ownership transfer.
- Transfer to an inactive or unrelated member.
- Concurrent transfer attempts.
- Prevention of multiple active Owners.
- Prevention of a workspace being left without an active Owner.
- Audit record creation.

### API Tests

Verify that protected routes enforce authentication, workspace membership, and required permissions.

### Database Tests

Use an isolated test database for migration and database-constraint integration tests.

Unit and mock-based tests must remain distinguishable from PostgreSQL integration tests.

Never run destructive tests against production data.

## 15. Implementation Plan

Implementation should proceed in the following order:

1. Approve this authorization design.
2. Implement centralized role and permission definitions.
3. Add the Workspace Authorization Service.
4. Add reusable FastAPI authorization dependencies.
5. Implement workspace-scoped access checks.
6. Implement membership-management workflows.
7. Implement ownership-transfer workflow.
8. Create and review the RBAC database migration.
9. Add authorization audit events.
10. Add unit, API, and database integration tests.
11. Review all protected endpoints for authorization coverage.

No production database migration should occur without explicit approval.

## 16. Deferred Decisions

The following items require separate decisions or detailed implementation design:

- Invitation delivery and email verification.
- Member invitation expiration.
- Fine-grained device-control permissions.
- Workspace deletion and data-retention workflow.
- Owner deactivation and account-deletion workflow.
- Audit retention and export policy.
- API rate limiting for membership operations.
- Whether Operators may manage automation schedules or only operational rules.
- Whether workspace settings should have finer permission categories.

These decisions must not weaken the four-role authorization model or workspace isolation.

## 17. Document Status

This document records the proposed Phase 1 authorization architecture.

The four fixed roles and centralized permission approach are approved architectural decisions.

The detailed permission matrix, ownership invariants, migration strategy, and implementation requirements remain subject to technical review before implementation.

**Status: Draft — pending technical review and approval.**
