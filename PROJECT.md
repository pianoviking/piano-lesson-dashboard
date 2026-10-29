# Programming Brief: Local Teaching Dashboard for Piano Lessons

## 1. Project objective

Build a lightweight, locally hosted web application to manage lesson preparation and lesson notes for my piano students.

I currently maintain:
- One Google Doc per student, shared with that student.
- A separate Google Doc containing my lesson preparation, usually one line per student.

The application should provide a single, convenient interface for reviewing a student's history, preparing a lesson, recording what happened, and updating both existing documents.

**The existing Google Docs are the source of truth.** Do not migrate the student records into a new database or replace the current workflow with a different document system.

The primary goal is to reduce administrative work between and during lessons, while preserving the existing documents and their formatting.

## 2. Initial development procedure

Before implementing anything:

1. Inspect the existing project directory, installed tools, runtime environment and relevant configuration.
2. Determine whether an existing application or reusable component can be used.
3. Propose a simple architecture appropriate for a single teacher using the application locally.
4. Identify any required Google Cloud configuration, API permissions, OAuth credentials or school administrator approval.
5. Report the proposed implementation plan and any genuine blockers before making substantial changes.

Do not replace or reorganise unrelated files. Keep the implementation simple and maintainable.

## 3. User interface

Create a responsive, straightforward web interface optimised for use on my desktop computer while teaching.

### Student selection

Provide a dropdown containing all configured students.

When a student is selected, automatically load and display:

- Student name.
- Take-in conversation.
- Current lesson preparation from the prep document.
- Previous lesson's notation, including its date and the recorded lesson fields.

The take-in conversation and previous lesson's notation are reference information and should be read-only in the initial version.

The current preparation should be clearly distinguished from the historical information.

Changing the selected student must load that student's data and clear any unsaved lesson inputs from the previously selected student. If there are unsaved changes, ask for confirmation before discarding them.

### Current lesson entry

Provide the following fields:

- **Date:** Default to today's date in the Europe/Brussels time zone. Allow manual adjustment.
- **Repertoire:** Multiline text input.
- **Vaardigheden:** Multiline text input.
- **Werkpunten:** Multiline text input.
- **Ideeën volgende les:** Optional multiline text input for ideas or preparation for the next lesson.

The three lesson fields must accept ordinary free-form text, including multiple lines. Do not impose rigid data structures or require individual bullet items.

The optional next-lesson ideas field is separate from the three fields that are published to the student's document.

Provide one prominent **Save lesson** button.

The interface should also provide clear loading, saving, success and error states.

## 4. Student Google Docs

Each student already has a Google Doc shared with them.

The existing document structure consists of:
- An introductory paragraph containing the take-in conversation.
- A first semester section.
- A second semester section.
- Lesson entries under each semester, recording the date, repertoire, vaardigheden and werkpunten.

The application must use the existing student documents rather than creating new documents.

### Reading existing information

Use the Google Docs API to read the selected student's document.

Extract the take-in conversation and the most recent completed lesson entry. Identify the lesson date and the three corresponding fields.

Do not assume all documents have perfectly identical formatting. Inspect the actual documents and design the parser around their existing structures. If a document cannot be parsed confidently, report the problem instead of silently displaying incorrect information.

### Writing a lesson entry

When I save a lesson:

1. Identify the correct student document.
2. Determine the semester from the lesson date.
3. Append a new lesson entry under the appropriate existing semester heading.
4. Include the date, repertoire, vaardigheden and werkpunten.
5. Preserve the take-in conversation, previous entries, semester headings and unrelated formatting.

Use a consistent, readable layout matching the existing documents.

For example, a lesson entry could be displayed as:

**28/10/2026**

**Repertoire**
Current repertoire notes go here.

**Vaardigheden**
Skills worked on during the lesson.

**Werkpunten**
Points to practise before the next lesson.

This is an illustrative layout. Inspect the actual student documents before finalising the format, and reuse their existing formatting conventions wherever possible.

Use Google Docs API operations that preserve surrounding content and formatting. Prefer targeted, atomic updates rather than rewriting the complete document. Google documents supports batched updates and revision controls for this purpose.

References:
- https://developers.google.com/workspace/docs/api/concepts/request-response
- https://developers.google.com/workspace/docs/api/reference/rest/v1/documents/batchUpdate

### Semester selection

Determine the semester automatically from the lesson date.

Inspect the existing semester headings and any established date conventions before implementing this logic. If the semester boundaries are not explicitly represented, make them configurable rather than hardcoding assumptions about the school calendar.

If the selected date falls outside the configured academic year, or the semester cannot be determined confidently, ask for clarification before saving.

Do not create new semester headings automatically unless this behaviour has been explicitly approved.

## 5. Lesson preparation document

I maintain a separate Google Doc for lesson preparation. It generally contains one line per student.

The application must read this document and find the preparation associated with the selected student.

When I enter ideas in the optional next-lesson preparation field and save the lesson:

- Update the preparation associated with that student.
- Preserve the document's existing structure and formatting.
- Leave all other students' preparation untouched.
- Do not create duplicate student entries.

Initially, assume that the optional field represents the next preparation to be recorded for the selected student. When it contains text, replace that student's existing preparation text with the new text, preserving the rest of the line and document.

If the field is empty, do not modify the prep document.

If the student's preparation entry cannot be identified unambiguously, stop and report the issue rather than creating or modifying a potentially incorrect entry.

If the existing prep document uses a format that cannot safely support this operation, report the limitation and propose the smallest necessary adjustment before implementing it.

## 6. Google Workspace authentication and API integration

Use the official Google APIs.

The intended approach is:
- Google Docs API for reading and updating document content.
- Google Drive API, if needed, to discover student documents and locate the prep document.
- OAuth 2.0 for authorisation using my school Google account.

Do not assume that access to Gemini automatically grants access to the Google Docs or Drive APIs. These are separate integration concerns.

Use the least-privileged practical permissions that support the required operations. Prefer read-only access for documents that the application only needs to inspect, and request write access only where required.

The application should:
- Store document IDs in configuration or resolve them through a reliable, configurable folder structure.
- Avoid relying on student names alone as unique identifiers.
- Never expose OAuth tokens, client secrets or credentials in frontend code, logs or version control.
- Keep secrets in environment variables or an appropriate local secret store.
- Handle revoked access, expired credentials, missing permissions and API failures gracefully.
- Respect school Workspace administrator policies and data-handling requirements.

Before choosing an authentication flow, verify which OAuth configuration is supported by the school's Workspace environment and whether administrator approval is necessary.

Do not build a browser automation workaround if the API integration is available and properly authorised.

## 7. Data integrity and safeguards

These safeguards are mandatory.

### Prevent duplicate lesson entries

A repeated click, browser refresh, timeout or retry must not blindly append the same lesson twice.

Before saving, check whether an entry already exists for the selected student and lesson date. If a potential duplicate is found, warn me and require an explicit decision before proceeding.

Use an idempotency mechanism or equivalent reliable duplicate protection. A date alone should not be treated as a universally unique lesson identifier because a student might have multiple lessons on the same day.

### Prevent accidental overwrites

- Never replace the entire contents of a student document.
- Never overwrite the take-in conversation or historical lesson entries.
- Never alter another student's preparation.
- Never silently replace existing lesson entries.
- Warn before saving an entry whose date already exists.
- Preserve all fields and content not explicitly targeted by the operation.

### Protect against concurrent edits

Students may edit their shared documents while the application is open.

Re-read the relevant document before writing, and use Google Docs revision controls where appropriate to avoid applying an update against an outdated document revision.

If a concurrent edit makes the intended update unsafe, stop, reload the latest document and ask me to retry if necessary. Do not silently discard another person's changes.

### Handle partial failures

Saving affects two separate documents, and the Google APIs do not provide a single atomic transaction covering both.

The application must track the result of each operation independently.

For example:
- Student lesson entry saved successfully.
- Prep update failed.

Display this accurately and provide a safe retry mechanism that does not duplicate the already-saved lesson.

Do not report complete success until all requested operations have succeeded.

### Confirm success

After saving, show which student and date were saved, whether the student document was updated, and whether the prep document was updated.

Provide a link to the updated student document if available.

Do not clear unsaved input fields until the relevant save operations have succeeded or the user explicitly chooses to discard the input.

## 8. Gemini integration

My school uses Google Workspace and has previously provided access to Gemini for education.

Do not make Gemini a dependency of the initial version.

First implement reliable reading, editing, authentication and error handling through the Google APIs.

Keep the architecture open to a later, optional Gemini-assisted feature, such as generating suggestions for the next lesson based on the previous lesson's notation.

Before implementing such a feature, verify what access to Gemini or the Gemini API is actually available through the school account. Do not assume that a school Gemini interface implies API access.

Any future AI-generated suggestions must remain editable and must never be published to a student's document without my explicit action.

## 9. Technical and operational requirements

- Run locally on my computer.
- Prefer a lightweight web interface accessible through a local browser.
- Keep external dependencies to a minimum.
- Do not require a paid external hosting service.
- Do not introduce a database unless a concrete technical requirement makes one necessary.
- Keep configuration separate from application code.
- Provide clear setup and startup instructions.
- Provide a way to configure or change the student document collection and prep document.
- Never commit credentials or sensitive student information to version control.
- Do not send student information to third-party services beyond the authorised Google Workspace services required for the application.
- Include basic diagnostic logging without recording full lesson contents or sensitive student information.

## 10. Implementation plan

Implement incrementally.

### Phase 1: Inspect and connect

- Inspect the existing development environment.
- Configure Google API access and authentication.
- Identify the student documents and prep document.
- Read representative documents without modifying them.
- Report any inconsistencies in document structure.

**Deliverable:** A verified read-only integration that can list students and retrieve their relevant information.

### Phase 2: Build the interface

- Implement student selection.
- Load the take-in conversation, current preparation and previous lesson.
- Add the date and three lesson input fields.
- Add the optional next-lesson ideas field.
- Implement unsaved-change handling.

**Deliverable:** A working interface that can prepare a lesson without changing any documents.

### Phase 3: Implement saving

- Implement semester detection.
- Append lesson entries using the existing document structure.
- Update the selected student's prep line when appropriate.
- Implement duplicate detection, revision checks and partial-failure recovery.
- Preserve existing formatting.

**Deliverable:** A functional end-to-end workflow.

### Phase 4: Test and harden

Test at least the following scenarios:

1. Select a student and load all reference information.
2. Save a normal lesson with all three fields populated.
3. Save a lesson with multiline text.
4. Save a lesson without next-lesson ideas.
5. Save a lesson with next-lesson ideas and verify that only the selected student's prep changes.
6. Attempt to save the same lesson twice.
7. Handle a date that falls in the other semester.
8. Handle an ambiguous or out-of-range date.
9. Handle an API failure during the student document update.
10. Handle a successful student update followed by a failed prep update.
11. Handle a document modified by a student while the application is open.
12. Verify that historical content and formatting remain intact.

Use test documents or copies of real document structures during development. Do not perform destructive tests against live student documents.

### Phase 5: Deliver and document

Provide:
- Complete application source code.
- Installation and startup instructions.
- Google Workspace/API setup instructions.
- Configuration instructions.
- A concise explanation of the save and recovery behaviour.
- A list of known limitations.

## 11. Acceptance criteria

The application is ready for normal use when:

- I can select any configured student from a dropdown.
- The correct take-in conversation, current preparation and previous lesson load automatically.
- I can enter the lesson date, repertoire, vaardigheden and werkpunten.
- The application appends a correctly formatted lesson entry under the appropriate semester.
- Existing content and formatting are preserved.
- Optional next-lesson ideas update only the selected student's preparation.
- Empty optional input does not erase existing preparation.
- Repeated saves cannot silently create duplicate entries.
- Concurrent edits and partial failures are handled safely.
- The interface clearly reports success or failure.
- The complete workflow works locally through my school Google account without requiring manual edits to the underlying documents.

**Priority order:** data integrity first, reliable Google Docs integration second, ease of use during teaching third, visual polish fourth. A dependable tool beats a pretty tool that eats student records.
