# Smart IoT Platform

## Technology Stack Decision Record

**Document Version:** 1.0
**Status:** Draft - Phase 1
**Last Updated:** 2026-11-02

---

## 1. Purpose

This document records the technology stack selected or proposed for Smart IoT Platform Phase 1.

It distinguishes approved decisions from proposals and unresolved implementation choices.

## 2. Project Constraints

- Self-hosted deployment.
- ARM64 server architecture.
- Approximately 4 GB of available RAM.
- Resource-efficient operation.
- Modular Monolith backend.
- Responsive Web / PWA user experience.
- Device Management and Monitoring are both product priorities.

## 3. Approved Technology Decisions

| Layer | Technology | Status |
|---|---|---|
| Frontend framework | React | Approved |
| Frontend language | TypeScript | Approved |
| Frontend build tool | Vite | Approved |
| CSS framework | Tailwind CSS | Approved |
| UI component system | shadcn/ui | Approved |
| Client application | Responsive Web / PWA | Approved |
| Backend architecture | Modular Monolith | Approved |
| Database | PostgreSQL | Approved |
| MQTT broker | Eclipse Mosquitto | Approved |
| Deployment | Docker Compose | Approved |
| Hosting | Self-hosted ARM64 | Approved |

## 4. Approved Backend Stack

| Component | Technology | Status |
|---|---|---|
| Programming language | Python | Approved |
| API framework | FastAPI | Approved |
| MQTT client library | gmqtt | Approved |
| Application API | REST over HTTPS | Architectural direction |

Python and FastAPI are approved because of their approachable development model and suitability for API and IoT integration work.

The backend implementation must remain a Modular Monolith.

The backend will use gmqtt with asynchronous I/O integrated with the FastAPI application lifecycle.

MQTT communication must be isolated behind an internal MQTT Adapter so that the client library can be replaced without changing business modules.

Before production use, validate automatic reconnection, QoS behavior, persistent sessions, message delivery, and ARM64 compatibility.

## 5. Proposed Frontend Supporting Tools

| Component | Proposed Technology | Status |
|---|---|---|
| Routing | React Router | Proposed |
| Global UI state | Zustand | Proposed |
| Charts | Recharts | Proposed |
| Icons | Lucide | Proposed |
| API communication | HTTPS REST API | Architectural direction |
| Real-time updates | WebSocket | Proposed |

Supporting libraries may be changed after implementation requirements and compatibility are reviewed.

## 6. Frontend Architecture

The frontend will be organized by product features.

Initial feature areas:

- Authentication
- Home Dashboard
- Device Management
- Room Management
- Device Control
- Scenes and Automation
- Monitoring and Telemetry History
- Notifications
- User and Platform Settings

The interface will support mobile, tablet, and desktop layouts.

The PWA will support installation where the browser and operating system permit it.

## 7. Backend Architecture

The backend will use a Modular Monolith with clear internal boundaries.

Initial module areas:

- Authentication and Authorization
- User Management
- Device Management
- Device Provisioning
- MQTT Integration
- Telemetry Ingestion
- Monitoring
- Automation
- Notifications
- Audit Logging

The backend will act as the trusted application boundary between frontend clients, MQTT infrastructure, and persistent storage.

Browsers will not connect directly to the MQTT broker in the initial architecture.

## 8. Infrastructure Components

| Component | Technology | Status |
|---|---|---|
| Container runtime | Docker | Pending installation |
| Service orchestration | Docker Compose | Approved |
| Relational database | PostgreSQL | Approved |
| MQTT broker | Eclipse Mosquitto | Approved |
| Reverse proxy | Not selected | Open |
| TLS certificate management | Not selected | Open |

All selected container images and dependencies must support ARM64.

Resource consumption must be evaluated before adding infrastructure components.

Redis will not be introduced unless a demonstrated requirement justifies its resource and operational cost.

## 9. Security Requirements

- Use HTTPS for application access.
- Use TLS for external MQTT connections where applicable.
- Enforce authentication and authorization on backend APIs.
- Apply MQTT topic-level access control.
- Keep database services off public interfaces.
- Store secrets outside source control.
- Record security-sensitive administrative actions.
- Apply least-privilege access principles.

## 10. Open Decisions

The following items require further evaluation:

1. Frontend routing and state management libraries.
2. Charting library.
3. Reverse proxy implementation.
4. Authentication and session strategy.
5. Authorization roles and permission matrix.
6. WebSocket event and reconnection strategy.
7. PWA offline behavior and caching policy.
8. Logging and monitoring implementation.
9. Production TLS certificate management.
10. Dependency versions and update policy.

## 11. Selection Principles

Technology selection must consider:

- ARM64 compatibility.
- Memory and CPU consumption.
- Security and maintenance.
- Learning and development complexity.
- Community and ecosystem maturity.
- Integration with the approved architecture.
- Long-term portability and extensibility.

## 12. Change Management

Changes to approved technologies must be documented with their rationale, impact, migration considerations, and approval status.

Proposed technologies must not be treated as approved implementation decisions.

---

**End of Document**
