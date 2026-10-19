# ServiceForce.ai - Security & Compliance Architecture

## 1. Server-Side Request Forgery (SSRF) Defense

When AI agents execute custom REST tools or dispatch outbound webhooks, ServiceForce.ai inspects both the destination URL and the resolved IP address before making network connections.

### Blocked Subnets
The following CIDRs and addresses are forbidden for outbound integration calls:
- `127.0.0.0/8` (Loopback / Localhost)
- `10.0.0.0/8` (Private RFC 1918)
- `172.16.0.0/12` (Private RFC 1918)
- `192.168.0.0/16` (Private RFC 1918)
- `169.254.0.0/16` (Link-Local & Cloud Metadata e.g. AWS `169.254.169.254`)
- `::1/128`, `fc00::/7`, `fe80::/10` (IPv6 Private & Link-Local)

Attempts to invoke internal endpoints return `HTTP 403 Forbidden` with an immutable audit log entry.

---

## 2. Multi-Tenant Isolation

- Every database query and service action is bound to the verified `organization_id` provided by the authenticated JWT session.
- RBAC roles (`Owner`, `Admin`, `Manager`, `Operator`) are evaluated on every protected route on the backend.
- Attempting to access resources across organization boundaries is rejected with `HTTP 403 Forbidden`.

---

## 3. Regulatory Compliance: TCPA, DNC & Calling Hours

Outbound campaigns must comply with commercial calling regulations:
1. **No Auto-Start:** Newly created outbound campaigns are placed in `Draft` state. They require explicit confirmation before dialing.
2. **Calling Windows:** Dialing is constrained to legal calling windows (default `09:00` to `20:00` local time).
3. **Do-Not-Call (DNC) Suppression:** Any caller who states an opt-out request is added to `suppression_entries`. The campaign scheduler automatically purges suppressed numbers from dialing queues.
4. **Lawful Call Recording:** Calls are only recorded when explicit caller notice or lawful consent is established.
