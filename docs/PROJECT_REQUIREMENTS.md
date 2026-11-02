# Smart IoT Platform
## Project Requirements Specification

**Document:** PROJECT_REQUIREMENTS.md  
**Project:** Smart IoT Platform  
**Version:** 1.0  
**Status:** Draft - Phase 1 Baseline  
**Last Updated:** 2026-11-02

---

## 1. Project Overview

Smart IoT Platform is a self-hosted, modular Internet of Things platform designed to connect, manage, monitor, and analyze data from IoT devices through a centralized application.

The platform will support multiple communication protocols through an extensible adapter architecture. MQTT will be the primary IoT messaging protocol, while HTTP/REST will provide application-facing APIs.

The system will initially target a resource-constrained ARM64 server and must be designed to support future expansion without requiring a complete architectural redesign.

## 2. Project Objectives

The primary objectives are:

1. Provide centralized management of IoT devices.
2. Receive and process telemetry data from connected devices.
3. Monitor device connectivity and operational status.
4. Provide a web-based interface for users.
5. Provide secure APIs for application integration.
6. Support device commands with authorization and auditability.
7. Store telemetry and operational data reliably.
8. Provide an extensible architecture for additional protocols.
9. Support self-hosted deployment and data ownership.
10. Establish a foundation for future analytics and automation.

## 3. Architecture Decisions

The following decisions are approved for Phase 1.

| Area | Decision |
|---|---|
| Architecture | Modular Monolith |
| Protocol Architecture | Multi-Protocol Adapter |
| Primary IoT Protocol | MQTT |
| Application API | HTTP/REST |
| Future Industrial Protocol | Modbus TCP/RTU |
| Database | PostgreSQL |
| MQTT Broker | Eclipse Mosquitto |
| Deployment | Self-hosted |
| Container Platform | Docker Compose |
| Initial Product Priority | Both device management and monitoring |
| Storage | External SSD mounted at /data |

Additional infrastructure components must be justified by actual requirements and available server resources.

## 4. Scope

### 4.1 Phase 1 - Initial Platform

Phase 1 includes:

- Backend application with modular architecture.
- Device registration and management.
- Device identity and authentication.
- MQTT broker integration.
- Telemetry ingestion and validation.
- Device status and connectivity monitoring.
- REST API for application access.
- Web dashboard foundation.
- User authentication and authorization.
- Role-based access control.
- PostgreSQL persistence.
- Basic device command management.
- Audit logging for security-sensitive actions.
- Docker Compose deployment.
- Configuration and secret management.
- Basic backup and recovery procedures.
- Health checks and operational logging.

### 4.2 Future Phases

The following capabilities are planned for future evaluation:

- Modbus TCP and Modbus RTU adapters.
- Additional industrial and IoT protocols.
- Advanced analytics and reporting.
- Alerting and notification integrations.
- Rule engine and automation workflows.
- Device firmware and OTA management.
- Multi-site and multi-tenant management.
- High availability and horizontal scaling.
- Advanced telemetry retention and time-series optimization.

These capabilities are not mandatory Phase 1 deliverables.

## 5. Functional Requirements

Priority definitions:

- **Must:** Required for Phase 1.
- **Should:** Important, but may follow the initial release.
- **Future:** Planned for a later phase.

### 5.1 Device Management

| ID | Requirement | Priority |
|---|---|---|
| FR-DEV-001 | Register a new IoT device | Must |
| FR-DEV-002 | Assign a unique device identifier | Must |
| FR-DEV-003 | Store device metadata | Must |
| FR-DEV-004 | Update device information | Must |
| FR-DEV-005 | Enable or disable a device | Must |
| FR-DEV-006 | View device details and status | Must |
| FR-DEV-007 | Track device last-seen timestamp | Must |
| FR-DEV-008 | Support device grouping | Should |
| FR-DEV-009 | Support device lifecycle management | Should |

### 5.2 Telemetry Management

| ID | Requirement | Priority |
|---|---|---|
| FR-TEL-001 | Receive telemetry through MQTT | Must |
| FR-TEL-002 | Validate incoming messages | Must |
| FR-TEL-003 | Associate telemetry with a registered device | Must |
| FR-TEL-004 | Store telemetry in PostgreSQL | Must |
| FR-TEL-005 | Record timestamps for telemetry events | Must |
| FR-TEL-006 | Query telemetry by device and time range | Must |
| FR-TEL-007 | Handle malformed messages safely | Must |
| FR-TEL-008 | Support configurable retention policies | Should |
| FR-TEL-009 | Support aggregation and analytics | Future |

### 5.3 Device Communication

| ID | Requirement | Priority |
|---|---|---|
| FR-COM-001 | Connect devices through MQTT | Must |
| FR-COM-002 | Support MQTT publish and subscribe workflows | Must |
| FR-COM-003 | Provide authenticated device connections | Must |
| FR-COM-004 | Restrict device access to authorized topics | Must |
| FR-COM-005 | Provide an application interface for device commands | Must |
| FR-COM-006 | Record command requests and outcomes | Must |
| FR-COM-007 | Support command timeout and failure handling | Should |
| FR-COM-008 | Add Modbus adapters | Future |

### 5.4 User and Access Management

| ID | Requirement | Priority |
|---|---|---|
| FR-AUTH-001 | Authenticate application users | Must |
| FR-AUTH-002 | Support role-based access control | Must |
| FR-AUTH-003 | Restrict administrative operations | Must |
| FR-AUTH-004 | Provide secure session or token handling | Must |
| FR-AUTH-005 | Record security-sensitive user actions | Must |
| FR-AUTH-006 | Support user lifecycle management | Should |

### 5.5 Dashboard and Application

| ID | Requirement | Priority |
|---|---|---|
| FR-UI-001 | Display an overview of registered devices | Must |
| FR-UI-002 | Display device connectivity status | Must |
| FR-UI-003 | Display recent telemetry | Must |
| FR-UI-004 | Display historical telemetry | Must |
| FR-UI-005 | Provide device detail pages | Must |
| FR-UI-006 | Provide device management interface | Must |
| FR-UI-007 | Provide responsive web interface | Should |
| FR-UI-008 | Provide charts and advanced visualization | Should |

## 6. Non-Functional Requirements

### 6.1 Security

The platform must:

- Use TLS for external communication.
- Disable anonymous MQTT access.
- Authenticate devices individually.
- Enforce topic-level authorization.
- Use HTTPS for application access.
- Apply role-based authorization to protected operations.
- Store secrets outside source code and version control.
- Avoid exposing PostgreSQL directly to public networks.
- Validate and sanitize untrusted input.
- Log authentication and privileged operations.
- Apply least-privilege access principles.
- Maintain a process for credential rotation and revocation.

### 6.2 Reliability

The platform should:

- Recover services automatically after an unexpected restart.
- Provide service health checks.
- Handle temporary network interruptions.
- Detect stale or disconnected devices.
- Handle duplicate or delayed telemetry messages safely.
- Support database backup and restoration.
- Avoid losing critical data during normal service restarts.

### 6.3 Performance and Resource Efficiency

The initial deployment must operate within the available server resources.

Initial server constraints:

- CPU: 4-core ARM64.
- Memory: Approximately 3.7 GiB RAM.
- Root storage: Approximately 57 GB.
- External SSD: Approximately 500 GB.
- Deployment: Self-hosted Linux server.

The implementation should:

- Support ARM64 container images.
- Use resource-efficient services.
- Avoid unnecessary infrastructure components.
- Apply database connection pooling where appropriate.
- Support pagination for large API responses.
- Avoid loading unbounded telemetry datasets into memory.

Specific throughput, latency, and concurrent-device targets must be established through workload analysis and testing.

### 6.4 Maintainability

The system must:

- Use clearly separated application modules.
- Keep protocol-specific logic outside core business logic.
- Provide consistent API conventions.
- Maintain technical documentation.
- Use version control for source code and configuration templates.
- Support automated testing.
- Use database migrations for schema changes.

### 6.5 Scalability

The architecture should support:

- Additional protocol adapters.
- Increasing numbers of IoT devices.
- Increasing telemetry volume.
- Future separation of modules into independent services when justified.
- External integrations through documented APIs.

## 7. Protocol Requirements

### 7.1 MQTT

MQTT is the primary protocol for device messaging.

The implementation should support:

- Authenticated connections.
- TLS-protected connections.
- Topic-level access control.
- Device-specific credentials.
- Telemetry publishing.
- Command delivery.
- Configurable Quality of Service.
- Last Will and Testament where appropriate.
- Message validation and processing.

Topic naming conventions and payload schemas must be documented in the API and protocol specifications.

### 7.2 HTTP/REST

HTTP/REST is the primary application integration interface.

The API should provide endpoints for:

- Authentication.
- User management.
- Device registration and management.
- Device status.
- Telemetry queries.
- Device commands.
- System health and operational status.

API versioning, error formats, pagination, and authorization rules must be consistent.

### 7.3 Modbus

Modbus TCP/RTU is reserved for a future adapter.

The adapter must translate Modbus-specific data into the platform's standard device and telemetry model.

Modbus implementation details will be defined when the target hardware and integration requirements are known.

## 8. Data Requirements

The initial data model is expected to include:

- Users
- Roles and permissions
- Devices
- Device credentials or credential references
- Device metadata
- Telemetry records
- Device status and connectivity events
- Device commands
- Audit events

Data ownership and retention requirements must be documented.

Sensitive credentials must not be stored as plaintext.

Database migrations and backup procedures must be maintained.

## 9. Deployment Requirements

The initial deployment environment is:

- Ubuntu Server.
- ARM64 architecture.
- Docker Engine.
- Docker Compose.
- PostgreSQL.
- Eclipse Mosquitto.
- Backend application.
- Web application.
- Reverse proxy where required.

Persistent data must be stored outside disposable containers.

The existing external SSD is mounted at:

`/data`

The project source directory is:

`/data/projects/Smart_IoT_Platform`

The intended storage separation is:

- Project source: `/data/projects/`
- Database persistent data: `/data/database/`
- Backups: `/data/backups/`
- Application uploads: `/data/uploads/`

These directories must be created only when their corresponding services are implemented.

## 10. Backup and Recovery

The platform must define:

- Database backup frequency.
- Backup retention policy.
- Configuration backup.
- Credential and secret recovery procedures.
- Restore testing.
- Recovery objectives.

The external SSD is primary application storage and must not be treated as the only backup destination.

An independent backup destination must be selected before production use.

## 11. Observability and Operations

The platform should provide:

- Application logs.
- MQTT broker logs.
- Database health monitoring.
- Container health checks.
- Device connectivity monitoring.
- Basic resource monitoring.
- Error and security event records.

Logs must avoid exposing passwords, private keys, access tokens, and other secrets.

## 12. Acceptance Criteria

Phase 1 will be considered ready for initial release when:

1. The platform can be deployed on the target ARM64 server.
2. Core services start and recover correctly.
3. Authorized users can authenticate.
4. Administrators can register and manage devices.
5. A registered device can authenticate with MQTT.
6. Telemetry can be received, validated, and stored.
7. Users can view device status and telemetry through the application.
8. Authorized users can submit device commands.
9. Unauthorized access is rejected.
10. Security-sensitive actions are auditable.
11. Database backup and restoration are tested.
12. Essential automated tests pass.
13. Deployment and operational procedures are documented.

Detailed measurable performance targets will be established before performance acceptance testing.

## 13. Assumptions and Constraints

- The initial deployment is a single self-hosted server.
- The server uses ARM64 architecture.
- Available RAM is limited.
- The external SSD is mounted at `/data`.
- GitHub is used for source control.
- MQTT and REST are the approved Phase 1 protocols.
- Modbus is planned for a future phase.
- High availability is not part of the initial deployment.
- The exact device count and telemetry rate are not yet finalized.

## 14. Open Decisions

The following items require confirmation before implementation:

1. Expected initial number of connected devices.
2. Expected telemetry frequency per device.
3. Target device types and manufacturers.
4. Frontend framework.
5. Backend programming language and framework.
6. User roles and permission matrix.
7. Device provisioning and credential issuance workflow.
8. MQTT topic naming convention.
9. Telemetry payload format and schema.
10. Data retention period.
11. Remote access and public domain requirements.
12. Backup destination and retention policy.
13. Performance and availability targets.

## 15. Related Documents

- `SYSTEM_ARCHITECTURE.md`
- `DEVELOPMENT_ROADMAP.md`
- `DATABASE_DESIGN.md` (planned)
- `API_SPECIFICATION.md` (planned)
- `UI_UX_GUIDELINES.md` (planned)
- `TESTING_STRATEGY.md` (planned)
- `CHANGELOG.md` (planned)

---

**End of Document**
