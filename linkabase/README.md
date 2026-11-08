# Linkabase

A self-hosted workspace for tasks, connected knowledge, and diagrams. The application version comes from `[project].version` in `pyproject.toml`.

## Run directly with uv

Run commands from the application folder containing `pyproject.toml`, `Dockerfile`, and `compose.yaml` (from the repository root: `cd linkabase`). Install uv and use Python 3.11–3.13. The uv workflow runs Python directly; it does not build a Docker image.

```bash
uv sync --frozen
uv run python main.py start
```

Open http://localhost:8501. The drawing service runs at http://localhost:8090. Both services start together. Compiled editor assets are bundled; Node/npm are only needed when editing their frontend source.

If `.env` does not already exist, create it with `cp .env.example .env`, then configure your data location/ports. Preserve existing `.env` files when upgrading.

```bash
uv run python main.py status
uv run python main.py logs
uv run python main.py restart
uv run python main.py stop
# Keep both services in the foreground until Ctrl+C:
uv run python main.py run
```

New installations start empty. Create the initial super-admin privately, then a project and topics. Use **Quick guide** in the sidebar for the role-aware interactive walkthrough.

## Build and run with Docker Compose

Docker Engine with the Compose plugin is required. Host Python, uv, and Node are not needed. Stop a uv instance first if it uses the same ports or workspace.

From the application folder, create `.env` from `.env.example` only if it does not exist. Compose automatically reads it in this folder, or select it explicitly as below.

```bash
docker compose --env-file .env config --quiet
docker compose --env-file .env up -d --build
```

For a separate build/start sequence, including refreshed base images:

```bash
docker compose --env-file .env build --pull
docker compose --env-file .env up -d
```

Both services use the same `linkabase:local` image by default. The multi-stage Dockerfile builds the drawing frontend, includes the bundled wiki editor, and uses `uv sync --frozen --no-dev` for locked Python dependencies.

```bash
docker compose ps
docker compose logs --tail=100
docker compose logs -f
docker compose down
```

Local URLs are http://localhost:8501 and http://localhost:8090. Restarting existing containers does not rebuild changed source; after updates, use `docker compose up -d --build` again.

### Build an image first, then run it

```bash
docker build --pull -t linkabase:local .
docker compose --env-file .env up -d --no-build --pull never
```

To use a versioned/registry tag, set `LINKABASE_IMAGE` in `.env`, build with that same tag, then use the no-build command above. The version displayed inside the app always comes from `pyproject.toml`.

The image's default command starts Streamlit only. Compose also starts the drawing API with its service command; use Compose for the complete application.

### Data and remote-server configuration

The default persistent bind mount is `./workspace:/data`, shared by both services. Set `LINKABASE_DATA_DIR=/absolute/host/data/path` to use another location. Keep the entire existing workspace when switching from uv to Docker: use its absolute path, stop both old services, and back it up first. Image rebuilds do not migrate data between different mount paths.

For the single-domain HTTPS proxy described in [the security review](SECURITY_REVIEW.md), use:

```dotenv
BIND_ADDRESS=127.0.0.1
EDITOR_PUBLIC_URL=https://your-domain.example
STREAMLIT_BROWSER_SERVER_ADDRESS=your-domain.example
```

Keep ports 8501/8090 private and protect the HTTPS service with a VPN or trusted-access gate. `.env` values configure Compose interpolation; only variables referenced by `compose.yaml` reach containers. Do not bake `.env`, credentials, or workspace data into an image.

## Project space

- **Overview:** assigned tasks ordered by due date and priority, project progress, topics, and content shortcuts.
- **Tasks:** drag-and-drop board and keyboard-friendly list, with priorities, project-scoped assignees, optional due dates, and an optional linked topic. Tasks cannot link to individual content items.
- **Topics:** collections of wiki pages and diagrams, with a tab for their linked tasks.
- **Wiki:** Markdown reading, visual/source editing, preview, conflict checks, and revision history.
- **Diagrams:** local Excalidraw editing, scene downloads, and saved PNG previews.
- **Settings:** profile, theme selection, passwords, project membership, and administration according to your role.

The overview, topic gallery, and library listings use custom HTML components within Streamlit. Click events are validated in Python and open the existing dialogs/readers. Shared component assets live in `src/components/`; the standalone HTML concepts in `../attempt/` are not runtime dependencies.

New accounts default to **Midnight**, the dark theme. Existing accounts retain their saved preference; choose **My preferences → Theme → Midnight → Apply theme** to switch. All eight themes remain available.

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


## Guided tour

Choose **Quick guide** in the sidebar. The `streamlit_tour` guide highlights the project controls, Topics, Wiki, and Diagrams. Super-admins see project creation instructions; writers/project admins see topic/content creation steps; readers see a read-only guide. Replay it anytime. There is no auto-playing tour on every login.

## Password-encrypted project transfers

**Super-admins only:** open **Project transfers** under Manage. Backend checks enforce this restriction independently of the visible buttons.

- **Export project:** select a project, enter and confirm a password of at least 12 characters, create the archive, and download the `.lbproj` file. Keep the password separately; it cannot be recovered.
- **Import project:** upload a `.lbproj`, enter its password and a new uppercase project key, optionally change the project name, then choose **Import as new project**. Existing projects are never overwritten. Memberships and user identities are not granted/imported; assign project access after reviewing the restored content.

The format is a compressed ZIP payload encrypted as a whole using AES-256-GCM with a random salt/nonce and scrypt password derivation (`N=65536, r=8, p=1`). This protects the contents and inner filenames and detects tampering. Open it through Linkabase Import rather than a generic ZIP utility. The outer download filename contains the project key/date. Prepared downloads contain encrypted bytes only, and expire from the transfer page after ten minutes.

Each archive includes the project's active topics, wiki pages (including loose Markdown), wiki revision history and author/editor names, diagrams with embedded image data and previews, tasks, and task-topic links. IDs are remapped on import. Task owner names remain historical labels; assign local users explicitly after import. Accounts, password hashes, sessions, project permissions, deleted/trash content, and retired uploads are excluded. Imports validate format, references, paths and size before committing, stage files privately, and roll back on failure.

Limits: **64 MiB encrypted**, **256 MiB expanded**, and **10,000 archive entries**. The password protects a downloaded file; it is not a substitute for HTTPS or the application's access controls. For whole-workspace disaster recovery (including accounts and deleted records), stop both services and back up the complete workspace directory separately. Per-project transfers are intentionally for portable content, not full-account/server recovery.

## Wiki attribution

The Wiki table shows **Author** and **Last editor** alongside topic and updated date. New pages record their creator; app saves update the last editor without changing the original author. Older pages without recorded provenance show **Unknown**. Detected changes made outside Linkabase show **External edit** rather than attributing them to the last signed-in user. Project archives preserve those display-name snapshots.
