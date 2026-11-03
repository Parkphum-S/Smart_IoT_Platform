# Database Design

**Project:** Smart IoT Platform
**Version:** 1.0
**Status:** Draft
**Last Updated:** 2026-11-03

---

## 1. Purpose

This document defines the initial PostgreSQL database architecture for Smart IoT Platform.

The database supports device management, telemetry ingestion, monitoring, user access control, and future automation capabilities.

The design uses a relational model with clear ownership boundaries and version-controlled schema migrations.

## 2. Database Technology

PostgreSQL is the approved primary relational database.

### 2.1 Database Principles

- Use relational tables with explicit primary and foreign keys.
- Use UUID identifiers for entities that may be referenced across modules.
- Use UTC timestamps for stored date and time values.
- Enforce data integrity through database constraints.
- Add indexes based on actual query patterns.
- Use database migrations for all schema changes.
- Keep database access behind module services and repository interfaces.
- Avoid unnecessary database extensions and infrastructure dependencies.

### 2.2 Data Ownership

- Each business module owns its tables and data access rules.
- Cross-module relationships must use stable identifiers.
- Modules must not modify another module data through direct table access.
- Shared database infrastructure manages connections and sessions, not business rules.

## 3. Common Data Standards

### 3.1 Identifiers

- Use UUID as the primary key for major business entities.
- Use consistent foreign key naming with the referenced entity name followed by `_id`.
- Never use sequential database IDs as public device identifiers.

### 3.2 Timestamps

- Use `TIMESTAMPTZ` for timestamps representing real points in time.
- Store timestamps in UTC.
- Use `created_at` and `updated_at` for mutable business entities.
- Use `recorded_at` for the time a device measured telemetry.
- Use `received_at` for the time the backend received telemetry.

### 3.3 Naming Conventions

- Use lowercase snake_case for table and column names.
- Use plural nouns for table names.
- Use explicit and descriptive column names.
- Avoid reserved SQL keywords as identifiers.

### 3.4 Data Integrity

- Define NOT NULL constraints for required fields.
- Define UNIQUE constraints for business identifiers that must not repeat.
- Define CHECK constraints for values with clear database-level rules.
- Define foreign key deletion behavior explicitly.
- Use transactions for operations that modify related records.

## 4. Workspace and User Management

A workspace represents an independently managed home, building, or site.

A user may belong to multiple workspaces. Each workspace may contain multiple users.

### 4.1 Tables

#### users

- `id`: UUID primary key.
- `email`: unique login email.
- `password_hash`: securely hashed password; never store plaintext passwords.
- `display_name`: user display name.
- `is_active`: account status.
- `created_at`, `updated_at`: timestamps.

#### workspaces

- `id`: UUID primary key.
- `name`: workspace name.
- `description`: optional description.
- `timezone`: workspace display timezone.
- `created_at`, `updated_at`: timestamps.

#### workspace_members

- `id`: UUID primary key.
- `workspace_id`: references workspaces.
- `user_id`: references users.
- `role`: workspace role, initially owner, admin, or member.
- `is_active`: whether the membership is active.
- `joined_at`: membership creation time.
- Unique constraint on (`workspace_id`, `user_id`).

### 4.2 Access Rules

- Every workspace-owned resource must be scoped to its workspace.
- Users may access only workspaces where they have an active membership.
- The backend must enforce workspace authorization on every relevant request.
- The frontend must never be treated as the security boundary.
- A workspace must retain at least one owner.

### 4.3 Design Notes

- Workspace is the proposed data isolation boundary for homes, buildings, and sites.
- Initial roles are stored on workspace membership; a separate roles table is deferred until custom roles are required.
- Workspace ownership transfer and account recovery procedures require further design.

## 5. Device Management

The Device Management domain owns device identity, registration, configuration, and current device state.

### 5.1 Tables

#### device_types

- `id`: UUID primary key.
- `name`: device type name.
- `description`: optional description.
- `capabilities`: JSONB describing supported capabilities.
- `created_at`, `updated_at`: timestamps.

#### devices

- `id`: UUID primary key.
- `workspace_id`: references workspaces.
- `device_type_id`: references device_types.
- `device_uid`: unique device identity within the platform.
- `name`: user-defined device name.
- `manufacturer`: optional manufacturer.
- `model`: optional device model.
- `protocol`: communication protocol, such as MQTT or HTTP.
- `is_enabled`: whether the device is enabled.
- `created_at`, `updated_at`: timestamps.

#### device_credentials

- `id`: UUID primary key.
- `device_id`: references devices.
- `credential_type`: credential mechanism.
- `secret_hash`: optional hash for credentials that can be verified without recovering the secret.
- `secret_reference`: reference to an externally managed secret when recovery is required.
- `created_at`, `expires_at`, `revoked_at`: credential lifecycle timestamps.
- Never store plaintext device passwords, tokens, or private keys.

#### device_status

- `device_id`: UUID primary key and foreign key to devices.
- `connection_state`: current connection state.
- `last_seen_at`: most recent observed device activity.
- `reported_state`: JSONB containing the latest reported state.
- `updated_at`: last status update timestamp.

### 5.2 Design Rules

- A device belongs to exactly one workspace.
- Device identity must be stable and independent of its display name.
- Device credentials must support revocation and rotation.
- Device status stores the latest snapshot; historical changes belong to the Monitoring and Events domain.
- Device capabilities describe supported functions and must not be treated as proof that a command is safe or authorized.
- Device communication must pass through trusted backend services and protocol adapters.

### 5.3 Open Design Decisions

- Device onboarding and ownership transfer workflows require further specification.
- The exact capability schema will be defined when device profiles are designed.
- Credential encryption and key management must be finalized before production.

## 6. Rooms and Device Groups

This domain organizes devices into workspace rooms and user-defined groups.

### 6.1 Tables

#### rooms

- `id`: UUID primary key.
- `workspace_id`: references workspaces.
- `name`: room name.
- `icon`: optional UI icon identifier.
- `sort_order`: display order.
- `created_at`, `updated_at`: timestamps.

#### device_rooms

- `workspace_id`: NOT NULL, references the owning workspace.
- `device_id`: references devices.
- `room_id`: references rooms.
- `assigned_at`: assignment timestamp.
- Primary key: `device_id`.
- A device may belong to zero or one room at a time.

#### device_groups

- `id`: UUID primary key.
- `workspace_id`: references workspaces.
- `name`: group name.
- `description`: optional description.
- `created_at`, `updated_at`: timestamps.

#### device_group_members

- `workspace_id`: NOT NULL, references the owning workspace.
- `device_group_id`: references device_groups.
- `device_id`: references devices.
- `added_at`: membership timestamp.
- Composite primary key: (`device_group_id`, `device_id`).

### 6.2 Design Rules

- Rooms and device groups belong to one workspace.
- A device can belong to multiple groups.
- A device can be assigned to only one room at a time.
- The backend must verify that related devices, rooms, and groups belong to the same workspace.
- Moving a device between rooms must not delete its telemetry or event history.
- Room and group deletion must not cascade into device deletion.

## 7. Telemetry

The Telemetry domain stores time-series measurements reported by devices.

### 7.1 Tables

#### telemetry_metrics

- `id`: UUID primary key.
- `device_type_id`: references device_types.
- `metric_key`: stable metric identifier, such as temperature or humidity.
- `display_name`: human-readable metric name.
- `data_type`: numeric, text, boolean, or JSON.
- `unit`: optional measurement unit.
- `created_at`, `updated_at`: timestamps.
- Unique constraint on (`device_type_id`, `metric_key`).

#### telemetry_readings

- `id`: UUID primary key.
- `workspace_id`: references workspaces.
- `device_id`: references devices.
- `device_type_id`: references the device type and supports device-to-metric consistency.
- `metric_id`: references telemetry_metrics.
- `value_numeric`: numeric measurement value when applicable.
- `value_text`: text value when applicable.
- `value_boolean`: boolean value when applicable.
- `value_json`: JSONB value for structured measurements when applicable.
- `recorded_at`: device measurement timestamp.
- `received_at`: backend receipt timestamp.
- `quality`: optional measurement quality indicator.

### 7.2 Data Rules

- Each reading must identify its workspace, device, and metric.
- Exactly one value column must contain a value for each reading.
- The selected value column must match the metric data type.
- Validate device ownership and metric compatibility before storing readings.
- Preserve both recorded_at and received_at to support delayed or out-of-order messages.
- Reject or quarantine invalid measurements without silently changing their values.

### 7.3 Indexing and Retention

- Add a composite index on (`device_id`, `recorded_at`).
- Add workspace and time indexes only when supported by query patterns.
- Define retention and archival policies before production.
- Start with standard PostgreSQL; defer TimescaleDB until measured workload justifies it.
- Evaluate partitioning when telemetry volume and query performance require it.

## 8. Monitoring and Events

This domain manages device events, alert lifecycles, notifications, and audit records.

### 8.1 Tables

#### device_events

- `id`: UUID primary key.
- `workspace_id`: references workspaces.
- `device_id`: references devices.
- `event_type`: event category.
- `severity`: informational, warning, or critical.
- `payload`: JSONB event details.
- `occurred_at`: event occurrence timestamp.
- `received_at`: backend receipt timestamp.

#### alert_rules

- `id`: UUID primary key.
- `workspace_id`: references workspaces.
- `name`: rule name.
- `is_enabled`: whether the rule is active.
- `condition_config`: JSONB rule configuration.
- `created_at`, `updated_at`: timestamps.

#### alerts

- `id`: UUID primary key.
- `workspace_id`: references workspaces.
- `alert_rule_id`: optional reference to alert_rules.
- `device_id`: optional reference to devices.
- `title`: alert title.
- `description`: optional details.
- `severity`: informational, warning, or critical.
- `status`: open, acknowledged, or resolved.
- `triggered_at`: alert creation time.
- `acknowledged_at`, `resolved_at`: optional lifecycle timestamps.

#### notifications

- `id`: UUID primary key.
- `workspace_id`: references workspaces.
- `user_id`: references users.
- `alert_id`: optional reference to alerts.
- `channel`: in_app, email, or push.
- `title`: notification title.
- `message`: notification content.
- `read_at`: optional read timestamp.
- `created_at`: creation timestamp.

#### audit_logs

- `id`: UUID primary key.
- `workspace_id`: optional workspace reference for system-wide actions.
- `actor_type`: user, device, or system.
- `actor_id`: optional actor identifier.
- `action`: action name.
- `resource_type`: affected resource type.
- `resource_id`: affected resource identifier.
- `details`: JSONB audit details; exclude secrets and credentials.
- `created_at`: event timestamp.

### 8.2 Design Rules

- Device events are historical records and must not be confused with the latest device_status snapshot.
- Alerts represent conditions requiring attention and have an explicit lifecycle.
- Notifications are user-facing delivery records, separate from alert state.
- Audit logs are append-only and must not be modified through ordinary application workflows.
- Apply workspace authorization before exposing events, alerts, or notifications.
- Define retention policies for events and audit logs before production.

## 9. Automation

The Automation domain stores user-defined rules, conditions, actions, and execution history.

### 9.1 Tables

#### automation_rules

- `id`: UUID primary key.
- `workspace_id`: references workspaces.
- `name`: automation name.
- `description`: optional description.
- `is_enabled`: whether the automation is enabled.
- `created_by`: references users.
- `created_at`, `updated_at`: timestamps.

#### automation_conditions

- `id`: UUID primary key.
- `automation_rule_id`: references automation_rules.
- `condition_type`: condition category.
- `condition_config`: JSONB condition parameters.
- `evaluation_order`: condition evaluation order.

#### automation_actions

- `id`: UUID primary key.
- `automation_rule_id`: references automation_rules.
- `action_type`: action category.
- `action_config`: JSONB action parameters.
- `execution_order`: action execution order.

#### automation_executions

- `id`: UUID primary key.
- `workspace_id`: references workspaces.
- `automation_rule_id`: references automation_rules.
- `status`: pending, running, succeeded, failed, or cancelled.
- `triggered_at`: execution start trigger timestamp.
- `started_at`, `finished_at`: optional execution timestamps.
- `result`: JSONB execution summary.
- `error_message`: optional sanitized error description.

### 9.2 Design Rules

- Automation records must belong to a workspace.
- Conditions and actions must be validated against supported capabilities.
- Execution history must be retained independently of the current rule configuration.
- Prevent duplicate processing of the same trigger where applicable.
- Enforce authorization and safety validation before any device action.
- Automation execution must be handled by backend services, never directly by the browser.

### 9.3 Implementation Scope

- Database design is included in the initial architecture.
- Automation execution engine is deferred until a later implementation phase.
- Initial condition and action schemas remain open until supported device capabilities are defined.

## 10. Relationships and Referential Integrity

### 10.1 Core Relationships

- A user can belong to multiple workspaces through workspace_members.
- A workspace has multiple devices, rooms, groups, events, alerts, and automation rules.
- A device belongs to one workspace and one device type.
- A device may have multiple credential records over its lifecycle.
- A device has at most one current device_status record.
- A device may be assigned to zero or one room.
- A device may belong to multiple device groups.
- A device type defines the metrics supported by its devices.
- A device may have many telemetry readings and device events.
- An alert may originate from an alert rule and optionally relate to a device.
- A user may receive multiple notifications.
- An automation rule has multiple conditions, actions, and executions.

### 10.2 Workspace Consistency

- Every workspace-owned record must reference a valid workspace.
- Related records must belong to the same workspace.
- Enforce workspace consistency through database constraints where practical and backend validation.
- Do not rely on UUID values alone as proof of workspace authorization.
- Use composite foreign keys where needed to prevent cross-workspace references.

### 10.3 Deletion Rules

- Prefer soft deletion or explicit archival for important business entities.
- Do not cascade-delete telemetry readings, device events, or audit logs when a device is removed.
- Restrict deletion when dependent records must be retained.
- Define retention and permanent deletion procedures separately.
- Membership removal must not delete the user account or workspace data.

## 11. Security and Data Protection

### 11.1 Database Access

- Do not expose PostgreSQL directly to the public internet.
- Allow database access only from authorized application services and administrators.
- Use a dedicated database role for the application.
- Apply least-privilege permissions to database roles.
- Keep administrative credentials separate from application credentials.

### 11.2 Sensitive Data

- Store user passwords only as secure password hashes using an approved password-hashing algorithm.
- Never store plaintext passwords, API tokens, MQTT passwords, or private keys.
- Encrypt recoverable secrets and manage encryption keys separately from the database.
- Exclude credentials, tokens, and sensitive personal data from logs and audit payloads.
- Restrict access to credential records and secret references.

### 11.3 Tenant Isolation

- Verify workspace membership and role permissions before accessing workspace data.
- Apply workspace scoping consistently in application queries.
- Consider PostgreSQL Row-Level Security as an additional defense after evaluating connection pooling and transaction behavior.
- Test cross-workspace access denial as part of the security test suite.

### 11.4 Operational Protection

- Use TLS for database connections when traffic crosses an untrusted network.
- Review database permissions and schema changes before production.
- Record security-relevant administrative actions in audit logs.
- Establish backup encryption and access controls.

## 12. Migrations and Backup Strategy

### 12.1 Schema Migrations

- Use Alembic to manage all database schema changes.
- Keep migration scripts under backend/migrations.
- Store migration scripts in Git with the application source code.
- Never modify production schema manually as a normal deployment procedure.
- Review generated migrations before applying them.
- Test migrations against a separate development database.
- Use backward-compatible changes where practical.
- Define rollback or recovery procedures for risky migrations.

### 12.2 Backup Strategy

- Back up PostgreSQL data on a defined schedule.
- Encrypt backups and restrict access to authorized administrators.
- Keep at least one backup copy on storage independent from the primary server.
- The primary `/data` SSD is application storage, not an independent backup destination.
- Define backup retention according to data importance and available storage.
- Document and periodically test database restoration.

### 12.3 Recovery Objectives

- Define Recovery Point Objective (RPO) before production.
- Define Recovery Time Objective (RTO) before production.
- Monitor backup job success and available storage.
- Do not consider a backup successful until its integrity and restoration process have been verified.

### 12.4 Open Decisions

- Backup destination and off-site strategy remain to be selected.
- Backup frequency and retention periods remain to be finalized.
- Point-in-time recovery requirements remain to be evaluated.

## 13. Phase 1 Implementation Scope

### 13.1 Initial Database Foundation

- Establish PostgreSQL connection management through the backend infrastructure layer.
- Configure SQLAlchemy 2.x asynchronous database access using asyncpg.
- Configure Alembic for version-controlled schema migrations.
- Implement database health checks.
- Establish transaction management and session lifecycle rules.
- Apply database constraints and indexes defined by the approved schema.

### 13.2 Initial Business Domains

- Users and workspace membership.
- Device types, devices, credentials, and current device status.
- Rooms and device groups.
- Telemetry metrics and readings.
- Device events, alerts, notifications, and audit logs.
- Automation schema preparation without enabling the execution engine.

### 13.3 Deferred Work

- Advanced telemetry partitioning and TimescaleDB evaluation.
- Custom workspace role management.
- Advanced automation execution and scheduling.
- Long-term telemetry archival implementation.
- High-availability database deployment.
- Point-in-time recovery implementation, subject to recovery requirements.

### 13.4 Implementation Principle

Implement the smallest reliable database foundation that supports the approved Phase 1 product scope. Expand only when measured requirements justify additional complexity.

## 14. Open Decisions

The following decisions must be finalized before production deployment:

1. Workspace ownership transfer and account recovery procedures.
2. Final workspace role and permission matrix.
3. Device onboarding, provisioning, and credential rotation workflows.
4. Device capability and telemetry metric schemas.
5. Telemetry, event, and audit data retention periods.
6. Backup destination, frequency, retention, and restoration objectives.
7. Encryption key management for recoverable device credentials.
8. PostgreSQL connection limits and resource allocation for the ARM64 server.
9. Whether PostgreSQL Row-Level Security is required in addition to application-level authorization.
10. Whether telemetry partitioning is justified by measured data volume.

## 15. Document Status

**Status:** Draft - Initial database architecture documented.

**Next Step:** Review the database model, resolve critical design decisions, and prepare the initial SQLAlchemy models and Alembic migration plan.

**Implementation Status:** No database schema or application code has been created by this document.

---

End of Database Design Document.

## 16. Database Integrity Clarifications

This section clarifies integrity requirements that must be addressed when translating the conceptual model into SQLAlchemy models and PostgreSQL constraints.

### 16.1 Workspace Isolation Constraints

- Workspace-owned entities should expose composite unique keys where required for workspace-scoped foreign keys.
- Use composite foreign keys to ensure related devices, rooms, groups, alerts, and automation records belong to the same workspace.
- A valid UUID reference alone does not establish workspace ownership.
- Apply the same consistency requirements to notification recipients and workspace memberships.

### 16.2 Telemetry Consistency Constraints

- A telemetry reading must reference a device and a metric supported by that device type.
- Enforce device-to-metric compatibility through composite foreign keys where practical, or validated backend services with database constraints.
- Ensure exactly one telemetry value column is populated.
- Ensure the populated value column matches the metric data type.

### 16.3 Ownership and Membership Constraints

- A workspace must always have at least one active owner.
- Owner removal or ownership transfer must be handled transactionally.
- Enforce membership checks when creating workspace notifications.
- Prevent removal of the final active owner.

### 16.4 Constraint Verification

- Include automated tests for cross-workspace reference rejection.
- Include tests for invalid device and metric combinations.
- Include tests for final-owner protection.
- Review foreign key constraints, unique constraints, and CHECK constraints before generating the initial production migration.

These requirements must be validated during database implementation; this document does not imply that the constraints have already been implemented.

## 17. Implementation Mapping Requirements

### 17.1 Workspace Membership Lifecycle

- Add an `is_active` boolean field to workspace_members.
- Membership revocation must preserve historical records where required.
- Only active owners count toward the minimum workspace ownership requirement.
- Membership role changes must be authorized and audited.

### 17.2 Cross-Workspace Relationship Protection

- device_rooms must ensure the assigned room and device belong to the same workspace.
- device_group_members must ensure the group and device belong to the same workspace.
- alerts must ensure referenced rules and devices belong to the alert workspace.
- notifications must ensure the recipient is an eligible workspace member.
- Automation child records must remain associated with their parent rule and workspace.

### 17.3 Database Implementation Review

- Define composite unique constraints and foreign keys for workspace-scoped relationships.
- Define explicit indexes for foreign key columns and frequently queried fields.
- Define status values and allowed transitions for devices, alerts, credentials, and automation executions.
- Confirm all ownership, membership, and deletion rules before generating migrations.

These requirements are part of the implementation design review and must be verified through database constraints and automated tests.

## 18. Composite Key and Transaction Implementation Specification

This section provides explicit PostgreSQL implementation requirements. It supplements and takes precedence over earlier conceptual relationship descriptions where additional columns or constraints are required.

### 18.1 Workspace-Scoped Composite Keys

- Add a UNIQUE constraint on (workspace_id, id) to workspace-owned parent tables, including devices, rooms, device_groups, alert_rules, and alerts.
- Use composite foreign keys containing workspace_id when a child record references a workspace-owned parent.
- Keep the ordinary UUID primary keys. Composite unique constraints provide additional referenced keys for workspace consistency.
- Ensure all composite foreign key columns have compatible data types and required NOT NULL behavior.

### 18.2 Device Room and Group Membership Mapping

The device_rooms table must contain:
- workspace_id: NOT NULL, references the owning workspace.
- device_id: NOT NULL.
- room_id: NOT NULL.
- assigned_at: assignment timestamp.
- Primary key: device_id, preserving the rule that a device belongs to at most one room.
- Composite foreign keys: (workspace_id, device_id) references devices (workspace_id, id); (workspace_id, room_id) references rooms (workspace_id, id).

The device_group_members table must contain:
- workspace_id: NOT NULL, references the owning workspace.
- device_group_id: NOT NULL.
- device_id: NOT NULL.
- added_at: membership timestamp.
- Primary key: (device_group_id, device_id).
- Composite foreign keys: (workspace_id, device_group_id) references device_groups (workspace_id, id); (workspace_id, device_id) references devices (workspace_id, id).

These constraints make cross-workspace room assignments and group memberships invalid at the database level.

### 18.3 Telemetry Device-Type Compatibility

- Add a UNIQUE constraint on devices (id, device_type_id) to support a composite reference.
- Add a UNIQUE constraint on telemetry_metrics (device_type_id, id).
- Include device_type_id in telemetry_readings.
- Reference devices through (device_id, device_type_id) to devices (id, device_type_id).
- Reference telemetry_metrics through (device_type_id, metric_id) to telemetry_metrics (device_type_id, id).
- Retain workspace_id and enforce the reading-to-device workspace relationship through a composite foreign key.
- Enforce exactly one populated value column with a CHECK constraint; enforce compatibility between data_type and the populated column through a CHECK constraint or a database trigger where required.

### 18.4 Alerts and Notifications

- Alerts must reference alert_rules and devices through workspace-scoped composite foreign keys whenever those optional references are present.
- Add a UNIQUE constraint on workspace_members (workspace_id, user_id) as the referenced membership key.
- Notifications must reference (workspace_id, user_id) in workspace_members so a notification cannot target a user who has no membership record in that workspace.
- Active membership must additionally be checked by the application transaction because a foreign key cannot enforce that is_active is true.

### 18.5 Minimum Active Workspace Owner

- Serialize membership operations that can deactivate, remove, or demote an owner by locking the parent workspace row within a transaction.
- After acquiring the lock, verify that the operation leaves at least one active owner.
- Apply the membership change only if the invariant remains satisfied; otherwise reject and roll back the transaction.
- Ownership transfer must promote the new owner and update the former owner atomically.
- Audit successful role and membership changes.
- Do not rely on a simple CHECK constraint to enforce an aggregate rule across multiple membership rows.

### 18.6 Constraint and Migration Verification

- Create referenced composite UNIQUE constraints before creating dependent composite foreign keys.
- Define indexes for foreign key columns and common workspace-scoped query patterns.
- Test cross-workspace references for devices, rooms, groups, telemetry, alerts, and notifications.
- Test invalid device-type and metric combinations.
- Test concurrent attempts to remove or demote the final active owner.
- Review generated SQL and migration ordering before applying migrations to any persistent database.
- Treat this section as an implementation specification; no database constraints or migrations are created by this document.
