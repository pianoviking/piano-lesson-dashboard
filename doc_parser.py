"""
Document parser for piano lesson dashboard.

Parses Google Docs API responses into structured data:
- Student documents: take-in conversation, semester sections, lesson entries
- Prep document: per-student preparation lines

This module operates on the raw JSON structure returned by the Google Docs API
(documents().get()), specifically the body.content array.
"""

import re
from datetime import date


def extract_paragraph_text(paragraph):
    """Extract concatenated text from a paragraph's elements."""
    parts = []
    for elem in paragraph.get("elements", []):
        if "textRun" in elem:
            parts.append(elem["textRun"].get("content", ""))
    return "".join(parts)


def get_plain_text_blocks(body_content):
    """
    Flatten body.content into a list of dicts describing each block.

    Returns a list where each item has:
      - type: 'paragraph' | 'table' | 'section_break' | 'unknown'
      - text: extracted plain text (empty string for non-text blocks)
      - startIndex / endIndex: indices in the original document
      - raw_element: the original element dict from the API response
    """
    blocks = []
    for element in body_content:
        start_idx = element.get("startIndex")
        end_idx = element.get("endIndex")

        if "paragraph" in element:
            para = element["paragraph"]
            text = extract_paragraph_text(para)
            # Detect section breaks via paragraph style or special markers
            para_style = para.get("paragraphStyle", {})
            named_style = para_style.get("namedStyleType", "")
            if named_style == "SECTION_BREAK":
                blocks.append({
                    "type": "section_break",
                    "text": text.strip(),
                    "startIndex": start_idx,
                    "endIndex": end_idx,
                    "raw_element": element,
                })
            else:
                blocks.append({
                    "type": "paragraph",
                    "text": text,
                    "startIndex": start_idx,
                    "endIndex": end_idx,
                    "raw_element": element,
                })
        elif "table" in element:
            table_text_parts = []
            for row in element["table"].get("tableRows", []):
                for cell in row.get("tableCells", []):
                    cell_text = extract_cell_text(cell)
                    table_text_parts.append(cell_text)
            blocks.append({
                "type": "table",
                "text": "\n".join(table_text_parts),
                "startIndex": start_idx,
                "endIndex": end_idx,
                "raw_element": element,
            })
        else:
            blocks.append({
                "type": "unknown",
                "text": "",
                "startIndex": start_idx,
                "endIndex": end_idx,
                "raw_element": element,
            })

    return blocks


def extract_cell_text(cell):
    """Recursively extract text from a table cell's content."""
    parts = []
    for element in cell.get("content", []):
        if "paragraph" in element:
            parts.append(extract_paragraph_text(element["paragraph"]))
    return "".join(parts)


# ---------------------------------------------------------------------------
# Semester heading detection
# ---------------------------------------------------------------------------

SEMESTER_1_KEYWORDS = [
    r"\beerste\s+semester:?\b",
    r"\b1e?\s*semester:?\b",
    r"\bfirst\s+semester:?\b",
    r"\bsemester\s*1:?\b",
]

SEMESTER_2_KEYWORDS = [
    r"\btweede\s+semester:?\b",
    r"\b2e?\s*semester:?\b",
    r"\bsecond\s+semester:?\b",
    r"\bsemester\s*2:?\b",
]


def classify_semester_heading(text, extra_keywords=None):
    """
    Classify a paragraph as belonging to semester_1, semester_2, or None.

    Args:
        text: The stripped paragraph text.
        extra_keywords: Optional dict with keys 'semester_1' and 'semester_2',
                        each mapping to a list of additional regex patterns.

    Returns:
        'semester_1', 'semester_2', or None
    """
    lower = text.lower().strip()

    s1_patterns = SEMESTER_1_KEYWORDS[:]
    s2_patterns = SEMESTER_2_KEYWORDS[:]

    if extra_keywords:
        s1_patterns.extend(extra_keywords.get("semester_1", []))
        s2_patterns.extend(extra_keywords.get("semester_2", []))

    for pat in s1_patterns:
        if re.search(pat, lower):
            return "semester_1"

    for pat in s2_patterns:
        if re.search(pat, lower):
            return "semester_2"

    return None


# ---------------------------------------------------------------------------
# Lesson entry parsing
# ---------------------------------------------------------------------------

DATE_PATTERN = re.compile(
    r"^(\d{1,2})[/\-.](\d{1,2})(?:[/\-.](\d{2,4}))?$"
)

PLACEHOLDER_PATTERN = re.compile(r"^\[.+\]$", re.IGNORECASE)

FIELD_LABELS = {
    "repertoire": ["Repertoire", "Repertoirestuk"],
    "vaardigheden": ["Vaardigheden", "Vaardigheid"],
    "werkpunten": ["Werkpunten", "Werkpunten/opmerkingen"],
}


def parse_date_line(text):
    """Try to parse a date like '28/10' or '28/10/2026'. Returns a date object or None."""
    cleaned = text.strip().replace("**", "").replace("*", "").strip()
    if PLACEHOLDER_PATTERN.match(cleaned):
        return None
    m = DATE_PATTERN.match(cleaned)
    if not m:
        return None
    day, month = int(m.group(1)), int(m.group(2))
    year = int(m.group(3)) if m.group(3) else 2026  # Defaulting year for now
    if year < 100:
        year += 2000
    try:
        return date(year, month, day)
    except ValueError:
        return None


def parse_field_label(text):
    """
    Check if a line starts with or matches a field label like '**Repertoire**' or 'Repertoirestuk: Mandinga'.
    Returns (field_key, inline_value) or (None, None).
    """
    cleaned = text.strip().replace("**", "").replace("*", "").strip()
    
    all_labels = []
    for key, labels in FIELD_LABELS.items():
        for label in labels:
            all_labels.append((key, label.rstrip(":")))
    all_labels.sort(key=lambda x: len(x[1]), reverse=True)

    for key, norm_label in all_labels:
        pattern = re.compile(rf"^{re.escape(norm_label)}:?\s*(.*)$", re.IGNORECASE)
        m = pattern.match(cleaned)
        if m:
            inline_val = m.group(1).strip()
            return key, inline_val

    return None, None


def extract_latest_lesson(blocks, semester_key):
    """
    Walk backwards through blocks within a given semester section and find
    the most recent complete lesson entry.

    A lesson entry consists of:
      - A date line (dd/mm/yyyy or dd/mm)
      - Followed by Repertoire + text, Vaardigheden + text, Werkpunten + text

    Returns a dict with keys: date, repertoire, vaardigheden, werkpunten
    or None if no valid entry is found.
    """
    # Find the range of blocks belonging to the target semester
    in_target_semester = False
    semester_block_indices = []

    for i, block in enumerate(blocks):
        if block["type"] != "paragraph":
            continue
        sem_class = classify_semester_heading(block["text"])
        if sem_class == semester_key:
            in_target_semester = True
            semester_block_indices.append(i)
        elif sem_class is not None and sem_class != semester_key:
            in_target_semester = False
        elif in_target_semester:
            semester_block_indices.append(i)

    if not semester_block_indices:
        return None

    # Walk backwards looking for a date followed by all three fields
    for idx_pos in reversed(range(len(semester_block_indices))):
        i = semester_block_indices[idx_pos]
        block = blocks[i]
        lesson_date = parse_date_line(block["text"])
        if lesson_date is None:
            continue

        # Look forward for the three fields
        fields_found = {}
        j = i + 1
        while j < len(blocks) and j <= max(semester_block_indices):
            b = blocks[j]
            if b["type"] != "paragraph":
                j += 1
                continue

            label, inline_val = parse_field_label(b["text"])
            if label and label not in fields_found:
                value_lines = []
                if inline_val:
                    value_lines.append(inline_val)

                k = j + 1
                while k < len(blocks) and k <= max(semester_block_indices):
                    nb = blocks[k]
                    if nb["type"] != "paragraph":
                        break
                    next_label, _ = parse_field_label(nb["text"])
                    if next_label is not None:
                        break
                    if parse_date_line(nb["text"]) is not None:
                        break
                    if PLACEHOLDER_PATTERN.match(nb["text"].strip()):
                        break
                    if nb["text"].strip():
                        value_lines.append(nb["text"].rstrip("\n"))
                    k += 1
                fields_found[label] = "\n".join(value_lines).strip()
                j = k
                continue
            j += 1

        if len(fields_found) == 3:
            return {
                "date": lesson_date.isoformat(),
                "repertoire": fields_found.get("repertoire", ""),
                "vaardigheden": fields_found.get("vaardigheden", ""),
                "werkpunten": fields_found.get("werkpunten", ""),
            }

    return None


def extract_take_in_conversation(blocks):
    """
    Extract the introductory/take-in conversation text.

    This is everything before the first recognized semester heading.
    Skips empty leading paragraphs, the title, and the literal 'Intake:' label.
    """
    intro_parts = []
    for block in blocks:
        if block["type"] != "paragraph":
            continue
        sem_class = classify_semester_heading(block["text"])
        if sem_class is not None:
            break
        
        text = block["text"].strip()
        # Skip title-like lines or 'Intake:' label
        if not text or "AGENDA" in text.upper() or text.upper() == "INTAKE:":
            continue
        intro_parts.append(text)
    return "\n\n".join(intro_parts)


# ---------------------------------------------------------------------------
# High-level student document parser
# ---------------------------------------------------------------------------

def parse_student_document(document_json):
    """
    Parse a full Google Docs API document response for a student.

    Args:
        document_json: The dict returned by service.documents().get(...).execute()

    Returns:
        {
            "title": str,
            "revision_id": str,
            "take_in_conversation": str,
            "latest_lesson": {...} | None,
            "parse_warnings": [str],
        }
    """
    warnings = []
    title = document_json.get("title", "")
    revision_id = document_json.get("revisionId", "")

    body = document_json.get("body", {})
    content = body.get("content", [])

    if not content:
        warnings.append("Document body is empty.")
        return {
            "title": title,
            "revision_id": revision_id,
            "take_in_conversation": "",
            "latest_lesson": None,
            "parse_warnings": warnings,
        }

    blocks = get_plain_text_blocks(content)

    take_in = extract_take_in_conversation(blocks)

    latest_lesson = extract_latest_lesson(blocks, "semester_2")
    if latest_lesson is None:
        latest_lesson = extract_latest_lesson(blocks, "semester_1")

    if latest_lesson is None:
        warnings.append("Could not identify a complete previous lesson entry.")

    return {
        "title": title,
        "revision_id": revision_id,
        "take_in_conversation": take_in,
        "latest_lesson": latest_lesson,
        "parse_warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Prep document parser
# ---------------------------------------------------------------------------

def parse_prep_document(document_json):
    """
    Parse the central lesson-preparation document.

    Expected format: one line per student, typically starting with the student's
    name followed by a separator (colon, dash, tab) and then the prep text.

    Returns:
        {
            "title": str,
            "revision_id": str,
            "entries": [
                {"student_name": str, "prep_text": str, "block_index": int},
                ...
            ],
            "parse_warnings": [str],
        }
    """
    warnings = []
    title = document_json.get("title", "")
    revision_id = document_json.get("revisionId", "")

    body = document_json.get("body", {})
    content = body.get("content", [])

    if not content:
        warnings.append("Prep document body is empty.")
        return {
            "title": title,
            "revision_id": revision_id,
            "entries": [],
            "parse_warnings": warnings,
        }

    blocks = get_plain_text_blocks(content)
    entries = []

    # Separator pattern: matches student name followed by colon, dash (with space), or tab, then prep text
    sep_pattern = re.compile(r"^(.+?)(?:\s*:\s*|\s+[\-—–]\s+|\t+)(.*)$", re.DOTALL)

    for i, block in enumerate(blocks):
        if block["type"] != "paragraph":
            continue
        raw_text = block["text"].strip()
        if not raw_text:
            continue

        m = sep_pattern.match(raw_text)
        if m:
            student_name = m.group(1).strip()
            prep_text = (m.group(2) or "").strip()
            entries.append({
                "student_name": student_name,
                "prep_text": prep_text,
                "block_index": i,
            })
        else:
            # Line without a recognizable separator — treat whole line as prep text
            # with unknown student association
            entries.append({
                "student_name": "",
                "prep_text": raw_text,
                "block_index": i,
            })

    if not entries:
        warnings.append("No student prep lines could be identified in the prep document.")

    return {
        "title": title,
        "revision_id": revision_id,
        "entries": entries,
        "parse_warnings": warnings,
    }


def find_student_prep(prep_data, student_name):
    """
    Find the prep entry matching a given student name (case-insensitive partial match).

    Returns the matching entry dict or None.
    Raises ValueError if multiple matches are found (ambiguous).
    """
    normalized_query = student_name.lower().strip()
    matches = []
    for entry in prep_data.get("entries", []):
        entry_name = entry["student_name"].lower().strip()
        if not entry_name:
            continue
        if normalized_query == entry_name or normalized_query in entry_name or entry_name in normalized_query:
            matches.append(entry)

    if len(matches) == 0:
        return None
    if len(matches) > 1:
        names = ", ".join(e["student_name"] for e in matches)
        raise ValueError(f"Ambiguous student match '{student_name}' matched multiple entries: {names}")
    return matches[0]
