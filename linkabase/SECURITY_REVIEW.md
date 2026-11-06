# Focused pre-deployment security review

Reviewed November 6, 2026. This is a source review with targeted regression checks, not a penetration test, dependency vulnerability audit, or assessment of a live Linode host. No production server was accessed. It does not certify the absence of vulnerabilities.

## Findings that affect deployment

### High: Streamlit media/download links bypass Linkabase account checks

The installed Streamlit media handler resolves `/media/{file_id}` directly from its in-memory media store, without calling Linkabase authentication. Downloads and some previews use this mechanism. An isolated check reproduced a 200 response for a known download URL with no application session. Possession of a working media URL can therefore grant access without signing into Linkabase, while that object remains available. This is not directory listing or arbitrary file access, but those URLs must be treated as bearer links.

**Status: remaining architectural limitation.** Protect the entire Streamlit service with a VPN/private network, or an authenticated reverse proxy that also covers `/media/*`. The example in `deploy/Caddyfile.example` supplies an outer access gate. Everyone who can pass that outer gate must be trusted with media links: it does not impose Linkabase project-level authorization on those links. For mutually untrusted project members, implement session-authorized downloads/previews before relying on strict project isolation.

### High: an uninitialized public instance can be claimed by its first visitor

Creating the first account intentionally creates the super-admin. The database transaction prevents two owners being created concurrently, but does not identify which visitor is the intended operator.

**Status: deployment requirement.** Create your owner account through an SSH tunnel or private network before exposing the site. Alternatively, configure and verify the outer access gate before first startup. An existing workspace does not re-open setup.

### High if misconfigured: HTTP or exposed backend ports can expose credentials/data

Login credentials, drawing content, and drawing bearer tokens require HTTPS outside localhost. The drawing launch URL contains a session token in its fragment, and the editor stores it in sessionStorage. Treat launch links and browser storage as sensitive; do not share or log launch links. A database change is not needed for this deployment.

**Status: configuration requirement.** Keep Compose's default `BIND_ADDRESS=127.0.0.1`; expose only the HTTPS reverse proxy, not ports 8501 or 8090. Set `EDITOR_PUBLIC_URL=https://your-domain` with the single-domain example. Do not disable CORS/XSRF protection to troubleshoot a proxy.

## Issues fixed during this review

- **Drawing request memory exhaustion:** the API previously read the whole request before checking 25 MB. It now rejects an oversized Content-Length and stops reading chunked bodies at the limit.
- **Malformed drawing payloads:** invalid scene types and out-of-range versions could raise server errors. These now return 400 before writing anything; stale valid saves still return 409.
- **Drawing ID disclosure:** unauthenticated API requests now authenticate before object lookup, unrelated users receive 404, and the public editor shell no longer queries drawing existence. The shell itself contains no drawing data.
- **Sensitive response caching:** drawing API/editor responses now send `Cache-Control: no-store` and a no-referrer policy. MIME sniffing is disabled for the drawing service. Unneeded API documentation endpoints are disabled.
- **Deployment defaults:** CORS/XSRF protections and disabled app static serving are explicit. Browser-facing Python error details are disabled. Environment variants, private key files, and SQLite snapshots are excluded from source/build contexts.

## Controls inspected

- SQL values use parameter binding in the reviewed paths; dynamic table names come from application-defined lists.
- Passwords are salted PBKDF2-HMAC-SHA256 hashes with 600,000 iterations. Session tokens are random, hashed in SQLite, expire after 12 hours, and are invalidated by logout/password reset.
- Project access is rechecked by the drawing API, including reader write restrictions, revoked sessions, and expired sessions.
- File path helpers reject traversal and escaping symlinks.
- New HTML component templates escape user-provided names/IDs. The wiki editor sanitizes rendered Markdown and disables raw HTML parsing.
- Login throttling is per email, not a comprehensive global/IP denial-of-service defense. Keep the access gate/private network and appropriate server resource limits.

## Suggested personal Linode deployment

1. Keep a backup of the complete workspace. Restrict the data directory and backups to the service account; never serve that directory with a web server. The current Docker image runs as root; container user/volume ownership hardening remains additional deployment work.
2. Keep the existing localhost-only application port mappings. Use the Linode/host firewall so 8501 and 8090 are not reachable externally. Restrict SSH access appropriately.
3. Create the first owner privately. Install an HTTPS reverse proxy and configure a trusted-access gate before public exposure, or use a VPN instead.
4. Adapt `deploy/Caddyfile.example`: replace its domain and generate a password hash with `caddy hash-password`. Use a separate strong outer-gate password. Validate with `caddy validate --config /path/to/Caddyfile --adapter caddyfile` before loading it. This example was reviewed but not executed here.
5. Set `EDITOR_PUBLIC_URL=https://your-domain` and `STREAMLIT_BROWSER_SERVER_ADDRESS=your-domain` in the deployment environment. The app and drawing service use one domain in this example. API requests are deliberately exempt from Basic Auth because they use the same Authorization header for their application Bearer token; those routes enforce their own authentication.
6. From outside the server, verify that the site and a known media link require the outer gate, backend ports are unreachable, and a drawing API request without a token returns 401. Confirm a reader cannot save a drawing.
7. Apply OS/container updates and run Python/JavaScript dependency advisory scans before release. Dependency advisories and the live host/firewall/TLS setup were not audited in this review.

A personal instance restricted to you is a much narrower exposure than a public multi-tenant service. Do not treat this review as approval to publish without the deployment controls above.

References: [Streamlit configuration](https://docs.streamlit.io/develop/api-reference/configuration/config.toml), [FastAPI HTTPS](https://fastapi.tiangolo.com/deployment/https/), [Caddy authentication](https://caddyserver.com/docs/caddyfile/directives/basic_auth), [Caddy reverse proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy).
