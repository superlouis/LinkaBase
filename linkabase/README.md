# Linkabase

A self-hosted workspace for tasks, connected knowledge, and diagrams. The application version comes from `[project].version` in `pyproject.toml`.

## Run locally

From this directory:

```bash
uv sync
uv run python main.py start
```

Open http://localhost:8501. New workspaces start empty. Create the first super-admin account, then a project and its topics. The drawing studio runs at http://localhost:8090. Its compiled assets are bundled; npm is only needed when changing the drawing frontend.

```bash
uv run python main.py status
uv run python main.py logs
uv run python main.py restart
uv run python main.py stop
# Keep both services in the foreground until Ctrl+C:
uv run python main.py run
```

Copy `.env.example` to `.env` to configure the listen address, ports, or workspace location. Do not run another instance on the same ports. The lifecycle manager tracks processes and logs in `.runtime/`.

## Workspace

- **Overview:** assigned tasks ordered by due date and priority, project progress, topics, and content shortcuts.
- **Tasks:** drag-and-drop board and keyboard-friendly list, with priorities, project-scoped assignees, optional due dates, and an optional linked topic. Tasks cannot link to individual content items.
- **Topics:** collections of wiki pages and diagrams, with a tab for their linked tasks.
- **Wiki:** Markdown reading, visual/source editing, preview, conflict checks, and revision history.
- **Diagrams:** local Excalidraw editing, scene downloads, and saved PNG previews.
- **Settings:** profile, theme selection, passwords, project membership, and administration according to your role.

The overview, topic gallery, and library listings use custom HTML components within Streamlit. Click events are validated in Python and open the existing dialogs/readers. Shared component assets live in `src/components/`; the standalone HTML concepts in `../attempt/` are not runtime dependencies.

New accounts use **Paper**, the light theme. Existing accounts retain their preference. Select **My preferences → Theme → Paper → Apply theme** to use the light design. All eight themes remain available.

Sign-in and first-time setup use the linked-node mark and a local SVG/CSS animation, with reduced-motion support and a compact mobile layout.

## Permissions

| Role | Read | Create/edit/delete | Manage membership |
|---|---|---|---|
| Reader | Yes | No | No |
| Writer | Yes | Yes | No |
| Project admin | Yes | Yes | Yes, for that project |

Super-admins can create projects, manage workspace accounts, and access all projects. The last active super-admin cannot be demoted. Users must be active and have access to a project to be assigned its tasks. Legacy typed assignees remain until replaced.

Passwords require at least 12 characters. Local sessions expire after 12 hours and may require a fresh sign-in after a browser reload. There is no email invitation or password-recovery service.

## Documents and drawings

Markdown lives under `workspace/docs/<project>/`. You can open `workspace/docs` as an Obsidian vault. Wiki readers refresh from disk every three seconds; newly discovered pages appear on a full refresh. Obsidian-specific plugins, wikilinks, and simultaneous collaborative editing are not supported.

Wiki edits are saved explicitly. Visual editing normalizes Markdown; use source mode for specialized syntax. Conflict checks prevent overwriting a changed document. Revision history appears after the first save.

The drawing studio can open in a new tab or within the app. Save to persist the editable scene and its preview. Drawings use native `.excalidraw` JSON. Embedded images inside a drawing remain supported by Excalidraw.

Moving content between topics does not change task-to-topic links. Deleting a topic clears its task links while retaining tasks. Deleting an individual page/drawing leaves task-to-topic links intact.

## Storage feature removed

The upload/external-link library, file previews, PDF-preview dependency, capacity panel, and `main.py storage` command have been removed. Topics now accept only wiki pages and diagrams.

On upgrade, old upload/link metadata is archived transactionally in SQLite's `trash_entries` table with `kind='retired_storage'`. The old `assets` table and active file-content entries are then removed. Existing uploaded files under `workspace/attachments/` are left untouched for manual recovery; the application no longer reads, serves, or manages them. Back up the complete workspace before upgrading. Fresh workspaces do not create that directory or table.

## Data, deletion, and backups

SQLite lives at `workspace/work.sqlite`. Markdown, drawing exports, revision history, and trash live beside it. Back up the complete workspace with both services stopped, including any legacy uploads retained after upgrade. Keep SQLite on local/block disk rather than NFS or an object-store mount.

Topic/content/project deletion requires confirmation and archives relevant local documents, drawings, and records under `workspace/trash/<archive-id>/`, with a JSON manifest and database entry. Recovery is manual. Deleting a project retains other projects and user accounts.

Set `WORKSPACE_DIR` to an existing absolute data directory for local installations. Docker uses `LINKABASE_DATA_DIR` for its host mount. Pointing at an empty directory creates a new workspace; it does not migrate existing data. Stop services and copy the complete workspace before changing its location.

## Docker

```bash
docker compose up -d --build
docker compose logs --tail 50
docker compose down
```

Compose binds application ports to localhost by default and mounts `./workspace:/data`. Both services must use the same data mount. Preserve `.env` and that mount during upgrades.

Before exposing a server, read [the security review](SECURITY_REVIEW.md). Create the initial owner privately, keep ports 8501/8090 private, and use HTTPS plus a VPN or trusted-access gate. Native Streamlit media/download links still need outer protection, including drawing downloads and previews. A [Caddy example](deploy/Caddyfile.example) is included but is not automatically deployed. `EDITOR_PUBLIC_URL` must be reachable by the browser and use HTTPS for a remote HTTPS deployment.

## Development

Application modules and UI assets live in `src/`, checks in `tests/`, and lifecycle/API entry points in `service/`. Dependencies are declared in `pyproject.toml` and locked by uv.

To rebuild the drawing editor:

```bash
cd frontend
npm ci
npm run build
```

To rebuild the wiki editor:

```bash
cd src/wiki_editor
npm ci
npm run build
```

Browser assets are served locally. Optional Excalidraw features and images linked from documents may request external resources.

Useful checks include:

```bash
uv run python tests/test_iteration.py
uv run python tests/test_projects.py
uv run python tests/test_task_topics.py
uv run python tests/test_auth_screen.py
uv run python tests/test_storage_removal.py
uv run python tests/test_security.py
```

Checks use temporary workspaces. They cover migration, permissions, task controls, readers, project deletion/rollback, metadata versions, authentication, removed-feature archival, and the drawing API. Restart and refresh the browser after changing component assets.

## Topic-scoped library and drawing workspace

The sidebar's **Library** section contains a topic selector with indented **Wiki** and **Diagrams** entries. Selecting a topic scopes both libraries to that topic; **All topics** restores the project-wide views. Opening a topic or its content also updates the sidebar context. Changing topic or project clears the previous reader.

Topic pages use a compact content selector and options menus for editing, moving, or deleting content. Drawings open in the embedded **Editor** by default, without a second large preview underneath. Switch to **Preview** for the last saved PNG, or use **Open in new tab** and **Download**. Saving happens in the drawing toolbar; readers receive the same embedded workspace in read-only mode. Diagram gallery items open in a full-page workspace rather than a popup.
