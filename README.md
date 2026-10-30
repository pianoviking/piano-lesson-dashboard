# Piano Lesson Dashboard

A lightweight, locally hosted web application to manage lesson preparation and lesson notes for piano students, integrating directly with existing Google Docs (student lesson notes and central preparation document).

## Features

- **Google Docs Integration**: Reads student take-in conversations and previous lesson entries, and appends new lesson notes under the appropriate semester heading using the Google Docs API.
- **Central Preparation Sync**: Automatically updates student preparation lines in a central Google Doc when notes are saved with next-lesson ideas.
- **Robust Safeguards**: 
  - **Duplicate Detection**: Prevents accidental duplicate lesson entries for the same date.
  - **Optimistic Concurrency Control**: Checks revision IDs to prevent overwriting concurrent edits made by students.
  - **Partial Failure Handling**: Tracks and reports status independently for student document updates and preparation updates.
  - **Formatting Preservation**: Preserves original document typography, bolding rules, and structure.
- **Modern Web Interface**: Clean, responsive dark-mode UI inspired by modern tooling design principles, with a dedicated **Configuration** tab for managing student mappings and document IDs.

---

## Installation & Setup Instructions

### 1. Prerequisites
- Python 3.9 or higher (for local development).
- Docker and Docker Compose (for containerized deployment).

### 2. Configuration & Secrets
Create a configuration directory (e.g., `./data`) on your host machine to store persistent state:
```bash
mkdir data
```
Copy your Google Cloud credentials to this directory:
- `credentials.json` (from Google Cloud Console).
- `token.json` (generate by running `python read_test_doc.py <doc_id>` on your host once, then copy the generated `token.json` into `./data/`).

Create `data/config.json` (you can copy `config.json.example` as a starting point).

### 3. Containerized Deployment
1. Build the application image:
   ```bash
   docker compose build
   ```
2. Start the container:
   ```bash
   docker compose up -d
   ```
3. Access the dashboard at `http://localhost:5000`.

To run on a home server (LAN access), update the `HOST_BIND` variable in `compose.yaml` (or via `.env`) to `0.0.0.0`.

### 4. Updating the image
1. Pull the latest code.
2. Rebuild the image:
   ```bash
   docker compose build
   docker compose up -d
   ```
Because persistent files (`config.json`, `token.json`) are mounted in `./data/`, your configuration and authentication remain intact after container recreation.

### 5. Troubleshooting
- **Permission Denied**: Ensure the user running the container has write access to your `./data` directory on the host. You can override the user in `compose.yaml` using `PUID` and `PGID` (default 1000:1000).
- **OAuth Failures**: Check the logs (`docker compose logs`) for clear error messages. If `token.json` is missing in `/data/`, you must perform the OAuth authorization on your host and copy the resulting `token.json` to `./data/`.

---

## Local Development (Native)
Start the local Flask development server:
```bash
source .venv/bin/activate
python3 app.py
```
Open your browser at `http://localhost:5000`.


---

## Save & Recovery Behavior

- **Atomic-style coordination**: When saving a lesson, the application first updates the student's shared Google Doc. If successful, it proceeds to update the central preparation document if "Next lesson ideas" were provided.
- **Concurrency protection**: If another user (or the student) modifies the Google Doc while you have the dashboard open, revision checking detects the mismatch and prompts you to refresh to prevent data loss.
- **Duplicate warning**: If a lesson entry for the exact same date already exists, the application warns you before appending to avoid duplicate entries.

---

## Backups & Recovery

The only persistent state is stored in your mounted configuration directory (`./data`).
- **Backup**: Regularly back up the `data/` directory. It contains your student mappings (`config.json`) and your Google access tokens (`token.json`).
- **Recovery**: To recover on a new machine, install Docker, copy your `data/` directory, and run `docker compose up -d`.

---

## Known Limitations
- The Google Docs API does not support true cross-document multi-phase transactions; partial failure tracking reports independent success/failure states.
- Initial take-in conversations and historical lesson entries are displayed as read-only reference data in this version.
