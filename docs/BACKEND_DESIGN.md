# Backend Design

**Project:** Smart IoT Platform  
**Version:** 1.0  
**Status:** Draft  
**Last Updated:** 2026-11-03

---

## 1. Purpose

This document defines the backend application design for the Smart IoT Platform.

The backend follows a Modular Monolith architecture. Modules remain logically independent while running as one deployable application in Phase 1.

## 2. Approved Technology Foundation

| Component | Technology |
|---|---|
| Programming language | Python |
| API framework | FastAPI |
| MQTT client library | gmqtt |
| Database | PostgreSQL |
| MQTT broker | Eclipse Mosquitto |
| Deployment | Docker Compose |
| Hosting | Self-hosted ARM64 |

## 3. Architectural Principles

- Clear separation of business modules and infrastructure.
- Explicit interfaces between modules.
- MQTT communication isolated behind an internal adapter.
- Asynchronous I/O for network-bound operations.
- Centralized configuration and logging.
- Secrets must not be stored in source control.
- Avoid unnecessary infrastructure and dependencies.


## 4. Application Structure

The backend is organized into the following layers:

### 4.1 Core

Responsible for application-wide capabilities:

- Configuration management.
- Logging setup.
- Shared security utilities.
- Common exceptions.

Core must not contain business-specific logic.

### 4.2 API

Responsible for HTTP API composition:

- Main API router.
- API dependencies.
- Request and response handling.
- API versioning.

API routes delegate business operations to module services.

### 4.3 Business Modules

| Module | Responsibility |
|---|---|
| Devices | Device registration, identity, metadata, and lifecycle |
| Telemetry | Sensor data validation, processing, and persistence |
| Monitoring | Device status and monitoring queries |
| Users | User accounts and identity-related operations |
| Automation | Future scenes, rules, and automation capabilities |

Automation is reserved in the initial structure. Full implementation is outside the initial backend foundation scope.

Modules must expose well-defined service interfaces and avoid directly accessing another module's internal implementation.

### 4.4 MQTT Integration

Responsible for communication with Eclipse Mosquitto through gmqtt.

- `adapter.py`: Internal MQTT interface.
- `client.py`: gmqtt connection and lifecycle.
- `handlers.py`: Incoming message dispatch.
- `topics.py`: MQTT topic definitions and utilities.

Business modules must not import or depend directly on gmqtt.

### 4.5 Infrastructure

Responsible for technical integrations:

- PostgreSQL connection management.
- Database session lifecycle.
- Shared infrastructure services.
- Messaging infrastructure abstractions where required.

Infrastructure must not own business rules.

## 5. Application Lifecycle

FastAPI application lifecycle management coordinates shared resources.

### Startup

1. Load and validate application configuration.
2. Initialize logging.
3. Initialize database connectivity.
4. Initialize the MQTT adapter.
5. Establish MQTT connection when enabled and configured.
6. Register message handlers.
7. Mark the application ready after required dependencies are available.

### Shutdown

1. Stop accepting new application work.
2. Stop or drain relevant background operations.
3. Disconnect MQTT cleanly.
4. Close database resources.
5. Release application resources.

The implementation must use FastAPI application lifespan management.

Startup and shutdown operations must handle partial initialization failures safely.

## 6. Database Architecture

PostgreSQL is the approved primary relational database.

Database access should follow this general flow:

API Router
    |
    v
Module Service
    |
    v
Repository Interface
    |
    v
Database Infrastructure
    |
    v
PostgreSQL

Responsibilities:

- Services implement business operations.
- Repositories encapsulate data access.
- Database infrastructure manages connections and sessions.
- Database schema changes must be version-controlled through migrations.
- Database services must not be exposed directly to public interfaces.

ORM selection, migration tooling, connection pool settings, and detailed schema design remain open decisions.

## 7. MQTT Message Architecture

Eclipse Mosquitto is the MQTT broker, and gmqtt is the approved Python client library.

The internal MQTT Adapter isolates broker communication from business modules.

### Message Flow

1. A device publishes telemetry or status messages to an authorized MQTT topic.
2. Mosquitto receives the message and applies broker-level access controls.
3. The MQTT client receives the message through the adapter.
4. The message handler validates and normalizes the payload.
5. The appropriate business module processes the message.
6. The module persists relevant data through the database repository.

### Design Requirements

- Define and version-control MQTT topic conventions.
- Define payload schemas and schema versions.
- Validate message structure and data types before processing.
- Handle duplicate and out-of-order messages safely where applicable.
- Avoid blocking the asynchronous event loop during message processing.
- Keep broker credentials and device credentials outside source control.
- Apply topic-level authorization for device identities.

## 8. API Design

FastAPI provides the HTTP/REST application API.

### API Principles

- Use versioned API routes, beginning with `/api/v1`.
- Use resource-oriented endpoint naming.
- Use consistent request and response schemas.
- Validate all incoming request data.
- Return consistent error response structures.
- Document endpoints using OpenAPI.
- Apply authentication and authorization to protected endpoints.

### API Responsibilities

- API routers handle HTTP concerns and request validation.
- Module services execute business operations.
- Response schemas define the public API contract.
- API handlers must not contain complex business logic.

The detailed endpoint catalog and authentication mechanism remain open design decisions.

## 9. Configuration and Secrets

Application configuration must be separated from source code.

### Configuration Requirements

- Use environment-based configuration for deployment-specific values.
- Validate required configuration during application startup.
- Provide safe defaults only for non-sensitive settings.
- Keep development, testing, and production configurations separate.

### Secrets Management

- Never commit passwords, tokens, private keys, or broker credentials to Git.
- Store secrets outside the repository with restrictive file permissions.
- Do not expose secrets in API responses or application logs.
- Rotate credentials when compromise is suspected or access changes.
- Use separate credentials for devices and backend services.

The final secrets storage mechanism and configuration file format remain open decisions.

## 10. Security Design

Security must be applied across the API, MQTT integration, database, and deployment layers.

### Application Security

- Enforce authentication for protected API operations.
- Enforce role-based authorization for user operations.
- Validate and sanitize untrusted input.
- Apply least-privilege access to application components.

### Communication Security

- Use HTTPS for external API communication.
- Use TLS for MQTT connections where supported by the deployment.
- Do not expose PostgreSQL directly to public networks.

### IoT Security

- Assign a distinct identity and credentials to each device.
- Restrict device access through MQTT topic-level authorization.
- Support credential revocation when a device is decommissioned or compromised.

### Operational Security

- Record security-relevant events in audit logs.
- Restrict access to configuration files and secrets.
- Apply security updates through a controlled maintenance process.

## 11. Error Handling and Logging

The backend must provide consistent error handling and structured logging.

### Error Handling

- Use consistent application-level error categories.
- Convert internal exceptions into safe API error responses.
- Do not expose stack traces or sensitive internal details to API clients.
- Handle database and MQTT connection failures gracefully.
- Apply bounded retry strategies where retries are appropriate.
- Avoid retrying non-idempotent operations without safeguards.

### Logging

- Use structured logs suitable for centralized collection.
- Include timestamps, severity, and relevant request or correlation identifiers.
- Record application startup, shutdown, and dependency connection events.
- Exclude passwords, tokens, private keys, and sensitive payload data.
- Keep security audit events distinguishable from general application logs.

The logging library, log retention period, and monitoring solution remain open decisions.

## 12. Testing Strategy

Testing must cover business logic, API behavior, database interactions, and MQTT integration.

### Test Categories

- Unit tests: verify individual functions and business rules.
- API tests: verify routes, request validation, responses, and authorization.
- Database tests: verify repository behavior and data integrity.
- MQTT integration tests: verify connection, message handling, and delivery behavior.
- End-to-end tests: verify critical workflows across system components.

### Quality Requirements

- Tests must be repeatable and isolated from production data.
- External dependencies should be replaceable with test doubles where appropriate.
- Critical business logic must have automated test coverage.
- Test failures must be resolved before changes are accepted.
- Never run destructive tests against production services or data.

## 13. Performance and Resource Constraints

The backend must operate efficiently within the available self-hosted server resources.

### Resource Requirements

- Maintain ARM64 compatibility across runtime dependencies and deployment images.
- Keep memory and CPU consumption low.
- Avoid unnecessary background workers and infrastructure services.
- Do not introduce Redis unless a demonstrated requirement justifies it.
- Use bounded connection pools and controlled concurrency.

### Performance Requirements

- Keep API operations responsive under expected workloads.
- Process MQTT messages asynchronously where appropriate.
- Prevent slow database operations from blocking unrelated requests.
- Apply pagination to potentially large API result sets.
- Define telemetry retention and archival policies before production-scale ingestion.

Performance targets and expected device/message volumes must be established before capacity planning.

## 14. Implementation Scope

### Phase 1 Foundation

- Establish the FastAPI application and modular project structure.
- Implement application configuration and lifecycle management.
- Establish PostgreSQL connectivity and migration foundations.
- Implement the internal MQTT Adapter using gmqtt.
- Establish API versioning and common error handling.
- Implement initial device management capabilities.
- Implement initial telemetry ingestion and storage.
- Provide monitoring data APIs for the frontend.
- Establish authentication and role-based authorization.
- Add automated tests for critical backend components.

### Deferred Scope

- Modbus TCP and Modbus RTU integration are planned for Phase 2.
- High availability and multi-node deployment are outside the initial deployment scope.
- Additional infrastructure services require explicit justification.

Implementation details must follow approved architecture and technology decisions.

## 15. Open Decisions

The following decisions must be finalized before or during implementation:

1. ORM and database migration tooling.
2. Database schema and telemetry data model.
3. MQTT topic naming and payload schemas.
4. MQTT QoS, session, and reconnection policies.
5. Device provisioning and credential lifecycle.
6. User authentication and authorization strategy.
7. WebSocket or other real-time frontend update mechanism.
8. Telemetry retention and archival policy.
9. Logging, monitoring, and alerting solution.
10. Reverse proxy and TLS certificate management.
11. Backup destination independent of the primary SSD.
12. Expected device count and message frequency.
13. PWA offline behavior and notification strategy.

These decisions must be documented before the related production features are finalized.

## 16. Document Status

This document defines the initial backend architecture and implementation guidelines for Smart IoT Platform.

It serves as the technical reference for backend development.

Any significant architectural changes must be reviewed and reflected in this document.

Implementation must not introduce unapproved technologies or infrastructure dependencies.

Status: Draft — pending final technical review.
