# Smart IoT Platform

## Development Roadmap

**Document Version:** 1.0  
**Status:** Draft - Phase 1 Baseline  
**Last Updated:** 2026-11-02  
**Project:** Smart IoT Platform  
**Deployment Model:** Self-hosted  
**Architecture:** Modular Monolith  
**Target Platform:** ARM64

---

## 1. Purpose

This document defines the planned development phases, milestones, dependencies, and acceptance criteria for the Smart IoT Platform.

The roadmap provides an implementation sequence while allowing technical details to evolve through documented decisions.

No delivery dates or performance targets are assumed until they are explicitly agreed upon.

## 2. Development Strategy

Development will follow these principles:

- Deliver a usable foundation before adding advanced capabilities.
- Prioritize both Device Management and Monitoring in Phase 1.
- Keep the initial backend as a Modular Monolith.
- Use MQTT as the primary IoT messaging protocol.
- Use REST APIs for application integration.
- Keep protocol-specific implementation behind adapter interfaces.
- Prefer resource-efficient components suitable for the available ARM64 server.
- Validate security, backup, and recovery before production use.
- Avoid premature microservices and infrastructure complexity.

## 3. Phase Overview

| Phase | Name | Main Outcome |
|---|---|---|
| 0 | Foundation | Approved baseline, repository, and development environment |
| 1 | MVP | Device Management and Monitoring platform |
| 2 | Protocol Expansion | Modbus TCP/RTU integration |
| 3 | Advanced Capabilities | Analytics, automation, notifications, OTA, and scaling evaluation |

Phase completion requires the relevant acceptance criteria to be reviewed and approved.

---

## 4. Phase 0 - Foundation

### 4.1 Objectives

Establish the project baseline, architecture, repository structure, and deployment preparation.

### 4.2 Work Items

**Documentation**
- Complete Project Requirements Specification.
- Complete System Architecture Document.
- Complete Development Roadmap.
- Identify unresolved architecture and product decisions.

**Repository**
- Establish the Git repository on the server.
- Define a consistent directory structure.
- Establish documentation and change-management conventions.
- Define the branching and review workflow.

**Infrastructure Discovery**
- Confirm ARM64 compatibility requirements.
- Confirm persistent storage at `/data`.
- Review available CPU, RAM, and disk resources.
- Define container deployment requirements.
- Identify a separate backup destination.

**Technical Decisions**
- Select backend language and framework.
- Select frontend framework.
- Select HTTPS reverse proxy.
- Define development and deployment configuration strategy.
- Define initial MQTT topic and payload conventions.
- Define authentication and device provisioning approaches.

### 4.3 Milestones

| ID | Milestone | Expected Result |
|---|---|---|
| F0-1 | Requirements Baseline | Requirements reviewed and approved |
| F0-2 | Architecture Baseline | Architecture and major components documented |
| F0-3 | Repository Baseline | Project repository and documentation organized |
| F0-4 | Technology Selection | Required implementation technologies decided |
| F0-5 | Deployment Readiness | Storage, security, and deployment approach reviewed |

### 4.4 Acceptance Criteria

- Requirements and architecture documents are available in the repository.
- The roadmap is reviewed and approved.
- Major open decisions have owners or an agreed decision process.
- The repository structure is suitable for application development.
- Persistent storage is available and its mount configuration is documented.
- ARM64 compatibility is considered for all selected components.
- Backup destination and recovery expectations are identified before production deployment.

### 4.5 Exit Gate

Phase 1 implementation may begin when the architecture baseline is accepted and the technology choices required for the first implementation milestone are decided.

---

## 5. Phase 1 - Minimum Viable Product (MVP)

### 5.1 Objectives

Deliver a self-hosted platform that supports both device administration and basic monitoring.

The initial deployment uses a Modular Monolith, PostgreSQL, Eclipse Mosquitto, and Docker Compose.

### 5.2 Core Capabilities

#### A. Platform Foundation

- Establish the application project structure.
- Implement configuration management.
- Establish database connectivity and migrations.
- Deploy the application using Docker Compose.
- Configure persistent data volumes.
- Establish application and dependency health checks.

#### B. Identity and Access Management

- Implement user authentication.
- Implement role-based authorization.
- Protect administrative and device-management operations.
- Record security-sensitive administrative events.
- Keep secrets outside the Git repository.

The exact authentication mechanism and role definitions remain subject to approval.

#### C. Device Management

- Register devices.
- Store device identity and metadata.
- View device details.
- Update permitted device configuration.
- Track device lifecycle and communication status.
- Associate devices with authorized communication identities.
- Support device enablement and disablement.

Device provisioning and credential rotation workflows must be defined before production use.

#### D. MQTT Communication

- Deploy Eclipse Mosquitto.
- Configure MQTT authentication.
- Configure topic-level authorization.
- Establish MQTT over TLS for production communication.
- Implement the MQTT adapter.
- Validate incoming messages.
- Publish authorized device commands.
- Record communication and command status.

Topic conventions, payload schemas, QoS, and session policies must be documented before integration is considered complete.

#### E. Monitoring and Telemetry

- Receive device telemetry.
- Validate telemetry data.
- Associate messages with registered devices.
- Persist telemetry in PostgreSQL.
- Retrieve telemetry through application APIs.
- Display device status and telemetry in the frontend.
- Handle invalid or unsupported messages safely.

Telemetry retention and expected data volume remain open decisions.

#### F. REST API

- Establish versioned API conventions.
- Implement authentication and authorization.
- Provide device-management endpoints.
- Provide telemetry and device-status endpoints.
- Provide command-management endpoints.
- Return consistent error responses.
- Document API contracts.

#### G. Frontend

- Provide a login interface.
- Provide a device list and device details.
- Provide device registration and management interfaces.
- Provide monitoring dashboards.
- Display device communication status.
- Display telemetry history.
- Provide authorized command-management interfaces.

#### H. Operations and Security

- Configure HTTPS.
- Restrict database access to internal services.
- Configure service health checks.
- Collect useful application and infrastructure logs.
- Monitor disk, CPU, and memory usage.
- Establish PostgreSQL backup and restore procedures.
- Test recovery using a separate backup destination.

### 5.3 Milestones

| ID | Milestone | Expected Result |
|---|---|---|
| M1-1 | Platform Skeleton | Application and deployment structure operational |
| M1-2 | Database Foundation | PostgreSQL schema and migrations operational |
| M1-3 | Identity Foundation | Authentication and authorization operational |
| M1-4 | Device Registry | Device registration and management operational |
| M1-5 | MQTT Integration | Authenticated device messaging operational |
| M1-6 | Telemetry Pipeline | Valid telemetry persisted and retrievable |
| M1-7 | REST API | Core application APIs operational |
| M1-8 | Frontend MVP | Device management and monitoring interfaces usable |
| M1-9 | Operational Readiness | Security, health checks, backup, and recovery reviewed |

The milestone order may be adjusted to account for technical dependencies.

### 5.4 Acceptance Criteria

**Device Management**
- Authorized users can register and view devices.
- Device metadata is stored persistently.
- Unauthorized users cannot perform protected device operations.

**Communication**
- Registered devices can communicate through authenticated MQTT connections.
- Topic permissions prevent unauthorized device access.
- Invalid messages are rejected or handled according to documented rules.
- Command publication and device execution status are represented separately.

**Monitoring**
- Valid telemetry is associated with the correct device.
- Telemetry is persisted and can be retrieved.
- Device status and telemetry are visible through the frontend.
- Invalid telemetry does not silently corrupt stored data.

**Application**
- Core REST APIs enforce authentication and authorization.
- Frontend workflows support the agreed MVP use cases.
- Application errors are logged without exposing secrets.

**Operations**
- Services can be deployed and restarted using the documented procedure.
- Persistent data survives service restarts.
- Health checks identify critical dependency failures.
- Backup and restore procedures have been tested.
- Production-facing services use the approved secure communication configuration.

### 5.5 Exit Gate

Phase 1 is complete when the agreed MVP workflows pass their acceptance tests and the deployment, security, backup, and recovery procedures are reviewed.

---

## 6. Phase 2 - Protocol Expansion

### 6.1 Objectives

Extend device connectivity through Modbus TCP/RTU while preserving the protocol adapter architecture.

### 6.2 Work Items

- Define Modbus TCP and RTU integration requirements.
- Define gateway and connection management.
- Define register mapping and data types.
- Define polling and timeout behavior.
- Implement the Modbus adapter.
- Translate Modbus data into application-level telemetry.
- Map protocol errors to common application error models.
- Add integration and regression tests.
- Document device-specific configuration.

### 6.3 Milestones

| ID | Milestone | Expected Result |
|---|---|---|
| M2-1 | Modbus Specification | Connection and register-mapping requirements approved |
| M2-2 | Adapter Design | Modbus adapter interfaces documented |
| M2-3 | Modbus TCP | TCP integration validated |
| M2-4 | Modbus RTU | RTU integration validated where required |
| M2-5 | Unified Monitoring | Modbus telemetry available through common platform interfaces |

### 6.4 Acceptance Criteria

- Modbus devices can be configured using documented mappings.
- Valid readings are translated into the common telemetry model.
- Communication failures and timeouts are observable.
- Modbus integration does not require changes to unrelated core business logic.
- Existing MQTT functionality continues to pass regression tests.

### 6.5 Exit Gate

Modbus integration is accepted when the agreed device and gateway scenarios pass integration tests and the operational configuration is documented.

---

## 7. Phase 3 - Advanced Capabilities

### 7.1 Objectives

Evaluate and implement advanced capabilities based on validated product needs and operational evidence.

### 7.2 Candidate Capabilities

**Analytics**
- Historical trend analysis.
- Aggregated telemetry.
- Device and site-level reporting.
- Data export.

**Automation**
- Rule-based automation.
- Threshold evaluation.
- Event-driven workflows.
- Automation execution history.

**Notifications**
- Configurable alert rules.
- Device communication alerts.
- Operational notifications.
- Notification delivery history.

**Over-the-Air Updates**
- Firmware and update package management.
- Device compatibility checks.
- Update authorization.
- Update status tracking.
- Failure handling and recovery planning.

**Multi-Site Support**
- Site and location organization.
- Site-level device grouping.
- Scoped access control.
- Site-level monitoring.

**Scaling Improvements**
- Database and query optimization.
- Telemetry retention improvements.
- MQTT capacity evaluation.
- Background processing where justified.
- Resource and performance monitoring.

### 7.3 Milestones

| ID | Milestone | Expected Result |
|---|---|---|
| M3-1 | Capability Prioritization | Candidate features ranked by validated needs |
| M3-2 | Analytics | Approved reporting and analytics capabilities |
| M3-3 | Automation | Approved automation workflows |
| M3-4 | Notifications | Approved alert and notification workflows |
| M3-5 | OTA Evaluation | Secure update design and validated implementation if approved |
| M3-6 | Scaling Review | Evidence-based scaling recommendations |

### 7.4 Acceptance Criteria

Each capability must have its own requirements, security review, tests, and acceptance criteria before release.

Advanced features must not compromise device isolation, data integrity, or platform security.

### 7.5 Exit Gate

Phase 3 milestones are accepted individually according to their approved scope. Completion of one capability does not imply that every candidate capability must be implemented.

---

## 8. Cross-Phase Quality Requirements

The following concerns apply throughout development:

### 8.1 Security

- Authentication and authorization.
- Per-device identity and credentials.
- MQTT topic-level access control.
- TLS for production communication.
- Secrets excluded from source control.
- Least-privilege service permissions.
- Security-sensitive audit logging.

### 8.2 Testing

- Unit tests for business logic.
- Integration tests for database and MQTT interactions.
- API tests for application contracts.
- Frontend workflow tests.
- Protocol adapter tests.
- Regression tests for existing functionality.
- Backup and restore validation.

### 8.3 Documentation

- Keep architecture and requirements aligned with implementation.
- Document configuration and deployment procedures.
- Document API and MQTT contracts.
- Record significant technical decisions.
- Maintain release notes and known limitations.

### 8.4 Resource Efficiency

- Validate ARM64 compatibility.
- Monitor CPU, memory, and disk consumption.
- Avoid unnecessary infrastructure components.
- Introduce additional services only when justified by measured requirements.

---

## 9. Dependencies and Risks

| Dependency or Risk | Potential Impact | Planned Response |
|---|---|---|
| Backend and frontend technology not selected | Implementation cannot be standardized | Decide during Phase 0 |
| MQTT topic and payload schema undefined | Device integration may be inconsistent | Define and version the contract before integration |
| Device provisioning not defined | Device identity and access risks | Approve provisioning and credential lifecycle |
| Telemetry volume unknown | Database growth and resource pressure | Establish expected workload and retention policy |
| Backup destination not selected | Inadequate disaster recovery | Select independent backup storage before production |
| ARM64 compatibility limitations | Deployment incompatibility | Validate images and dependencies before adoption |
| Single-node deployment | Server failure causes service interruption | Document recovery procedures; evaluate HA only when justified |
| Modbus device variations | Integration complexity | Define register maps and test representative devices |

---

## 10. Open Decisions

The following decisions remain open and must be resolved at the appropriate phase:

- Backend programming language and framework.
- Frontend framework.
- HTTPS reverse proxy.
- User authentication and session strategy.
- Role and permission model.
- MQTT topic naming and payload schema.
- MQTT QoS and session policy.
- Device provisioning and credential rotation.
- Telemetry retention and expected volume.
- Backup destination and recovery objectives.
- Expected device count and telemetry frequency.
- Modbus gateway and register-mapping strategy.
- OTA security and device compatibility requirements.
- Multi-site access and tenancy requirements.

No open decision should be treated as an approved implementation choice.

---

## 11. Change Management

Changes to scope, architecture, or acceptance criteria should be documented and reviewed.

Significant changes should include:
- Reason for the change.
- Affected requirements and components.
- Security and operational impact.
- Migration or compatibility considerations.
- Updated acceptance criteria.

The roadmap should be revised when approved project decisions materially change the implementation sequence.

## 12. Related Documents

- `PROJECT_REQUIREMENTS.md`
- `SYSTEM_ARCHITECTURE.md`
- `DATABASE_DESIGN.md` (planned)
- `API_SPECIFICATION.md` (planned)
- `UI_UX_GUIDELINES.md` (planned)
- `TESTING_STRATEGY.md` (planned)
- `CHANGELOG.md` (planned)

---

**End of Document**
