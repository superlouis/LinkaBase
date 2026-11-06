# Linkabase 0.4.2

A complete self-hosted workspace for tasks, connected knowledge, diagrams, and files. Includes all Python source, the board component, Excalidraw frontend source **and prebuilt local assets**, the custom icon, tests, uv lockfile, and Docker deployment files. No previous installation is needed.

## Start with uv

Unzip, open the `linkabase` folder, then:

```bash
uv sync
uv run python manage.py start
```

Open http://localhost:8501, create the first workspace administrator, then create your first project. New installations start with no projects, topics, or tasks. Drawings open at http://localhost:8090 through the app. The editor is bundled; you do not need npm or an `EDITOR_DIST_DIR` setting to run this release.

```bash
uv run python manage.py status
uv run python manage.py logs
uv run python manage.py restart
uv run python manage.py stop
# Keep both services in the foreground until Ctrl+C:
uv run python manage.py run
```

Copy `.env.example` to `.env` to change the listen address, ports, or data folder. `EDITOR_PUBLIC_URL` must be reachable by your browser; for remote access use the server's private/Tailscale IP. Keep the app private or behind an access-controlled TLS proxy. The first account is the workspace administrator; no default password is provided. Passwords require at least 12 characters. Local sessions expire after 12 hours and may require a fresh sign-in after a browser reload.

If another Linkabase instance occupies the same ports, stop it before starting this one. The lifecycle manager tracks its own services and logs in `.runtime/`, checks process identities to avoid stopping reused PIDs, and supports start/stop/status/restart/logs. Detached process tracking has unit safety checks; this build environment's process namespace prevented an end-to-end detached-manager test. Direct app/API startup and browser flows were verified.

## Upgrade

In your current installation folder:

1. Stop the running app (`uv run python manage.py stop`, or `docker compose down` for Docker).
2. Replace application files with this release, preserving `workspace/`, `.env`, and `.runtime/`.
3. Run `uv sync`, then `uv run python manage.py start` (or rebuild/start with Compose).

Use the same working directory, or explicitly set `WORKSPACE_DIR` to your existing absolute data path. Accounts, project permissions, tasks, topics, content, and history remain compatible. Existing "bases"/"notes" are now displayed as **Topics**; their database IDs do not change. A small assignment table is added automatically. If your old `.env` sets `EDITOR_DIST_DIR`, remove it to use the editor bundled here, unless you intentionally want that override.

## Navigation

- **Highlight** — project overview and work shortcuts.
- **Tasks** — drag-and-drop board and list views.
- **Topics** — connected containers for wiki pages, drawings, uploads, and storage links.
- **Files** — grouped Wiki, Diagrams, and Storage views of topic content.
- **Settings** — appearance/account and user administration, according to access.

Topics appear directly below Tasks, outside the Files group. A task can link to one topic or one child of a topic. The Topics workspace uses a narrow list and a wider content panel. Task creation remains in Tasks; linked tasks can still be opened from a topic.

## Task assignment and dates

Assignees are selected from active users who have access to the current project, including workspace administrators. Dropdown labels show name and email so duplicate names are distinct; assignment is stored by user ID with a display-name snapshot for compatibility. Inactive and unrelated-project users cannot be newly assigned. A previous typed assignment is shown as a legacy choice until you replace it; editing an unrelated field does not silently remove it. Choose Unassigned to clear it.

Due dates use a calendar picker and are saved as ISO dates. Dates are optional; you can clear them. Existing task titles, statuses, priorities, descriptions, links, board behavior, and saved dates are preserved.

## Users and permissions

| Role | View / download | Create / edit / delete | Manage project membership |
|---|---|---|---|
| Read | Yes | No | No |
| Write | Yes | Yes | No |
| Admin | Yes | Yes | Yes |

Workspace administrators have access to all projects and can create projects/users, disable users, and reset account passwords. Project administrators manage read/write/admin membership for existing active accounts. No email invitation/password-recovery system is included. The drawing API requires a valid session and checks the same project permissions. Do not share drawing launch URLs: their fragment carries your session token, which the editor removes and keeps in that browser tab's sessionStorage.

## Topics, wiki, diagrams, storage

Wiki pages are ordinary Markdown in `workspace/docs/<project>/`. Open `workspace/docs` as an Obsidian vault if desired. Standard Markdown is supported; Obsidian plugin blocks, wikilinks, embedded attachments, and simultaneous collaborative typing are not included. Live pages refresh from disk every three seconds; newly discovered files appear after a full page refresh. Existing loose content is grouped in a Project library topic.

The bundled Excalidraw studio opens in a new tab or inside the app. Save to workspace to persist its editable scene and PNG preview. Previews refresh automatically. Drawings use native `.excalidraw` JSON, not the Obsidian Excalidraw plugin's `.excalidraw.md` format.

Upload local files or add HTTPS storage links to topics. Direct Wasabi/S3 browsing and bucket uploads are not implemented. Topic content appears consistently under Files → Wiki, Diagrams, or Storage. Moving content between topics preserves its task links.

## Deletion and recovery

Delete individual children with **Delete content**, or a topic and all its children with **Delete topic**. A confirmation lists the scope. Tasks remain; removed-content links are cleared. Local files, diagram records, and metadata are archived under `workspace/trash/<archive-id>/`, with a JSON manifest and matching database archive record. Recovery is manual in this release. External storage objects are never deleted; only their Linkabase links are removed. Deleting a topic does not delete the project.

## Data and backups

SQLite lives in `workspace/work.sqlite`; Markdown, editable drawing exports, attachments, revision history, and trash are subfolders beside it. Back up the complete workspace with both services stopped. Keep SQLite on local disk, not an object-storage mount. Web permissions do not replace operating-system file permissions. Do not use this prototype for patient data.

## Docker alternative

```bash
docker compose up -d --build
docker compose logs --tail 50
docker compose down
```

Compose binds localhost by default and mounts `./workspace:/data`. Set `BIND_ADDRESS` and `EDITOR_PUBLIC_URL` in `.env` for private remote access. Docker builds include the npm frontend build; a host Topic installation is not required. Do not run Docker and uv services on the same ports at the same time.

## Development

`app.py`, `ui.py`, and `admin_views.py` render the Streamlit interface; `store.py`, `auth.py`, and `notes.py` handle persistence/access; `editor_api.py` serves the drawing studio/API; `manage.py` manages local processes. Internal note table/function names remain stable for upgrade compatibility.

To rebuild the editor from source (only needed if you change it):

```bash
cd frontend
npm ci
npm run build
```

Browser editor assets are served locally. Some optional Excalidraw features such as public libraries may still request external resources if invoked.

## Checks

```bash
uv run python test_iteration.py
uv run python test_delete.py
uv run python test_task_controls.py
uv run python test_manage.py
```

Tests use temporary data, and lifecycle tests use mocked process identities. Checks cover migration, topic/child/task links, roles, archive rollback, deletion/cancel, project-scoped assignee selection, calendar create/edit/clear, legacy assignments, and theme preferences. Real-time coediting, notifications, task deletion, and within-column drag ordering remain future work.

## Storage capacity and volumes

Settings includes SQLite file size, volume free space, and volume usage. It shows a warning below 10% free capacity; it does not automatically create another database. SQLite grows as needed until constrained by disk space, filesystem limits, or an explicit database limit. Writes may fail with SQLITE_FULL when space is exhausted. A new database on the same full drive does not add capacity.

For uv, configure `WORKSPACE_DIR=/mnt/linkabase-data` in `.env`. For Docker, configure `LINKABASE_DATA_DIR=/mnt/linkabase-data`; both services mount that host folder at `/data`. The folder can be a directory on a mounted local/block volume. Stop both services and copy your existing complete workspace there before changing the path, then restart. Pointing to an empty folder creates a separate workspace rather than migrating data.

Keep SQLite on local/block storage, not NFS or an S3 mount. Linkabase currently uses one live SQLite database. Transparent multi-database rollover is not implemented; it requires routing and cross-database link/auth handling. Prefer expanding the volume, or a deliberate PostgreSQL migration when scale demands it.

Topics now have a title only in the interface. Existing summaries remain in storage for backward compatibility and are neither displayed nor included in topic searches.

## Version 0.4.2 — projects and scoped content forms

New workspaces start completely empty. No sample projects or tasks are inserted, including after the final project is deleted. Existing projects are preserved during upgrades; if you want to remove an earlier demo project, select it and use Settings → Project settings → Delete project.

Files → Wiki offers **Add Wiki**, with only a wiki form. Diagrams offers **Add Diagram**, with only a drawing form. Storage offers **Add Storage**, with only file-upload/storage-link options. Each form selects its parent topic. Inside Topics, **Add content** still lets you choose any content type. Create a topic first if none exist.

Project administrators and workspace administrators can open **Settings → Project settings** to rename a project or delete it. Renaming preserves the project key and all links. Deletion requires typing the project key, removes the project's tasks, topics, wiki, drawings, file references, and memberships from the active workspace, and archives local files/records for manual recovery under workspace/trash. User accounts, other projects, and external storage objects stay intact.

Run `uv run python test_projects.py` for fresh-start, scoped-form, rename, permission, archive rollback, full cleanup, cancellation, and final-project deletion checks. Test sample data is created explicitly in test_fixtures.py; the application never calls it.


## v0.4.3: clearer roles and document editing

- Existing workspace administrators are now called **Super-admins**. Their existing `site_admin` flag and project access are preserved. Only super-admins create projects and manage workspace accounts. Project admins manage only their assigned projects.
- Workspace administration → Workspace role lets super-admins promote/demote active accounts. The last active super-admin cannot be demoted. Assign Reader, Writer, or Project admin separately per project.
- Wiki opens in reading mode. **Edit** opens a locally bundled visual editor with headings, bold, italic, lists, quotes, links, images by URL, and tables. **Save changes** and Cancel sit above the editor; Ctrl/Cmd+S also saves. Unsaved edits are not autosaved; Cancel asks before discarding. Navigating away/reloading can discard drafts.
- Files pages have a compact item list and wide reading pane. Wiki history is collapsed below the document.
- Markdown remains authoritative. Visual editing normalizes Markdown formatting; frontmatter, wikilinks, raw HTML and display-math documents default to Markdown source. Use source mode for specialized syntax. Images use URLs; this editor does not upload images.
- Optimistic conflict checks prevent overwriting external edits. On a conflict, keep/copy your draft, Cancel, and reopen the latest document before merging.
- The bundled visual editor works without external CDN requests. To rebuild it: `cd wiki_editor && npm ci && npm run build`. Python-only installs use the included bundle; the existing drawing-editor build is unchanged.

Upgrade: stop Linkabase, keep `.env` and the complete `workspace/` directory, replace application files, run `uv sync`, then `uv run python manage.py start`.

## v0.4.4: remote board fix, more themes, editor preview

- Task card clicks, keyboard activation, drag/drop, and Wiki save/cancel no longer depend on a secure-context-only browser API. This fixes events failing over an HTTP Tailscale/LAN address. Browser regression disables `crypto.randomUUID` and checks click, real drag/drop, document save, Cancel, and conflicting edits.
- Eight themes: Midnight, Paper, Ocean, Forest, Plum, Sand, Slate, Rose.
- Visual Wiki editing and Markdown source both offer Preview, with mode-specific guidance and top Save/Cancel controls. Advanced syntax should remain in source mode.
- `uv run python manage.py storage` reports the configured workspace and database paths without starting services or initializing a database.
- Existing Docker installation: `docker inspect linkabase-workspace-1 --format '{{range .Mounts}}{{println .Type ":" .Source "->" .Destination}}{{end}}'`. The host source mapped to `/data` is the persistent workspace; SQLite is `/data/work.sqlite` in the container. Inspect the drawing-studio container as well to confirm both use the same source.
- When upgrading Docker, preserve `.env` and the existing data mount, then `docker compose up -d --build`. Hard-refresh the browser after upgrading cached frontend assets.

## v0.4.5: focused file libraries

Wiki now uses compact title/topic/updated rows. Diagrams uses thumbnail cards. Storage uses filename/topic/size rows. Select an item to open a wide popup, then choose **Full page** for more room or **Back** to return to the library. There is no permanent split-screen preview.

The Wiki reader retains visual and Markdown editing, Preview, top Save/Cancel, live vault refresh, and version history. Drawing popups retain Excalidraw launch, optional embedded editing, live PNG preview, and editable-scene download. Storage popups preview images, PDFs, and small UTF-8 text files; other formats remain downloadable. External links open through **Open link**. Text preview is limited to 256 KB. Existing project permissions and file formats are unchanged.

For Docker upgrades, keep `.env` and the existing workspace mount. Run `docker compose down`, replace app files, then `docker compose up -d --build`. The PDF viewer dependency is included in the rebuilt image. No database migration or data reset is needed.

## v0.4.6: visual refresh

Distinct sidebar gradients now separate navigation from the reading canvas in all eight themes. Navigation uses quiet inactive links and an inset accent on the active page. Metrics have subtle accent edges, dialogs have softer elevation, and file lists have roomier rows. Focus indicators and reduced-motion preferences are respected.

A new linked-node icon replaces the previous mark in the sidebar, sign-in screen, and browser page icon. Editable vector source is included at `assets/linkabase.svg`; `assets/linkabase.png` is the bundled app asset. No workspace, database, permission, or content format changes.
