# Authentication and Session Design

Version: 1.0
Status: Approved
Phase: 1

## 1. Architecture Decision

The Smart IoT Platform Phase 1 authentication standard is:

- Argon2id for password hashing.
- Cryptographically secure opaque session tokens.
- SHA-256 hashes of session tokens stored in PostgreSQL.
- HttpOnly, Secure, and SameSite cookies for browser sessions.
- PostgreSQL as the central session store.
- Workspace-based Role-Based Access Control (RBAC).

Redis is not required for the initial implementation.

## 2. Password Security

- Passwords must never be stored in plaintext.
- Use Argon2id through a maintained password-hashing library.
- Use library-supported secure defaults and parameter configuration.
- Verify passwords using the password-hashing library.
- Never include passwords in logs, API responses, or audit records.

## 3. Session Token Design

- Generate opaque tokens using a cryptographically secure random generator.
- Tokens must contain sufficient entropy and must not encode user information.
- Store only a SHA-256 hash of each token in PostgreSQL.
- Never store or log the original session token.
- Associate each session with a user and relevant lifecycle timestamps.
- Support expiration, rotation, and revocation.

## 4. Browser Cookie Policy

Session cookies must use:

- HttpOnly
- Secure in production
- SameSite=Lax by default
- A restricted cookie path
- An explicit expiration policy

Cookie settings must be configurable for development and production environments.

## 5. CSRF Protection

- Protect state-changing requests authenticated by cookies against CSRF.
- Use a CSRF token mechanism.
- Validate request origin where appropriate.
- Do not treat SameSite cookies as the only CSRF protection.

## 6. Session Lifecycle

The implementation must support:

- Session creation after successful authentication.
- Session validation on protected requests.
- Session expiration.
- Session revocation during logout.
- Session rotation after authentication or other security-sensitive events.
- Revocation of sessions when account security requires it.

Idle and absolute session lifetimes will be configurable and finalized before production deployment.

## 7. Authorization

- Use workspace-based RBAC.
- Initial workspace roles are owner, admin, and member.
- Verify workspace membership and permissions on protected operations.
- Never rely on frontend authorization as the security boundary.
- Deny access by default when authorization cannot be established.

## 8. Database

The authentication implementation will introduce a dedicated session model.

The session model should include:

- UUID primary key.
- User foreign key.
- Unique session token hash.
- Created timestamp.
- Last activity timestamp.
- Expiration timestamp.
- Optional revocation timestamp.

Database migrations must be version-controlled.

No migration may be applied to the production database without explicit approval.

## 9. Audit and Logging

Record security-relevant events, including:

- Successful authentication.
- Failed authentication.
- Logout.
- Session revocation.
- Privileged account operations.

Never log passwords, raw session tokens, or other authentication secrets.

## 10. Implementation Boundaries

- Authentication business logic belongs in the users module.
- Shared security utilities belong in the core layer.
- Database access belongs in repositories.
- API handlers must remain thin.
- Tests must cover password verification, session lifecycle, CSRF protection, and authorization.
- PostgreSQL integration tests must be distinguished from unit and mock-based tests.

## 11. Deferred Decisions

The following details must be finalized during implementation:

- Exact Argon2id parameters.
- Session idle and absolute expiration durations.
- CSRF token transport and validation details.
- Login rate-limiting policy.
- Account recovery and email verification workflows.
