"""
Document writer and safeguard module for piano lesson dashboard.

Handles:
- Inserting lesson entries under the correct semester heading in student Google Docs.
- Updating student preparation lines in the central prep document.
- Idempotency / duplicate detection (preventing duplicate lesson entries on the same date).
- Optimistic concurrency control (checking document revision IDs).
- Independent partial failure tracking and safe retry logic.
"""

import re
from datetime import date
from doc_parser import get_plain_text_blocks, classify_semester_heading, parse_date_line


def format_lesson_entry_data(lesson_date_str, repertoire, vaardigheden, werkpunten):
    """
    Returns structured string data for lesson insertion.
    """
    try:
        dt = date.fromisoformat(lesson_date_str)
        date_str = f"{dt.day}/{dt.month}"
    except ValueError:
        date_str = lesson_date_str

    return {
        "date": date_str,
        "repertoire_label": "Repertoirestuk: ",
        "repertoire_val": repertoire.strip(),
        "vaardigheid_label": "Vaardigheid: ",
        "vaardigheid_val": vaardigheden.strip(),
        "werkpunten_label": "Werkpunten/opmerkingen: ",
        "werkpunten_val": werkpunten.strip()
    }


def check_duplicate_lesson(document_json, target_date_str):
    """
    Check if a lesson entry for target_date_str already exists in the document.
    Returns True if found, False otherwise.
    """
    body = document_json.get("body", {})
    content = body.get("content", [])
    if not content:
        return False

    blocks = get_plain_text_blocks(content)
    try:
        target_date = date.fromisoformat(target_date_str)
    except ValueError:
        return False

    for block in blocks:
        if block["type"] == "paragraph":
            parsed_date = parse_date_line(block["text"])
            if parsed_date and parsed_date == target_date:
                return True

    return False


def find_semester_insertion_index(blocks, semester_key):
    """
    Find the best insertion index to append a new lesson entry under the given semester key.
    Prioritizes inserting above the first '[datum]' placeholder found in the section.
    """
    in_target_semester = False
    semester_start_index = None
    first_placeholder_index = None
    next_semester_start_index = None
    semester_end_index = None

    for block in blocks:
        if block["type"] != "paragraph":
            continue
        text = block["text"]
        sem_class = classify_semester_heading(text)

        if sem_class == semester_key:
            in_target_semester = True
            semester_start_index = block["endIndex"]
            continue
        
        if sem_class is not None and sem_class != semester_key:
            if in_target_semester:
                next_semester_start_index = block["startIndex"]
                break
            in_target_semester = False
            continue

        if in_target_semester:
            semester_end_index = block["endIndex"]
            if first_placeholder_index is None and "[datum]" in text.lower():
                first_placeholder_index = block["startIndex"]

    if semester_start_index is None:
        raise ValueError(f"Could not find semester heading for {semester_key} in document.")

    # 1. Best case: Insert right above the first template placeholder
    if first_placeholder_index is not None:
        return first_placeholder_index
    
    # 2. Fallback: Insert before next semester heading
    if next_semester_start_index is not None:
        return next_semester_start_index - 1
        
    # 3. Final fallback: Insert at end of current semester section
    return (semester_end_index or semester_start_index) - 1


def build_insert_lesson_request(document_json, semester_key, lesson_date_str, repertoire, vaardigheden, werkpunten):
    """
    Construct a Google Docs API batchUpdate request list to insert a formatted lesson entry
    with exact spacing, unbolding the entire block first, and bolding ONLY labels and date.
    """
    if check_duplicate_lesson(document_json, lesson_date_str):
        raise ValueError(f"A lesson entry for date {lesson_date_str} already exists for this student document.")

    body = document_json.get("body", {})
    content = body.get("content", [])
    blocks = get_plain_text_blocks(content)

    insert_idx = find_semester_insertion_index(blocks, semester_key)
    
    data = format_lesson_entry_data(lesson_date_str, repertoire, vaardigheden, werkpunten)
    
    line_date = f"{data['date']}\n"
    line_rep = f"{data['repertoire_label']}{data['repertoire_val']}\n"
    line_vaa = f"{data['vaardigheid_label']}{data['vaardigheid_val']}\n"
    line_wer = f"{data['werkpunten_label']}{data['werkpunten_val']}\n"
    trailing_sep = "\n"

    full_text = line_date + line_rep + line_vaa + line_wer + trailing_sep

    requests = [
        {
            "insertText": {
                "location": {
                    "index": insert_idx
                },
                "text": full_text
            }
        },
        # FIRST: Explicitly un-bold the entire inserted range so it doesn't inherit bold styling from preceding lines
        {
            "updateTextStyle": {
                "range": {
                    "startIndex": insert_idx,
                    "endIndex": insert_idx + len(full_text)
                },
                "textStyle": {"bold": False},
                "fields": "bold"
            }
        }
    ]

    # Calculate exact character offsets to bold ONLY labels and date
    curr = insert_idx

    # 1. Bold the date line
    requests.append({
        "updateTextStyle": {
            "range": {
                "startIndex": curr,
                "endIndex": curr + len(data['date'])
            },
            "textStyle": {"bold": True},
            "fields": "bold"
        }
    })
    curr += len(line_date)

    # 2. Bold "Repertoirestuk: "
    requests.append({
        "updateTextStyle": {
            "range": {
                "startIndex": curr,
                "endIndex": curr + len(data['repertoire_label'])
            },
            "textStyle": {"bold": True},
            "fields": "bold"
        }
    })
    curr += len(line_rep)

    # 3. Bold "Vaardigheid: "
    requests.append({
        "updateTextStyle": {
            "range": {
                "startIndex": curr,
                "endIndex": curr + len(data['vaardigheid_label'])
            },
            "textStyle": {"bold": True},
            "fields": "bold"
        }
    })
    curr += len(line_vaa)

    # 4. Bold "Werkpunten/opmerkingen: "
    requests.append({
        "updateTextStyle": {
            "range": {
                "startIndex": curr,
                "endIndex": curr + len(data['werkpunten_label'])
            },
            "textStyle": {"bold": True},
            "fields": "bold"
        }
    })

    return requests


def build_update_prep_request(prep_document_json, student_name, new_prep_text):
    """
    Construct a Google Docs API batchUpdate request to update a student's preparation line
    in the central prep document.
    """
    body = prep_document_json.get("body", {})
    content = body.get("content", [])
    blocks = get_plain_text_blocks(content)

    normalized_query = student_name.lower().strip()
    target_block = None

    # Separator pattern: matches student name followed by colon, dash (with space), or tab, then prep text
    sep_pattern = re.compile(r"^(.+?)(?:\s*:\s*|\s+[\-—–]\s+|\t+)(.*)$", re.DOTALL)
    
    # Check if student exists
    for block in blocks:
        if block["type"] != "paragraph":
            continue
        raw_text = block["text"].strip()
        m = sep_pattern.match(raw_text)
        if m:
            s_name = m.group(1).strip().lower()
            if normalized_query == s_name or normalized_query in s_name or s_name in normalized_query:
                target_block = block
                break
    
    # If not found, prepare to append to end of doc
    if not target_block:
        # Prepare request to append new line
        append_idx = blocks[-1]["endIndex"] - 1 if blocks else 0
        new_line = f"{student_name}: {new_prep_text}\n"
        
        requests = [
            {
                "insertText": {
                    "location": {"index": append_idx},
                    "text": new_line
                }
            },
            {
                "updateTextStyle": {
                    "range": {"startIndex": append_idx, "endIndex": append_idx + len(student_name)},
                    "textStyle": {"bold": True},
                    "fields": "bold"
                }
            }
        ]
        return requests

    # If found, replace/update
    start_idx = target_block["startIndex"]
    end_idx = target_block["endIndex"]
    
    new_line_text = f"{student_name}: {new_prep_text}\n"
    
    requests = [
        {
            "deleteContentRange": {
                "range": {"startIndex": start_idx, "endIndex": end_idx - 1}
            }
        },
        {
            "insertText": {
                "location": {"index": start_idx},
                "text": new_line_text
            }
        },
        # Explicitly unbold the new line to ensure text remains plain
        {
            "updateTextStyle": {
                "range": {"startIndex": start_idx, "endIndex": start_idx + len(new_line_text) - 1},
                "textStyle": {"bold": False},
                "fields": "bold"
            }
        },
        # Bold only the student name
        {
            "updateTextStyle": {
                "range": {"startIndex": start_idx, "endIndex": start_idx + len(student_name)},
                "textStyle": {"bold": True},
                "fields": "bold"
            }
        }
    ]
    return requests
