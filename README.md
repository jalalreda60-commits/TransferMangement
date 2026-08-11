# Transfer Management System

A professional desktop application for managing manufacturing transfer
projects from preparation through release. Built with **Python +
PySide6**, **SQLAlchemy ORM**, and a **SQLite** database that can live
on a shared network folder for multi-user access — no cloud dependency.

---

## 1. Technology stack

- Python 3.13
- PySide6 (desktop UI)
- SQLAlchemy 2.0 ORM
- SQLite
- MVC-style architecture: `models/` (ORM) → `services/` (business logic,
  the "controller" layer) → `ui/` (views)

## 2. Data model

```
Transfer
 ├─ PTTApproval (1:1)  ──► OEMApproval (1:many)
 ├─ E2EFollowup (1:1)
 ├─ Release (1:1)
 ├─ Attachments, Comments, ActivityLog (1:many)
 └─ Tools (1:many)
     ├─ SafetyStock (1:1)
     ├─ Training (1:1)
     └─ PartNumbers (1:many)
         ├─ RawMaterial (1:1)
         ├─ PreCheck (1:1)
         └─ Applicator (1:1, if Transfer.activity == "Stamping")
            or CounterPart (1:1, if Transfer.activity == "Molding")
```

Every Transfer/Tool/PartNumber automatically gets its one-to-one child
records provisioned the moment it's created (see
`services.transfer_service.ensure_related_records`), so every
Preparation sub-module always has something to bind its form to — no
null-checking scattered through the UI.

## 3. Progress calculation (automatic, at every level)

`services/progress_service.py` rolls progress up the hierarchy exactly
as specified:

```
activity progress  →  Tool progress  →  Transfer Preparation/Release progress  →  Dashboard global progress
```

Each Preparation/Release entity computes its own `progress_pct()`
(e.g. Safety Stock = built ÷ required quantity; PTT = fraction of
Internal + every OEM approval that reached "Approved"). Tool progress
averages its Part Numbers' progress with Safety Stock and Training.
Transfer Preparation progress averages PTT, E2E, and every Tool's
progress. `Transfer.status` (Not Started / Ongoing / Delayed /
Completed) is then derived automatically from that progress plus the
planned transfer date and Release status, and cached on the Transfer
row so the Dashboard and Transfers list can sort/filter cheaply.

## 4. A note on the "Release" module

The spec names Release as a sidebar module and requires the Dashboard
to show "Release Progress," but — unlike Preparation's seven detailed
sub-modules — doesn't specify Release's own fields. This build
implements Release as a **sign-off checklist mirroring the seven
Preparation sub-modules** (so each phase can be explicitly signed off,
independent of its automatically-computed status) plus the **final
release decision**: status (Pending / Ready for Release / Released /
On Hold), actual release date, released-by, and sign-off comments. If
your organization's real release process looks different, `models/release.py`
and `ui/views/release_view.py` are the two files to adapt — everything
else (progress rollups, Dashboard, notifications) already reads
`Transfer.release_progress` generically and doesn't need to change.

## 5. Getting started

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
python main.py
```

On first launch the app creates `data/transfer_management.db`
automatically via SQLAlchemy's `create_all()` — no migrations needed
for a fresh install.

## 6. Pushing this project to GitHub

```bash
git init
git add .
git commit -m "Initial commit: Transfer Management System"
git branch -M main
git remote add origin https://github.com/<your-org>/<your-repo>.git
git push -u origin main
```

Pushing to `main` automatically triggers the `build-windows-exe.yml`
workflow (section 8) and produces a downloadable `.exe` under the
**Actions** tab within a couple of minutes. `data/` (your local
database, attachments, exports) is excluded via `.gitignore`.

## 7. Multi-user setup (shared network folder)

SQLite supports multiple readers/writers against the same file as long
as every workstation points at the identical path.

1. Create a folder on your file server, e.g. `\\server\share\TMS\`.
2. On the **first** workstation: **Settings → Database Location →
   Browse**, pick a new file inside that folder, then **Apply &
   Reconnect** — this creates the shared database.
3. On every other workstation: **Settings → Database Location**, point
   at that exact same UNC path, then **Apply & Reconnect**.

The engine (`database/base.py`) uses SQLite's classic rollback journal
(not WAL, which is unreliable over SMB/CIFS) and a 30-second busy
timeout, so a save from one user waits briefly if another is mid-write
rather than failing outright. Suited to small/medium teams (a handful
of concurrent users).

## 8. Building a Windows .exe

### Option A — GitHub Actions (recommended, no Windows machine needed)

`.github/workflows/build-windows-exe.yml` builds the `.exe` on GitHub's
own Windows runners on every push to `main`/PR, or manually via the
**Actions** tab (`Run workflow`). Download the finished
`TransferManagementSystem-windows.zip` artifact, unzip, and run.

To publish a versioned release with the .exe attached:
```bash
git tag v1.0.0
git push origin v1.0.0
```

### Option B — Build locally on Windows

PyInstaller does not cross-compile, so this must run **on Windows**:
```bash
pip install -r requirements.txt
pip install pyinstaller
python build_exe.py
```

Both options use the same `TransferManagementSystem.spec`, so results
are identical: `dist/TransferManagementSystem/TransferManagementSystem.exe`.
Copy the whole folder to each workstation, then point **Settings →
Database Location** at your shared file.

## 9. Project structure

```
TMS/
├── main.py                          # Entry point
├── config.py                        # Paths, settings persistence
├── requirements.txt
├── build_exe.py                     # Local PyInstaller build helper
├── TransferManagementSystem.spec    # PyInstaller build spec (local + CI)
│
├── .github/workflows/
│   └── build-windows-exe.yml        # Builds the .exe on GitHub's Windows runners
│
├── resources/icons/                 # App icon (.ico for the exe, .png for in-app)
│
├── database/
│   └── base.py                      # SQLAlchemy engine/session, network-share-safe PRAGMAs
│
├── models/                          # SQLAlchemy ORM
│   ├── transfer.py                  # Transfer, Tool, PartNumber
│   ├── preparation.py               # PTTApproval, OEMApproval, SafetyStock, RawMaterial,
│   │                                   PreCheck, E2EFollowup, Applicator, CounterPart, Training
│   ├── release.py                   # Release (sign-off checklist + decision)
│   └── support.py                   # Attachment, Comment, ActivityLog
│
├── services/                        # Business logic ("controller" layer)
│   ├── transfer_service.py          # CRUD, search/filter/sort, duplicate, comments, attachments
│   ├── progress_service.py          # Automatic progress roll-up (activity → Tool → Transfer → global)
│   ├── notification_service.py      # Overdue-activity detection across every module
│   └── dashboard_service.py         # KPI/chart/table aggregate queries
│
├── ui/
│   ├── main_window.py               # Sidebar + stacked pages
│   ├── theme.py                     # Professional blue industrial QSS (light/dark)
│   ├── widgets/                     # KpiCard, Badge, Sidebar, charts, EntityPicker, DynamicForm
│   └── views/                       # Dashboard, Transfers (+dialog), Preparation, Release,
│                                       Notifications, Reports, Settings
│
├── reports/
│   ├── excel_export.py              # .xlsx export (flattened by Tool/Part Number)
│   └── print_service.py             # Native OS print dialog + print preview
│
└── data/                            # Created on first run (db, attachments, exports) - gitignored
```

## 10. Design notes

- **`ui/widgets/dynamic_form.py`** — a small declarative form builder
  (`FieldSpec` list → `QFormLayout`) that every Preparation sub-module
  and the Release checklist bind to. This is what keeps seven distinct
  sub-modules from needing seven hand-written, repetitive form files.
- **`ui/widgets/entity_picker.py`** — a single reusable Transfer → Tool
  → Part Number tree, parameterised by which level is selectable
  (`scope="transfer"|"tool"|"part_number"`), used by every Preparation
  sub-module and Release to pick which record a form is editing.
- **Printing** uses Qt's native `QPrintDialog`/`QPrintPreviewDialog`
  rather than a PDF library, so it goes straight to the OS print
  system as requested.
