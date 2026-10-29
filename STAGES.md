Proposed Staged Implementation Plan
In accordance with AGENTS.md ("Work in stages. Present a plan and wait for approval before beginning a new implementation stage"):
Stage 1: Configuration & Document Parser Engine (Read-Only)  
Deliverables:
- Configuration schema (config.json.example / config.json) for student mappings, prep document ID, and semester rules.
- Student document parser module (parser.py) to extract Take-in conversation, identify semester sections, and parse the latest lesson entry.
- Lesson prep parser module to extract student prep lines.
- Read-only inspection CLI/test script to verify parsing against sample/test documents without making any modifications.
Dependencies: Existing read_test_doc.py OAuth setup, google-api-python-client.
Completion Criteria: Successfully parse and print structured JSON representations of Take-in conversation, latest lesson entry, and prep text for a target document without errors or writes.
Stage 2: Web Server & Browser Interface (Read-Only UI)
Deliverables:
- Lightweight local web server (Python http.server, Flask, or FastAPI).
- Web interface featuring student selection, read-only reference panels (Take-in, Current Prep, Previous Lesson), lesson entry inputs (with Europe/Brussels default date), and unsaved changes confirmation prompts.
Dependencies: Stage 1 completion.
Completion Criteria: Fully functional web application running locally in browser; student switching correctly loads reference data and manages unsaved inputs in 100% read-only mode.
Stage 3: Lesson Saving, Safeguards & Prep Updates (Write Operations)
Deliverables:
- Google Docs write engine using batchUpdate API.
- Duplicate detection / idempotency check before saving.
- Optimistic concurrency check (document revision verification).
- Independent partial failure tracking and safe retry handling.
Dependencies: Stage 1, Stage 2, and explicit user approval to enable write permissions and update student documents.
Completion Criteria: End-to-end saving of lesson entries and prep updates with zero duplicate risk, verified format preservation, and failure recovery.
Stage 4: Testing, Hardening & Documentation
Deliverables:
- Execution of all 12 test scenarios defined in PROJECT.md Phase 4 using test documents.
- Complete user documentation (README.md), configuration guide, and diagnostic logging.
Dependencies: Stage 3 completion.
Completion Criteria: All acceptance criteria in PROJECT.md met and verified.
