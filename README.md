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
- Python 3.9 or higher.
- Google Cloud Project with the **Google Docs API** enabled.
- OAuth 2.0 Credentials (`credentials.json`) downloaded from the Google Cloud Console and placed in the project root directory.

### 2. Environment Setup
Create and activate a virtual environment, then install dependencies:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configuration
1. Copy `config.json.example` to `config.json`:
   ```bash
   cp config.json.example config.json
   ```
2. Open `config.json` and fill in:
   - `prep_document_id`: The Google Document ID for your central preparation document.
   - `students`: A list of student objects, each containing:
     - `id`: A unique slug (e.g. `"anna-kowalska"`).
     - `name`: Full display name matching the prep document and student records.
     - `doc_id`: The Google Document ID of the student's shared document.

Alternatively, you can configure these interactively through the **Configuratie** tab in the web interface once the server is running.

---

## Running the Application

Start the local Flask development server:
```bash
source .venv/bin/activate
python3 app.py
```
Open your browser at `http://localhost:5000`.

When you first authenticate, follow the browser prompt to sign in with your school Google account and grant the requested read/write permissions.

---

## Save & Recovery Behavior

- **Atomic-style coordination**: When saving a lesson, the application first updates the student's shared Google Doc. If successful, it proceeds to update the central preparation document if "Next lesson ideas" were provided.
- **Concurrency protection**: If another user (or the student) modifies the Google Doc while you have the dashboard open, revision checking detects the mismatch and prompts you to refresh to prevent data loss.
- **Duplicate warning**: If a lesson entry for the exact same date already exists, the application warns you before appending to avoid duplicate entries.

---

## Known Limitations
- The Google Docs API does not support true cross-document multi-phase transactions; partial failure tracking reports independent success/failure states.
- Initial take-in conversations and historical lesson entries are displayed as read-only reference data in this version.
